#!/usr/bin/env python3
"""
SAM.gov Daily Bulk Fetcher
Fetches ALL recent opportunities once per day, stores locally
Then dashboard filters from local cache - fast and no rate limits!
"""

import requests
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
import logging
import yaml
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_PATH = "data/team_dashboard.db"
CONFIG_PATH = "config.yaml"

class BulkOpportunityFetcher:
    """Fetches all opportunities in bulk, stores locally for fast filtering"""
    
    def __init__(self, config_path=CONFIG_PATH):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.api_key = self.config['sam_gov']['api_key']
        self.base_url = "https://api.sam.gov/opportunities/v2/search"
        
    def fetch_all_opportunities(self, days_back=30, batch_size=100):
        """
        Fetch ALL opportunities from SAM.gov for the past N days
        Does pagination automatically to get everything
        
        Args:
            days_back: How many days back to fetch
            batch_size: Records per API call (max 100)
        
        Returns:
            List of all opportunities
        """
        from_date = (datetime.now() - timedelta(days=days_back)).strftime('%m/%d/%Y')
        to_date = datetime.now().strftime('%m/%d/%Y')
        
        logger.info(f"Starting bulk fetch: {from_date} to {to_date}")
        
        all_opportunities = []
        offset = 0
        total_fetched = 0
        
        while True:
            params = {
                'api_key': self.api_key,
                'postedFrom': from_date,
                'postedTo': to_date,
                'limit': batch_size,
                'offset': offset
            }
            
            try:
                logger.info(f"Fetching batch at offset {offset}...")
                response = requests.get(self.base_url, params=params, timeout=30)
                response.raise_for_status()
                
                data = response.json()
                opportunities = data.get('opportunitiesData', [])
                total_records = data.get('totalRecords', 0)
                
                if not opportunities:
                    logger.info("No more opportunities to fetch")
                    break
                
                all_opportunities.extend(opportunities)
                total_fetched += len(opportunities)
                
                logger.info(f"Fetched {len(opportunities)} opportunities (total: {total_fetched}/{total_records})")
                
                # Check if we got everything
                if total_fetched >= total_records:
                    logger.info("Fetched all available opportunities")
                    break
                
                # Move to next batch
                offset += batch_size
                
                # Rate limiting - wait between requests
                time.sleep(2)
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching opportunities: {e}")
                break
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                break
        
        logger.info(f"Bulk fetch complete: {len(all_opportunities)} opportunities")
        return all_opportunities
    
    def store_opportunities_bulk(self, opportunities):
        """
        Store all opportunities in database
        Stores RAW data for flexible filtering later
        """
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # Create raw opportunities table if not exists
        c.execute('''
            CREATE TABLE IF NOT EXISTS raw_opportunities (
                notice_id TEXT PRIMARY KEY,
                title TEXT,
                type TEXT,
                naics_code TEXT,
                agency TEXT,
                posted_date TEXT,
                deadline TEXT,
                contract_value INTEGER,
                set_aside TEXT,
                description TEXT,
                raw_json TEXT,
                fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        inserted = 0
        updated = 0
        
        for opp in opportunities:
            notice_id = opp.get('noticeId')
            if not notice_id:
                continue
            
            # Extract key fields
            title = opp.get('title', '')
            opp_type = opp.get('type', '')
            naics_code = opp.get('naicsCode', '')
            agency = opp.get('fullParentPathName', '')
            posted_date = opp.get('postedDate', '')
            deadline = opp.get('responseDeadLine', '')
            set_aside = opp.get('typeOfSetAside', '')
            description = opp.get('description', '')
            
            # Extract contract value
            contract_value = 0
            award = opp.get('award', {})
            if isinstance(award, dict):
                amount = award.get('amount', '0')
                try:
                    contract_value = int(str(amount).replace('$', '').replace(',', '').strip())
                except:
                    contract_value = 0
            
            # Store full JSON for future flexibility
            raw_json = json.dumps(opp)
            
            # Insert or update
            try:
                c.execute('''
                    INSERT INTO raw_opportunities 
                    (notice_id, title, type, naics_code, agency, posted_date, 
                     deadline, contract_value, set_aside, description, raw_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(notice_id) DO UPDATE SET
                        title=excluded.title,
                        type=excluded.type,
                        naics_code=excluded.naics_code,
                        agency=excluded.agency,
                        posted_date=excluded.posted_date,
                        deadline=excluded.deadline,
                        contract_value=excluded.contract_value,
                        set_aside=excluded.set_aside,
                        description=excluded.description,
                        raw_json=excluded.raw_json,
                        last_updated=CURRENT_TIMESTAMP
                ''', (notice_id, title, opp_type, naics_code, agency, posted_date,
                      deadline, contract_value, set_aside, description, raw_json))
                
                if c.rowcount == 1:
                    inserted += 1
                else:
                    updated += 1
                    
            except Exception as e:
                logger.error(f"Error storing opportunity {notice_id}: {e}")
        
        conn.commit()
        conn.close()
        
        logger.info(f"Stored {inserted} new, updated {updated} existing opportunities")
        return inserted, updated
    
    def save_fetch_metadata(self, total_fetched, inserted, updated):
        """Track when bulk fetch was run"""
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS fetch_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fetch_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_fetched INTEGER,
                inserted INTEGER,
                updated INTEGER,
                fetch_type TEXT
            )
        ''')
        
        c.execute('''
            INSERT INTO fetch_history (total_fetched, inserted, updated, fetch_type)
            VALUES (?, ?, ?, 'daily_bulk')
        ''', (total_fetched, inserted, updated))
        
        conn.commit()
        conn.close()


class LocalOpportunityFilter:
    """Filter opportunities from local database - FAST!"""
    
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH)
        self.conn.row_factory = sqlite3.Row
    
    def filter_opportunities(self, 
                            naics_codes=None,
                            agencies=None,
                            opportunity_types=None,
                            min_value=None,
                            max_value=None,
                            keywords=None,
                            set_asides=None,
                            posted_after=None,
                            deadline_before=None):
        """
        Filter opportunities using local SQL queries - instant results!
        
        All parameters are optional. If None, that filter is skipped.
        
        Args:
            naics_codes: List of NAICS codes ['541512', '541519']
            agencies: List of agency names
            opportunity_types: List of types ['Solicitation', 'Presolicitation']
            min_value: Minimum contract value
            max_value: Maximum contract value
            keywords: List of keywords to search in title/description
            set_asides: List of set-aside types ['Small Business', '8(a)']
            posted_after: Date string 'YYYY-MM-DD'
            deadline_before: Date string 'YYYY-MM-DD'
        
        Returns:
            List of matching opportunities
        """
        query = "SELECT * FROM raw_opportunities WHERE 1=1"
        params = []
        
        # NAICS filter
        if naics_codes:
            placeholders = ','.join('?' * len(naics_codes))
            query += f" AND naics_code IN ({placeholders})"
            params.extend(naics_codes)
        
        # Agency filter
        if agencies:
            placeholders = ','.join('?' * len(agencies))
            query += f" AND agency IN ({placeholders})"
            params.extend(agencies)
        
        # Type filter
        if opportunity_types:
            placeholders = ','.join('?' * len(opportunity_types))
            query += f" AND type IN ({placeholders})"
            params.extend(opportunity_types)
        
        # Value range filter
        if min_value is not None:
            query += " AND contract_value >= ?"
            params.append(min_value)
        
        if max_value is not None:
            query += " AND contract_value <= ?"
            params.append(max_value)
        
        # Keywords filter (search in title and description)
        if keywords:
            keyword_conditions = []
            for keyword in keywords:
                keyword_conditions.append("(title LIKE ? OR description LIKE ?)")
                params.append(f"%{keyword}%")
                params.append(f"%{keyword}%")
            query += " AND (" + " OR ".join(keyword_conditions) + ")"
        
        # Set-aside filter
        if set_asides:
            placeholders = ','.join('?' * len(set_asides))
            query += f" AND set_aside IN ({placeholders})"
            params.extend(set_asides)
        
        # Date filters
        if posted_after:
            query += " AND posted_date >= ?"
            params.append(posted_after)
        
        if deadline_before:
            query += " AND deadline <= ?"
            params.append(deadline_before)
        
        # Execute query
        c = self.conn.cursor()
        c.execute(query, params)
        
        # Convert to list of dicts
        opportunities = []
        for row in c.fetchall():
            opp = dict(row)
            # Parse JSON for full data if needed
            if opp.get('raw_json'):
                try:
                    opp['full_data'] = json.loads(opp['raw_json'])
                except:
                    pass
            opportunities.append(opp)
        
        return opportunities
    
    def get_filter_stats(self):
        """Get statistics for building filter dropdowns"""
        c = self.conn.cursor()
        
        stats = {}
        
        # Available NAICS codes
        c.execute("SELECT DISTINCT naics_code, COUNT(*) as count FROM raw_opportunities GROUP BY naics_code ORDER BY count DESC")
        stats['naics_codes'] = [{'code': row[0], 'count': row[1]} for row in c.fetchall()]
        
        # Available agencies
        c.execute("SELECT DISTINCT agency, COUNT(*) as count FROM raw_opportunities GROUP BY agency ORDER BY count DESC LIMIT 20")
        stats['agencies'] = [{'name': row[0], 'count': row[1]} for row in c.fetchall()]
        
        # Available types
        c.execute("SELECT DISTINCT type, COUNT(*) as count FROM raw_opportunities GROUP BY type ORDER BY count DESC")
        stats['types'] = [{'type': row[0], 'count': row[1]} for row in c.fetchall()]
        
        # Value ranges
        c.execute("SELECT MIN(contract_value), MAX(contract_value), AVG(contract_value) FROM raw_opportunities WHERE contract_value > 0")
        row = c.fetchone()
        stats['value_range'] = {
            'min': row[0],
            'max': row[1],
            'avg': row[2]
        }
        
        # Set-asides
        c.execute("SELECT DISTINCT set_aside, COUNT(*) as count FROM raw_opportunities WHERE set_aside != '' GROUP BY set_aside ORDER BY count DESC")
        stats['set_asides'] = [{'type': row[0], 'count': row[1]} for row in c.fetchall()]
        
        return stats
    
    def close(self):
        self.conn.close()


