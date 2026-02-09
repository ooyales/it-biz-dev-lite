#!/usr/bin/env python3
"""
SAM.gov Opportunity Collector
Automated collection with entity extraction and graph storage

Usage:
    python collect_opportunities.py --limit 10   # Start small
    python collect_opportunities.py --limit 50   # Full run
"""

import sys
sys.path.append('..')

from nlp.minimal_claude_extractor import MinimalClaudeExtractor
from graph.neo4j_client import KnowledgeGraphClient, generate_person_id, generate_org_id
import requests
import argparse
from datetime import datetime, timedelta
from typing import Dict, List
import time
from tqdm import tqdm
import json

# ANSI colors for terminal output
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

def print_error(text):
    print(f"{Colors.RED}✗ {text}{Colors.END}")

def print_info(text):
    print(f"{Colors.CYAN}→ {text}{Colors.END}")


class OpportunityCollector:
    """Collects opportunities from SAM.gov and populates knowledge graph"""
    
    def __init__(
        self,
        sam_api_key: str,
        neo4j_password: str,
        anthropic_api_key: str = None
    ):
        self.sam_api_key = sam_api_key
        
        print_info("Initializing components...")
        
        # Initialize extractor
        self.extractor = MinimalClaudeExtractor(api_key=anthropic_api_key)
        print_success("Entity extractor ready")
        
        # Initialize graph client
        self.kg = KnowledgeGraphClient(
            uri="bolt://localhost:7687",
            user="neo4j",
            password=neo4j_password
        )
        print_success("Knowledge graph connected")
        
        # Statistics
        self.stats = {
            'opportunities_fetched': 0,
            'opportunities_processed': 0,
            'people_created': 0,
            'orgs_created': 0,
            'relationships_created': 0,
            'errors': 0,
            'cost': 0.0
        }
    
    def fetch_opportunities(
        self, 
        limit: int = 10,
        naics_codes: List[str] = None,
        days_back: int = 30
    ) -> List[Dict]:
        """Fetch opportunities from SAM.gov"""
        
        print_info(f"Fetching opportunities from SAM.gov (limit: {limit})...")
        
        from_date = (datetime.now() - timedelta(days=days_back)).strftime('%m/%d/%Y')
        to_date = datetime.now().strftime('%m/%d/%Y')
        
        url = "https://api.sam.gov/opportunities/v2/search"
        
        all_opportunities = []
        
        # Default NAICS codes for IT services
        if not naics_codes:
            naics_codes = [
                '541512',  # Computer Systems Design Services
                '541511',  # Custom Computer Programming Services
                '541519',  # Other Computer Related Services
            ]
        
        for naics in naics_codes:
            if len(all_opportunities) >= limit:
                break
                
            try:
                params = {
                    'api_key': self.sam_api_key,
                    'postedFrom': from_date,
                    'postedTo': to_date,
                    'naicsCode': naics,
                    'limit': min(100, limit - len(all_opportunities))
                }
                
                response = requests.get(url, params=params, timeout=30)
                response.raise_for_status()
                
                data = response.json()
                opps = data.get('opportunitiesData', [])
                all_opportunities.extend(opps)
                
                print_info(f"  NAICS {naics}: {len(opps)} opportunities")
                
                # Respect rate limits
                time.sleep(1)
                
            except requests.exceptions.RequestException as e:
                print_warning(f"Error fetching NAICS {naics}: {e}")
                continue
        
        # Limit to requested number
        all_opportunities = all_opportunities[:limit]
        self.stats['opportunities_fetched'] = len(all_opportunities)
        
        print_success(f"Fetched {len(all_opportunities)} opportunities")
        return all_opportunities
    
    def process_opportunity(self, opp: Dict) -> Dict:
        """Process one opportunity: extract entities and store in graph"""
        
        opp_stats = {
            'people': 0,
            'orgs': 0,
            'relationships': 0,
            'error': None
        }
        
        try:
            # Build text for extraction
            text_parts = [
                f"Title: {opp.get('title', '')}",
                f"Organization: {opp.get('organizationName', '')}",
                f"Description: {opp.get('description', '')}"
            ]
            
            # Add point of contact
            if opp.get('pointOfContact'):
                pocs = opp.get('pointOfContact', [])
                if isinstance(pocs, list) and len(pocs) > 0:
                    poc = pocs[0]
                    text_parts.append(f"\nPoint of Contact:")
                    text_parts.append(f"Name: {poc.get('fullName', '')}")
                    text_parts.append(f"Email: {poc.get('email', '')}")
                    text_parts.append(f"Phone: {poc.get('phone', '')}")
                    text_parts.append(f"Title: {poc.get('title', '')}")
            
            text = '\n'.join(filter(None, text_parts))
            
            # Skip if too short
            if len(text) < 100:
                return opp_stats
            
            # Extract entities
            entities, relationships = self.extractor.extract(
                text, 
                extract_relationships=True
            )
            
            # Store entities
            for entity in entities:
                try:
                    if entity.type == 'PERSON':
                        person_id = generate_person_id(
                            entity.text,
                            entity.metadata.get('email') if entity.metadata else None
                        )
                        
                        person_data = {
                            'id': person_id,
                            'name': entity.text,
                            'source': f"SAM.gov: {opp.get('noticeId', 'unknown')}",
                            'confidence': entity.confidence,
                            'extracted_at': datetime.now().isoformat()
                        }
                        
                        # Add metadata
                        if entity.metadata:
                            person_data.update({
                                k: v for k, v in entity.metadata.items()
                                if v and k in ['email', 'phone', 'title', 'organization']
                            })
                        
                        # Infer role type from title
                        if 'title' in person_data:
                            person_data['role_type'] = self._guess_role_type(person_data['title'])
                            person_data['influence_level'] = self._guess_influence_level(person_data['title'])
                        
                        self.kg.create_person(person_data)
                        opp_stats['people'] += 1
                        
                    elif entity.type == 'ORGANIZATION':
                        org_id = generate_org_id(entity.text)
                        
                        org_data = {
                            'id': org_id,
                            'name': entity.text,
                            'source': f"SAM.gov: {opp.get('noticeId', 'unknown')}",
                            'confidence': entity.confidence,
                            'type': 'Federal Agency' if any(word in entity.text for word in ['Department', 'Agency', 'Administration']) else 'Organization'
                        }
                        
                        self.kg.create_organization(org_data)
                        opp_stats['orgs'] += 1
                        
                except Exception as e:
                    # Skip individual entity errors
                    continue
            
            # Store relationships
            for rel in relationships:
                try:
                    subject_matches = self.kg.search_people(rel.subject)
                    
                    if subject_matches:
                        subject_id = subject_matches[0]['id']
                        
                        # Determine target
                        if rel.relation in ['WORKS_AT', 'EMPLOYED_BY']:
                            target_id = generate_org_id(rel.object)
                        else:
                            object_matches = self.kg.search_people(rel.object)
                            if object_matches:
                                target_id = object_matches[0]['id']
                            else:
                                continue
                        
                        self.kg.create_relationship(
                            from_id=subject_id,
                            to_id=target_id,
                            rel_type=rel.relation,
                            properties={
                                'confidence': rel.confidence,
                                'source': f"SAM.gov: {opp.get('noticeId', 'unknown')}"
                            }
                        )
                        opp_stats['relationships'] += 1
                        
                except Exception as e:
                    # Skip individual relationship errors
                    continue
            
        except Exception as e:
            opp_stats['error'] = str(e)
        
        return opp_stats
    
    def run_collection(
        self,
        limit: int = 10,
        naics_codes: List[str] = None,
        days_back: int = 30
    ):
        """Run full collection pipeline"""
        
        print_header("SAM.GOV OPPORTUNITY COLLECTION")
        
        # Get initial stats
        initial_stats = self.kg.get_network_statistics()
        print_info(f"Starting graph state:")
        print(f"  People: {initial_stats.get('total_people', 0)}")
        print(f"  Organizations: {initial_stats.get('total_organizations', 0)}")
        print(f"  Relationships: {initial_stats.get('total_relationships', 0)}")
        
        # Fetch opportunities
        print()
        opportunities = self.fetch_opportunities(
            limit=limit,
            naics_codes=naics_codes,
            days_back=days_back
        )
        
        if not opportunities:
            print_error("No opportunities fetched. Check your API key or search parameters.")
            return
        
        # Process opportunities with progress bar
        print()
        print_info(f"Processing {len(opportunities)} opportunities...")
        print()
        
        for opp in tqdm(opportunities, desc="Processing", unit="opp"):
            opp_stats = self.process_opportunity(opp)
            
            self.stats['opportunities_processed'] += 1
            self.stats['people_created'] += opp_stats['people']
            self.stats['orgs_created'] += opp_stats['orgs']
            self.stats['relationships_created'] += opp_stats['relationships']
            
            if opp_stats['error']:
                self.stats['errors'] += 1
            
            # Small delay to avoid overwhelming the system
            time.sleep(0.1)
        
        # Get final stats
        final_stats = self.kg.get_network_statistics()
        
        # Get cost
        cost_stats = self.extractor.get_cost_estimate()
        self.stats['cost'] = cost_stats['estimated_cost']
        
        # Print results
        print()
        print_header("COLLECTION COMPLETE!")
        
        print(f"{Colors.BOLD}Opportunities:{Colors.END}")
        print(f"  Fetched: {self.stats['opportunities_fetched']}")
        print(f"  Processed: {self.stats['opportunities_processed']}")
        print(f"  Errors: {self.stats['errors']}")
        
        print(f"\n{Colors.BOLD}Entities Created:{Colors.END}")
        print(f"  People: {self.stats['people_created']}")
        print(f"  Organizations: {self.stats['orgs_created']}")
        print(f"  Relationships: {self.stats['relationships_created']}")
        
        print(f"\n{Colors.BOLD}Graph Growth:{Colors.END}")
        print(f"  People: {initial_stats.get('total_people', 0)} → {final_stats.get('total_people', 0)} (+{final_stats.get('total_people', 0) - initial_stats.get('total_people', 0)})")
        print(f"  Organizations: {initial_stats.get('total_organizations', 0)} → {final_stats.get('total_organizations', 0)} (+{final_stats.get('total_organizations', 0) - initial_stats.get('total_organizations', 0)})")
        print(f"  Relationships: {initial_stats.get('total_relationships', 0)} → {final_stats.get('total_relationships', 0)} (+{final_stats.get('total_relationships', 0) - initial_stats.get('total_relationships', 0)})")
        
        print(f"\n{Colors.BOLD}Cost:{Colors.END}")
        print(f"  Extraction cost: ${self.stats['cost']:.2f}")
        print(f"  Average per opportunity: ${self.stats['cost'] / max(self.stats['opportunities_processed'], 1):.4f}")
        
        print(f"\n{Colors.BOLD}Extraction Stats:{Colors.END}")
        print(f"  Claude calls: {cost_stats['extractions']}")
        print(f"  Tokens used: {cost_stats['tokens_total']:,}")
        
        print(f"\n{Colors.GREEN}{Colors.BOLD}✓ Your knowledge graph is now {final_stats.get('total_people', 0)} people strong!{Colors.END}")
        
        print(f"\n{Colors.CYAN}View your graph:{Colors.END}")
        print(f"  1. Open: http://localhost:7474")
        print(f"  2. Database: contactsgraphdb")
        print(f"  3. Query: MATCH (n) RETURN n LIMIT 100")
        
        print(f"\n{Colors.CYAN}Or see just the new contacts:{Colors.END}")
        print(f"  MATCH (n) WHERE n.source CONTAINS 'SAM.gov' RETURN n")
        
        # Save summary to file
        summary = {
            'timestamp': datetime.now().isoformat(),
            'opportunities_processed': self.stats['opportunities_processed'],
            'people_created': self.stats['people_created'],
            'orgs_created': self.stats['orgs_created'],
            'relationships_created': self.stats['relationships_created'],
            'cost': self.stats['cost'],
            'final_graph_size': {
                'people': final_stats.get('total_people', 0),
                'organizations': final_stats.get('total_organizations', 0),
                'relationships': final_stats.get('total_relationships', 0)
            }
        }
        
        with open('collection_summary.json', 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"\n{Colors.CYAN}Summary saved to: collection_summary.json{Colors.END}")
    
    def _guess_role_type(self, title: str) -> str:
        """Guess role type from title"""
        title_lower = title.lower()
        
        if any(word in title_lower for word in ['contracting officer', 'procurement', 'acquisition']):
            return 'Decision Maker'
        elif any(word in title_lower for word in ['program manager', 'project manager', 'pm']):
            return 'Technical Lead'
        elif any(word in title_lower for word in ['director', 'chief', 'executive', 'cio', 'cto']):
            return 'Executive'
        else:
            return 'Influencer'
    
    def _guess_influence_level(self, title: str) -> str:
        """Guess influence level from title"""
        title_lower = title.lower()
        
        if any(word in title_lower for word in ['chief', 'director', 'executive']):
            return 'Very High'
        elif any(word in title_lower for word in ['contracting officer', 'program manager']):
            return 'High'
        elif any(word in title_lower for word in ['manager', 'lead', 'supervisor']):
            return 'Medium'
        else:
            return 'Low'
    
    def close(self):
        """Close connections"""
        self.kg.close()


