#!/usr/bin/env python3
"""
Opportunity Scout Agent
Monitors SAM.gov and scores opportunities based on your relationships and capabilities

Features:
- Daily monitoring of SAM.gov
- Contact matching via knowledge graph
- Opportunity scoring algorithm
- Warm intro path detection
- Daily intelligence reports
"""

import sys
sys.path.append('..')

from graph.neo4j_client import KnowledgeGraphClient, generate_org_id
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import os
from pathlib import Path
import json

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ANSI colors
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*70}")
    print(f"{text}")
    print(f"{'='*70}{Colors.END}\n")

def print_success(text):
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")

def print_warning(text):
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.END}")

def print_info(text):
    print(f"{Colors.CYAN}→ {text}{Colors.END}")


class OpportunityScout:
    """
    Intelligent opportunity scout that uses your relationship network
    to identify high-probability wins
    """
    
    def __init__(self):
        """Initialize scout with connections to SAM.gov and Neo4j"""
        
        print_info("Initializing Opportunity Scout Agent...")
        
        # Load config
        self.sam_api_key = os.getenv('SAM_API_KEY')
        neo4j_password = os.getenv('NEO4J_PASSWORD')
        
        if not self.sam_api_key or not neo4j_password:
            raise ValueError("Missing SAM_API_KEY or NEO4J_PASSWORD in environment")
        
        # Connect to knowledge graph
        self.kg = KnowledgeGraphClient(
            uri=os.getenv('NEO4J_URI', 'bolt://localhost:7687'),
            user=os.getenv('NEO4J_USER', 'neo4j'),
            password=neo4j_password
        )
        print_success("Connected to knowledge graph")
        
        # Configuration
        self.naics_codes = os.getenv('NAICS_CODES', '541512,541511,541519').split(',')
        self.company_size = 'small'  # small, medium, large
        self.min_contract_value = 100000  # $100K minimum
        self.max_contract_value = 25000000  # $25M maximum for small business
        
        print_success("Opportunity Scout ready")
    
    def fetch_opportunities(self, days_back: int = 7) -> List[Dict]:
        """Fetch recent opportunities from SAM.gov"""
        
        print_info(f"Fetching opportunities from last {days_back} days...")
        
        from_date = (datetime.now() - timedelta(days=days_back)).strftime('%m/%d/%Y')
        to_date = datetime.now().strftime('%m/%d/%Y')
        
        url = "https://api.sam.gov/opportunities/v2/search"
        opportunities = []
        
        for naics in self.naics_codes:
            try:
                params = {
                    'api_key': self.sam_api_key,
                    'postedFrom': from_date,
                    'postedTo': to_date,
                    'naicsCode': naics.strip(),
                    'limit': 100
                }
                
                response = requests.get(url, params=params, timeout=30)
                response.raise_for_status()
                
                data = response.json()
                opps = data.get('opportunitiesData', [])
                opportunities.extend(opps)
                
                print_info(f"  NAICS {naics}: {len(opps)} opportunities")
                
            except Exception as e:
                print_warning(f"Error fetching NAICS {naics}: {e}")
        
        print_success(f"Fetched {len(opportunities)} total opportunities")
        return opportunities
    
    def check_contacts_at_agency(self, agency_name: str) -> Dict:
        """Check if we have contacts at this agency"""
        
        # Import the agency mapper
        try:
            from agency_mapper import get_contacts_for_agency
            return get_contacts_for_agency(self.kg, agency_name)
        except ImportError:
            # Fallback to old method if mapper not available
            from graph.neo4j_client import generate_org_id
            
            # Try exact match and fuzzy match
            org_id = generate_org_id(agency_name)
            
            # Query for contacts at this organization
            with self.kg.driver.session(database="contactsgraphdb") as session:
                query = """
                MATCH (p:Person)-[:WORKS_AT]->(o:Organization)
                WHERE o.id = $org_id OR o.name CONTAINS $agency_name
                RETURN p.name as name, 
                       p.title as title, 
                       p.role_type as role_type,
                       p.influence_level as influence_level,
                       p.email as email,
                       o.name as organization
                """
                
                result = session.run(query, org_id=org_id, agency_name=agency_name[:20])
                contacts = [dict(record) for record in result]
            
            # Categorize contacts
            decision_makers = [c for c in contacts if c.get('role_type') == 'Decision Maker']
            technical_leads = [c for c in contacts if c.get('role_type') == 'Technical Lead']
            executives = [c for c in contacts if c.get('role_type') == 'Executive']
            influencers = [c for c in contacts if c.get('role_type') == 'Influencer']
            
            return {
                'total_contacts': len(contacts),
                'decision_makers': decision_makers,
                'technical_leads': technical_leads,
                'executives': executives,
                'influencers': influencers,
                'all_contacts': contacts
            }
    
    def score_opportunity(self, opp: Dict) -> Dict:
        """
        Score opportunity based on multiple factors
        
        Scoring Algorithm:
        - Base score: 35 points (industry average win rate)
        - Relationships: +0-40 points
        - Contract size fit: +0-10 points
        - Set-aside match: +0-10 points
        - NAICS match: +0-5 points
        
        Total: 0-100 points
        """
        
        score_breakdown = {
            'base_score': 35,
            'relationship_score': 0,
            'size_fit_score': 0,
            'setaside_score': 0,
            'naics_score': 0,
            'total_score': 0,
            'win_probability': 0,
            'recommendation': '',
            'reasoning': []
        }
        
        # Extract opportunity details
        agency = opp.get('organizationName', '')
        notice_id = opp.get('noticeId', '')
        title = opp.get('title', '')
        
        # 1. Relationship Score (0-40 points)
        contacts = self.check_contacts_at_agency(agency)
        
        if contacts['decision_makers']:
            score_breakdown['relationship_score'] += 25
            score_breakdown['reasoning'].append(
                f"✓ {len(contacts['decision_makers'])} decision maker(s) at agency"
            )
        
        if contacts['technical_leads']:
            score_breakdown['relationship_score'] += 10
            score_breakdown['reasoning'].append(
                f"✓ {len(contacts['technical_leads'])} technical lead(s) at agency"
            )
        
        if contacts['executives']:
            score_breakdown['relationship_score'] += 5
            score_breakdown['reasoning'].append(
                f"✓ {len(contacts['executives'])} executive(s) at agency"
            )
        
        if contacts['total_contacts'] == 0:
            score_breakdown['reasoning'].append(
                "✗ No existing contacts at agency"
            )
        
        # 2. Contract Size Fit (0-10 points)
        # Try to extract contract value from description or use default range
        description = opp.get('description', '').lower()
        
        # Simple heuristic based on opportunity type
        if 'idiq' in description or 'gwac' in description:
            # Large contracts
            if self.company_size == 'small':
                score_breakdown['size_fit_score'] = 3
                score_breakdown['reasoning'].append("~ Large IDIQ/GWAC - may need teaming")
            else:
                score_breakdown['size_fit_score'] = 10
        else:
            # Assume good fit for small business
            score_breakdown['size_fit_score'] = 8
            score_breakdown['reasoning'].append("✓ Contract size likely appropriate")
        
        # 3. Set-Aside Score (0-10 points)
        setaside = opp.get('typeOfSetAside') or ''
        setaside_lower = setaside.lower() if setaside else ''
        
        if 'small business' in setaside_lower or 'total small business' in setaside_lower:
            score_breakdown['setaside_score'] = 10
            score_breakdown['reasoning'].append("✓ Small Business set-aside")
        elif '8(a)' in setaside_lower:
            score_breakdown['setaside_score'] = 10
            score_breakdown['reasoning'].append("✓ 8(a) set-aside")
        elif 'hubzone' in setaside_lower:
            score_breakdown['setaside_score'] = 10
            score_breakdown['reasoning'].append("✓ HUBZone set-aside")
        elif 'unrestricted' in setaside_lower or 'full and open' in setaside_lower:
            score_breakdown['setaside_score'] = 3
            score_breakdown['reasoning'].append("~ Full and open competition")
        elif not setaside_lower:
            score_breakdown['setaside_score'] = 3
            score_breakdown['reasoning'].append("~ Set-aside not specified")
        
        # 4. NAICS Match (0-5 points)
        opp_naics = opp.get('naicsCode', '')
        if opp_naics in self.naics_codes:
            score_breakdown['naics_score'] = 5
            score_breakdown['reasoning'].append(f"✓ Primary NAICS match: {opp_naics}")
        
        # Calculate total score
        score_breakdown['total_score'] = (
            score_breakdown['base_score'] +
            score_breakdown['relationship_score'] +
            score_breakdown['size_fit_score'] +
            score_breakdown['setaside_score'] +
            score_breakdown['naics_score']
        )
        
        # Calculate win probability
        score_breakdown['win_probability'] = min(score_breakdown['total_score'], 85)
        
        # Generate recommendation
        if score_breakdown['total_score'] >= 70:
            score_breakdown['recommendation'] = 'PURSUE - High Priority'
            score_breakdown['priority'] = 'HIGH'
        elif score_breakdown['total_score'] >= 55:
            score_breakdown['recommendation'] = 'REVIEW - Good Opportunity'
            score_breakdown['priority'] = 'MEDIUM'
        elif score_breakdown['total_score'] >= 40:
            score_breakdown['recommendation'] = 'MONITOR - Low Priority'
            score_breakdown['priority'] = 'LOW'
        else:
            score_breakdown['recommendation'] = 'PASS - Not Recommended'
            score_breakdown['priority'] = 'SKIP'
        
        # Add contact details
        score_breakdown['contacts'] = contacts
        
        return score_breakdown
    
    def generate_daily_report(self, opportunities: List[Dict], scores: List[Dict]) -> str:
        """Generate daily intelligence report"""
        
        # Sort by score
        scored_opps = list(zip(opportunities, scores))
        scored_opps.sort(key=lambda x: x[1]['total_score'], reverse=True)
        
        # Build report
        report_lines = []
        report_lines.append("="*70)
        report_lines.append("DAILY OPPORTUNITY INTELLIGENCE REPORT")
        report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        report_lines.append("="*70)
        report_lines.append("")
        
        # Summary statistics
        high_priority = sum(1 for _, s in scored_opps if s['priority'] == 'HIGH')
        medium_priority = sum(1 for _, s in scored_opps if s['priority'] == 'MEDIUM')
        low_priority = sum(1 for _, s in scored_opps if s['priority'] == 'LOW')
        
        report_lines.append("SUMMARY")
        report_lines.append("-" * 70)
        report_lines.append(f"Total Opportunities Analyzed: {len(opportunities)}")
        report_lines.append(f"High Priority (Pursue):       {high_priority}")
        report_lines.append(f"Medium Priority (Review):     {medium_priority}")
        report_lines.append(f"Low Priority (Monitor):       {low_priority}")
        report_lines.append("")
        
        # Top opportunities
        report_lines.append("TOP OPPORTUNITIES")
        report_lines.append("="*70)
        report_lines.append("")
        
        for i, (opp, score) in enumerate(scored_opps[:10], 1):
            report_lines.append(f"{i}. {opp.get('title', 'Untitled')[:60]}")
            report_lines.append(f"   Notice ID: {opp.get('noticeId', 'N/A')}")
            report_lines.append(f"   Agency: {opp.get('organizationName', 'N/A')}")
            report_lines.append(f"   Posted: {opp.get('postedDate', 'N/A')}")
            report_lines.append(f"   Response Deadline: {opp.get('responseDeadLine', 'N/A')}")
            report_lines.append(f"   Set-Aside: {opp.get('typeOfSetAside', 'N/A')}")
            report_lines.append("")
            report_lines.append(f"   SCORE: {score['total_score']}/100 (Win Probability: {score['win_probability']}%)")
            report_lines.append(f"   RECOMMENDATION: {score['recommendation']}")
            report_lines.append("")
            report_lines.append("   Score Breakdown:")
            report_lines.append(f"     Base Score:         {score['base_score']}")
            report_lines.append(f"     Relationships:      +{score['relationship_score']}")
            report_lines.append(f"     Contract Size Fit:  +{score['size_fit_score']}")
            report_lines.append(f"     Set-Aside Match:    +{score['setaside_score']}")
            report_lines.append(f"     NAICS Match:        +{score['naics_score']}")
            report_lines.append("")
            report_lines.append("   Analysis:")
            for reason in score['reasoning']:
                report_lines.append(f"     {reason}")
            report_lines.append("")
            
            # Show contacts
            if score['contacts']['total_contacts'] > 0:
                report_lines.append("   YOUR CONTACTS AT THIS AGENCY:")
                
                if score['contacts']['decision_makers']:
                    report_lines.append("     Decision Makers:")
                    for contact in score['contacts']['decision_makers'][:3]:
                        report_lines.append(f"       • {contact['name']} - {contact['title']}")
                        if contact.get('email'):
                            report_lines.append(f"         Email: {contact['email']}")
                
                if score['contacts']['technical_leads']:
                    report_lines.append("     Technical Leads:")
                    for contact in score['contacts']['technical_leads'][:3]:
                        report_lines.append(f"       • {contact['name']} - {contact['title']}")
                
                if score['contacts']['executives']:
                    report_lines.append("     Executives:")
                    for contact in score['contacts']['executives'][:2]:
                        report_lines.append(f"       • {contact['name']} - {contact['title']}")
            else:
                report_lines.append("   ⚠️  NO CONTACTS AT THIS AGENCY")
                report_lines.append("     Action: Network building needed")
            
            report_lines.append("")
            report_lines.append("-" * 70)
            report_lines.append("")
        
        # Action items
        report_lines.append("")
        report_lines.append("RECOMMENDED ACTIONS")
        report_lines.append("="*70)
        
        # High priority with contacts
        high_with_contacts = [
            (opp, score) for opp, score in scored_opps 
            if score['priority'] == 'HIGH' and score['contacts']['total_contacts'] > 0
        ]
        
        if high_with_contacts:
            report_lines.append("")
            report_lines.append("1. IMMEDIATE OUTREACH OPPORTUNITIES:")
            for opp, score in high_with_contacts[:5]:
                report_lines.append(f"   • {opp.get('title', '')[:50]}")
                if score['contacts']['decision_makers']:
                    dm = score['contacts']['decision_makers'][0]
                    report_lines.append(f"     → Contact {dm['name']} ({dm['title']})")
                report_lines.append(f"     → Deadline: {opp.get('responseDeadLine', 'N/A')}")
        
        # High priority without contacts
        high_no_contacts = [
            (opp, score) for opp, score in scored_opps 
            if score['priority'] == 'HIGH' and score['contacts']['total_contacts'] == 0
        ]
        
        if high_no_contacts:
            report_lines.append("")
            report_lines.append("2. RELATIONSHIP BUILDING NEEDED:")
            for opp, score in high_no_contacts[:3]:
                report_lines.append(f"   • {opp.get('title', '')[:50]}")
                report_lines.append(f"     → Agency: {opp.get('organizationName', 'N/A')}")
                report_lines.append(f"     → Action: Research and network at this agency")
        
        report_lines.append("")
        report_lines.append("="*70)
        report_lines.append("")
        
        return "\n".join(report_lines)
    
    def run_daily_scout(self, days_back: int = 7, save_report: bool = True) -> str:
        """Run the daily scouting operation"""
        
        print_header("OPPORTUNITY SCOUT - DAILY RUN")
        
        # Fetch opportunities
        opportunities = self.fetch_opportunities(days_back=days_back)
        
        if not opportunities:
            print_warning("No opportunities found")
            return ""
        
        # Score each opportunity
        print_info(f"Scoring {len(opportunities)} opportunities...")
        scores = []
        
        for opp in opportunities:
            score = self.score_opportunity(opp)
            scores.append(score)
        
        print_success(f"Scored {len(opportunities)} opportunities")
        
        # Generate report
        print_info("Generating intelligence report...")
        report = self.generate_daily_report(opportunities, scores)
        
        # Save report
        if save_report:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            report_file = f"scout_report_{timestamp}.txt"
            
            with open(report_file, 'w') as f:
                f.write(report)
            
            print_success(f"Report saved to: {report_file}")
            
            # Also save JSON data
            json_file = f"scout_data_{timestamp}.json"
            with open(json_file, 'w') as f:
                json.dump({
                    'timestamp': timestamp,
                    'opportunities': opportunities,
                    'scores': scores
                }, f, indent=2)
            
            print_success(f"Data saved to: {json_file}")
        
        # Print summary
        high_priority = sum(1 for s in scores if s['priority'] == 'HIGH')
        medium_priority = sum(1 for s in scores if s['priority'] == 'MEDIUM')
        
        print("")
        print_header("SCOUT SUMMARY")
        print(f"Total Opportunities: {len(opportunities)}")
        print(f"High Priority:       {high_priority}")
        print(f"Medium Priority:     {medium_priority}")
        print("")
        
        if high_priority > 0:
            print(f"{Colors.GREEN}{Colors.BOLD}✓ {high_priority} high-priority opportunities identified!{Colors.END}")
        else:
            print(f"{Colors.YELLOW}⚠️  No high-priority opportunities this cycle{Colors.END}")
        
        return report
    
    def close(self):
        """Close connections"""
        self.kg.close()


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Opportunity Scout Agent')
    parser.add_argument('--days', type=int, default=7, help='Days back to search (default: 7)')
    parser.add_argument('--show-report', action='store_true', help='Print full report to terminal')
    
    args = parser.parse_args()
    
    try:
        scout = OpportunityScout()
        report = scout.run_daily_scout(days_back=args.days)
        
        if args.show_report and report:
            print("\n")
            print(report)
        
        scout.close()
        
    except Exception as e:
        print(f"{Colors.RED}✗ Error: {e}{Colors.END}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
