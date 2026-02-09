#!/usr/bin/env python3
"""
SAM.gov Opportunity Scout
Monitors SAM.gov for relevant federal contracting opportunities
"""

import os
import json
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Any
import yaml
import logging
from pathlib import Path


class SAMOpportunityScout:
    """Monitors SAM.gov for federal contracting opportunities"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize the scout with configuration"""
        self.config = self._load_config(config_path)
        self._setup_logging()
        self._setup_directories()
        
        # SAM.gov API endpoints
        self.base_url = "https://api.sam.gov/opportunities/v2/search"
        self.api_key = self.config['sam_gov']['api_key']
        
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
    
    def search_opportunities(self, days_back: int = None) -> List[Dict[str, Any]]:
        """
        Search SAM.gov for opportunities matching configured criteria
        
        Args:
            days_back: Number of days to look back (default from config)
        
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
            'limit': 100,
            'offset': 0
        }
        
        # Add NAICS codes filter
        naics_codes = self.config['company']['naics_codes']
        if naics_codes:
            params['ncode'] = ','.join(naics_codes)
        
        # Add set-aside filter if configured
        set_asides = self.config['company']['set_asides']
        if set_asides:
            params['typeOfSetAside'] = ','.join(set_asides)
        
        all_opportunities = []
        
        try:
            self.logger.info(f"Searching SAM.gov from {start_date.date()} to {end_date.date()}")
            
            while True:
                response = requests.get(self.base_url, params=params, timeout=30)
                response.raise_for_status()
                
                data = response.json()
                opportunities = data.get('opportunitiesData', [])
                
                if not opportunities:
                    break
                
                # Filter by opportunity type
                filtered_opps = [
                    opp for opp in opportunities
                    if opp.get('type') in self.config['sam_gov']['search']['opportunity_types']
                ]
                
                all_opportunities.extend(filtered_opps)
                
                # Check if there are more results
                if len(opportunities) < params['limit']:
                    break
                
                params['offset'] += params['limit']
            
            self.logger.info(f"Found {len(all_opportunities)} opportunities")
            
            # Filter by keywords if configured
            keywords = self.config['sam_gov']['search'].get('keywords', [])
            if keywords:
                all_opportunities = self._filter_by_keywords(all_opportunities, keywords)
                self.logger.info(f"After keyword filtering: {len(all_opportunities)} opportunities")
            
            # Filter by value range if configured
            all_opportunities = self._filter_by_value(all_opportunities)
            self.logger.info(f"After value filtering: {len(all_opportunities)} opportunities")
            
            return all_opportunities
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error fetching opportunities from SAM.gov: {e}")
            return []
    
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
        """
        Save opportunities to JSON file
        
        Args:
            opportunities: List of opportunity dictionaries
            filename: Optional filename (auto-generated if not provided)
        
        Returns:
            Path to saved file
        """
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
    
    def get_opportunity_details(self, notice_id: str) -> Dict[str, Any]:
        """
        Fetch detailed information for a specific opportunity
        
        Args:
            notice_id: The notice ID from SAM.gov
        
        Returns:
            Detailed opportunity information
        """
        url = f"https://api.sam.gov/opportunities/v2/search"
        params = {
            'api_key': self.api_key,
            'noticeId': notice_id
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            opportunities = data.get('opportunitiesData', [])
            if opportunities:
                return opportunities[0]
            else:
                self.logger.warning(f"No details found for notice ID: {notice_id}")
                return {}
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error fetching opportunity details: {e}")
            return {}
    
    def generate_summary_report(self, opportunities: List[Dict]) -> str:
        """
        Generate a summary report of opportunities
        
        Args:
            opportunities: List of opportunities
        
        Returns:
            Path to summary report
        """
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


def main():
    """Main execution function"""
    scout = SAMOpportunityScout()
    
    # Search for opportunities
    opportunities = scout.search_opportunities()
    
    if opportunities:
        # Save to JSON
        json_path = scout.save_opportunities(opportunities)
        
        # Generate summary report
        report_path = scout.generate_summary_report(opportunities)
        
        print(f"\n✓ Found {len(opportunities)} opportunities")
        print(f"✓ Saved to: {json_path}")
        print(f"✓ Summary: {report_path}")
        
        return json_path
    else:
        print("No opportunities found matching your criteria")
        return None


if __name__ == "__main__":
    main()
