#!/usr/bin/env python3
"""
Re-collect opportunities with STRICT IT-only filtering
This will remove janitorial, construction, facilities, and other non-IT opportunities
"""

import os
import sys

# Add knowledge_graph to path
sys.path.insert(0, 'knowledge_graph')

from collect_env import SAMCollector
from dotenv import load_dotenv

load_dotenv()

print("="*70)
print("🔍 RE-COLLECTING WITH STRICT IT-ONLY FILTERING")
print("="*70)
print("\nThis will:")
print("  1. Fetch opportunities from SAM.gov using IT NAICS codes")
print("  2. Apply 4-layer IT filtering (NAICS + PSC + Keywords + Exclusions)")
print("  3. Remove janitorial, construction, facilities, maintenance")
print("  4. Keep ONLY genuine IT opportunities")
print("\n" + "="*70 + "\n")

# Create collector
collector = SAMCollector(
    api_key=os.getenv('SAM_API_KEY'),
    days_back=30  # Last 30 days
)

print("\n📊 Collecting with IT-ONLY filters:")
print("   NAICS: 541511, 541512, 541519, 518210")
print("   Filtering: PSC codes, IT keywords, exclusions")
print("   Limit: 50 opportunities (increase if needed)\n")

# Collect opportunities
opportunities = collector.collect_opportunities(
    naics_codes=['541511', '541512', '541519', '518210'],
    limit=50,
    setaside=None
)

print(f"\n✅ Collection complete!")
print(f"   Total opportunities collected: {len(opportunities)}")
print(f"   These are IT-filtered and ready for scoring\n")

print("="*70)
print("🚀 NEXT STEPS:")
print("="*70)
print("\n1. Score the opportunities:")
print("   cd knowledge_graph")
print("   python opportunity_scout.py --days 30")
print("\n2. Restart the dashboard:")
print("   python team_dashboard_integrated.py")
print("\n3. Refresh BD Intelligence Hub to see clean IT opportunities")
print("\n" + "="*70)
