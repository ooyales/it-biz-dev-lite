#!/usr/bin/env python3
"""
Federal Contracting AI Assistant - Integrated System with Competitive Intelligence
Main orchestration script with FPDS and USAspending intelligence built-in
"""

import os
import sys
import json
import yaml
import logging
from datetime import datetime
from pathlib import Path
import argparse

# Import our modules
from sam_scout import SAMOpportunityScout
from claude_agents_integrated import AgentOrchestrator
from competitive_intel_agent import CompetitiveIntelligenceAgent, generate_competitive_intelligence_report
from typing import Dict, Any, List


class FedContractingAIIntegrated:
    """Main orchestrator with competitive intelligence built-in"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config = self._load_config(config_path)
        self._setup_logging()
        
        # Initialize components
        self.sam_scout = SAMOpportunityScout(config_path)
        self.agent_orchestrator = AgentOrchestrator(config_path)
        self.competitive_intel = CompetitiveIntelligenceAgent(self.config)
        
        self.logger = logging.getLogger(__name__)
    
    def _load_config(self, config_path: str):
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def _setup_logging(self):
        log_dir = Path(self.config['logging']['file_path']).parent
        log_dir.mkdir(parents=True, exist_ok=True)
        
        logging.basicConfig(
            level=self.config['logging']['level'],
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.config['logging']['file_path']),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def run_full_pipeline(self, days_back: int = None, competitive_intel: bool = True):
        """
        Run the complete pipeline with competitive intelligence
        
        Args:
            days_back: Number of days to look back (uses config default if None)
            competitive_intel: Whether to include competitive intelligence
        """
        self.logger.info("=" * 80)
        self.logger.info("Federal Contracting AI Assistant - INTEGRATED SYSTEM")
        self.logger.info("With Competitive Intelligence: " + ("ENABLED" if competitive_intel else "DISABLED"))
        self.logger.info("=" * 80)
        
        # Step 1: Search SAM.gov
        self.logger.info("\n[1/5] Searching SAM.gov for opportunities...")
        opportunities = self.sam_scout.search_opportunities(days_back)
        
        if not opportunities:
            self.logger.info("No opportunities found. Pipeline complete.")
            return {
                'opportunities_found': 0,
                'opportunities_analyzed': 0,
                'high_priority': 0
            }
        
        # Save opportunities
        opp_file = self.sam_scout.save_opportunities(opportunities)
        summary_file = self.sam_scout.generate_summary_report(opportunities)
        
        self.logger.info(f"Found {len(opportunities)} opportunities")
        
        # Step 2: Gather competitive intelligence (if enabled)
        self.logger.info(f"\n[2/5] Gathering competitive intelligence...")
        competitive_data = {}
        
        if competitive_intel:
            for i, opp in enumerate(opportunities, 1):
                notice_id = opp.get('noticeId', f'unknown_{i}')
                
                # Check if we should run intel for this opportunity
                if self._should_run_intel(opp):
                    self.logger.info(f"  Running intel {i}/{len(opportunities)}: {notice_id}")
                    
                    try:
                        comp_intel = self.competitive_intel.analyze_opportunity_competitiveness(opp)
                        competitive_data[notice_id] = comp_intel
                        
                        # Save individual competitive intelligence report
                        self._save_competitive_report(comp_intel)
                        
                    except Exception as e:
                        self.logger.error(f"  Error gathering intel for {notice_id}: {e}")
                else:
                    self.logger.debug(f"  Skipping intel for {notice_id} (below threshold)")
        else:
            self.logger.info("  Competitive intelligence disabled - skipping")
        
        # Step 3: AI analysis with competitive context
        self.logger.info(f"\n[3/5] Analyzing opportunities with AI agents...")
        analysis_results = []
        
        for i, opp in enumerate(opportunities, 1):
            notice_id = opp.get('noticeId', f'unknown_{i}')
            self.logger.info(f"  Processing {i}/{len(opportunities)}: {opp.get('title', 'Unknown')[:60]}...")
            
            try:
                # Get competitive intel for this opportunity
                comp_intel = competitive_data.get(notice_id)
                
                # Run AI analysis with competitive context
                result = self.agent_orchestrator.process_opportunity(
                    opp, 
                    competitive_intel=comp_intel
                )
                
                analysis_results.append(result)
                
            except Exception as e:
                self.logger.error(f"  Error processing opportunity: {e}")
                continue
        
        # Step 4: Generate prioritized reports
        self.logger.info("\n[4/5] Generating reports...")
        action_report = self._generate_action_report(analysis_results)
        intel_summary = self._generate_intel_summary(competitive_data)
        
        # Step 5: Send notifications
        self.logger.info("\n[5/5] Sending notifications...")
        self._send_notifications(analysis_results, action_report)
        
        # Summary
        high_priority = [r for r in analysis_results 
                        if r.get('analysis', {}).get('fit_score', 0) >= 7]
        
        with_intel = [r for r in analysis_results if r.get('competitive_intelligence')]
        
        summary = {
            'opportunities_found': len(opportunities),
            'opportunities_analyzed': len(analysis_results),
            'with_competitive_intel': len(with_intel),
            'high_priority': len(high_priority),
            'summary_report': summary_file,
            'action_report': action_report,
            'intel_summary': intel_summary,
            'opportunities_file': opp_file
        }
        
        self.logger.info("\n" + "=" * 80)
        self.logger.info("Pipeline Complete!")
        self.logger.info(f"  Opportunities Found: {summary['opportunities_found']}")
        self.logger.info(f"  Analyzed: {summary['opportunities_analyzed']}")
        self.logger.info(f"  With Competitive Intel: {summary['with_competitive_intel']}")
        self.logger.info(f"  High Priority (≥7): {summary['high_priority']}")
        self.logger.info(f"\nReports Generated:")
        self.logger.info(f"  Action Report: {summary['action_report']}")
        self.logger.info(f"  Intel Summary: {summary['intel_summary']}")
        self.logger.info("=" * 80)
        
        return summary
    
    def _should_run_intel(self, opportunity: Dict[str, Any]) -> bool:
        """Determine if competitive intelligence should be run for this opportunity"""
        
        # Check if competitive intel is enabled
        comp_config = self.config.get('competitive_intelligence', {})
        if not comp_config.get('enabled', True):
            return False
        
        # Check value threshold
        min_value = comp_config.get('triggers', {}).get('min_value', 0)
        if min_value > 0:
            estimated_value = self._estimate_opportunity_value(opportunity)
            if estimated_value < min_value:
                return False
        
        # Check NAICS filter
        naics_filter = comp_config.get('triggers', {}).get('naics_codes', [])
        if naics_filter:
            opp_naics = opportunity.get('naicsCode', '')
            if opp_naics not in naics_filter:
                return False
        
        return True
    
    def _estimate_opportunity_value(self, opportunity: Dict[str, Any]) -> float:
        """Estimate opportunity value from available data"""
        
        # Try to get award amount
        award = opportunity.get('award', {})
        if isinstance(award, dict):
            amount = award.get('amount')
            if amount:
                try:
                    return float(amount)
                except (ValueError, TypeError):
                    pass
        
        # Try description for dollar amounts (simplified)
        description = opportunity.get('description', '').lower()
        
        # Look for common patterns like "$5M" or "$5,000,000"
        import re
        patterns = [
            r'\$(\d+)m',  # $5M format
            r'\$(\d+) million',  # $5 million format
            r'\$(\d{1,3}(?:,\d{3})*)',  # $5,000,000 format
        ]
        
        for pattern in patterns:
            match = re.search(pattern, description)
            if match:
                value_str = match.group(1).replace(',', '')
                try:
                    value = float(value_str)
                    if 'm' in pattern or 'million' in pattern:
                        value *= 1000000
                    return value
                except ValueError:
                    continue
        
        # Default: return 0 (will run intel if no minimum is set)
        return 0
    
    def _save_competitive_report(self, comp_intel: Dict[str, Any]):
        """Save individual competitive intelligence report"""
        notice_id = comp_intel.get('opportunity_id', 'unknown')
        
        # Generate text report
        report = generate_competitive_intelligence_report(comp_intel)
        
        # Save to file
        report_path = os.path.join(
            self.config['storage']['analysis_path'],
            f"{notice_id}_competitive_intel.txt"
        )
        
        with open(report_path, 'w') as f:
            f.write(report)
        
        self.logger.debug(f"  Saved competitive intel report: {report_path}")
    
    def _generate_action_report(self, analysis_results: list) -> str:
        """Generate prioritized action report"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_path = os.path.join(
            self.config['storage']['reports_path'],
            f"action_report_{timestamp}.txt"
        )
        
        # Sort by fit score
        sorted_results = sorted(
            analysis_results,
            key=lambda x: x.get('analysis', {}).get('fit_score', 0),
            reverse=True
        )
        
        with open(report_path, 'w') as f:
            f.write("=" * 80 + "\n")
            f.write("FEDERAL CONTRACTING OPPORTUNITY ACTION REPORT\n")
            f.write("WITH INTEGRATED COMPETITIVE INTELLIGENCE\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n\n")
            
            # High priority section
            high_priority = [r for r in sorted_results 
                           if r.get('analysis', {}).get('fit_score', 0) >= 7]
            
            if high_priority:
                f.write("🔥 HIGH PRIORITY - IMMEDIATE ACTION REQUIRED\n")
                f.write("=" * 80 + "\n\n")
                
                for result in high_priority:
                    self._write_opportunity_summary(f, result, detailed=True)
            
            # Medium priority section
            medium_priority = [r for r in sorted_results 
                             if 4 <= r.get('analysis', {}).get('fit_score', 0) < 7]
            
            if medium_priority:
                f.write("\n\n⚠️  MEDIUM PRIORITY - MONITOR\n")
                f.write("=" * 80 + "\n\n")
                
                for result in medium_priority:
                    self._write_opportunity_summary(f, result, detailed=False)
            
            # Low priority section
            low_priority = [r for r in sorted_results 
                          if r.get('analysis', {}).get('fit_score', 0) < 4]
            
            if low_priority:
                f.write("\n\n📋 LOW PRIORITY - PASS OR RECONSIDER LATER\n")
                f.write("=" * 80 + "\n")
                f.write(f"Total: {len(low_priority)} opportunities\n")
                f.write("(Details available in individual analysis files)\n")
        
        return report_path
    
    def _write_opportunity_summary(self, f, result: dict, detailed: bool = True):
        """Write opportunity summary with competitive intelligence to report file"""
        analysis = result.get('analysis', {})
        capability = result.get('capability_match', {})
        comp_intel = result.get('competitive_intelligence', {})
        
        f.write(f"\n{'─' * 80}\n")
        f.write(f"Title: {result.get('title', 'Unknown')}\n")
        f.write(f"Notice ID: {result.get('notice_id')}\n")
        f.write(f"Fit Score: {analysis.get('fit_score', 'N/A')}/10\n")
        f.write(f"Recommendation: {analysis.get('recommendation', 'N/A')}\n")
        
        # Add win probability if available
        if comp_intel:
            assessment = comp_intel.get('competitive_assessment', {})
            win_prob = assessment.get('win_probability')
            if win_prob is not None:
                f.write(f"Win Probability: {win_prob}%\n")
        
        opp_data = result.get('opportunity_data', {})
        f.write(f"Type: {opp_data.get('type', 'N/A')}\n")
        f.write(f"Response Deadline: {opp_data.get('responseDeadLine', 'N/A')}\n")
        f.write(f"SAM.gov URL: https://sam.gov/opp/{result.get('notice_id')}\n")
        
        if detailed:
            f.write(f"\nRationale: {analysis.get('rationale', 'N/A')}\n")
            
            # Competitive intelligence section
            if comp_intel:
                f.write("\n--- COMPETITIVE INTELLIGENCE ---\n")
                
                # Incumbent
                incumbent = comp_intel.get('incumbent')
                if incumbent and incumbent.get('contractor_name'):
                    f.write(f"\nIncumbent: {incumbent.get('contractor_name')}\n")
                    incumbent_profile = comp_intel.get('incumbent_profile', {})
                    if incumbent_profile.get('total_contract_value_3yr'):
                        f.write(f"  3-Yr Revenue: ${incumbent_profile['total_contract_value_3yr']:,.0f}\n")
                
                # Pricing
                pricing = comp_intel.get('pricing_intelligence', {})
                if pricing.get('average'):
                    f.write(f"\nPricing Intelligence:\n")
                    f.write(f"  Market Average: ${pricing['average']:,.0f}\n")
                    f.write(f"  Range: ${pricing['min']:,.0f} - ${pricing['max']:,.0f}\n")
                    if 'trend' in pricing:
                        trend = pricing['trend']
                        f.write(f"  Trend: {trend['direction'].upper()} ({trend['percent_change']:+.1f}%)\n")
                
                # Market trends
                trends = comp_intel.get('market_trends', {})
                if trends.get('trend_direction'):
                    f.write(f"\nMarket Trend: {trends['trend_direction'].upper()}\n")
                    if trends.get('growth_rate_percent'):
                        f.write(f"  Growth Rate: {trends['growth_rate_percent']:+.1f}%\n")
                
                # Competitive assessment
                assessment = comp_intel.get('competitive_assessment', {})
                if assessment:
                    f.write(f"\nCompetitive Position:\n")
                    f.write(f"  Incumbent Strength: {assessment.get('incumbent_strength', 'unknown').upper()}\n")
                    f.write(f"  Strategy: {assessment.get('recommended_strategy', 'N/A')}\n")
            
            # Capability match
            if capability:
                f.write(f"\nCapability Coverage: {capability.get('coverage_score', 'N/A')}%\n")
                f.write(f"Recommended Team Size: {capability.get('team_size_estimate', 'N/A')}\n")
                
                gaps = capability.get('gaps', [])
                if gaps:
                    f.write(f"\nCapability Gaps:\n")
                    for gap in gaps[:3]:
                        f.write(f"  ⚠ {gap}\n")
                    
                    mitigation = capability.get('gap_mitigation', [])
                    if mitigation:
                        f.write(f"\nMitigation:\n")
                        for m in mitigation[:3]:
                            f.write(f"  → {m}\n")
            
            # Original strengths and concerns
            strengths = analysis.get('strengths', [])
            if strengths:
                f.write("\nStrengths:\n")
                for strength in strengths:
                    f.write(f"  ✓ {strength}\n")
            
            concerns = analysis.get('concerns', [])
            if concerns:
                f.write("\nConcerns:\n")
                for concern in concerns:
                    f.write(f"  ⚠ {concern}\n")
            
            # Next actions
            next_actions = analysis.get('next_actions', [])
            if next_actions:
                f.write("\nNext Actions:\n")
                for action in next_actions:
                    f.write(f"  → {action}\n")
            
            # Check if RFI was drafted
            if 'rfi_draft' in result:
                rfi_file = os.path.join(
                    self.config['storage']['analysis_path'],
                    f"{result.get('notice_id')}_rfi_draft.txt"
                )
                with open(rfi_file, 'w') as rfi_f:
                    rfi_f.write(result['rfi_draft'])
                f.write(f"\n✓ RFI Draft: {rfi_file}\n")
    
    def _generate_intel_summary(self, competitive_data: Dict[str, Dict]) -> str:
        """Generate summary of competitive intelligence gathered"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        summary_path = os.path.join(
            self.config['storage']['reports_path'],
            f"competitive_intel_summary_{timestamp}.txt"
        )
        
        with open(summary_path, 'w') as f:
            f.write("=" * 80 + "\n")
            f.write("COMPETITIVE INTELLIGENCE SUMMARY\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n\n")
            
            f.write(f"Total Opportunities with Intel: {len(competitive_data)}\n\n")
            
            if competitive_data:
                # Count incumbents found
                incumbents_found = sum(
                    1 for intel in competitive_data.values()
                    if intel.get('incumbent') and intel['incumbent'].get('contractor_name')
                )
                
                f.write(f"Incumbents Identified: {incumbents_found}\n")
                f.write(f"Market Trends Analyzed: {len(competitive_data)}\n\n")
                
                # List top competitors found
                competitors = {}
                for intel in competitive_data.values():
                    incumbent = intel.get('incumbent', {})
                    name = incumbent.get('contractor_name')
                    if name:
                        competitors[name] = competitors.get(name, 0) + 1
                
                if competitors:
                    f.write("Top Competitors Identified:\n")
                    top_competitors = sorted(competitors.items(), key=lambda x: x[1], reverse=True)
                    for name, count in top_competitors[:10]:
                        f.write(f"  • {name}: {count} opportunity/opportunities\n")
        
        return summary_path
    
    def _send_notifications(self, analysis_results: list, report_file: str):
        """Send notifications via configured channels"""
        high_priority = [r for r in analysis_results 
                        if r.get('analysis', {}).get('fit_score', 0) >= 7]
        
        if not high_priority:
            self.logger.info("No high-priority opportunities, skipping notifications")
            return
        
        # Email notification
        if self.config['notifications']['email']['enabled']:
            self._send_email_notification(high_priority, report_file)
        
        # Slack notification
        if self.config['notifications']['slack']['enabled']:
            self._send_slack_notification(high_priority, report_file)
    
    def _send_email_notification(self, opportunities: list, report_file: str):
        """Send email notification"""
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            email_config = self.config['notifications']['email']
            
            msg = MIMEMultipart()
            msg['From'] = email_config['from_address']
            msg['To'] = ', '.join(email_config['to_addresses'])
            msg['Subject'] = f"🔥 {len(opportunities)} High-Priority Federal Contracting Opportunities"
            
            body = f"""Federal Contracting AI Assistant - Competitive Intelligence Alert

