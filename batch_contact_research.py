#!/usr/bin/env python3
"""
Batch Contact Research

Researches all contacts in your database using the Contact Research Agent.
Runs overnight or during off-hours. Caches results in Neo4j.

Usage:
    python batch_contact_research.py --limit 100       # Research first 100
    python batch_contact_research.py --all             # Research everyone
    python batch_contact_research.py --filter "Navy"   # Only Navy contacts
    python batch_contact_research.py --skip-cached     # Skip already-researched
"""

import os
import sys
import json
import sqlite3
import argparse
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict

# Add knowledge_graph to path
sys.path.insert(0, 'knowledge_graph')

from contact_research_agent import ContactResearchAgent


class BatchContactResearcher:
    """Batch research contacts from SQLite database"""
    
    PROGRESS_FILE = 'data/batch_research_progress.json'
    
    def __init__(self, db_path: str = 'data/contacts.db'):
        self.db_path = db_path
        self.agent = ContactResearchAgent()
        
        # Stats
        self.researched = 0
        self.cached = 0
        self.errors = 0
        self.total_cost_estimate = 0
        
        # Load progress from file (tracks which contacts have been attempted)
        self.progress = self._load_progress()
    
    def _load_progress(self) -> dict:
        """Load progress file that tracks completed contacts"""
        try:
            with open(self.PROGRESS_FILE) as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {'completed': [], 'failed': []}
    
    def _save_progress(self):
        """Save progress to file"""
        import json
        Path(self.PROGRESS_FILE).parent.mkdir(exist_ok=True)
        with open(self.PROGRESS_FILE, 'w') as f:
            json.dump(self.progress, f, indent=2)
        
    def get_contacts(self, 
                    limit: int = None, 
                    filter_text: str = None,
                    skip_cached: bool = False) -> List[Dict]:
        """Fetch contacts from SQLite"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT * FROM contacts WHERE 1=1"
        params = []
        
        # Filter by organization/agency/name
        if filter_text:
            query += " AND (name LIKE ? OR organization LIKE ? OR agency LIKE ?)"
            pattern = f"%{filter_text}%"
            params.extend([pattern, pattern, pattern])
        
        # Skip contacts without enough info
        query += " AND name IS NOT NULL AND name != ''"
        
        # Order by relationship strength (research important contacts first)
        query += " ORDER BY CASE relationship_strength "
        query += "WHEN 'Strong' THEN 1 "
        query += "WHEN 'Medium' THEN 2 "
        query += "ELSE 3 END, name"
        
        if limit:
            query += f" LIMIT {limit}"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        contacts = [dict(row) for row in rows]
        
        # Skip cached if requested (uses progress file)
        if skip_cached:
            completed_names = set(self.progress.get('completed', []))
            before = len(contacts)
            contacts = [c for c in contacts if c.get('name', '') not in completed_names]
            skipped = before - len(contacts)
            if skipped > 0:
                print(f"   Skipping {skipped} already-researched contacts")
        
        return contacts
    
    def _is_cached(self, contact: Dict) -> bool:
        """Check if contact has recent cached research"""
        cached = self.agent._get_cached_research(contact)
        return cached is not None
    
    def research_batch(self, 
                      contacts: List[Dict],
                      delay_seconds: float = 1.0,
                      stop_on_error: bool = False) -> Dict:
        """
        Research a batch of contacts
        
        Args:
            contacts: List of contact dicts
            delay_seconds: Delay between requests (rate limiting)
            stop_on_error: Stop on first error (default: continue)
        
        Returns:
            Summary statistics
        """
        total = len(contacts)
        
        print("=" * 70)
        print("BATCH CONTACT RESEARCH")
        print("=" * 70)
        print(f"  Total contacts: {total}")
        print(f"  Already completed: {len(self.progress.get('completed', []))}")
        print(f"  Estimated cost: ${total * 0.017:.2f}")
        print(f"  Estimated time: {total * (delay_seconds + 3) / 60:.1f} minutes")
        print()
        
        response = input("Continue? (y/n): ")
        if response.lower() != 'y':
            print("Cancelled.")
            return None
        
        print()
        print(f"🚀 Starting batch research...")
        print(f"   Rate limit: {delay_seconds}s between requests")
        print(f"   Auto-backoff on rate limit errors")
        print()
        
        start_time = time.time()
        consecutive_errors = 0
        current_delay = delay_seconds
        i = 0
        
        for i, contact in enumerate(contacts, 1):
            try:
                name = contact.get('name', 'Unknown')
                print(f"[{i}/{total}] {name}")
                
                # Research (uses cache if available)
                profile = self.agent.research_contact(contact, force_refresh=False)
                
                # Check if research actually succeeded
                if 'error' in profile:
                    self.errors += 1
                    consecutive_errors += 1
                    print(f"   ❌ Error: {profile['error']}")
                elif profile.get('confidence') == 'low' and profile.get('method') == 'fallback':
                    # This was a rate limit failure that returned a fallback
                    self.errors += 1
                    consecutive_errors += 1
                    print(f"   ⚠️  Got fallback response (likely rate limited)")
                else:
                    # Success!
                    self.researched += 1
                    self.total_cost_estimate += 0.017
                    consecutive_errors = 0
                    current_delay = delay_seconds  # Reset delay
                    
                    # Track as completed
                    if name not in self.progress['completed']:
                        self.progress['completed'].append(name)
                        self._save_progress()
                
                # Rate limit backoff
                if consecutive_errors >= 2:
                    current_delay = min(current_delay * 2, 120)  # Double delay, max 2 min
                    print(f"   🔄 Backing off: waiting {current_delay:.0f}s (consecutive errors: {consecutive_errors})")
                
                if consecutive_errors >= 5:
                    print(f"\n   ❌ Too many consecutive errors ({consecutive_errors}). Stopping.")
                    print(f"   💡 Try again later or increase --delay")
                    break
                
                # Wait between requests
                if i < total:
                    time.sleep(current_delay)
                
            except KeyboardInterrupt:
                print("\n⚠️  Interrupted by user")
                self._save_progress()
                break
            
            except Exception as e:
                self.errors += 1
                consecutive_errors += 1
                print(f"   ❌ Error: {e}")
                
                if stop_on_error:
                    print("Stopping due to error")
                    break
                
                continue
        
        elapsed = time.time() - start_time
        
        # Save final progress
        self._save_progress()
        
        print()
        print("=" * 70)
        print("BATCH RESEARCH COMPLETE")
        print("=" * 70)
        print(f"  Total processed: {i}")
        print(f"  New research: {self.researched}")
        print(f"  Used cache: {self.cached}")
        print(f"  Errors: {self.errors}")
        print(f"  Estimated cost: ${self.total_cost_estimate:.2f}")
        print(f"  Time elapsed: {elapsed / 60:.1f} minutes")
        print(f"  Total completed (all runs): {len(self.progress.get('completed', []))}")
        print()
        
        return {
            'total_processed': i,
            'researched': self.researched,
            'cached': self.cached,
            'errors': self.errors,
            'estimated_cost': self.total_cost_estimate,
            'elapsed_seconds': elapsed
        }
    
    def close(self):
        self.agent.close()


def main():
    parser = argparse.ArgumentParser(
        description='Batch research contacts using AI'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Research all contacts (default: first 100)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=100,
        help='Maximum contacts to research (default: 100)'
    )
    parser.add_argument(
        '--filter',
        type=str,
        default=None,
        help='Filter contacts by name/org/agency (e.g., "Navy")'
    )
    parser.add_argument(
        '--skip-cached',
        action='store_true',
        help='Skip contacts with cached research'
    )
    parser.add_argument(
        '--delay',
        type=float,
        default=1.0,
        help='Seconds between API calls (default: 1.0)'
    )
    parser.add_argument(
        '--stop-on-error',
        action='store_true',
        help='Stop on first error (default: continue)'
    )
    
    args = parser.parse_args()
    
    # Determine limit
    limit = None if args.all else args.limit
    
    # Initialize researcher
    researcher = BatchContactResearcher()
    
    # Get contacts
    print("📋 Loading contacts from database...")
    contacts = researcher.get_contacts(
        limit=limit,
        filter_text=args.filter,
        skip_cached=args.skip_cached
    )
    
    if not contacts:
        print("❌ No contacts found matching criteria")
        return
    
    print(f"   Found {len(contacts)} contacts to research")
    print()
    
    # Show preview
    if len(contacts) <= 10:
        print("Contacts to research:")
        for c in contacts:
            print(f"  - {c.get('name')} ({c.get('organization', 'N/A')})")
        print()
    else:
        print("First 10 contacts:")
        for c in contacts[:10]:
            print(f"  - {c.get('name')} ({c.get('organization', 'N/A')})")
        print(f"  ... and {len(contacts) - 10} more")
        print()
    
    # Run batch research
    try:
        results = researcher.research_batch(
            contacts,
            delay_seconds=args.delay,
            stop_on_error=args.stop_on_error
        )
        
        if results:
            # Save summary
            import json
            from pathlib import Path
            
            Path('knowledge_graph').mkdir(exist_ok=True)
            summary_file = Path('knowledge_graph') / f'batch_research_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            
            with open(summary_file, 'w') as f:
                json.dump(results, f, indent=2)
            
            print(f"💾 Summary saved to: {summary_file}")
            print()
            print("✓ Batch research complete!")
            print("  All research is cached in Neo4j")
            print("  Use the Contact Intelligence page to view profiles")
            print()
        
    finally:
        researcher.close()


if __name__ == '__main__':
    main()
