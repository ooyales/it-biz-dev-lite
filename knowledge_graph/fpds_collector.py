#!/usr/bin/env python3
"""
FPDS Contract Data Collector
Collects contract award data and populates knowledge graph

Note: This uses publicly available contract data
FPDS data can be accessed via:
1. USASpending.gov API (recommended)
2. Data.gov bulk downloads
3. FPDS.gov direct queries
"""

import sys
sys.path.append('..')

from graph.neo4j_client import KnowledgeGraphClient, generate_org_id
import requests
from datetime import datetime, timedelta
from typing import Dict, List
import os
import time
from tqdm import tqdm

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ANSI colors
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_success(text):
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")

def print_info(text):
    print(f"{Colors.CYAN}→ {text}{Colors.END}")


class FPDSCollector:
    """
    Collects federal contract award data from USASpending.gov API
    (Free, no API key required, comprehensive data)
    """
    
    def __init__(self):
        """Initialize FPDS collector"""
        
        print_info("Initializing FPDS Contract Collector...")
        
        # Connect to knowledge graph
        neo4j_password = os.getenv('NEO4J_PASSWORD')
        self.kg = KnowledgeGraphClient(
            uri=os.getenv('NEO4J_URI', 'bolt://localhost:7687'),
            user=os.getenv('NEO4J_USER', 'neo4j'),
            password=neo4j_password
        )
        print_success("Connected to knowledge graph")
        
        # USASpending.gov API (free, comprehensive)
        self.usaspending_base = "https://api.usaspending.gov/api/v2"
        
        self.naics_codes = os.getenv('NAICS_CODES', '541512,541511,541519').split(',')
        
        print_success("FPDS Collector ready")
    
    def fetch_contracts_by_naics(
        self,
        naics_code: str,
        months_back: int = 12,
        limit: int = 100
    ) -> List[Dict]:
        """
        Fetch contract awards from USASpending.gov
        
        USASpending API is free and doesn't require API key
        """
        
        print_info(f"Fetching contracts for NAICS {naics_code}...")
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=months_back * 30)
        
        url = f"{self.usaspending_base}/search/spending_by_award"
        
        payload = {
            "filters": {
                "time_period": [{
                    "start_date": start_date.strftime("%Y-%m-%d"),
                    "end_date": end_date.strftime("%Y-%m-%d")
                }],
                "naics_codes": [naics_code.strip()],
                "award_type_codes": ["A", "B", "C", "D"]  # Contracts
            },
            "fields": [
                "Award ID",
                "Recipient Name",
                "Award Amount",
                "Award Type",
                "Awarding Agency",
                "Start Date",
                "End Date",
                "NAICS Code",
                "Description"
            ],
            "limit": limit,
            "page": 1
        }
        
        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            results = data.get('results', [])
            
            print_success(f"  Found {len(results)} contracts")
            
            return results
            
        except Exception as e:
            print(f"{Colors.YELLOW}⚠️  Error fetching NAICS {naics_code}: {e}{Colors.END}")
            return []
    
    def store_contract_in_graph(self, contract: Dict) -> bool:
        """Store contract data in knowledge graph"""
        
        try:
            # Extract contract details
            contract_id = contract.get('Award ID', 'unknown')
            recipient = contract.get('Recipient Name', 'Unknown')
            amount = contract.get('Award Amount', 0)
            agency = contract.get('Awarding Agency', 'Unknown')
            start_date = contract.get('Start Date', '')
            naics = contract.get('NAICS Code', '')
            description = contract.get('Description', '')
            
            # Create contract node
            with self.kg.driver.session(database="contactsgraphdb") as session:
                query = """
                MERGE (c:Contract {id: $contract_id})
                SET c.contract_number = $contract_id,
                    c.title = $description,
                    c.value = $amount,
                    c.award_date = $start_date,
                    c.agency = $agency,
                    c.naics = $naics,
                    c.source = 'USASpending.gov',
                    c.updated_at = datetime()
                RETURN c
                """
                
                session.run(query,
                    contract_id=contract_id,
                    description=description[:200] if description else 'Contract',
                    amount=float(amount) if amount else 0,
                    start_date=start_date,
                    agency=agency,
                    naics=naics
                )
            
            # Create organization node for recipient
            org_id = generate_org_id(recipient)
            
            org_data = {
                'id': org_id,
                'name': recipient,
                'type': 'Contractor',
                'source': 'FPDS'
            }
            
            self.kg.create_organization(org_data)
            
            # Create AWARDED_TO relationship
            with self.kg.driver.session(database="contactsgraphdb") as session:
                query = """
                MATCH (c:Contract {id: $contract_id})
                MATCH (o:Organization {id: $org_id})
                MERGE (c)-[r:AWARDED_TO]->(o)
                SET r.date = $award_date
                """
                
                session.run(query,
                    contract_id=contract_id,
                    org_id=org_id,
                    award_date=start_date
                )
            
            return True
            
        except Exception as e:
            print(f"{Colors.YELLOW}⚠️  Error storing contract: {e}{Colors.END}")
            return False
    
    def collect_and_store(
        self,
        months_back: int = 12,
        limit_per_naics: int = 100
    ) -> Dict:
        """Collect contracts and store in graph"""
        
        print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*70}")
        print("FPDS CONTRACT DATA COLLECTION")
        print(f"{'='*70}{Colors.END}\n")
        
        stats = {
            'contracts_fetched': 0,
            'contracts_stored': 0,
            'organizations_created': 0,
            'errors': 0
        }
        
        initial_stats = self.kg.get_network_statistics()
        
        # Collect for each NAICS code
        all_contracts = []
        
        for naics in self.naics_codes:
            contracts = self.fetch_contracts_by_naics(
                naics.strip(),
                months_back=months_back,
                limit=limit_per_naics
            )
            all_contracts.extend(contracts)
            stats['contracts_fetched'] += len(contracts)
            time.sleep(1)  # Be nice to the API
        
        if not all_contracts:
            print(f"{Colors.YELLOW}⚠️  No contracts found{Colors.END}")
            return stats
        
        print(f"\n{Colors.CYAN}→ Storing {len(all_contracts)} contracts in knowledge graph...{Colors.END}\n")
        
        # Store contracts with progress bar
        for contract in tqdm(all_contracts, desc="Storing", unit="contract"):
            success = self.store_contract_in_graph(contract)
            if success:
                stats['contracts_stored'] += 1
            else:
                stats['errors'] += 1
            
            time.sleep(0.1)  # Small delay
        
        final_stats = self.kg.get_network_statistics()
        
        print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*70}")
        print("COLLECTION COMPLETE")
        print(f"{'='*70}{Colors.END}\n")
        
        print(f"{Colors.BOLD}Contracts:{Colors.END}")
        print(f"  Fetched: {stats['contracts_fetched']}")
        print(f"  Stored: {stats['contracts_stored']}")
        print(f"  Errors: {stats['errors']}")
        
        print(f"\n{Colors.BOLD}Graph Growth:{Colors.END}")
        print(f"  Organizations: {initial_stats.get('total_organizations', 0)} → {final_stats.get('total_organizations', 0)} (+{final_stats.get('total_organizations', 0) - initial_stats.get('total_organizations', 0)})")
        
        print(f"\n{Colors.GREEN}{Colors.BOLD}✓ FPDS data collection complete!{Colors.END}")
        print(f"\n{Colors.CYAN}Now run: python competitive_intel.py --agency 'Your Agency'{Colors.END}\n")
        
        return stats
    
    def close(self):
        """Close connections"""
        self.kg.close()


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='FPDS Contract Data Collector')
    parser.add_argument('--months', type=int, default=12, help='Months back to collect (default: 12)')
    parser.add_argument('--limit', type=int, default=100, help='Contracts per NAICS (default: 100)')
    
    args = parser.parse_args()
    
    try:
        collector = FPDSCollector()
        stats = collector.collect_and_store(
            months_back=args.months,
            limit_per_naics=args.limit
        )
        collector.close()
        
    except Exception as e:
        print(f"{Colors.YELLOW}✗ Error: {e}{Colors.END}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
