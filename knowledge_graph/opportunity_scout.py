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

from graph.graph_client import KnowledgeGraphClient, generate_org_id, generate_person_id
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import os
import time
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
        """Initialize scout with connections to SAM.gov and SQLite knowledge graph"""

        print_info("Initializing Opportunity Scout Agent...")

        # Load config
        self.sam_api_key = os.getenv('SAM_API_KEY')

        if not self.sam_api_key:
            raise ValueError("Missing SAM_API_KEY in environment")

        # Connect to knowledge graph (SQLite-based, no credentials needed)
        self.kg = KnowledgeGraphClient()
        print_success("Connected to knowledge graph")

        # Load config.yaml for search parameters
        self.config = {}
        for config_path in ['config.yaml', '/app/config.yaml']:
            if os.path.exists(config_path):
                import yaml
                with open(config_path) as f:
                    self.config = yaml.safe_load(f) or {}
                print_success(f"Loaded config from {config_path}")
                break

        search_config = self.config.get('sam_gov', {}).get('search', {})

        # Configuration
        self.naics_codes = os.getenv('NAICS_CODES', '541512,541511,541519').split(',')
        self.keywords = search_config.get('keywords', [])
        self.opportunity_types = search_config.get('opportunity_types', [])
        self.company_size = 'small'  # small, medium, large
        value_range = search_config.get('value_range', {})
        self.min_contract_value = value_range.get('min', 100000)
        self.max_contract_value = value_range.get('max', 25000000)

        if self.keywords:
            print_info(f"IT keywords: {', '.join(self.keywords)}")
        if self.opportunity_types:
            print_info(f"Opportunity types: {', '.join(self.opportunity_types)}")

        print_success("Opportunity Scout ready")
    
    def fetch_opportunities(self, days_back: int = 7) -> List[Dict]:
        """Fetch recent opportunities from SAM.gov using NAICS + keyword filters"""

        print_info(f"Fetching opportunities from last {days_back} days...")

        from_date = (datetime.now() - timedelta(days=days_back)).strftime('%m/%d/%Y')
        to_date = datetime.now().strftime('%m/%d/%Y')

        url = "https://api.sam.gov/opportunities/v2/search"
        seen_ids = set()
        opportunities = []

        # Map config opportunity types to SAM.gov ptype codes
        ptype_map = {
            'Solicitation': 'o',
            'Presolicitation': 'p',
            'Sources Sought': 'r',
            'Special Notice': 's',
        }
        ptype = ','.join(ptype_map[t] for t in self.opportunity_types if t in ptype_map) if self.opportunity_types else None

        # Search by each NAICS + keyword combination for targeted results
        search_terms = self.keywords if self.keywords else [None]
        request_count = 0

        for naics in self.naics_codes:
            for keyword in search_terms:
                try:
                    # Rate limit: wait between requests to avoid 429s
                    if request_count > 0:
                        time.sleep(3)

                    params = {
                        'api_key': self.sam_api_key,
                        'postedFrom': from_date,
                        'postedTo': to_date,
                        'naicsCode': naics.strip(),
                        'limit': 100
                    }
                    if keyword:
                        params['keyword'] = keyword
                    if ptype:
                        params['ptype'] = ptype

                    response = requests.get(url, params=params, timeout=30)
                    request_count += 1

                    # Retry once on rate limit
                    if response.status_code == 429:
                        retry_after = int(response.headers.get('Retry-After', 60))
                        print_warning(f"Rate limited — waiting {retry_after}s before retry...")
                        time.sleep(retry_after)
                        response = requests.get(url, params=params, timeout=30)
                        request_count += 1

                    response.raise_for_status()

                    data = response.json()
                    opps = data.get('opportunitiesData', [])

                    # Deduplicate by noticeId
                    new_count = 0
                    for opp in opps:
                        nid = opp.get('noticeId', '')
                        if nid not in seen_ids:
                            seen_ids.add(nid)
                            opportunities.append(opp)
                            new_count += 1

                    label = f"NAICS {naics.strip()}"
                    if keyword:
                        label += f" + '{keyword}'"
                    print_info(f"  {label}: {len(opps)} found, {new_count} new")

                except Exception as e:
                    print_warning(f"Error fetching NAICS {naics}" +
                                  (f" + '{keyword}'" if keyword else "") +
                                  f": {e}")

        print_success(f"Fetched {len(opportunities)} unique opportunities")

        # Local IT relevance filter
        filtered = self._filter_it_relevant(opportunities)
        print_success(f"After IT relevance filter: {len(filtered)} of {len(opportunities)} kept")
        return filtered

    def _filter_it_relevant(self, opportunities: List[Dict]) -> List[Dict]:
        """Filter opportunities to only IT-relevant ones using NAICS codes and keyword matching"""

        # IT-related NAICS codes (strict — no general electronics/construction)
        it_naics = {
            '541512', '541511', '541519', '541513', '541514',  # Computer systems / IT consulting
            '541611', '541618',  # Management consulting
            '518210', '518110',  # Data processing / hosting
            '511210', '513210',  # Software publishers
            '517110', '517111', '517112', '517210', '517911', '517919',  # Telecom
            '334111', '334118', '334210',  # Computer hardware (not 334290 - general electronic)
            '334610', '334614',  # Software / media manufacturing
            '423430',  # Computer equipment wholesale
            '811211', '811212', '811213',  # Computer repair / maintenance
        }

        # IT keywords for title/description matching
        it_keywords = [
            'software', 'cyber', 'cloud', 'saas', 'paas', 'iaas', 'devops', 'devsecops',
            'it services', 'it support', 'information technology', 'data center',
            'help desk', 'service desk', 'network', 'firewall', 'server',
            'database', 'sql', 'oracle', 'sap', 'erp', 'crm',
            'web development', 'web application', 'mobile app',
            'artificial intelligence', ' ai ', 'machine learning', 'analytics',
            'power bi', 'power automate', 'powerapps', 'sharepoint', 'office 365', 'm365',
            'azure', 'aws', 'amazon web services', 'gcp',
            'agile', 'scrum', 'digital transformation', 'modernization',
            'systems integration', 'enterprise architecture',
            'zero trust', 'siem', 'endpoint', 'vulnerability',
            'managed services', 'staff augmentation', 'development',
            'telecommunications', 'voip', 'unified communications',
            'iptv', 'fiber optic', 'wan', ' lan ',
        ]

        filtered = []
        for opp in opportunities:
            naics = opp.get('naicsCode', '')
            if naics in it_naics:
                filtered.append(opp)
                continue

            title = (opp.get('title', '') or '').lower()
            desc = (opp.get('description', '') or '').lower()
            text = f" {title} {desc} "

            if any(kw in text for kw in it_keywords):
                filtered.append(opp)

        return filtered

    def check_contacts_at_agency(self, agency_name: str) -> Dict:
        """Check if we have contacts at this agency"""

        # Import the agency mapper
        try:
            from agency_mapper import get_contacts_for_agency
            return get_contacts_for_agency(self.kg, agency_name)
        except ImportError:
            # Fallback: query SQLite directly for contacts at this agency
            from graph.graph_client import generate_org_id

            conn = self.kg._conn()
            rows = conn.execute("""
                SELECT c.name, c.title, c.role as role_type,
                       c.relationship_strength as influence_level,
                       c.email,
                       COALESCE(o.name, c.organization) as organization
                FROM contacts c
                LEFT JOIN graph_edges e ON e.from_id = c.graph_id AND e.rel_type = 'WORKS_AT'
                LEFT JOIN organizations o ON o.id = e.to_id
                WHERE o.name LIKE ? OR c.organization LIKE ? OR c.agency LIKE ?
            """, (f"%{agency_name}%", f"%{agency_name}%", f"%{agency_name}%")).fetchall()
            conn.close()

            contacts = [dict(row) for row in rows]

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
        
        # Extract opportunity details — parse dotted agency path for matching
        full_agency = opp.get('fullParentPathName', '') or opp.get('organizationName', '')
        agency_parts = [p.strip() for p in full_agency.split('.') if p.strip()]
        notice_id = opp.get('noticeId', '')
        title = opp.get('title', '')

        # 1. Relationship Score (0-40 points)
        # Try each level of the agency hierarchy for contact matching
        contacts = {'total_contacts': 0, 'decision_makers': [], 'technical_leads': [],
                     'executives': [], 'influencers': [], 'all_contacts': []}
        for agency_part in agency_parts:
            contacts = self.check_contacts_at_agency(agency_part)
            if contacts['total_contacts'] > 0:
                break
        # Also try the full string for keyword matching if no match yet
        if contacts['total_contacts'] == 0 and full_agency:
            contacts = self.check_contacts_at_agency(full_agency)
        
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
    
    # ==================================================================
    # DB SYNC + FPDS COLLECTION (called automatically after scoring)
    # ==================================================================

    def _collect_fpds_intel(self, opportunities: List[Dict]) -> dict:
        """Collect FPDS contract data from USAspending.gov for agencies in scored opportunities.

        Uses the free USAspending.gov API (no key required, separate from SAM.gov).
        Stores Contract + Organization + AWARDED_TO relationships in SQLite.
        """
        from fpds_collector import FPDSCollector

        # Extract unique NAICS codes from the opportunities we just scored
        naics_codes = set()
        for opp in opportunities:
            naics = (opp.get('naicsCode') or '').strip()
            if naics:
                naics_codes.add(naics)

        if not naics_codes:
            print_warning("No NAICS codes found in opportunities — skipping FPDS collection")
            return {'contracts_fetched': 0, 'contracts_stored': 0, 'errors': 0}

        print_info(f"Collecting FPDS data for {len(naics_codes)} NAICS codes: {', '.join(sorted(naics_codes))}")

        collector = FPDSCollector()
        stats = {'contracts_fetched': 0, 'contracts_stored': 0, 'errors': 0}

        for naics in sorted(naics_codes):
            try:
                contracts = collector.fetch_contracts_by_naics(naics, months_back=12, limit=50)
                stats['contracts_fetched'] += len(contracts)

                for contract in contracts:
                    if collector.store_contract_in_graph(contract):
                        stats['contracts_stored'] += 1
                    else:
                        stats['errors'] += 1

                time.sleep(1)  # Be polite to USAspending.gov
            except Exception as e:
                print_warning(f"FPDS collection error for NAICS {naics}: {e}")
                stats['errors'] += 1

        collector.close()
        return stats

    def _sync_opportunities_to_db(self, opportunities: List[Dict], scores: List[Dict]) -> int:
        """Sync scored opportunities to SQLite.

        Opportunities are already saved as JSON files by run_daily_scout.
        Here we create Organization entries for agencies and Person entries
        for any POC contacts embedded in the opportunity data.
        """
        synced = 0

        for opp, score in zip(opportunities, scores):
            notice_id = opp.get('noticeId', '')
            if not notice_id:
                continue

            agency = opp.get('fullParentPathName', '') or opp.get('organizationName', '')
            agency_clean = agency.split('.')[0].strip() if '.' in agency else agency

            try:
                # Ensure agency organization exists in the graph
                if agency_clean:
                    self.kg.create_organization({
                        'name': agency_clean,
                        'type': 'Federal Agency',
                        'source': 'SAM.gov',
                    })

                # Create Person entries for any POC contacts on this opportunity
                for poc in (opp.get('pointOfContact') or []):
                    full_name = (poc.get('fullName') or '').strip()
                    email = (poc.get('email') or '').strip()
                    if not full_name and not email:
                        continue
                    poc_type = poc.get('type', 'primary')
                    role = 'Contracting Officer' if poc_type == 'primary' else 'Point of Contact'

                    pid = self.kg.create_person({
                        'name': full_name or email,
                        'email': email or None,
                        'phone': (poc.get('phone') or '').strip() or None,
                        'title': poc.get('title') or None,
                        'role_type': role,
                        'organization': agency_clean,
                        'source': 'SAM.gov POC',
                    })

                    if agency_clean:
                        org_id = generate_org_id(agency_clean)
                        self.kg.create_works_at(pid, org_id, source='SAM.gov POC')

                synced += 1
            except Exception as e:
                print_warning(f"Error syncing opportunity {notice_id}: {e}")

        return synced

    def _sync_poc_contacts_to_db(self, opportunities: List[Dict]) -> dict:
        """Sync POC contacts from opportunities to SQLite as Person entries with WORKS_AT.

        Uses graph_client's create_person, create_organization, and create_works_at.
        """
        stats = {'people': 0, 'orgs': 0, 'relationships': 0}

        for opp in opportunities:
            agency = opp.get('fullParentPathName', '') or opp.get('organizationName', '')
            agency_clean = agency.split('.')[0].strip() if '.' in agency else agency

            if not agency_clean:
                continue

            # Create/update Organization
            org_id = self.kg.create_organization({
                'name': agency_clean,
                'type': 'Federal Agency',
                'source': 'SAM.gov',
            })
            stats['orgs'] += 1

            # Process each point of contact
            for poc in (opp.get('pointOfContact') or []):
                full_name = (poc.get('fullName') or '').strip()
                email = (poc.get('email') or '').strip()

                if not full_name and not email:
                    continue

                poc_type = poc.get('type', 'primary')
                role = 'Contracting Officer' if poc_type == 'primary' else 'Point of Contact'

                # Create/update Person
                person_id = self.kg.create_person({
                    'name': full_name or email,
                    'email': email or None,
                    'phone': (poc.get('phone') or '').strip() or None,
                    'title': poc.get('title') or None,
                    'role_type': role,
                    'organization': agency_clean,
                    'source': 'SAM.gov POC',
                })
                stats['people'] += 1

                # Create WORKS_AT relationship
                self.kg.create_works_at(person_id, org_id, source='SAM.gov POC')
                stats['relationships'] += 1

        return stats

    def run_daily_scout(self, days_back: int = 7, save_report: bool = True) -> dict:
        """Run the daily scouting operation.

        Returns:
            dict with keys: total, scored, high_priority, medium_priority, report
        """

        print_header("OPPORTUNITY SCOUT - DAILY RUN")

        # Fetch opportunities
        opportunities = self.fetch_opportunities(days_back=days_back)

        if not opportunities:
            print_warning("No opportunities found")
            return {'total': 0, 'scored': 0, 'high_priority': 0, 'medium_priority': 0, 'report': ''}

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

        # Save report to knowledge_graph/ so the dashboard can find them
        if save_report:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            save_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)))
            os.makedirs(save_dir, exist_ok=True)

            report_file = os.path.join(save_dir, f"scout_report_{timestamp}.txt")

            with open(report_file, 'w') as f:
                f.write(report)

            print_success(f"Report saved to: {report_file}")

            # Also save JSON data
            json_file = os.path.join(save_dir, f"scout_data_{timestamp}.json")
            with open(json_file, 'w') as f:
                json.dump({
                    'timestamp': timestamp,
                    'opportunities': opportunities,
                    'scores': scores
                }, f, indent=2)

            print_success(f"Data saved to: {json_file}")

        # ---- Sync everything to SQLite ----

        # 1. Sync scored opportunities (create org/person entries)
        print_info("Syncing scored opportunities to database...")
        opp_synced = self._sync_opportunities_to_db(opportunities, scores)
        print_success(f"Synced {opp_synced} opportunities to database")

        # 2. Sync POC contacts as Person entries with WORKS_AT relationships
        print_info("Syncing POC contacts to database...")
        contact_stats = self._sync_poc_contacts_to_db(opportunities)
        print_success(f"DB contacts: {contact_stats['people']} people, {contact_stats['orgs']} orgs, {contact_stats['relationships']} relationships")

        # 3. Collect FPDS contract data from USAspending.gov (free API)
        print_info("Collecting FPDS contract data for competitive intelligence...")
        fpds_stats = {'contracts_fetched': 0, 'contracts_stored': 0, 'errors': 0}
        try:
            fpds_stats = self._collect_fpds_intel(opportunities)
            print_success(f"FPDS: {fpds_stats['contracts_fetched']} fetched, {fpds_stats['contracts_stored']} stored in database")
        except Exception as e:
            print_warning(f"FPDS collection skipped: {e}")

        # Print summary
        high_priority = sum(1 for s in scores if s['priority'] == 'HIGH')
        medium_priority = sum(1 for s in scores if s['priority'] == 'MEDIUM')

        print("")
        print_header("SCOUT SUMMARY")
        print(f"Total Opportunities: {len(opportunities)}")
        print(f"High Priority:       {high_priority}")
        print(f"Medium Priority:     {medium_priority}")
        print(f"DB Synced:           {opp_synced} opps, {contact_stats['people']} contacts, {fpds_stats['contracts_stored']} contracts")
        print("")

        if high_priority > 0:
            print(f"{Colors.GREEN}{Colors.BOLD}✓ {high_priority} high-priority opportunities identified!{Colors.END}")
        else:
            print(f"{Colors.YELLOW}⚠️  No high-priority opportunities this cycle{Colors.END}")

        return {
            'total': len(opportunities),
            'scored': len(scores),
            'high_priority': high_priority,
            'medium_priority': medium_priority,
            'report': report,
            'db_opportunities': opp_synced,
            'db_contacts': contact_stats,
            'fpds_contracts': fpds_stats
        }
    
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
