#!/usr/bin/env python3
"""
Unified SAM.gov Collector — Maximum Efficiency

Makes ONE set of API calls to SAM.gov and extracts:
1. Opportunities (for scouting/scoring)
2. Contracts & Awards (for competitive intel)
3. Contacts (vendors, agencies, incumbents)

This 3x's your efficiency by avoiding redundant API calls.

Usage:
    python unified_samgov_collector.py --days 90
    python unified_samgov_collector.py --days 180 --max-calls 10
"""

import os
import sys
import json
import argparse
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Set
from dotenv import load_dotenv

load_dotenv()

# IT-related NAICS codes
IT_NAICS = {
    '541512': 'Computer Systems Design Services',
    '541511': 'Custom Computer Programming',
    '541519': 'Other Computer Related Services',
    '518210': 'Computer Processing & Data Prep',
}


class UnifiedSAMCollector:
    """Unified collector that extracts opportunities, contracts, and contacts in one pass"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.opportunities_url = "https://api.sam.gov/opportunities/v2/search"
        self.contracts_url = "https://api.sam.gov/contract-awards/v1/search"
        
        # Collections
        self.opportunities = []
        self.contracts = []
        self.vendors = {}  # vendor_name -> {contract_count, agencies, total_value}
        self.agencies = {}  # agency -> {contract_count, vendors, total_value}
        self.incumbents = {}  # opportunity_id -> incumbent_info
        
        self.api_calls = 0
        self.max_calls = None
    
    def collect_all(self, days: int = 90, max_calls: int = None) -> Dict:
        """
        Unified collection strategy
        
        Args:
            days: Days back to search
            max_calls: Maximum API calls (respects rate limit)
        
        Returns:
            Dictionary with all collected data
        """
        self.max_calls = max_calls
        
        print("=" * 70)
        print("UNIFIED SAM.GOV COLLECTOR — Maximum Efficiency")
        print("=" * 70)
        print()
        print(f"  Strategy: Single-pass collection")
        print(f"  Period: Last {days} days")
        print(f"  NAICS codes: {len(IT_NAICS)}")
        print(f"  Max API calls: {max_calls if max_calls else 'Unlimited'}")
        print()
        print("  Will collect:")
        print("    ✓ Active opportunities (solicitations)")
        print("    ✓ Recent contract awards")
        print("    ✓ Vendor/agency contacts")
        print("    ✓ Incumbent intelligence")
        print()
        
        response = input("Continue? (y/n): ")
        if response.lower() != 'y':
            print("Cancelled.")
            return None
        
        print()
        print("🚀 Starting unified collection...")
        print()
        
        posted_from = (datetime.now() - timedelta(days=days)).strftime('%m/%d/%Y')
        posted_to = datetime.now().strftime('%m/%d/%Y')
        
        # Phase 1: Collect opportunities (also captures incumbent info)
        print("📡 Phase 1: Collecting opportunities...")
        for naics_code, naics_name in IT_NAICS.items():
            if self.max_calls and self.api_calls >= self.max_calls:
                print(f"   ⚠️  Reached max API call limit ({self.max_calls})")
                break
            
            print(f"   → NAICS {naics_code} ({naics_name})")
            opps = self._fetch_opportunities(naics_code, posted_from, posted_to)
            self.opportunities.extend(opps)
            
            # Extract incumbent info from opportunities
            for opp in opps:
                self._extract_incumbent_from_opportunity(opp)
        
        print(f"   ✓ Collected {len(self.opportunities)} opportunities")
        print()
        
        # Phase 2: Collect contract awards (captures vendors, agencies, competitive intel)
        print("📦 Phase 2: Collecting contract awards...")
        for naics_code, naics_name in IT_NAICS.items():
            if self.max_calls and self.api_calls >= self.max_calls:
                print(f"   ⚠️  Reached max API call limit ({self.max_calls})")
                break
            
            print(f"   → NAICS {naics_code} ({naics_name})")
            contracts = self._fetch_contracts(naics_code, posted_from, posted_to)
            self.contracts.extend(contracts)
            
            # Extract vendors and agencies
            for contract in contracts:
                self._extract_vendor_agency_from_contract(contract)
        
        print(f"   ✓ Collected {len(self.contracts)} contract awards")
        print()
        
        # Phase 3: Build contact lists
        print("👥 Phase 3: Building contact database...")
        contacts = self._build_contacts()
        print(f"   ✓ Built {len(contacts)} unique contacts")
        print()
        
        # Phase 4: Generate competitive intelligence
        print("🔍 Phase 4: Generating competitive intelligence...")
        competitive_intel = self._build_competitive_intel()
        print(f"   ✓ Generated intel on {len(competitive_intel['incumbents'])} incumbents")
        print()
        
        # Summary
        print("=" * 70)
        print("COLLECTION COMPLETE")
        print("=" * 70)
        print(f"  API calls used: {self.api_calls}/{self.max_calls if self.max_calls else '∞'}")
        print(f"  Opportunities: {len(self.opportunities)}")
        print(f"  Contracts: {len(self.contracts)}")
        print(f"  Contacts: {len(contacts)}")
        print(f"  Incumbents tracked: {len(competitive_intel['incumbents'])}")
        print()
        
        return {
            'collection_date': datetime.now().isoformat(),
            'search_period_days': days,
            'api_calls_used': self.api_calls,
            'opportunities': self.opportunities,
            'contracts': self.contracts,
            'contacts': contacts,
            'competitive_intelligence': competitive_intel,
            'summary': {
                'opportunities_count': len(self.opportunities),
                'contracts_count': len(self.contracts),
                'contacts_count': len(contacts),
                'incumbents_count': len(competitive_intel['incumbents']),
                'vendors_count': len(self.vendors),
                'agencies_count': len(self.agencies)
            }
        }
    
    def _fetch_opportunities(self, naics_code: str, posted_from: str, posted_to: str) -> List[Dict]:
        """Fetch opportunities from SAM.gov Opportunities API"""
        params = {
            'api_key': self.api_key,
            'postedFrom': posted_from,
            'postedTo': posted_to,
            'ncode': naics_code,
            'ptype': 'o,p',  # solicitations and pre-solicitations
            'limit': 100,
            'offset': 0
        }
        
        opportunities = []
        
        try:
            while True:
                if self.max_calls and self.api_calls >= self.max_calls:
                    break
                
                response = requests.get(self.opportunities_url, params=params, timeout=30)
                self.api_calls += 1
                
                if response.status_code == 401:
                    print("      ❌ 401 Unauthorized")
                    break
                
                if response.status_code == 429:
                    print("      ❌ Rate limited")
                    break
                
                response.raise_for_status()
                data = response.json()
                
                opps = data.get('opportunitiesData', [])
                if not opps:
                    break
                
                opportunities.extend(opps)
                
                # Check if more pages
                if len(opps) < params['limit']:
                    break
                
                params['offset'] += params['limit']
                
        except Exception as e:
            print(f"      ❌ Error: {e}")
        
        print(f"      Found {len(opportunities)} opportunities")
        return opportunities
    
    def _fetch_contracts(self, naics_code: str, date_from: str, date_to: str) -> List[Dict]:
        """Fetch contract awards from SAM.gov Contract Awards API"""
        params = {
            'api_key': self.api_key,
            'naicsCode': naics_code,
            'dateSigned': f'[{date_from},{date_to}]',
            'awardOrIDV': 'Award',
            'limit': 100,
            'offset': 0
        }
        
        contracts = []
        
        try:
            while True:
                if self.max_calls and self.api_calls >= self.max_calls:
                    break
                
                response = requests.get(self.contracts_url, params=params, timeout=30)
                self.api_calls += 1
                
                if response.status_code == 401:
                    print("      ❌ 401 Unauthorized")
                    break
                
                if response.status_code == 429:
                    print("      ❌ Rate limited")
                    break
                
                response.raise_for_status()
                data = response.json()
                
                awards = data.get('awardSummary', [])
                if not awards:
                    break
                
                # Parse contracts
                for award in awards:
                    parsed = self._parse_contract(award)
                    if parsed:
                        contracts.append(parsed)
                
                # Check if more pages
                if len(awards) < params['limit']:
                    break
                
                params['offset'] += params['limit']
                
        except Exception as e:
            print(f"      ❌ Error: {e}")
        
        print(f"      Found {len(contracts)} contracts")
        return contracts
    
    def _parse_contract(self, award: Dict) -> Dict:
        """Parse contract award from SAM.gov response"""
        try:
            contract_id = award.get('contractId', {}).get('piid', '')
            
            core = award.get('coreData', {})
            details = award.get('awardDetails', {})
            
            # Agency
            fed_org = core.get('federalOrganization', {})
            contracting = fed_org.get('contractingInformation', {})
            dept = contracting.get('contractingDepartment', {})
            agency = dept.get('name', '')
            
            # Vendor
            awardee_data = details.get('awardeeData', {})
            awardee_header = awardee_data.get('awardeeHeader', {})
            vendor_name = awardee_header.get('awardeeName', '')
            
            # Value
            dollars = details.get('dollars', {})
            value = float(dollars.get('baseDollarsObligated', 0) or 0)
            
            # Date
            dates = details.get('dates', {})
            date_signed = dates.get('dateSigned', '')
            if date_signed and 'T' in date_signed:
                date_signed = date_signed.split('T')[0]
            
            if not vendor_name or not agency:
                return None
            
            return {
                'contract_id': contract_id,
                'vendor_name': vendor_name,
                'agency': agency,
                'value': value,
                'date_signed': date_signed
            }
            
        except Exception:
            return None
    
    def _extract_incumbent_from_opportunity(self, opp: Dict):
        """Extract incumbent information from opportunity description"""
        opp_id = opp.get('noticeId', '')
        description = (opp.get('description', '') or '').lower()
        title = (opp.get('title', '') or '').lower()
        
        # Look for incumbent keywords
        incumbent_keywords = ['incumbent', 'current contractor', 'existing contractor', 'current awardee']
        
        for keyword in incumbent_keywords:
            if keyword in description or keyword in title:
                self.incumbents[opp_id] = {
                    'opportunity_id': opp_id,
                    'opportunity_title': opp.get('title', ''),
                    'detected_via': 'opportunity_description',
                    'description_snippet': description[:500]
                }
                break
    
    def _extract_vendor_agency_from_contract(self, contract: Dict):
        """Extract vendor and agency information from contract"""
        vendor = contract['vendor_name']
        agency = contract['agency']
        value = contract.get('value', 0)
        
        # Track vendor
        if vendor not in self.vendors:
            self.vendors[vendor] = {
                'name': vendor,
                'contract_count': 0,
                'agencies': set(),
                'total_value': 0
            }
        
        self.vendors[vendor]['contract_count'] += 1
        self.vendors[vendor]['agencies'].add(agency)
        self.vendors[vendor]['total_value'] += value
        
        # Track agency
        if agency not in self.agencies:
            self.agencies[agency] = {
                'name': agency,
                'contract_count': 0,
                'vendors': set(),
                'total_value': 0
            }
        
        self.agencies[agency]['contract_count'] += 1
        self.agencies[agency]['vendors'].add(vendor)
        self.agencies[agency]['total_value'] += value
    
    def _build_contacts(self) -> List[Dict]:
        """Build unified contact list from vendors and agencies"""
        contacts = []
        
        # Vendor contacts
        for vendor, info in self.vendors.items():
            contacts.append({
                'name': vendor,
                'organization': vendor,
                'type': 'Vendor',
                'role': 'Contract Holder',
                'contract_count': info['contract_count'],
                'total_value': info['total_value'],
                'agencies': list(info['agencies']),
                'relationship_strength': self._infer_strength(info['contract_count'])
            })
        
        # Agency contacts
        for agency, info in self.agencies.items():
            contacts.append({
                'name': agency,
                'organization': agency,
                'type': 'Agency',
                'role': 'Contracting Office',
                'contract_count': info['contract_count'],
                'total_value': info['total_value'],
                'vendors': list(info['vendors'])[:10],  # Top 10 vendors
                'relationship_strength': 'New'
            })
        
        return contacts
    
    def _build_competitive_intel(self) -> Dict:
        """Build competitive intelligence report"""
        # Top incumbents by contract count
        top_incumbents = sorted(
            self.vendors.items(),
            key=lambda x: x[1]['contract_count'],
            reverse=True
        )[:20]
        
        # Agency spending patterns
        agency_patterns = {}
        for agency, info in self.agencies.items():
            agency_patterns[agency] = {
                'total_spend': info['total_value'],
                'contract_count': info['contract_count'],
                'top_vendors': sorted(
                    list(info['vendors']),
                    key=lambda v: self.vendors.get(v, {}).get('contract_count', 0),
                    reverse=True
                )[:5]
            }
        
        return {
            'incumbents': {
                name: {
                    'contract_count': info['contract_count'],
                    'total_value': info['total_value'],
                    'agencies': list(info['agencies'])
                }
                for name, info in top_incumbents
            },
            'agency_patterns': agency_patterns,
            'detected_incumbents_in_opportunities': self.incumbents
        }
    
    def _infer_strength(self, contract_count: int) -> str:
        """Infer relationship strength from contract count"""
        if contract_count >= 10:
            return 'Strong'
        elif contract_count >= 3:
            return 'Medium'
        else:
            return 'New'
    
    def save_results(self, data: Dict, output_dir: str = 'knowledge_graph'):
        """Save all results to JSON files"""
        Path(output_dir).mkdir(exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save full dataset
        full_file = Path(output_dir) / f'unified_collection_{timestamp}.json'
        with open(full_file, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        print(f"💾 Saved complete dataset: {full_file}")
        
        # Save opportunities (for dashboard compatibility)
        opp_file = Path(output_dir) / f'scout_data_{timestamp}.json'
        with open(opp_file, 'w') as f:
            json.dump({
                'collection_date': data['collection_date'],
                'opportunities': data['opportunities']
            }, f, indent=2)
        
        print(f"💾 Saved opportunities: {opp_file}")
        
        # Save contacts (for import script)
        contacts_file = Path(output_dir) / f'contacts_extract_{timestamp}.json'
        with open(contacts_file, 'w') as f:
            json.dump({
                'collection_date': data['collection_date'],
                'contacts': data['contacts']
            }, f, indent=2, default=str)
        
        print(f"💾 Saved contacts: {contacts_file}")
        
        # Save competitive intel (for analysis)
        intel_file = Path(output_dir) / f'competitive_intel_{timestamp}.json'
        with open(intel_file, 'w') as f:
            json.dump({
                'collection_date': data['collection_date'],
                'competitive_intelligence': data['competitive_intelligence']
            }, f, indent=2, default=str)
        
        print(f"💾 Saved competitive intel: {intel_file}")


def main():
    parser = argparse.ArgumentParser(
        description='Unified SAM.gov collector — maximum efficiency'
    )
    parser.add_argument(
        '--days',
        type=int,
        default=90,
        help='Number of days back to search (default: 90)'
    )
    parser.add_argument(
        '--max-calls',
        type=int,
        default=None,
        help='Maximum API calls to respect rate limit (default: unlimited)'
    )
    
    args = parser.parse_args()
    
    api_key = os.getenv('SAM_API_KEY')
    if not api_key:
        print("❌ Error: SAM_API_KEY not found in environment")
        print("   Set it in your .env file")
        sys.exit(1)
    
    collector = UnifiedSAMCollector(api_key)
    data = collector.collect_all(days=args.days, max_calls=args.max_calls)
    
    if data:
        collector.save_results(data)
        
        print()
        print("✓ Collection complete!")
        print("  Refresh your dashboard to see the new data")


if __name__ == '__main__':
    main()
