#!/usr/bin/env python3
"""
Federal Contracting AI Assistant - Main Orchestration Script
Coordinates SAM.gov monitoring and AI analysis workflow
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
from claude_agents import AgentOrchestrator


class FedContractingAI:
    """Main orchestrator for the federal contracting AI system"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config = self._load_config(config_path)
        self._setup_logging()
        
        # Initialize components
        self.sam_scout = SAMOpportunityScout(config_path)
        self.agent_orchestrator = AgentOrchestrator(config_path)
        
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
    
    def run_full_pipeline(self, days_back: int = None):
        """
        Run the complete pipeline: search SAM.gov and analyze opportunities
        
        Args:
            days_back: Number of days to look back (uses config default if None)
        """
        self.logger.info("=" * 80)
        self.logger.info("Starting Federal Contracting AI Assistant Pipeline")
        self.logger.info("=" * 80)
        
        # Step 1: Search SAM.gov
        self.logger.info("\n[1/4] Searching SAM.gov for opportunities...")
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
        
        # Step 2: Analyze with AI agents
        self.logger.info("\n[2/4] Analyzing opportunities with AI agents...")
        analysis_results = []
        
        for i, opp in enumerate(opportunities, 1):
            self.logger.info(f"Processing {i}/{len(opportunities)}: {opp.get('title', 'Unknown')[:60]}...")
            
            try:
                result = self.agent_orchestrator.process_opportunity(opp)
                analysis_results.append(result)
            except Exception as e:
                self.logger.error(f"Error processing opportunity: {e}")
                continue
        
        # Step 3: Generate prioritized report
        self.logger.info("\n[3/4] Generating prioritized action report...")
        report_file = self._generate_action_report(analysis_results)
        
        # Step 4: Send notifications if configured
        self.logger.info("\n[4/4] Sending notifications...")
        self._send_notifications(analysis_results, report_file)
        
        # Summary
        high_priority = [r for r in analysis_results 
                        if r.get('analysis', {}).get('fit_score', 0) >= 7]
        
        summary = {
            'opportunities_found': len(opportunities),
            'opportunities_analyzed': len(analysis_results),
            'high_priority': len(high_priority),
            'summary_report': summary_file,
            'action_report': report_file,
            'opportunities_file': opp_file
        }
        
        self.logger.info("\n" + "=" * 80)
        self.logger.info("Pipeline Complete!")
        self.logger.info(f"  Opportunities Found: {summary['opportunities_found']}")
        self.logger.info(f"  Analyzed: {summary['opportunities_analyzed']}")
        self.logger.info(f"  High Priority (≥7): {summary['high_priority']}")
        self.logger.info(f"  Action Report: {summary['action_report']}")
        self.logger.info("=" * 80)
        
        return summary
    
    def _generate_action_report(self, analysis_results: list) -> str:
        """Generate a prioritized action report"""
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
        """Write opportunity summary to report file"""
        analysis = result.get('analysis', {})
        capability = result.get('capability_match', {})
        
        f.write(f"\n{'─' * 80}\n")
        f.write(f"Title: {result.get('title', 'Unknown')}\n")
        f.write(f"Notice ID: {result.get('notice_id')}\n")
        f.write(f"Fit Score: {analysis.get('fit_score', 'N/A')}/10\n")
        f.write(f"Recommendation: {analysis.get('recommendation', 'N/A')}\n")
        
        opp_data = result.get('opportunity_data', {})
        f.write(f"Type: {opp_data.get('type', 'N/A')}\n")
        f.write(f"Response Deadline: {opp_data.get('responseDeadLine', 'N/A')}\n")
        f.write(f"SAM.gov URL: https://sam.gov/opp/{result.get('notice_id')}\n")
        
        if detailed:
            f.write(f"\nRationale: {analysis.get('rationale', 'N/A')}\n")
            
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
            
            if capability:
                f.write(f"\nCapability Coverage: {capability.get('coverage_score', 'N/A')}%\n")
                f.write(f"Recommended Team Size: {capability.get('team_size_estimate', 'N/A')}\n")
            
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
            
            body = f"""Federal Contracting AI Assistant Alert

{len(opportunities)} high-priority opportunities have been identified:

"""
            for opp in opportunities[:5]:  # Top 5
                body += f"\n• {opp.get('title')} (Score: {opp.get('analysis', {}).get('fit_score')}/10)\n"
                body += f"  {opp.get('analysis', {}).get('recommendation')}\n"
            
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
            
            message = f"🔥 *{len(opportunities)} High-Priority Opportunities Found*\n\n"
            
            for opp in opportunities[:3]:  # Top 3
                score = opp.get('analysis', {}).get('fit_score')
                title = opp.get('title')
                notice_id = opp.get('notice_id')
                
                message += f"• *{title}* (Score: {score}/10)\n"
                message += f"  <https://sam.gov/opp/{notice_id}|View on SAM.gov>\n\n"
            
            message += f"\nFull report available at: `{report_file}`"
            
            payload = {'text': message}
            requests.post(webhook_url, json=payload)
            
            self.logger.info("Slack notification sent")
            
        except Exception as e:
            self.logger.error(f"Failed to send Slack notification: {e}")


def main():
    """Main entry point with command-line arguments"""
    parser = argparse.ArgumentParser(
        description='Federal Contracting AI Assistant'
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
        '--test',
        action='store_true',
        help='Test mode: search only, no AI analysis'
    )
    
    args = parser.parse_args()
    
    # Initialize system
    system = FedContractingAI(args.config)
    
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
        summary = system.run_full_pipeline(args.days)
        
        # Exit with appropriate code
        if summary['high_priority'] > 0:
            sys.exit(0)  # Success with high-priority opportunities
        else:
            sys.exit(1)  # No high-priority opportunities


if __name__ == "__main__":
    main()
