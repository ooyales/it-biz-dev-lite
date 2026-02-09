#!/usr/bin/env python3
"""
Re-score opportunities with better agency extraction
This fixes the issue where agencies show as "Not Specified"
"""

import sys
import os

# Change to project root if needed
if os.path.exists('knowledge_graph'):
    pass  # Already in root
elif os.path.exists('../knowledge_graph'):
    os.chdir('..')
else:
    print("✗ Cannot find knowledge_graph directory!")
    sys.exit(1)

sys.path.append('knowledge_graph')

import json
from pathlib import Path
from opportunity_scout import OpportunityScout

print("🔧 Re-scoring opportunities with better agency detection...")
print()

# Find latest scout data - check both locations
scout_files = list(Path('knowledge_graph').glob('scout_data_*.json'))
if not scout_files:
    scout_files = list(Path('.').glob('scout_data_*.json'))

scout_files = sorted(scout_files, reverse=True)

if not scout_files:
    print("✗ No scout data found!")
    print("  Checked: knowledge_graph/scout_data_*.json")
    print("  Checked: scout_data_*.json")
    print()
    print("💡 Scout data should be in:")
    import glob
    kgfiles = glob.glob('knowledge_graph/*.json')
    if kgfiles:
        print(f"  Found these files: {kgfiles[:5]}")
    sys.exit(1)

# Load the data
with open(scout_files[0]) as f:
    data = json.load(f)

opportunities = data.get('opportunities', [])
print(f"→ Found {len(opportunities)} opportunities to re-score")

# Initialize scout
scout = OpportunityScout()

# Re-score each opportunity
new_scores = []
fixed_count = 0

for opp in opportunities:
    # Extract agency from multiple fields
    agency = (opp.get('organizationName') or 
             opp.get('fullParentPathName') or
             opp.get('department') or
             opp.get('subtier') or
             opp.get('office'))
    
    if agency and agency != opp.get('organizationName'):
        print(f"  Fixed: {opp.get('title', '')[:50]} → {agency[:30]}")
        opp['organizationName'] = agency
        fixed_count += 1
    
    # Re-score with proper agency
    score = scout.score_opportunity(opp)
    
    # Ensure contacts have all_contacts list populated
    if score['contacts']['total_contacts'] > 0 and not score['contacts'].get('all_contacts'):
        # Rebuild all_contacts from categorized lists
        all_contacts = []
        all_contacts.extend(score['contacts'].get('decision_makers', []))
        all_contacts.extend(score['contacts'].get('technical_leads', []))
        all_contacts.extend(score['contacts'].get('executives', []))
        all_contacts.extend(score['contacts'].get('influencers', []))
        score['contacts']['all_contacts'] = all_contacts
    
    new_scores.append(score)

scout.close()

print()
print(f"✓ Fixed {fixed_count} opportunities with missing agencies")
print(f"✓ Re-scored all {len(opportunities)} opportunities")

# Save updated data
output_file = scout_files[0]
data['scores'] = new_scores

with open(output_file, 'w') as f:
    json.dump(data, f, indent=2)

print(f"✓ Saved to {output_file}")
print()
print("🎉 Done! Refresh your browser to see the updated data")
print("   http://localhost:8080/bd-intelligence")
