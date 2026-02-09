#!/usr/bin/env python3
"""
Remove duplicate opportunities from scout data
"""

import json
import sys
from pathlib import Path
from collections import defaultdict

# Find scout data files
scout_files = list(Path('knowledge_graph').glob('scout_data_*.json'))
if not scout_files:
    scout_files = list(Path('.').glob('scout_data_*.json'))

if not scout_files:
    print("❌ No scout data files found!")
    print("   Run: cd knowledge_graph && python opportunity_scout.py --days 30")
    sys.exit(1)

# Get most recent
scout_file = sorted(scout_files, reverse=True)[0]
print(f"📂 Processing: {scout_file}")

# Load data
with open(scout_file) as f:
    data = json.load(f)

opportunities = data.get('opportunities', [])
scores = data.get('scores', [])

print(f"\n📊 Before deduplication: {len(opportunities)} opportunities")

# Check for duplicates by notice_id
seen_ids = {}
duplicates = []

for i, opp in enumerate(opportunities):
    notice_id = opp.get('noticeId') or opp.get('notice_id')
    
    if not notice_id:
        print(f"   ⚠️  Warning: Opportunity #{i} has no notice_id")
        continue
    
    if notice_id in seen_ids:
        duplicates.append({
            'notice_id': notice_id,
            'title': opp.get('title', 'Unknown'),
            'original_index': seen_ids[notice_id],
            'duplicate_index': i
        })
    else:
        seen_ids[notice_id] = i

if duplicates:
    print(f"\n🔍 Found {len(duplicates)} duplicate opportunities:")
    for dup in duplicates[:10]:  # Show first 10
        print(f"   - {dup['title'][:50]}... (appears at indices {dup['original_index']} and {dup['duplicate_index']})")
    
    if len(duplicates) > 10:
        print(f"   ... and {len(duplicates) - 10} more")
    
    # Remove duplicates
    print(f"\n🧹 Removing duplicates...")
    
    # Keep track of which indices to keep
    indices_to_keep = []
    seen_in_output = set()
    
    for i, opp in enumerate(opportunities):
        notice_id = opp.get('noticeId') or opp.get('notice_id')
        if notice_id and notice_id not in seen_in_output:
            indices_to_keep.append(i)
            seen_in_output.add(notice_id)
        elif not notice_id:
            # Keep opportunities without IDs (shouldn't happen but be safe)
            indices_to_keep.append(i)
    
    # Filter opportunities and scores
    clean_opportunities = [opportunities[i] for i in indices_to_keep]
    clean_scores = [scores[i] for i in indices_to_keep if i < len(scores)]
    
    print(f"✅ After deduplication: {len(clean_opportunities)} opportunities")
    print(f"   Removed: {len(opportunities) - len(clean_opportunities)} duplicates")
    
    # Save cleaned data
    data['opportunities'] = clean_opportunities
    data['scores'] = clean_scores
    
    backup_file = str(scout_file) + '.backup'
    print(f"\n💾 Saving backup to: {backup_file}")
    with open(backup_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"💾 Saving cleaned data to: {scout_file}")
    with open(scout_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    print("\n✅ Deduplication complete!")
    print(f"   Original: {len(opportunities)} opportunities")
    print(f"   Cleaned:  {len(clean_opportunities)} opportunities")
    print(f"   Removed:  {len(opportunities) - len(clean_opportunities)} duplicates")
    
else:
    print("\n✅ No duplicates found! Data is already clean.")

print("\n🚀 Restart the dashboard to see the cleaned data:")
print("   python team_dashboard_integrated.py")
