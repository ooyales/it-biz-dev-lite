#!/usr/bin/env python3
"""
SAM.gov Rate Limit Checker
Shows your current API quota status
"""

import requests
import yaml
from datetime import datetime

CONFIG_PATH = "config.yaml"

print("\n" + "="*70)
print("SAM.GOV RATE LIMIT STATUS")
print("="*70 + "\n")

# Load config
try:
    with open(CONFIG_PATH, 'r') as f:
        config = yaml.safe_load(f)
    api_key = config['sam_gov']['api_key']
except Exception as e:
    print(f"Error loading config: {e}")
    exit(1)

# Make a minimal test request to check headers
url = "https://api.sam.gov/opportunities/v2/search"
params = {
    'api_key': api_key,
    'limit': 1  # Minimal request
}

try:
    print("Checking API status...")
    response = requests.get(url, params=params, timeout=10)
    
    print(f"Status Code: {response.status_code}\n")
    
    # Check rate limit headers (if SAM.gov provides them)
    headers = response.headers
    
    print("Response Headers:")
    print("-" * 70)
    
    # Common rate limit headers
    rate_limit_headers = [
        'X-RateLimit-Limit',
        'X-RateLimit-Remaining',
        'X-RateLimit-Reset',
        'Retry-After',
        'X-Rate-Limit-Limit',
        'X-Rate-Limit-Remaining',
        'X-Rate-Limit-Reset'
    ]
    
    found_headers = False
    for header in rate_limit_headers:
        if header in headers:
            print(f"{header}: {headers[header]}")
            found_headers = True
    
    if not found_headers:
        print("No rate limit headers found in response")
        print("(SAM.gov may not expose rate limit details)")
    
    print()
    
    if response.status_code == 200:
        print("✓ API is accessible - Rate limit not currently exceeded")
        data = response.json()
        total = data.get('totalRecords', 0)
        print(f"✓ {total:,} opportunities available")
        
    elif response.status_code == 429:
        print("✗ RATE LIMIT EXCEEDED")
        print()
        print("You've made too many requests to SAM.gov API")
        print()
        
        if 'Retry-After' in headers:
            retry_after = headers['Retry-After']
            print(f"Retry after: {retry_after} seconds")
        else:
            print("Typical rate limits:")
            print("  • Hourly: ~100-200 requests")
            print("  • Daily: ~1,000 requests")
            print()
            print("Wait time:")
            print("  • If hourly limit: Wait 1 hour")
            print("  • If daily limit: Wait until midnight")
        
    elif response.status_code == 401:
        print("✗ UNAUTHORIZED - Invalid API key")
        
    elif response.status_code == 403:
        print("✗ FORBIDDEN - API key may be expired or restricted")
        
    else:
        print(f"✗ Unexpected status: {response.status_code}")
        print(f"Response: {response.text[:200]}")
    
except requests.exceptions.RequestException as e:
    print(f"✗ Error: {e}")

print()
print("="*70)
print("RECOMMENDATIONS")
print("="*70 + "\n")

print("If rate limited (429 error):")
print()
print("1. WAIT - Rate limits typically reset:")
print("   • Hourly limits: Wait 1 hour")
print("   • Daily limits: Wait until midnight (your timezone)")
print()
print("2. USE DEMO DATA - Dashboard already has 40 opportunities")
print("   • python reset_database.py")
print("   • python generate_demo_data.py")
print("   • Works perfectly for development/testing")
print()
print("3. SCHEDULE BULK FETCH - Run during off-hours")
print("   • Setup cron for 2 AM: ./setup_daily_fetch.sh")
print("   • Edit cron time: 0 2 * * * (runs at 2 AM)")
print("   • Less likely to hit rate limits at night")
print()
print("4. REDUCE FREQUENCY - Don't fetch more than once/day")
print("   • Bulk fetch gets ALL opportunities at once")
print("   • No need to run multiple times per day")
print("   • Schedule for early morning (2-6 AM)")
print()
print("Current time:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
print()