def main():
    parser = argparse.ArgumentParser(description='Collect opportunities from SAM.gov')
    parser.add_argument('--limit', type=int, default=10, help='Number of opportunities to collect (default: 10)')
    parser.add_argument('--days', type=int, default=30, help='Days back to search (default: 30)')
    parser.add_argument('--sam-key', type=str, help='SAM.gov API key (or set SAM_API_KEY env var)')
    parser.add_argument('--neo4j-password', type=str, help='Neo4j password (or set NEO4J_PASSWORD env var)')
    parser.add_argument('--anthropic-key', type=str, help='Anthropic API key (or set ANTHROPIC_API_KEY env var)')
    
    args = parser.parse_args()
    
    # Get credentials
    import os
    #sam_key = args.sam_key or os.getenv('SAM_API_KEY')
    #neo4j_password = args.neo4j_password or os.getenv('NEO4J_PASSWORD')
    #anthropic_key = args.anthropic_key or os.getenv('ANTHROPIC_API_KEY')

    sam_key = args.sam_key if hasattr(args, 'sam_key') and args.sam_key else os.getenv('SAM_API_KEY')
    neo4j_password = args.neo4j_password if hasattr(args, 'neo4j_password') and args.neo4j_password else os.getenv('NEO4J_PASSWORD')
    anthropic_key = args.anthropic_key if hasattr(args, 'anthropic_key') and args.anthropic_key else os.getenv('ANTHROPIC_API_KEY')

    
    # Prompt if missing
    if not sam_key:
        sam_key = input("Enter your SAM.gov API key: ").strip()
    
    if not neo4j_password:
        neo4j_password = input("Enter your Neo4j password: ").strip()
    
    if not anthropic_key:
        anthropic_key = input("Enter your Anthropic API key: ").strip()
    
    if not sam_key or not neo4j_password or not anthropic_key:
        print_error("Missing required credentials!")
        return
    
    # Run collection
    collector = OpportunityCollector(
        sam_api_key=sam_key,
        neo4j_password=neo4j_password,
        anthropic_api_key=anthropic_key
    )
    
    try:
        collector.run_collection(
            limit=args.limit,
            days_back=args.days
        )
    finally:
        collector.close()


if __name__ == "__main__":
    main()
