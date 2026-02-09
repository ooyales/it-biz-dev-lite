#!/usr/bin/env python3
"""
Enhanced SAM.gov Opportunity Collector with Deduplication
Tracks processed opportunities to avoid re-extraction

Features:
- Skips already-processed opportunities
- Saves processed IDs to cache file
- Only extracts from new opportunities
- Continues from where you left off
"""

import sys
sys.path.append('..')

from nlp.minimal_claude_extractor import MinimalClaudeExtractor
from graph.neo4j_client import KnowledgeGraphClient, generate_person_id, generate_org_id
import requests
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Set
import time
from tqdm import tqdm
import json
from pathlib import Path

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


class SmartOpportunityCollector:
    """Enhanced collector with deduplication"""
    
    def __init__(
        self,
        sam_api_key: str,
        neo4j_password: str,
        anthropic_api_key: str = None,
        cache_file: str = "processed_opportunities.json"
    ):
        self.sam_api_key = sam_api_key
        self.cache_file = Path(cache_file)
        
        print_info("Initializing components...")
        
        # Load processed opportunities cache
        self.processed_opps = self._load_cache()
        print_info(f"Loaded cache: {len(self.processed_opps)} opportunities already processed")
        
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
            'opportunities_skipped': 0,
            'opportunities_processed': 0,
            'people_created': 0,
            'orgs_created': 0,
            'relationships_created': 0,
            'errors': 0,
            'cost': 0.0
        }
    
    def _load_cache(self) -> Set[str]:
        """Load set of already-processed opportunity IDs"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r') as f:
                    data = json.load(f)
                    return set(data.get('processed_ids', []))
            except Exception as e:
                print_warning(f"Could not load cache: {e}")
                return set()
        return set()
    
    def _save_cache(self):
        """Save processed opportunity IDs"""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump({
                    'processed_ids': list(self.processed_opps),
                    'last_updated': datetime.now().isoformat(),
                    'total_processed': len(self.processed_opps)
                }, f, indent=2)
        except Exception as e:
            print_warning(f"Could not save cache: {e}")
    
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
            if len(all_opportunities) >= limit * 2:  # Fetch 2x to account for already processed
                break
                
            try:
                params = {
                    'api_key': self.sam_api_key,
                    'postedFrom': from_date,
                    'postedTo': to_date,
                    'naicsCode': naics,
                    'limit': 100  # Get max per NAICS
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
        
        # Filter out already processed
        new_opportunities = []
        for opp in all_opportunities:
            opp_id = opp.get('noticeId', '')
            if opp_id not in self.processed_opps:
                new_opportunities.append(opp)
                if len(new_opportunities) >= limit:
                    break
        
        self.stats['opportunities_fetched'] = len(all_opportunities)
        self.stats['opportunities_skipped'] = len(all_opportunities) - len(new_opportunities)
        
        print_success(f"Fetched {len(all_opportunities)} total opportunities")
        print_info(f"  Already processed: {self.stats['opportunities_skipped']}")
        print_info(f"  New to process: {len(new_opportunities)}")
        
        return new_opportunities
    
    def process_opportunity(self, opp: Dict) -> Dict:
        """Process one opportunity: extract entities and store in graph"""
        
        opp_stats = {
            'people': 0,
            'orgs': 0,
            'relationships': 0,
            'error': None
        }
        
        opp_id = opp.get('noticeId', 'unknown')
        
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
                # Mark as processed even if skipped
                self.processed_opps.add(opp_id)
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
                            'source': f"SAM.gov: {opp_id}",
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
                            'source': f"SAM.gov: {opp_id}",
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
                                'source': f"SAM.gov: {opp_id}"
                            }
                        )
                        opp_stats['relationships'] += 1
                        
                except Exception as e:
                    # Skip individual relationship errors
                    continue
            
            # Mark as processed
            self.processed_opps.add(opp_id)
            
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
        
        print_header("SMART SAM.GOV COLLECTION (WITH DEDUPLICATION)")
        
        # Get initial stats
        initial_stats = self.kg.get_network_statistics()
        print_info(f"Starting graph state:")
        print(f"  People: {initial_stats.get('total_people', 0)}")
        print(f"  Organizations: {initial_stats.get('total_organizations', 0)}")
        print(f"  Relationships: {initial_stats.get('total_relationships', 0)}")
        print(f"  Previously processed opportunities: {len(self.processed_opps)}")
        
        # Fetch opportunities
        print()
        opportunities = self.fetch_opportunities(
            limit=limit,
            naics_codes=naics_codes,
            days_back=days_back
        )
        
        if not opportunities:
            print_warning("No new opportunities to process!")
            print_info("Try:")
            print_info("  1. Increase --days parameter (search further back)")
            print_info("  2. Increase --limit parameter")
            print_info("  3. Clear cache: rm processed_opportunities.json")
            return
        
        # Process opportunities with progress bar
        print()
        print_info(f"Processing {len(opportunities)} NEW opportunities...")
        print()
        
        for opp in tqdm(opportunities, desc="Processing", unit="opp"):
            opp_stats = self.process_opportunity(opp)
            
            self.stats['opportunities_processed'] += 1
            self.stats['people_created'] += opp_stats['people']
            self.stats['orgs_created'] += opp_stats['orgs']
            self.stats['relationships_created'] += opp_stats['relationships']
            
            if opp_stats['error']:
                self.stats['errors'] += 1
            
            # Save cache periodically
            if self.stats['opportunities_processed'] % 10 == 0:
                self._save_cache()
            
            # Small delay to avoid overwhelming the system
            time.sleep(0.1)
        
        # Save final cache
        self._save_cache()
        
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
        print(f"  Already processed (skipped): {self.stats['opportunities_skipped']}")
        print(f"  New processed: {self.stats['opportunities_processed']}")
        print(f"  Errors: {self.stats['errors']}")
        print(f"  Total in cache: {len(self.processed_opps)}")
        
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
        if self.stats['opportunities_processed'] > 0:
            print(f"  Average per opportunity: ${self.stats['cost'] / self.stats['opportunities_processed']:.4f}")
        
        print(f"\n{Colors.BOLD}Cost Savings from Deduplication:{Colors.END}")
        if self.stats['opportunities_skipped'] > 0:
            saved = self.stats['opportunities_skipped'] * 0.02  # Assume $0.02 per opp
            print(f"  Skipped {self.stats['opportunities_skipped']} already-processed opportunities")
            print(f"  Estimated savings: ${saved:.2f}")
        else:
            print(f"  All opportunities were new!")
        
        print(f"\n{Colors.GREEN}{Colors.BOLD}✓ Your knowledge graph is now {final_stats.get('total_people', 0)} people strong!{Colors.END}")
        
        print(f"\n{Colors.CYAN}Cache file: {self.cache_file}{Colors.END}")
        print(f"  To reset and reprocess everything: rm {self.cache_file}")
        
        # Save summary to file
        summary = {
            'timestamp': datetime.now().isoformat(),
            'opportunities_fetched': self.stats['opportunities_fetched'],
            'opportunities_skipped': self.stats['opportunities_skipped'],
            'opportunities_processed': self.stats['opportunities_processed'],
            'people_created': self.stats['people_created'],
            'orgs_created': self.stats['orgs_created'],
            'relationships_created': self.stats['relationships_created'],
            'cost': self.stats['cost'],
            'total_cached': len(self.processed_opps),
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
    parser = argparse.ArgumentParser(description='Smart SAM.gov collector with deduplication')
    parser.add_argument('--limit', type=int, default=10, help='Number of NEW opportunities to collect')
    parser.add_argument('--days', type=int, default=30, help='Days back to search')
    parser.add_argument('--clear-cache', action='store_true', help='Clear processed opportunities cache')
    parser.add_argument('--sam-key', type=str, help='SAM.gov API key')
    parser.add_argument('--neo4j-password', type=str, help='Neo4j password')
    parser.add_argument('--anthropic-key', type=str, help='Anthropic API key')
    
    args = parser.parse_args()
    
    # Clear cache if requested
    if args.clear_cache:
        cache_file = Path("processed_opportunities.json")
        if cache_file.exists():
            cache_file.unlink()
            print_success("Cache cleared!")
        else:
            print_info("No cache file to clear")
        return
    
    # Get credentials
    import os
    sam_key = args.sam_key or os.getenv('SAM_API_KEY')
    neo4j_password = args.neo4j_password or os.getenv('NEO4J_PASSWORD')
    anthropic_key = args.anthropic_key or os.getenv('ANTHROPIC_API_KEY')
    
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
    collector = SmartOpportunityCollector(
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
