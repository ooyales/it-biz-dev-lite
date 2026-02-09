cd knowledge_graph
python3 << 'EOF'
import json
from pathlib import Path

scout_files = sorted(Path('.').glob('scout_data_*.json'), reverse=True)
with open(scout_files[0]) as f:
    data = json.load(f)

# Find a score with contacts
for i, score in enumerate(data['scores'][:10]):
    if score.get('contacts', {}).get('total_contacts', 0) > 0:
        print(f"Opportunity {i}: {data['opportunities'][i].get('title', '')[:50]}")
        print(f"  total_contacts: {score['contacts']['total_contacts']}")
        print(f"  all_contacts length: {len(score['contacts'].get('all_contacts', []))}")
        print(f"  decision_makers length: {len(score['contacts'].get('decision_makers', []))}")
        
        # Show first contact if exists
        if score['contacts'].get('decision_makers'):
            dm = score['contacts']['decision_makers'][0]
            print(f"  Sample DM: {dm.get('name')} - {dm.get('email')}")
        
        print()
        break
EOF
