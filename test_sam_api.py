#!/usr/bin/env python3
"""
SAM.gov API Test and Fix
Diagnoses and fixes common SAM.gov API issues
"""

import yaml
import requests
from datetime import datetime, timedelta
import json

print("\n" + "="*70)
print("SAM.GOV API TEST & FIX")
print("="*70 + "\n")

# Load config
try:
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    api_key = config.get('sam_gov', {}).get('api_key', '')
except Exception as e:
    print(f"✗ Error loading config: {e}")
    api_key = ''

if not api_key:
    print("✗ No API key found in config.yaml\n")
    print("To get a SAM.gov API key:")
    print("1. Go to: https://open.gsa.gov/api/sam-gov-opportunities/")
    print("2. Request an API key")
    print("3. Add to config.yaml:")
    print("   sam_gov:")
    print("     api_key: 'your-key-here'")
    exit(1)

print(f"✓ API key found (length: {len(api_key)} chars)\n")

# Test different parameter combinations
base_url = "https://api.sam.gov/opportunities/v2/search"

print("Testing SAM.gov API with different parameter combinations...\n")

tests = [
    {
        'name': 'Test 1: Minimal parameters',
        'params': {
            'api_key': api_key,
            'limit': 1
        }
    },
    {
        'name': 'Test 2: With simple date',
        'params': {
            'api_key': api_key,
            'limit': 1,
            'postedFrom': '01/01/2026'
        }
    },
    {
        'name': 'Test 3: With date range',
        'params': {
            'api_key': api_key,
            'limit': 1,
            'postedFrom': (datetime.now() - timedelta(days=30)).strftime('%m/%d/%Y'),
            'postedTo': datetime.now().strftime('%m/%d/%Y')
        }
    },
    {
        'name': 'Test 4: With NAICS code',
        'params': {
            'api_key': api_key,
            'limit': 1,
            'naicsCode': '541512',
            'postedFrom': '01/01/2026'
        }
    }
]

working_params = None

for test in tests:
    print(f"{test['name']}")
    print(f"  Parameters: {', '.join([k for k in test['params'].keys() if k != 'api_key'])}")
    
    try:
        response = requests.get(base_url, params=test['params'], timeout=10)
        print(f"  Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            total = data.get('totalRecords', 0)
            print(f"  ✓ SUCCESS! Total records: {total}")
            
            if total > 0:
                opps = data.get('opportunitiesData', [])
                if opps:
                    print(f"  Sample: {opps[0].get('title', 'N/A')[:50]}...")
            
            working_params = test['params']
            break
        elif response.status_code == 400:
            print(f"  ✗ Bad Request")
            try:
                error_data = response.json()
                print(f"  Error: {error_data}")
            except:
                print(f"  Response: {response.text[:200]}")
        elif response.status_code == 401:
            print(f"  ✗ Unauthorized - Invalid API key")
        elif response.status_code == 403:
            print(f"  ✗ Forbidden - Check API key")
        elif response.status_code == 429:
            print(f"  ✗ Rate limited")
        else:
            print(f"  ✗ Error: {response.status_code}")
            
    except requests.exceptions.Timeout:
        print(f"  ✗ Timeout")
    except Exception as e:
        print(f"  ✗ Exception: {e}")
    
    print()

print("="*70)

if working_params:
    print("✓ FOUND WORKING CONFIGURATION!")
    print("="*70 + "\n")
    print("Working parameters:")
    for key, value in working_params.items():
        if key != 'api_key':
            print(f"  {key}: {value}")
    
    print("\nRecommended config.yaml:")
    print("-" * 70)
    print("sam_gov:")
    print(f"  api_key: '{api_key}'")
    print(f"  lookback_days: 30")
    print("  naics_codes:")
    print("    - '541512'")
    print("    - '541519'")
    print()
    
else:
    print("✗ NO WORKING CONFIGURATION FOUND")
    print("="*70 + "\n")
    print("Possible issues:")
    print("1. Invalid API key")
    print("2. API key expired")
    print("3. API quota exceeded")
    print("4. SAM.gov API is down")
    print()
    print("Solutions:")
    print("• Get a new API key: https://open.gsa.gov/api/sam-gov-opportunities/")
    print("• Wait 24 hours (quota may reset)")
    print("• Use demo data: python generate_demo_data.py")
    print()

print("💡 For your demo tomorrow:")
print("-" * 70)
print("Use demo data instead - it's instant and looks real!")
print()
print("Commands:")
print("  python reset_database.py")
print("  python generate_demo_data.py")
print("  python setup_contact_network.py")
print("  ./start_team_system.sh")
print()
