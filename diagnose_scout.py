#!/usr/bin/env python3
"""
SAM.gov Scout Diagnostic - Check why opportunities folder is empty
"""

import os
import yaml
from pathlib import Path
from datetime import datetime
import json

print("\n" + "="*70)
print("SAM.GOV SCOUT DIAGNOSTIC")
print("="*70 + "\n")

# Check directory structure
print("📁 CHECKING DIRECTORY STRUCTURE")
print("-" * 70)

directories = [
    'data',
    'data/opportunities',
    'data/analysis',
    'data/cache',
    'logs'
]

for dir_path in directories:
    exists = os.path.exists(dir_path)
    status = "✓" if exists else "✗"
    
    if exists:
        files = list(Path(dir_path).glob('*'))
        file_count = len(files)
        print(f"{status} {dir_path:<30} EXISTS ({file_count} files)")
        
        if file_count > 0 and file_count <= 5:
            for f in files[:5]:
                size = os.path.getsize(f) if os.path.isfile(f) else 0
                print(f"    └─ {f.name} ({size:,} bytes)")
    else:
        print(f"{status} {dir_path:<30} MISSING")

print()

# Check config.yaml
print("⚙️  CHECKING CONFIG.YAML")
print("-" * 70)

if os.path.exists('config.yaml'):
    print("✓ config.yaml found")
    try:
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        # Check SAM.gov settings
        sam_config = config.get('sam_gov', {})
        api_key = sam_config.get('api_key', '')
        
        if api_key:
            # Mask the key for security
            masked_key = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "***"
            print(f"  API Key: {masked_key} (length: {len(api_key)} chars)")
            
            if len(api_key) < 20:
                print("  ⚠️  API key seems too short - might be invalid")
        else:
            print("  ✗ NO API KEY FOUND")
            print("  Add your SAM.gov API key to config.yaml:")
            print("    sam_gov:")
            print("      api_key: 'your-key-here'")
        
        # Check search parameters
        print(f"  Lookback days: {sam_config.get('lookback_days', 'NOT SET')}")
        print(f"  NAICS codes: {sam_config.get('naics_codes', 'NOT SET')}")
        
    except Exception as e:
        print(f"  ✗ Error reading config: {e}")
else:
    print("✗ config.yaml NOT FOUND")
    print("  Create config.yaml with SAM.gov API key")

print()

# Check logs
print("📋 CHECKING LOGS")
print("-" * 70)

log_files = list(Path('logs').glob('*.log')) if os.path.exists('logs') else []

if log_files:
    print(f"Found {len(log_files)} log file(s)")
    
    # Check most recent log
    latest_log = max(log_files, key=lambda p: p.stat().st_mtime)
    print(f"\nMost recent: {latest_log}")
    
    try:
        with open(latest_log, 'r') as f:
            lines = f.readlines()
        
        print(f"Lines: {len(lines)}")
        
        if lines:
            print("\nLast 10 lines:")
            for line in lines[-10:]:
                print(f"  {line.rstrip()}")
    except Exception as e:
        print(f"Error reading log: {e}")
else:
    print("No log files found")

print()

# Check database
print("🗄️  CHECKING DATABASE")
print("-" * 70)

db_path = "data/team_dashboard.db"
if os.path.exists(db_path):
    import sqlite3
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        c.execute("SELECT COUNT(*) FROM opportunities")
        count = c.fetchone()[0]
        
        print(f"✓ Database exists: {db_path}")
        print(f"  Total opportunities: {count}")
        
        if count > 0:
            c.execute("SELECT notice_id, title, posted_date FROM opportunities ORDER BY created_at DESC LIMIT 5")
            print("\n  Most recent opportunities:")
            for row in c.fetchall():
                print(f"    • {row[0]}: {row[1][:50]}... ({row[2]})")
        
        conn.close()
    except Exception as e:
        print(f"✗ Error reading database: {e}")
else:
    print(f"✗ Database not found: {db_path}")

print()

# Check if scout has ever run
print("🔍 SCOUT EXECUTION CHECK")
print("-" * 70)

indicators = {
    'data/opportunities/*.json': 'Opportunity files saved',
    'data/cache/*.json': 'API cache files',
    'logs/*.log': 'Log files',
    'data/analysis/*.json': 'Analysis files'
}

ran_before = False
for pattern, description in indicators.items():
    files = list(Path('.').glob(pattern))
    if files:
        print(f"✓ {description}: {len(files)} files found")
        ran_before = True
    else:
        print(f"✗ {description}: None found")

if not ran_before:
    print("\n⚠️  Scout appears to have NEVER RUN")
    print("\nTo run the scout:")
    print("  1. Using dashboard: http://localhost:8080 → Click 'Run Scout'")
    print("  2. Using script: python main_integrated.py")
    print("  3. Using automated: Set up cron job (see documentation)")

print()

# SAM.gov API test
print("🌐 SAM.GOV API TEST")
print("-" * 70)

if os.path.exists('config.yaml'):
    try:
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        api_key = config.get('sam_gov', {}).get('api_key', '')
        
        if api_key:
            print("Testing SAM.gov API connection...")
            import requests
            
            test_url = "https://api.sam.gov/opportunities/v2/search"
            params = {
                'api_key': api_key,
                'limit': 1,
                'postedFrom': '01/01/2026'
            }
            
            try:
                response = requests.get(test_url, params=params, timeout=10)
                print(f"  Status code: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    total = data.get('totalRecords', 0)
                    print(f"  ✓ API working! Total records available: {total}")
                elif response.status_code == 401:
                    print("  ✗ UNAUTHORIZED - Invalid API key")
                    print("    Get a valid key from: https://open.gsa.gov/api/sam-gov-opportunities/")
                elif response.status_code == 403:
                    print("  ✗ FORBIDDEN - API key might be expired or invalid")
                elif response.status_code == 429:
                    print("  ✗ RATE LIMITED - Too many requests")
                else:
                    print(f"  ✗ Error: {response.status_code}")
                    
            except requests.exceptions.RequestException as e:
                print(f"  ✗ Connection error: {e}")
        else:
            print("⚠️  No API key - skipping API test")
            
    except Exception as e:
        print(f"Error: {e}")

print()

# Recommendations
print("="*70)
print("💡 RECOMMENDATIONS")
print("="*70 + "\n")

if not os.path.exists('config.yaml'):
    print("1. CREATE config.yaml with your SAM.gov API key")
    print("   Get key from: https://open.gsa.gov/api/sam-gov-opportunities/\n")
elif not config.get('sam_gov', {}).get('api_key'):
    print("1. ADD SAM.gov API key to config.yaml\n")

if not ran_before:
    print("2. RUN the scout to fetch opportunities:")
    print("   • Via dashboard: ./start_team_system.sh then click 'Run Scout'")
    print("   • Via command: python main_integrated.py")
    print("   • Or: python automated_daily_scout.py\n")

print("3. For demo with data NOW:")
print("   • Generate demo data: python generate_demo_data.py")
print("   • This creates realistic fake data for testing\n")

print("4. Check if scout is scheduled:")
print("   • View crontab: crontab -l")
print("   • Should run daily at 7 AM\n")

print()