def run_daily_bulk_fetch():
    """Main function to run daily bulk fetch"""
    
    print("\n" + "="*70)
    print("SAM.GOV DAILY BULK FETCH")
    print("="*70 + "\n")
    
    fetcher = BulkOpportunityFetcher()
    
    # Fetch all opportunities from last 30 days
    print("Step 1: Fetching all opportunities from SAM.gov...")
    opportunities = fetcher.fetch_all_opportunities(days_back=30)
    
    if not opportunities:
        print("No opportunities fetched. Check API key and connectivity.")
        return
    
    print(f"\n✓ Fetched {len(opportunities)} opportunities")
    
    # Store in database
    print("\nStep 2: Storing in local database...")
    inserted, updated = fetcher.store_opportunities_bulk(opportunities)
    
    print(f"✓ Stored {inserted} new opportunities")
    print(f"✓ Updated {updated} existing opportunities")
    
    # Save metadata
    fetcher.save_fetch_metadata(len(opportunities), inserted, updated)
    
    print("\n" + "="*70)
    print("BULK FETCH COMPLETE")
    print("="*70)
    print(f"\nTotal opportunities in database: {inserted + updated}")
    print("Dashboard can now filter these instantly without API calls!")
    print("\nNext steps:")
    print("  • Dashboard will filter from local database")
    print("  • No rate limits during the day")
    print("  • Instant filter results")
    print("  • Run this script daily (via cron)")
    print()


