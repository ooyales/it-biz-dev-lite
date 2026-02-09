#!/usr/bin/env python3
"""
SAM.gov Opportunity Scout - Rate Limited Version
Handles SAM.gov API rate limits with intelligent retry and caching
"""

import os
import json
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Any
import yaml
import logging
from pathlib import Path
import time
import hashlib


class SAMOpportunityScoutRateLimited:
    """SAM.gov scout with rate limiting and caching"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize the scout with configuration"""
        self.config = self._load_config(config_path)
        self._setup_logging()
        self._setup_directories()
        
        # SAM.gov API endpoints
        self.base_url = "https://api.sam.gov/opportunities/v2/search"
        self.api_key = self.config['sam_gov']['api_key']
        
        # Rate limiting settings
        self.request_delay = 2  # Wait 2 seconds between requests
        self.max_retries = 3
        self.retry_delay = 60  # Wait 60 seconds before retry on rate limit
        
        # Cache directory
        self.cache_dir = Path("data/cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file"""
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def _setup_logging(self):
        """Configure logging"""
        log_dir = Path(self.config['logging']['file_path']).parent
        log_dir.mkdir(parents=True, exist_ok=True)
        
        logging.basicConfig(
            level=self.config['logging']['level'],
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.config['logging']['file_path']),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def _setup_directories(self):
        """Create necessary directories"""
        for path in [
            self.config['storage']['opportunities_path'],
            self.config['storage']['analysis_path'],
            self.config['storage']['proposals_path'],
            self.config['storage']['reports_path']
        ]:
            Path(path).mkdir(parents=True, exist_ok=True)
    
    def _get_cache_key(self, params: Dict) -> str:
        """Generate cache key from search parameters"""
        # Create a deterministic hash of the parameters
        param_str = json.dumps(params, sort_keys=True)
        return hashlib.md5(param_str.encode()).hexdigest()
    
    def _get_cached_results(self, cache_key: str, max_age_hours: int = 24) -> List[Dict]:
        """Get cached results if they exist and are fresh"""
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        if cache_file.exists():
            # Check age
            file_age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
            
            if file_age < timedelta(hours=max_age_hours):
                self.logger.info(f"Using cached results (age: {file_age.seconds//3600}h {(file_age.seconds//60)%60}m)")
                with open(cache_file, 'r') as f:
                    return json.load(f)
        
        return None
    
    def _save_to_cache(self, cache_key: str, data: List[Dict]):
        """Save results to cache"""
        cache_file = self.cache_dir / f"{cache_key}.json"
        with open(cache_file, 'w') as f:
            json.dump(data, f, indent=2)
        self.logger.info(f"Saved {len(data)} opportunities to cache")
    
    def _make_api_request(self, params: Dict, retry_count: int = 0) -> Dict:
        """
        Make API request with rate limiting and retry logic
        
        Args:
            params: Request parameters
            retry_count: Current retry attempt
        
        Returns:
            API response data
        """
        try:
            # Add delay between requests to respect rate limits
            if retry_count == 0:
                time.sleep(self.request_delay)
            
            self.logger.debug(f"Making API request (attempt {retry_count + 1}/{self.max_retries + 1})")
            
            response = requests.get(self.base_url, params=params, timeout=30)
            
            # Handle rate limiting
            if response.status_code == 429:
                self.logger.warning("⚠️  Rate limit exceeded")
                
                if retry_count < self.max_retries:
                    retry_after = int(response.headers.get('Retry-After', self.retry_delay))
                    self.logger.info(f"Waiting {retry_after} seconds before retry...")
                    time.sleep(retry_after)
                    return self._make_api_request(params, retry_count + 1)
                else:
                    self.logger.error("Max retries reached. Using cached data or reducing scope.")
                    return {'opportunitiesData': []}
            
            # Handle other errors
            if response.status_code != 200:
                self.logger.error(f"API error: {response.status_code}")
                self.logger.error(f"Response: {response.text[:500]}")
                return {'opportunitiesData': []}
            
            return response.json()
            
        except requests.exceptions.Timeout:
            self.logger.error("Request timeout")
            if retry_count < self.max_retries:
                time.sleep(10)
                return self._make_api_request(params, retry_count + 1)
            return {'opportunitiesData': []}
        
        except Exception as e:
            self.logger.error(f"Error making API request: {e}")
            return {'opportunitiesData': []}
    
    def search_opportunities(self, days_back: int = None, use_cache: bool = True) -> List[Dict[str, Any]]:
        """
        Search SAM.gov for opportunities with rate limiting
        
        Args:
            days_back: Number of days to look back (default from config)
            use_cache: Whether to use cached results if available
        
        Returns:
            List of opportunity dictionaries
        """
        if days_back is None:
            days_back = self.config['sam_gov']['search']['lookback_days']
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        # Build search parameters
        params = {
            'api_key': self.api_key,
            'postedFrom': start_date.strftime('%m/%d/%Y'),
            'postedTo': end_date.strftime('%m/%d/%Y'),
            'limit': 100,  # SAM.gov max per request
            'offset': 0
        }
        
        # Add NAICS codes filter
        naics_codes = self.config['company']['naics_codes']
        if naics_codes:
            params['ncode'] = ','.join(naics_codes)
        
        # Add set-aside filter if configured
        set_asides = self.config['company']['set_asides']
        if set_asides:
            # Map to SAM.gov format
            sam_set_asides = []
            for sa in set_asides:
                if sa == 'small_business':
                    sam_set_asides.append('SBA')
                elif sa == '8a':
                    sam_set_asides.append('8A')
                elif sa == 'hubzone':
                    sam_set_asides.append('HZS')
                elif sa == 'wosb':
                    sam_set_asides.append('WOSB')
                elif sa == 'sdvosb':
                    sam_set_asides.append('SDVOSBC')
                else:
                    sam_set_asides.append(sa.upper())
            
            if sam_set_asides:
                params['typeOfSetAside'] = ','.join(sam_set_asides)
        
        # Check cache first
        cache_key = self._get_cache_key(params)
        if use_cache:
            cached_results = self._get_cached_results(cache_key)
            if cached_results is not None:
                self.logger.info(f"Using {len(cached_results)} cached opportunities")
                return cached_results
        
        # Fetch from API
        self.logger.info(f"Searching SAM.gov from {start_date.date()} to {end_date.date()}")
        self.logger.info("⏱️  Using rate-limited requests (may take longer)...")
        
        all_opportunities = []
        page = 1
        
        while True:
            self.logger.info(f"Fetching page {page}...")
            
            data = self._make_api_request(params)
            opportunities = data.get('opportunitiesData', [])
            
            if not opportunities:
                break
            
            # Filter by opportunity type
            config_types = self.config['sam_gov']['search']['opportunity_types']
            filtered_opps = [
                opp for opp in opportunities
                if opp.get('type') in config_types
            ]
            
            all_opportunities.extend(filtered_opps)
            
            # Check if there are more results
            if len(opportunities) < params['limit']:
                break
            
            # Update offset for next page
            params['offset'] += params['limit']
            page += 1
            
            # Safety limit to prevent excessive API calls
            if page > 10:
                self.logger.warning("Reached page limit (10). Stopping to avoid rate limits.")
                break
        
        self.logger.info(f"Found {len(all_opportunities)} opportunities (after type filter)")
        
        # Filter by keywords if configured
        keywords = self.config['sam_gov']['search'].get('keywords', [])
        if keywords:
            all_opportunities = self._filter_by_keywords(all_opportunities, keywords)
            self.logger.info(f"After keyword filtering: {len(all_opportunities)} opportunities")
        
        # Filter by value range if configured
        all_opportunities = self._filter_by_value(all_opportunities)
        self.logger.info(f"After value filtering: {len(all_opportunities)} opportunities")
        
        # Save to cache
        self._save_to_cache(cache_key, all_opportunities)
        
        return all_opportunities
    
    def _filter_by_keywords(self, opportunities: List[Dict], keywords: List[str]) -> List[Dict]:
        """Filter opportunities by keywords in title and description"""
        filtered = []
        for opp in opportunities:
            title = opp.get('title', '').lower()
            description = opp.get('description', '').lower()
            
            # Check if any keyword matches
            if any(keyword.lower() in title or keyword.lower() in description 
                   for keyword in keywords):
                filtered.append(opp)
        
        return filtered
    
    def _filter_by_value(self, opportunities: List[Dict]) -> List[Dict]:
        """Filter opportunities by contract value range"""
        min_val = self.config['sam_gov']['search']['value_range']['min']
        max_val = self.config['sam_gov']['search']['value_range']['max']
        
        filtered = []
        for opp in opportunities:
            # Try to extract value from award amount or description
            award_amount = opp.get('award', {}).get('amount')
            
            if award_amount:
                try:
                    amount = float(award_amount)
                    if min_val <= amount <= max_val:
                        filtered.append(opp)
                except (ValueError, TypeError):
                    # If we can't parse the amount, include it to be safe
                    filtered.append(opp)
            else:
                # If no amount specified, include it
                filtered.append(opp)
        
        return filtered
    
    def save_opportunities(self, opportunities: List[Dict], filename: str = None) -> str:
        """Save opportunities to JSON file"""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"opportunities_{timestamp}.json"
        
        filepath = os.path.join(
            self.config['storage']['opportunities_path'],
            filename
        )
        
        with open(filepath, 'w') as f:
            json.dump({
                'retrieved_at': datetime.now().isoformat(),
                'count': len(opportunities),
                'opportunities': opportunities
            }, f, indent=2)
        
        self.logger.info(f"Saved {len(opportunities)} opportunities to {filepath}")
        return filepath
    
    def generate_summary_report(self, opportunities: List[Dict]) -> str:
        """Generate a summary report of opportunities"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_path = os.path.join(
            self.config['storage']['reports_path'],
            f"opportunity_summary_{timestamp}.txt"
        )
        
        with open(report_path, 'w') as f:
            f.write("=" * 80 + "\n")
            f.write(f"SAM.gov Opportunity Summary Report\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n\n")
            
            f.write(f"Total Opportunities Found: {len(opportunities)}\n\n")
            
            if opportunities:
                # Group by type
                by_type = {}
                for opp in opportunities:
                    opp_type = opp.get('type', 'Unknown')
                    by_type[opp_type] = by_type.get(opp_type, 0) + 1
                
                f.write("Breakdown by Type:\n")
                for opp_type, count in sorted(by_type.items()):
                    f.write(f"  {opp_type}: {count}\n")
                
                f.write("\n" + "=" * 80 + "\n\n")
                
                # List each opportunity
                for i, opp in enumerate(opportunities, 1):
                    f.write(f"{i}. {opp.get('title', 'No Title')}\n")
                    f.write(f"   Notice ID: {opp.get('noticeId', 'N/A')}\n")
                    f.write(f"   Type: {opp.get('type', 'N/A')}\n")
                    f.write(f"   Posted: {opp.get('postedDate', 'N/A')}\n")
                    f.write(f"   Response Deadline: {opp.get('responseDeadLine', 'N/A')}\n")
                    
                    naics = opp.get('naicsCode')
                    if naics:
                        f.write(f"   NAICS: {naics}\n")
                    
                    set_aside = opp.get('typeOfSetAside')
                    if set_aside:
                        f.write(f"   Set-Aside: {set_aside}\n")
                    
                    f.write(f"   URL: https://sam.gov/opp/{opp.get('noticeId', '')}\n")
                    f.write("\n")
        
        self.logger.info(f"Generated summary report: {report_path}")
        return report_path
    
    def clear_cache(self, older_than_hours: int = None):
        """Clear cached results"""
        if older_than_hours is None:
            # Clear all cache
            for cache_file in self.cache_dir.glob("*.json"):
                cache_file.unlink()
            self.logger.info("Cleared all cached results")
        else:
            # Clear old cache
            cutoff = datetime.now() - timedelta(hours=older_than_hours)
            cleared = 0
            for cache_file in self.cache_dir.glob("*.json"):
                if datetime.fromtimestamp(cache_file.stat().st_mtime) < cutoff:
                    cache_file.unlink()
                    cleared += 1
            self.logger.info(f"Cleared {cleared} cached results older than {older_than_hours}h")


def main():
    """Main execution function"""
    scout = SAMOpportunityScoutRateLimited()
    
    # Search for opportunities (will use cache if available)
    print("\n🔍 Searching for opportunities...")
    print("⏱️  Using rate-limited requests and caching to avoid quota issues\n")
    
    opportunities = scout.search_opportunities(use_cache=True)
    
    if opportunities:
        # Save to JSON
        json_path = scout.save_opportunities(opportunities)
        
        # Generate summary report
        report_path = scout.generate_summary_report(opportunities)
        
        print(f"\n✅ Success!")
        print(f"✓ Found {len(opportunities)} opportunities")
        print(f"✓ Saved to: {json_path}")
        print(f"✓ Summary: {report_path}")
        
        return json_path
    else:
        print("\n⚠️  No opportunities found matching your criteria")
        print("\nTips:")
        print("  • Increase lookback_days in config.yaml")
        print("  • Broaden your NAICS codes")
        print("  • Check data/cache/ for cached results")
        return None

# Alias for backwards compatibility
SAMOpportunityScout = SAMOpportunityScoutRateLimited
if __name__ == "__main__":
    main()
