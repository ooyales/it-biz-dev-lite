#!/usr/bin/env python3
"""
Competitive Intelligence Agent
Analyzes FPDS contract awards to identify competitors, incumbents, and teaming opportunities

Features:
- FPDS contract award analysis
- Incumbent identification
- Competitor profiling
- Teaming partner recommendations
- Agency spending patterns
- Win rate analysis
"""

import sys
# Remove the sys.path.append - we handle paths in agent_executor.py

from knowledge_graph.graph.neo4j_client import KnowledgeGraphClient, generate_person_id, generate_org_id
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import os
from pathlib import Path
import json
from collections import defaultdict

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


class CompetitiveIntelAgent:
    """
    Analyzes competitive landscape using FPDS contract award data
    """
    
    def __init__(self):
        """Initialize competitive intelligence agent"""
        
        print_info("Initializing Competitive Intelligence Agent...")
        
        # Load config
        neo4j_password = os.getenv('NEO4J_PASSWORD')
        
        if not neo4j_password:
            raise ValueError("Missing NEO4J_PASSWORD in environment")
        
        # Connect to knowledge graph
        self.kg = KnowledgeGraphClient(
            uri=os.getenv('NEO4J_URI', 'bolt://localhost:7687'),
            user=os.getenv('NEO4J_USER', 'neo4j'),
            password=neo4j_password
        )
        print_success("Connected to knowledge graph")
        
        # Configuration
        self.naics_codes = os.getenv('NAICS_CODES', '541512,541511,541519').split(',')
        self.fpds_base_url = "https://api.sam.gov/prod/opportunities/v1/search"
        
        # Note: FPDS API also uses SAM.gov API key
        self.api_key = os.getenv('SAM_API_KEY')
        
        print_success("Competitive Intelligence Agent ready")
    
    def fetch_contract_awards(
        self, 
        naics_code: str,
        months_back: int = 12,
        limit: int = 100
    ) -> List[Dict]:
        """
        Fetch contract awards from FPDS via SAM.gov API
        
        Note: This uses the opportunities API with archive filter
        For production, you'd want direct FPDS API access
        """
        
        print_info(f"Fetching contract awards for NAICS {naics_code}...")
        
        # For now, we'll use a simplified approach
        # In production, you'd use fpds.gov API or data.gov downloads
        
        # Simulate FPDS data structure
        # TODO: Replace with actual FPDS API calls when you have access
        
        return []
    
    def analyze_competitor(self, company_name: str) -> Dict:
        """
        Analyze a specific competitor
        
        Returns:
        - Total contract value won
        - Number of contracts
        - Average contract size
        - Agencies they work with
        - NAICS codes they compete in
        - Win rate (if calculable)
        """
        
        org_id = generate_org_id(company_name)
        
        # Query graph for contracts awarded to this company
        with self.kg.driver.session(database="neo4j") as session:
            query = """
            MATCH (c:Contract)-[:AWARDED_TO]->(o:Organization {id: $org_id})
            RETURN c.contract_number as contract_number,
                   c.title as title,
                   c.value as value,
                   c.award_date as award_date,
                   c.agency as agency,
                   c.naics as naics
            ORDER BY c.award_date DESC
            """
            
            result = session.run(query, org_id=org_id)
            contracts = [dict(record) for record in result]
        
        if not contracts:
            return {
                'company': company_name,
                'total_contracts': 0,
                'total_value': 0,
                'agencies': [],
                'naics_codes': []
            }
        
        # Analyze
        total_value = sum(c.get('value', 0) for c in contracts if c.get('value'))
        agencies = list(set(c.get('agency') for c in contracts if c.get('agency')))
        naics_codes = list(set(c.get('naics') for c in contracts if c.get('naics')))
        
        return {
            'company': company_name,
            'total_contracts': len(contracts),
            'total_value': total_value,
            'average_value': total_value / len(contracts) if contracts else 0,
            'agencies': agencies,
            'naics_codes': naics_codes,
            'recent_wins': contracts[:5]
        }
    
    def identify_incumbents(self, agency: str, naics_code: str = None) -> List[Dict]:
        """
        Identify incumbent contractors at an agency
        
        Incumbents are companies with recent contract awards at that agency
        """
        
        print_info(f"Identifying incumbents at {agency}...")
        
        with self.kg.driver.session(database="neo4j") as session:
            query = """
            MATCH (c:Contract)-[:AWARDED_TO]->(o:Organization)
            WHERE c.agency CONTAINS $agency
            """
            
            if naics_code:
                query += " AND c.naics = $naics"
            
            query += """
            RETURN o.name as company,
                   count(c) as contract_count,
                   sum(c.value) as total_value,
                   max(c.award_date) as latest_award
            ORDER BY total_value DESC
            LIMIT 20
            """
            
            params = {'agency': agency}
            if naics_code:
                params['naics'] = naics_code
            
            result = session.run(query, **params)
            incumbents = [dict(record) for record in result]
        
        return incumbents
    
    def find_teaming_partners(
        self, 
        target_agency: str = None,
        naics_code: str = None,
        min_contracts: int = 3
    ) -> List[Dict]:
        """
        Identify potential teaming partners
        
        Good teaming partners:
        - Have experience at target agency
        - Have won contracts in your NAICS
        - Are not direct competitors (different size/capability)
        - Have complementary capabilities
        """
        
        print_info("Identifying potential teaming partners...")
        
        with self.kg.driver.session(database="neo4j") as session:
            query = """
            MATCH (c:Contract)-[:AWARDED_TO]->(o:Organization)
            WHERE 1=1
            """
            
            params = {}
            
            if target_agency:
                query += " AND c.agency CONTAINS $agency"
                params['agency'] = target_agency
            
            if naics_code:
                query += " AND c.naics = $naics"
                params['naics'] = naics_code
            
            query += """
            WITH o, count(c) as contract_count, sum(c.value) as total_value
            WHERE contract_count >= $min_contracts
            RETURN o.name as company,
                   o.type as company_type,
                   contract_count,
                   total_value
            ORDER BY contract_count DESC
            LIMIT 50
            """
            
            params['min_contracts'] = min_contracts
            
            result = session.run(query, **params)
            partners = [dict(record) for record in result]
        
        return partners
    
    def analyze_agency_spending(self, agency: str, years: int = 3) -> Dict:
        """
        Analyze spending patterns at an agency
        
        Returns:
        - Total spending
        - Top contractors
        - Spending by NAICS
        - Trend (increasing/decreasing)
        - Average contract size
        """
        
        print_info(f"Analyzing spending at {agency}...")
        
        with self.kg.driver.session(database="neo4j") as session:
            # Get all contracts at this agency
            query = """
            MATCH (c:Contract)
            WHERE c.agency CONTAINS $agency
            RETURN c.value as value,
                   c.award_date as award_date,
                   c.naics as naics
            """
            
            result = session.run(query, agency=agency)
            contracts = [dict(record) for record in result]
        
        if not contracts:
            return {
                'agency': agency,
                'total_spending': 0,
                'contract_count': 0,
                'message': 'No contract data available'
            }
        
        # Calculate metrics
        total_spending = sum(c.get('value', 0) for c in contracts if c.get('value'))
        
        # Spending by NAICS
        naics_spending = defaultdict(float)
        for c in contracts:
            naics = c.get('naics', 'Unknown')
            value = c.get('value', 0)
            if value:
                naics_spending[naics] += value
        
        return {
            'agency': agency,
            'total_spending': total_spending,
            'contract_count': len(contracts),
            'average_contract_size': total_spending / len(contracts) if contracts else 0,
            'naics_breakdown': dict(naics_spending),
            'top_naics': sorted(naics_spending.items(), key=lambda x: x[1], reverse=True)[:5]
        }
    
    def competitor_comparison(self, competitors: List[str]) -> Dict:
        """
        Compare multiple competitors side-by-side
        """
        
        print_info(f"Comparing {len(competitors)} competitors...")
        
        comparison = {}
        
        for company in competitors:
            analysis = self.analyze_competitor(company)
            comparison[company] = analysis
        
        # Rank by total value
        ranked = sorted(
            comparison.items(),
            key=lambda x: x[1]['total_value'],
            reverse=True
        )
        
        return {
            'competitors': comparison,
            'ranked_by_value': ranked
        }
    
    def generate_intel_report(
        self,
        target_agency: str = None,
        naics_code: str = None
    ) -> str:
        """Generate competitive intelligence report"""
        
        report_lines = []
        report_lines.append("="*70)
        report_lines.append("COMPETITIVE INTELLIGENCE REPORT")
        report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        report_lines.append("="*70)
        report_lines.append("")
        
        # If specific agency provided
        if target_agency:
            report_lines.append(f"TARGET AGENCY: {target_agency}")
            report_lines.append("-" * 70)
            report_lines.append("")
            
            # Agency spending analysis
            spending = self.analyze_agency_spending(target_agency)
            report_lines.append("SPENDING ANALYSIS")
            report_lines.append(f"  Total Contracts: {spending['contract_count']}")
            report_lines.append(f"  Total Value: ${spending['total_spending']:,.0f}")
            report_lines.append(f"  Average Contract: ${spending['average_contract_size']:,.0f}")
            report_lines.append("")
            
            if spending.get('top_naics'):
                report_lines.append("  Top NAICS Codes by Spending:")
                for naics, value in spending['top_naics']:
                    report_lines.append(f"    {naics}: ${value:,.0f}")
            report_lines.append("")
            
            # Incumbents
            incumbents = self.identify_incumbents(target_agency, naics_code)
            if incumbents:
                report_lines.append("INCUMBENT CONTRACTORS")
                report_lines.append("-" * 70)
                for i, inc in enumerate(incumbents[:10], 1):
                    report_lines.append(f"{i}. {inc['company']}")
                    report_lines.append(f"   Contracts: {inc['contract_count']}")
                    if inc.get('total_value'):
                        report_lines.append(f"   Total Value: ${inc['total_value']:,.0f}")
                    report_lines.append(f"   Latest Award: {inc.get('latest_award', 'N/A')}")
                    report_lines.append("")
            else:
                report_lines.append("INCUMBENT CONTRACTORS")
                report_lines.append("-" * 70)
                report_lines.append("  No contract data available in knowledge graph")
                report_lines.append("  Action: Run FPDS data collection to populate")
                report_lines.append("")
            
            # Teaming partners
            partners = self.find_teaming_partners(target_agency, naics_code)
            if partners:
                report_lines.append("POTENTIAL TEAMING PARTNERS")
                report_lines.append("-" * 70)
                for i, partner in enumerate(partners[:10], 1):
                    report_lines.append(f"{i}. {partner['company']}")
                    report_lines.append(f"   Contracts at Agency: {partner['contract_count']}")
                    if partner.get('total_value'):
                        report_lines.append(f"   Total Value: ${partner['total_value']:,.0f}")
                    report_lines.append("")
            else:
                report_lines.append("POTENTIAL TEAMING PARTNERS")
                report_lines.append("-" * 70)
                report_lines.append("  No teaming partner data available")
                report_lines.append("")
        
        # General market intelligence
        else:
            report_lines.append("MARKET OVERVIEW")
            report_lines.append("-" * 70)
            report_lines.append("")
            
            # Get overall stats from graph
            stats = self.kg.get_network_statistics()
            report_lines.append(f"Knowledge Graph Statistics:")
            report_lines.append(f"  Total People: {stats.get('total_people', 0)}")
            report_lines.append(f"  Total Organizations: {stats.get('total_organizations', 0)}")
            report_lines.append(f"  Total Relationships: {stats.get('total_relationships', 0)}")
            report_lines.append("")
            
            report_lines.append("Note: For detailed competitive intelligence, specify a target agency")
            report_lines.append("Usage: python competitive_intel.py --agency 'Department of Defense'")
            report_lines.append("")
        
        report_lines.append("="*70)
        report_lines.append("RECOMMENDATIONS")
        report_lines.append("="*70)
        report_lines.append("")
        
        if not target_agency:
            report_lines.append("1. Run with --agency flag to analyze specific agencies")
            report_lines.append("2. Collect FPDS contract data to populate competitive intel")
            report_lines.append("3. Build relationships with incumbents for teaming opportunities")
        else:
            if incumbents:
                report_lines.append("1. INCUMBENT STRATEGY:")
                report_lines.append(f"   • Research top 3 incumbents: {', '.join(i['company'] for i in incumbents[:3])}")
                report_lines.append("   • Identify their strengths and weaknesses")
                report_lines.append("   • Consider subcontracting or teaming")
                report_lines.append("")
            
            if partners:
                report_lines.append("2. TEAMING STRATEGY:")
                report_lines.append(f"   • Reach out to potential partners")
                report_lines.append("   • Look for complementary capabilities")
                report_lines.append("   • Propose joint pursuit on upcoming opportunities")
                report_lines.append("")
            
            report_lines.append("3. RELATIONSHIP BUILDING:")
            report_lines.append("   • Network with incumbent employees")
            report_lines.append("   • Attend agency industry days")
            report_lines.append("   • Build contacts at the agency")
        
        report_lines.append("")
        report_lines.append("="*70)
        report_lines.append("")
        
        return "\n".join(report_lines)
    
    def run_competitive_intel(
        self,
        target_agency: str = None,
        naics_code: str = None,
        save_report: bool = True
    ) -> str:
        """Run competitive intelligence analysis"""
        
        print_header("COMPETITIVE INTELLIGENCE ANALYSIS")
        
        if target_agency:
            print_info(f"Analyzing: {target_agency}")
        if naics_code:
            print_info(f"NAICS: {naics_code}")
        
        # Generate report
        print_info("Generating intelligence report...")
        report = self.generate_intel_report(target_agency, naics_code)
        
        # Save report
        if save_report:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            agency_slug = target_agency.replace(' ', '_').lower() if target_agency else 'general'
            report_file = f"competitive_intel_{agency_slug}_{timestamp}.txt"
            
            with open(report_file, 'w') as f:
                f.write(report)
            
            print_success(f"Report saved to: {report_file}")
        
        print("")
        print_success("Competitive intelligence analysis complete")
        
        return report
    
    def close(self):
        """Close connections"""
        self.kg.close()


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Competitive Intelligence Agent')
    parser.add_argument('--agency', type=str, help='Target agency to analyze')
    parser.add_argument('--naics', type=str, help='NAICS code to filter by')
    parser.add_argument('--show-report', action='store_true', help='Print full report to terminal')
    parser.add_argument('--compare', nargs='+', help='Compare specific competitors')
    
    args = parser.parse_args()
    
    try:
        agent = CompetitiveIntelAgent()
        
        if args.compare:
            # Compare specific competitors
            comparison = agent.competitor_comparison(args.compare)
            print_header("COMPETITOR COMPARISON")
            for company, rank in comparison['ranked_by_value']:
                print(f"\n{company}:")
                print(f"  Contracts: {rank['total_contracts']}")
                print(f"  Total Value: ${rank['total_value']:,.0f}")
                print(f"  Agencies: {', '.join(rank['agencies'][:3])}")
        else:
            # Run full intel report
            report = agent.run_competitive_intel(
                target_agency=args.agency,
                naics_code=args.naics
            )
            
            if args.show_report:
                print("\n")
                print(report)
        
        agent.close()
        
    except Exception as e:
        print(f"{Colors.RED}✗ Error: {e}{Colors.END}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