{len(opportunities)} high-priority opportunities identified with competitive analysis:

"""
            for opp in opportunities[:5]:
                comp_intel = opp.get('competitive_intelligence', {})
                assessment = comp_intel.get('competitive_assessment', {})
                
                body += f"\n• {opp.get('title')} (Score: {opp.get('analysis', {}).get('fit_score')}/10"
                if assessment.get('win_probability'):
                    body += f", Win Prob: {assessment['win_probability']}%"
                body += ")\n"
                body += f"  {opp.get('analysis', {}).get('recommendation')}\n"
                
                if comp_intel.get('incumbent'):
                    incumbent = comp_intel['incumbent'].get('contractor_name', 'Unknown')
                    body += f"  Incumbent: {incumbent}\n"
            
            body += f"\n\nFull report: {report_file}\n"
            
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(email_config['smtp_server'], email_config['smtp_port'])
            server.starttls()
            server.login(email_config['from_address'], email_config['password'])
            server.send_message(msg)
            server.quit()
            
            self.logger.info("Email notification sent")
            
        except Exception as e:
            self.logger.error(f"Failed to send email: {e}")
    
    def _send_slack_notification(self, opportunities: list, report_file: str):
        """Send Slack notification"""
        try:
            import requests
            
            webhook_url = self.config['notifications']['slack']['webhook_url']
            
            message = f"🔥 *{len(opportunities)} High-Priority Opportunities Found*\n"
            message += "_With Competitive Intelligence Analysis_\n\n"
            
            for opp in opportunities[:3]:
                score = opp.get('analysis', {}).get('fit_score')
                title = opp.get('title')
                notice_id = opp.get('notice_id')
                
                comp_intel = opp.get('competitive_intelligence', {})
                assessment = comp_intel.get('competitive_assessment', {})
                win_prob = assessment.get('win_probability')
                
                message += f"• *{title}* (Score: {score}/10"
                if win_prob:
                    message += f", Win: {win_prob}%"
                message += ")\n"
                
                if comp_intel.get('incumbent'):
                    incumbent = comp_intel['incumbent'].get('contractor_name', 'TBD')
                    message += f"  Incumbent: {incumbent}\n"
                
                message += f"  <https://sam.gov/opp/{notice_id}|View on SAM.gov>\n\n"
            
            message += f"\nFull report: `{report_file}`"
            
            payload = {'text': message}
            requests.post(webhook_url, json=payload)
            
            self.logger.info("Slack notification sent")
            
        except Exception as e:
            self.logger.error(f"Failed to send Slack notification: {e}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Federal Contracting AI Assistant with Competitive Intelligence'
    )
    parser.add_argument(
        '--config',
        default='config.yaml',
        help='Path to configuration file'
    )
    parser.add_argument(
        '--days',
        type=int,
        help='Number of days to look back (overrides config)'
    )
    parser.add_argument(
        '--no-intel',
        action='store_true',
        help='Disable competitive intelligence (faster but less insight)'
    )
    parser.add_argument(
        '--test',
        action='store_true',
        help='Test mode: search only, no AI analysis'
    )
    
    args = parser.parse_args()
    
    # Initialize system
    system = FedContractingAIIntegrated(args.config)
    
    if args.test:
        # Test mode: just search SAM.gov
        print("Running in TEST mode (search only)...")
        opportunities = system.sam_scout.search_opportunities(args.days)
        if opportunities:
            system.sam_scout.save_opportunities(opportunities)
            system.sam_scout.generate_summary_report(opportunities)
            print(f"✓ Found {len(opportunities)} opportunities")
    else:
        # Full pipeline
        competitive_intel = not args.no_intel
        summary = system.run_full_pipeline(args.days, competitive_intel)
        
        # Exit with appropriate code
        if summary['high_priority'] > 0:
            sys.exit(0)
        else:
            sys.exit(1)


if __name__ == "__main__":
    main()
