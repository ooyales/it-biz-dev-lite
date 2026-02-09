#!/usr/bin/env python3
"""
Environment-Aware Smart Collector
Loads credentials from .env file or environment variables

Usage:
    python collect_env.py --limit 50
    python collect_env.py --limit 100 --days 60
    python collect_env.py --clear-cache
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
import os

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✓ Loaded environment variables from .env file")
except ImportError:
    print("⚠️  python-dotenv not installed. Using system environment variables only.")
    print("   Install with: pip install python-dotenv")

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


class EnvSmartCollector:
    """Smart collector that loads config from environment"""
    
    def __init__(self, cache_file: str = "processed_opportunities.json"):
        self.cache_file = Path(cache_file)
        
        print_info("Loading configuration from environment...")
        
        # Load credentials from environment
        self.sam_api_key = os.getenv('SAM_API_KEY')
        self.neo4j_uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
        self.neo4j_user = os.getenv('NEO4J_USER', 'neo4j')
        self.neo4j_password = os.getenv('NEO4J_PASSWORD')
        self.neo4j_database = os.getenv('NEO4J_DATABASE', 'contactsgraphdb')
        self.anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
        
        # Validate credentials
        missing = []
        if not self.sam_api_key:
            missing.append('SAM_API_KEY')
        if not self.neo4j_password:
            missing.append('NEO4J_PASSWORD')
        if not self.anthropic_api_key:
            missing.append('ANTHROPIC_API_KEY')
        
        if missing:
            print_error(f"Missing environment variables: {', '.join(missing)}")
            print_info("Create a .env file with:")
            for var in missing:
                print(f"  {var}=your_key_here")
            raise ValueError("Missing required environment variables")
        
        print_success("Configuration loaded successfully")
        
        print_info("Initializing components...")
        
        # Load processed opportunities cache
        self.processed_opps = self._load_cache()
        print_info(f"Loaded cache: {len(self.processed_opps)} opportunities already processed")
        
        # Initialize extractor
        self.extractor = MinimalClaudeExtractor(api_key=self.anthropic_api_key)
        print_success("Entity extractor ready")
        
        # Initialize graph client
        self.kg = KnowledgeGraphClient(
            uri=self.neo4j_uri,
            user=self.neo4j_user,
            password=self.neo4j_password
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
        """Fetch opportunities from SAM.gov with IT-specific filtering"""
        
        print_info(f"Fetching IT opportunities from SAM.gov (limit: {limit})...")
        
        from_date = (datetime.now() - timedelta(days=days_back)).strftime('%m/%d/%Y')
        to_date = datetime.now().strftime('%m/%d/%Y')
        
        url = "https://api.sam.gov/opportunities/v2/search"
        
        all_opportunities = []
        
        # Updated IT-specific NAICS codes
        if not naics_codes:
            naics_env = os.getenv('NAICS_CODES', '541511,541512,541519,518210')
            naics_codes = naics_env.split(',')
        
        print_info(f"Using NAICS codes: {', '.join(naics_codes)}")
        
        for naics in naics_codes:
            if len(all_opportunities) >= limit * 3:  # Fetch 3x to account for filtering
                break
                
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
                all_opportunities.extend(opps)
                
                print_info(f"  NAICS {naics}: {len(opps)} opportunities")
                
                # Respect rate limits
                time.sleep(1)
                
            except requests.exceptions.RequestException as e:
                print_warning(f"Error fetching NAICS {naics}: {e}")
                continue
        
        # Apply IT-specific filters
        print_info(f"Applying IT-specific filters...")
        filtered_opportunities = self.filter_it_opportunities(all_opportunities)
        
        print_info(f"  Before filtering: {len(all_opportunities)} opportunities")
        print_info(f"  After filtering: {len(filtered_opportunities)} IT opportunities")
        print_info(f"  Filtered out: {len(all_opportunities) - len(filtered_opportunities)} non-IT")
        
        # Filter out already processed
        new_opportunities = []
        for opp in filtered_opportunities:
            opp_id = opp.get('noticeId', '')
            if opp_id not in self.processed_opps:
                new_opportunities.append(opp)
                if len(new_opportunities) >= limit:
                    break
        
        self.stats['opportunities_fetched'] = len(all_opportunities)
        self.stats['opportunities_filtered'] = len(all_opportunities) - len(filtered_opportunities)
        self.stats['opportunities_skipped'] = len(filtered_opportunities) - len(new_opportunities)
        
        print_success(f"Fetched {len(all_opportunities)} total opportunities")
        print_info(f"  Non-IT filtered out: {self.stats['opportunities_filtered']}")
        print_info(f"  Already processed: {self.stats['opportunities_skipped']}")
        print_info(f"  New IT opportunities: {len(new_opportunities)}")
        
        return new_opportunities
    
    def filter_it_opportunities(self, opportunities: List[Dict]) -> List[Dict]:
        """Filter for real IT opportunities using PSC codes, keywords, and exclusions"""
        
        # IT-related PSC codes (Product Service Codes)
        IT_PSC_CODES = [
            'D302',  # IT & Telecom - Systems Development
            'D307',  # IT & Telecom - IT Strategy & Architecture
            'D310',  # IT & Telecom - Cybersecurity
            'D311',  # IT & Telecom - Software Engineering
            'D312',  # IT & Telecom - Systems Analysis
            'D314',  # IT & Telecom - Data Management
            'D316',  # IT & Telecom - Network Management
            'D317',  # IT & Telecom - Web-Based Services
            'D318',  # IT & Telecom - Cloud Computing
            'D320',  # IT & Telecom - Database Design
            'D321',  # IT & Telecom - Programming
            'D399',  # IT & Telecom - Other
            '7030',  # ADP & Telecom Equipment
        ]
        
        # IT-related keywords (must have at least one)
        IT_KEYWORDS = [
            # Core IT
            'software', 'hardware', 'network', 'database', 'server', 'cloud',
            'application', 'system', 'data', 'cyber', 'security', 'infrastructure',
            
            # Development
            'development', 'programming', 'coding', 'engineering', 'devops',
            'agile', 'scrum', 'api', 'integration', 'web', 'mobile',
            
            # Modern Tech
            'artificial intelligence', 'machine learning', 'ai/ml', 'analytics',
            'big data', 'blockchain', 'iot', 'saas', 'paas', 'iaas',
            
            # IT Services
            'it support', 'help desk', 'technical support', 'system admin',
            'architecture', 'migration', 'modernization', 'digital transformation',
            
            # Specific Technologies
            'aws', 'azure', 'google cloud', 'kubernetes', 'docker', 
            'python', 'java', 'javascript', 'sql', 'oracle', 'salesforce',
            
            # IT Management
            'it service', 'itil', 'it operations', 'service desk',
            'incident management', 'configuration management'
        ]
        
        # Non-IT exclusion keywords (if present without IT context, exclude)
        EXCLUSION_KEYWORDS = [
            # Construction & Facilities
            'construction', 'renovation', 'building maintenance', 'hvac',
            'plumbing', 'electrical work', 'carpentry', 'painting',
            'roofing', 'flooring', 'demolition',
            
            # Janitorial & Cleaning
            'janitorial', 'custodial', 'cleaning services', 'sanitation',
            'housekeeping', 'waste removal', 'groundskeeping',
            
            # Facilities Management (non-IT)
            'facilities maintenance', 'grounds maintenance', 'landscaping',
            'pest control', 'snow removal', 'trash removal',
            
            # Medical & Healthcare Services
            'medical services', 'healthcare provider', 'nursing', 'clinical',
            'patient care', 'dental', 'pharmacy',
            
            # Food Services
            'food service', 'catering', 'cafeteria', 'dining',
            
            # Security Guards (not cybersecurity)
            'security guard', 'physical security officer', 'armed guard',
            
            # Other Non-IT
            'transportation', 'moving services', 'freight', 'shipping',
            'printing services', 'courier', 'mail service'
        ]
        
        filtered = []
        
        for opp in opportunities:
            title = opp.get('title', '').lower()
            description = opp.get('description', '').lower()
            psc_code = opp.get('classificationCode', '')
            
            # Combine title and description for checking
            full_text = f"{title} {description}"
            
            # Check 1: PSC Code (if present, automatic include)
            has_it_psc = False
            if psc_code:
                # Check if PSC starts with any IT code
                has_it_psc = any(psc_code.startswith(code[:4]) for code in IT_PSC_CODES)
            
            # Check 2: IT Keywords (must have at least one)
            has_it_keyword = any(keyword in full_text for keyword in IT_KEYWORDS)
            
            # Check 3: Exclusion Keywords (exclude if present without IT context)
            has_exclusion = any(keyword in full_text for keyword in EXCLUSION_KEYWORDS)
            
            # Decision logic:
            # - If has IT PSC code: Include (even with exclusions)
            # - Else if has IT keyword AND no exclusions: Include
            # - Else if has IT keyword AND has exclusions: Only include if multiple IT keywords
            # - Else: Exclude
            
            if has_it_psc:
                filtered.append(opp)
            elif has_it_keyword and not has_exclusion:
                filtered.append(opp)
            elif has_it_keyword and has_exclusion:
                # Check if there are multiple IT keywords (likely IT despite exclusion keyword)
                it_keyword_count = sum(1 for keyword in IT_KEYWORDS if keyword in full_text)
                if it_keyword_count >= 3:  # At least 3 IT keywords = probably IT
                    filtered.append(opp)
            
        return filtered
    
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
                        
                        if entity.metadata:
                            person_data.update({
                                k: v for k, v in entity.metadata.items()
                                if v and k in ['email', 'phone', 'title', 'organization']
                            })
                        
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
                        
                except Exception:
                    continue
            
            # Store relationships
            for rel in relationships:
                try:
                    subject_matches = self.kg.search_people(rel.subject)
                    
                    if subject_matches:
                        subject_id = subject_matches[0]['id']
                        
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
                        
                except Exception:
                    continue
            
            self.processed_opps.add(opp_id)
            
        except Exception as e:
            opp_stats['error'] = str(e)
        
        return opp_stats
    
    def run_collection(
        self,
        limit: int = None,
        naics_codes: List[str] = None,
        days_back: int = None
    ):
        """Run full collection pipeline"""
        
        # Use environment defaults if not specified
        if limit is None:
            limit = int(os.getenv('DEFAULT_LIMIT', 10))
        if days_back is None:
            days_back = int(os.getenv('DEFAULT_DAYS_BACK', 30))
        
        print_header("SMART SAM.GOV COLLECTION (ENVIRONMENT-AWARE)")
        
        initial_stats = self.kg.get_network_statistics()
        print_info(f"Starting graph state:")
        print(f"  People: {initial_stats.get('total_people', 0)}")
        print(f"  Organizations: {initial_stats.get('total_organizations', 0)}")
        print(f"  Relationships: {initial_stats.get('total_relationships', 0)}")
        print(f"  Previously processed opportunities: {len(self.processed_opps)}")
        
        print()
        opportunities = self.fetch_opportunities(
            limit=limit,
            naics_codes=naics_codes,
            days_back=days_back
        )
        
        if not opportunities:
            print_warning("No new opportunities to process!")
            print_info("Try:")
            print_info("  1. Increase --days parameter")
            print_info("  2. Increase --limit parameter")
            print_info("  3. Clear cache: python collect_env.py --clear-cache")
            return
        
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
            
            if self.stats['opportunities_processed'] % 10 == 0:
                self._save_cache()
            
            time.sleep(0.1)
        
        self._save_cache()
        
        final_stats = self.kg.get_network_statistics()
        cost_stats = self.extractor.get_cost_estimate()
        self.stats['cost'] = cost_stats['estimated_cost']
        
        print()
        print_header("COLLECTION COMPLETE!")
        
        print(f"{Colors.BOLD}Opportunities:{Colors.END}")
        print(f"  Fetched: {self.stats['opportunities_fetched']}")
        print(f"  Already processed (skipped): {self.stats['opportunities_skipped']}")
        print(f"  New processed: {self.stats['opportunities_processed']}")
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
        
        if self.stats['opportunities_skipped'] > 0:
            saved = self.stats['opportunities_skipped'] * 0.02
            print(f"\n{Colors.BOLD}Cost Savings:{Colors.END}")
            print(f"  Skipped {self.stats['opportunities_skipped']} already-processed")
            print(f"  Estimated savings: ${saved:.2f}")
        
        print(f"\n{Colors.GREEN}{Colors.BOLD}✓ Your knowledge graph is now {final_stats.get('total_people', 0)} people strong!{Colors.END}")
        
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
        self.kg.close()


def main():
    parser = argparse.ArgumentParser(description='Environment-aware smart collector')
    parser.add_argument('--limit', type=int, help='Number of NEW opportunities to collect')
    parser.add_argument('--days', type=int, help='Days back to search')
    parser.add_argument('--clear-cache', action='store_true', help='Clear processed opportunities cache')
    
    args = parser.parse_args()
    
    if args.clear_cache:
        cache_file = Path("processed_opportunities.json")
        if cache_file.exists():
            cache_file.unlink()
            print_success("Cache cleared!")
        else:
            print_info("No cache file to clear")
        return
    
    try:
        collector = EnvSmartCollector()
        collector.run_collection(
            limit=args.limit,
            days_back=args.days
        )
    except ValueError as e:
        print_error(str(e))
        return
    finally:
        try:
            collector.close()
        except:
            pass


if __name__ == "__main__":
    main()
