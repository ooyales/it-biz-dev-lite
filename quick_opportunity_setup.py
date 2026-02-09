#!/usr/bin/env python3
"""
Quick Opportunity Setup — SAM.gov Opportunities API

Collects active opportunities from SAM.gov and stores them in JSON.
No config files needed — completely standalone.

Usage:
    python quick_opportunity_setup.py --days 90
    python quick_opportunity_setup.py --days 180 --count 500
"""

import os
import sys
import json
import argparse
import requests
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


IT_NAICS = {
    '541512': 'Computer Systems Design Services',
    '541511': 'Custom Computer Programming',
    '541519': 'Other Computer Related Services',
    '518210': 'Computer Processing & Data Prep',
}


def search_sam_opportunities(api_key: str, naics_code: str, posted_from: str, posted_to: str, limit: int = 100):
    """
    Search SAM.gov Opportunities API for a specific NAICS code
    
    Args:
        api_key: SAM.gov API key
        naics_code: NAICS code to search for
        posted_from: Start date (MM/DD/YYYY)
        posted_to: End date (MM/DD/YYYY)
        limit: Results per page
    
    Returns:
        List of opportunities
    """
    base_url = "https://api.sam.gov/opportunities/v2/search"
    
    params = {
        'api_key': api_key,
        'postedFrom': posted_from,
        'postedTo': posted_to,
        'ncode': naics_code,  # NAICS code filter
        'ptype': 'o',  # o = solicitation, p = presolicitation
        'limit': limit,
        'offset': 0
    }
    
    all_opportunities = []
    
    try:
        while True:
            response = requests.get(base_url, params=params, timeout=30)
            
            if response.status_code == 401:
                print("      ❌ 401 Unauthorized — Check your SAM_API_KEY")
                break
            
            if response.status_code == 429:
                print("      ❌ Rate limited (10 req/day on free tier)")
                break
            
            response.raise_for_status()
            data = response.json()
            
            opportunities = data.get('opportunitiesData', [])
            if not opportunities:
                break
            
            all_opportunities.extend(opportunities)
            
            # Check if there are more pages
            total_records = data.get('totalRecords', 0)
            if len(all_opportunities) >= total_records:
                break
            
            if len(opportunities) < limit:
                break
            
            # Next page
            params['offset'] += limit
        
        return all_opportunities
        
    except requests.RequestException as e:
        print(f"      ❌ API Error: {e}")
        return []


def quick_setup(days: int = 90, max_opportunities: int = None):
    """
    Quick setup to collect opportunities from SAM.gov
    
    Args:
        days: How many days back to search (default: 90)
        max_opportunities: Maximum opportunities to collect (default: unlimited)
    """
    print("=" * 70)
    print(" QUICK OPPORTUNITY SETUP — SAM.gov Opportunities API")
    print("=" * 70)
    print()
    print(f"  Search period: Last {days} days")
    print(f"  NAICS codes  : {len(IT_NAICS)} IT-related codes")
    print(f"  Max opps     : {max_opportunities if max_opportunities else 'Unlimited'}")
    print()
    
    # Get API key
    api_key = os.getenv('SAM_API_KEY')
    if not api_key:
        print("❌ Error: SAM_API_KEY not found in environment")
        print("   Set it in your .env file or export SAM_API_KEY=your-key")
        return
    
    print("  ⚠️  Rate limit: 10 requests/day (free tier)")
    print("     Each NAICS code = ~1-2 requests")
    print("     This run will use ~4-8 requests")
    print()
    
    response = input("Continue? (y/n): ")
    if response.lower() != 'y':
        print("Cancelled.")
        return
    
    print()
    print("🚀 Starting opportunity collection...")
    print()
    
    # Date range
    posted_to = datetime.now().strftime('%m/%d/%Y')
    posted_from = (datetime.now() - timedelta(days=days)).strftime('%m/%d/%Y')
    
    print(f"   Date range: {posted_from} to {posted_to}")
    print()
    
    all_opportunities = []
    
    # Search by NAICS codes
    for naics_code, naics_name in IT_NAICS.items():
        print(f"   📡 NAICS {naics_code} ({naics_name})...")
        
        opportunities = search_sam_opportunities(
            api_key=api_key,
            naics_code=naics_code,
            posted_from=posted_from,
            posted_to=posted_to
        )
        
        if opportunities:
            print(f"      ✓ Found {len(opportunities)} opportunities")
            all_opportunities.extend(opportunities)
        else:
            print(f"      ✗ No opportunities found")
        
        # Check if we've hit the target
        if max_opportunities and len(all_opportunities) >= max_opportunities:
            print(f"\n   Reached target of {max_opportunities} opportunities")
            all_opportunities = all_opportunities[:max_opportunities]
            break
    
    print()
    print("=" * 70)
    print("COLLECTION COMPLETE")
    print("=" * 70)
    print(f"  Total opportunities collected: {len(all_opportunities)}")
    print()
    
    if len(all_opportunities) > 0:
        # Save to JSON file
        output_dir = Path('knowledge_graph')
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = output_dir / f'scout_data_{timestamp}.json'
        
        output_data = {
            'collection_date': datetime.now().isoformat(),
            'search_period_days': days,
            'naics_codes': list(IT_NAICS.keys()),
            'total_opportunities': len(all_opportunities),
            'opportunities': all_opportunities
        }
        
        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        print(f"  ✓ Saved to: {output_file}")
        print()
        
        # Summary stats
        agencies = {}
        set_asides = {}
        active_count = 0
        
        for opp in all_opportunities:
            agency = opp.get('department', {}).get('name', 'Unknown')
            agencies[agency] = agencies.get(agency, 0) + 1
            
            set_aside = opp.get('typeOfSetAsideDescription', 'None')
            set_asides[set_aside] = set_asides.get(set_aside, 0) + 1
            
            if opp.get('active') == 'Yes':
                active_count += 1
        
        print(f"  Active opportunities: {active_count}/{len(all_opportunities)}")
        print()
        print("  Top Agencies:")
        for agency, count in sorted(agencies.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"    {count:3d}  {agency[:60]}")
        
        print()
        print("  Set-Aside Types:")
        for set_aside, count in sorted(set_asides.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"    {count:3d}  {set_aside[:60]}")
        
        print()
        print("📊 Next steps:")
        print("   1. Opportunities are saved in knowledge_graph/")
        print("   2. Refresh your dashboard (reload page) to see them")
        print("   3. Use AI agents to analyze and match opportunities")
        print()
    else:
        print(f"  ⚠️  No opportunities found. This could mean:")
        print(f"     • No active solicitations in the last {days} days")
        print("     • Rate limit hit before completing search")
        print("     • SAM.gov API temporarily unavailable")
        print()


def main():
    parser = argparse.ArgumentParser(
        description='Quick setup to collect opportunities from SAM.gov'
    )
    parser.add_argument(
        '--days',
        type=int,
        default=90,
        help='Number of days back to search (default: 90)'
    )
    parser.add_argument(
        '--count',
        type=int,
        default=None,
        help='Maximum number of opportunities to collect (default: unlimited)'
    )
    
    args = parser.parse_args()
    
    quick_setup(days=args.days, max_opportunities=args.count)


if __name__ == '__main__':
    main()
