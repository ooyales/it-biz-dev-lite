#!/usr/bin/env python3
"""
SAM.gov Smart Bulk Fetcher - Rate Limit Aware
Intelligently handles SAM.gov rate limits with multiple strategies
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

class SmartBulkFetcher:
    """
    Smart bulk fetcher with three strategies to avoid rate limits:
    
    Strategy 1: Filtered Fetch (RECOMMENDED)
    - Only fetch opportunities matching your criteria
    - Much smaller dataset (hundreds vs thousands)
    - Completes in 1-5 API calls instead of 180
    
    Strategy 2: Incremental Fetch (SAFE)
    - Fetch in chunks over multiple days
    - Today: Last 7 days, Tomorrow: Next 7 days, etc.
    - Spreads load across time
    
    Strategy 3: Resume on Rate Limit (FALLBACK)
    - Detects 429 errors
    - Saves progress
    - Resumes later from where it stopped
    """
    
    def __init__(self, config_path=CONFIG_PATH):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.api_key = self.config['sam_gov']['api_key']
        self.base_url = "https://api.sam.gov/opportunities/v2/search"
        
        # Progress tracking
        self.progress_file = Path("data/cache/fetch_progress.json")
        self.progress_file.parent.mkdir(parents=True, exist_ok=True)
    
    def fetch_filtered(self, days_back=30):
        """
        STRATEGY 1: Filtered Fetch (RECOMMENDED)
        
        Only fetch opportunities matching YOUR company's criteria.
        Instead of fetching 18,000 opportunities, fetch 200-500 relevant ones.
        
        Completes in 2-5 API calls instead of 180!
        """
        logger.info("="*70)
        logger.info("STRATEGY 1: FILTERED FETCH (Recommended)")
        logger.info("="*70)
        logger.info("Fetching only opportunities matching your criteria...")
        
        from_date = (datetime.now() - timedelta(days=days_back)).strftime('%m/%d/%Y')
        to_date = datetime.now().strftime('%m/%d/%Y')
        
        # Get your company's filter criteria from config
        naics_codes = self.config.get('sam_gov', {}).get('naics_codes', [])
        keywords = self.config.get('sam_gov', {}).get('keywords', [])
        min_value = self.config.get('sam_gov', {}).get('min_value', 50000)
        max_value = self.config.get('sam_gov', {}).get('max_value', 10000000)
        
        all_opportunities = []
        
        # Fetch by NAICS code (most selective filter)
        if naics_codes:
            logger.info(f"Filtering by NAICS codes: {naics_codes}")
            
            for naics in naics_codes:
                logger.info(f"\nFetching NAICS {naics}...")
                
                opportunities = self._fetch_with_filter(
                    from_date=from_date,
                    to_date=to_date,
                    naics_code=naics,
                    min_value=min_value,
                    max_value=max_value
                )
                
                all_opportunities.extend(opportunities)
                logger.info(f"  Found {len(opportunities)} opportunities for NAICS {naics}")
                
                # Small delay between NAICS codes
                time.sleep(3)
        else:
            # No NAICS filter, fetch with value range at least
            logger.info("No NAICS codes configured, fetching by value range...")
            opportunities = self._fetch_with_filter(
                from_date=from_date,
                to_date=to_date,
                min_value=min_value,
                max_value=max_value
            )
            all_opportunities.extend(opportunities)
        
        # Remove duplicates (same opportunity may appear in multiple NAICS)
        unique_opps = {}
        for opp in all_opportunities:
            notice_id = opp.get('noticeId')
            if notice_id:
                unique_opps[notice_id] = opp
        
        final_opportunities = list(unique_opps.values())
        
        logger.info("\n" + "="*70)
        logger.info(f"FILTERED FETCH COMPLETE: {len(final_opportunities)} opportunities")
        logger.info("="*70)
        
        return final_opportunities
    
    def _fetch_with_filter(self, from_date, to_date, naics_code=None, min_value=None, max_value=None):
        """Fetch with filters, handling pagination"""
        
        opportunities = []
        offset = 0
        batch_size = 100
        
        while True:
            params = {
                'api_key': self.api_key,
                'postedFrom': from_date,
                'postedTo': to_date,
                'limit': batch_size,
                'offset': offset
            }
            
            if naics_code:
                params['naicsCode'] = naics_code
            
            # Note: SAM.gov API may not support min/max value filtering
            # We'll filter locally if needed
            
            try:
                response = requests.get(self.base_url, params=params, timeout=30)
                
                # Handle rate limit
                if response.status_code == 429:
                    logger.warning("Rate limit hit! Waiting...")
                    retry_after = int(response.headers.get('Retry-After', 3600))
                    logger.warning(f"Waiting {retry_after} seconds...")
                    time.sleep(retry_after)
                    continue
                
                response.raise_for_status()
                
                data = response.json()
                batch = data.get('opportunitiesData', [])
                total_records = data.get('totalRecords', 0)
                
                if not batch:
                    break
                
                # Apply local value filtering if API doesn't support it
                if min_value or max_value:
                    batch = self._filter_by_value(batch, min_value, max_value)
                
                opportunities.extend(batch)
                
                logger.info(f"  Fetched {len(batch)} (total: {len(opportunities)}/{total_records})")
                
                # Check if done
                if len(batch) < batch_size or len(opportunities) >= total_records:
                    break
                
                offset += batch_size
                time.sleep(2)  # Rate limiting delay
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching: {e}")
                break
        
        return opportunities
    
    def _filter_by_value(self, opportunities, min_value=None, max_value=None):
        """Filter opportunities by contract value"""
        filtered = []
        
        for opp in opportunities:
            try:
                award = opp.get('award', {})
                if isinstance(award, dict):
                    amount_str = str(award.get('amount', '0'))
                    amount = int(amount_str.replace('$', '').replace(',', '').strip())
                    
                    if min_value and amount < min_value:
                        continue
                    if max_value and amount > max_value:
                        continue
                    
                    filtered.append(opp)
                else:
                    filtered.append(opp)  # Include if can't determine value
            except:
                filtered.append(opp)  # Include on error
        
        return filtered
    
    def fetch_incremental(self, days_per_fetch=7):
        """
        STRATEGY 2: Incremental Fetch
        
        Fetch in smaller time windows spread across multiple days.
        Today: Last 7 days, Tomorrow: Days 8-14, etc.
        
        Reduces API calls per session.
        """
        logger.info("="*70)
        logger.info("STRATEGY 2: INCREMENTAL FETCH")
        logger.info("="*70)
        
        # Check if we have a saved position
        progress = self._load_progress()
        
        start_day = progress.get('last_fetched_day', 0)
        end_day = start_day + days_per_fetch
        
        from_date = (datetime.now() - timedelta(days=end_day)).strftime('%m/%d/%Y')
        to_date = (datetime.now() - timedelta(days=start_day)).strftime('%m/%d/%Y')
        
        logger.info(f"Fetching days {start_day}-{end_day} ago ({from_date} to {to_date})")
        
        opportunities = self._fetch_with_filter(from_date, to_date)
        
        # Save progress
        self._save_progress({'last_fetched_day': end_day})
        
        logger.info(f"Incremental fetch complete: {len(opportunities)} opportunities")
        logger.info(f"Next run will fetch days {end_day}-{end_day+days_per_fetch}")
        
        return opportunities
    
    def fetch_with_resume(self, days_back=30, max_calls=50):
        """
        STRATEGY 3: Resumable Fetch
        
        Fetches until hitting rate limit, then saves progress.
        Resume later from where it stopped.
        """
        logger.info("="*70)
        logger.info("STRATEGY 3: RESUMABLE FETCH")
        logger.info("="*70)
        
        from_date = (datetime.now() - timedelta(days=days_back)).strftime('%m/%d/%Y')
        to_date = datetime.now().strftime('%m/%d/%Y')
        
        # Load progress
        progress = self._load_progress()
        offset = progress.get('offset', 0)
        
        logger.info(f"Resuming from offset {offset}")
        
        opportunities = []
        batch_size = 100
        calls_made = 0
        
        while calls_made < max_calls:
            params = {
                'api_key': self.api_key,
                'postedFrom': from_date,
                'postedTo': to_date,
                'limit': batch_size,
                'offset': offset
            }
            
            try:
                response = requests.get(self.base_url, params=params, timeout=30)
                
                if response.status_code == 429:
                    logger.warning("Rate limit hit! Saving progress...")
                    self._save_progress({'offset': offset})
                    logger.info(f"Saved progress at offset {offset}")
                    logger.info("Run this script again later to resume")
                    break
                
                response.raise_for_status()
                
                data = response.json()
                batch = data.get('opportunitiesData', [])
                
                if not batch:
                    logger.info("No more opportunities")
                    self._save_progress({'offset': 0})  # Reset for next full fetch
                    break
                
                opportunities.extend(batch)
                offset += batch_size
                calls_made += 1
                
                logger.info(f"Fetched {len(batch)} (total: {len(opportunities)}, offset: {offset})")
                
                time.sleep(2)
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Error: {e}")
                self._save_progress({'offset': offset})
                break
        
        if calls_made >= max_calls:
            logger.warning(f"Reached max calls limit ({max_calls})")
            self._save_progress({'offset': offset})
            logger.info("Run again later to continue")
        
        return opportunities
    
    def _load_progress(self):
        """Load fetch progress"""
        if self.progress_file.exists():
            with open(self.progress_file, 'r') as f:
                return json.load(f)
        return {}
    
    def _save_progress(self, progress):
        """Save fetch progress"""
        with open(self.progress_file, 'w') as f:
            json.dump(progress, f, indent=2)
    
    def store_opportunities(self, opportunities):
        """Store opportunities in database"""
        if not opportunities:
            logger.warning("No opportunities to store")
            return 0, 0
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # Create table if not exists
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
            
            # Extract fields (same as before)
            title = opp.get('title', '')
            opp_type = opp.get('type', '')
            naics_code = opp.get('naicsCode', '')
            agency = opp.get('fullParentPathName', '')
            posted_date = opp.get('postedDate', '')
            deadline = opp.get('responseDeadLine', '')
            set_aside = opp.get('typeOfSetAside', '')
            description = opp.get('description', '')
            
            # Contract value
            contract_value = 0
            award = opp.get('award', {})
            if isinstance(award, dict):
                try:
                    amount = str(award.get('amount', '0')).replace('$', '').replace(',', '').strip()
                    contract_value = int(amount)
                except:
                    pass
            
            raw_json = json.dumps(opp)
            
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
                logger.error(f"Error storing {notice_id}: {e}")
        
        conn.commit()
        conn.close()
        
        logger.info(f"Stored: {inserted} new, {updated} updated")
        return inserted, updated


def main():
    """Main function with strategy selection"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Smart SAM.gov Bulk Fetcher')
    parser.add_argument('--strategy', 
                       choices=['filtered', 'incremental', 'resume'],
                       default='filtered',
                       help='Fetch strategy (default: filtered)')
    parser.add_argument('--days', type=int, default=30,
                       help='Days to look back (default: 30)')
    
    args = parser.parse_args()
    
    print("\n" + "="*70)
    print("SAM.GOV SMART BULK FETCHER")
    print("="*70 + "\n")
    
    fetcher = SmartBulkFetcher()
    
    if args.strategy == 'filtered':
        print("Using FILTERED FETCH strategy")
        print("✓ Only fetches opportunities matching your criteria")
        print("✓ Much faster (2-10 API calls vs 180)")
        print("✓ Less likely to hit rate limits\n")
        opportunities = fetcher.fetch_filtered(days_back=args.days)
        
    elif args.strategy == 'incremental':
        print("Using INCREMENTAL FETCH strategy")
        print("✓ Fetches 7 days at a time")
        print("✓ Spreads load across multiple days")
        print("✓ Run daily to build up full dataset\n")
        opportunities = fetcher.fetch_incremental(days_per_fetch=7)
        
    elif args.strategy == 'resume':
        print("Using RESUMABLE FETCH strategy")
        print("✓ Fetches until rate limit or max calls")
        print("✓ Saves progress")
        print("✓ Resume later to continue\n")
        opportunities = fetcher.fetch_with_resume(days_back=args.days, max_calls=50)
    
    if opportunities:
        print(f"\nStoring {len(opportunities)} opportunities...")
        inserted, updated = fetcher.store_opportunities(opportunities)
        
        print("\n" + "="*70)
        print("FETCH COMPLETE")
        print("="*70)
        print(f"Total fetched: {len(opportunities)}")
        print(f"New: {inserted}")
        print(f"Updated: {updated}")
        print()
    else:
        print("\nNo opportunities fetched.")
        print("If you hit rate limit, try again later or use --strategy incremental")


if __name__ == "__main__":
    main()