def demo_local_filtering():
    """Demo the local filtering capabilities"""
    
    print("\n" + "="*70)
    print("LOCAL FILTERING DEMO")
    print("="*70 + "\n")
    
    filter_engine = LocalOpportunityFilter()
    
    # Get stats
    print("Available filters:")
    stats = filter_engine.get_filter_stats()
    
    print(f"\nNAICS Codes: {len(stats['naics_codes'])} unique codes")
    for item in stats['naics_codes'][:5]:
        print(f"  • {item['code']}: {item['count']} opportunities")
    
    print(f"\nAgencies: {len(stats['agencies'])} unique agencies")
    for item in stats['agencies'][:5]:
        print(f"  • {item['name']}: {item['count']} opportunities")
    
    print(f"\nTypes: {len(stats['types'])} types")
    for item in stats['types']:
        print(f"  • {item['type']}: {item['count']} opportunities")
    
    # Example filter 1: IT contracts over $500K
    print("\n" + "-"*70)
    print("Example Filter 1: IT contracts (NAICS 541512) over $500K")
    results = filter_engine.filter_opportunities(
        naics_codes=['541512'],
        min_value=500000
    )
    print(f"Results: {len(results)} opportunities")
    if results:
        print(f"Sample: {results[0]['title'][:60]}...")
    
    # Example filter 2: DoD cloud contracts
    print("\n" + "-"*70)
    print("Example Filter 2: DoD contracts with 'cloud' keyword")
    results = filter_engine.filter_opportunities(
        agencies=['Department of Defense'],
        keywords=['cloud']
    )
    print(f"Results: {len(results)} opportunities")
    
    # Example filter 3: Small business set-asides
    print("\n" + "-"*70)
    print("Example Filter 3: Small Business set-asides")
    results = filter_engine.filter_opportunities(
        set_asides=['Small Business']
    )
    print(f"Results: {len(results)} opportunities")
    
    filter_engine.close()
    
    print("\n" + "="*70)
    print("All filters executed INSTANTLY from local database!")
    print("No API calls required!")
    print("="*70 + "\n")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'demo':
        demo_local_filtering()
    else:
        run_daily_bulk_fetch()
