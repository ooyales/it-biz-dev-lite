#!/usr/bin/env python3
"""
Filter existing opportunities to IT-only WITHOUT re-pulling from SAM.gov
This applies the same 4-layer filtering to your existing data
"""

import json
import sys
from pathlib import Path

# IT Keywords (Layer 3)
IT_KEYWORDS = {
    'software', 'cloud', 'cybersecurity', 'cyber security', 'network', 'database',
    'application', 'development', 'programming', 'devops', 'agile', 'scrum',
    'data analytics', 'data science', 'machine learning', 'artificial intelligence',
    'IT infrastructure', 'systems integration', 'help desk', 'technical support',
    'server', 'virtualization', 'container', 'kubernetes', 'docker',
    'web development', 'mobile app', 'API', 'microservices', 'SaaS',
    'information technology', 'computer systems', 'IT services',
    'system administration', 'IT security', 'information security',
    'software engineering', 'full stack', 'frontend', 'backend',
    'cloud computing', 'AWS', 'Azure', 'Google Cloud', 'GCP',
    'automation', 'CI/CD', 'continuous integration', 'deployment',
    'monitoring', 'logging', 'observability', 'performance',
    'digital transformation', 'modernization', 'migration',
    'enterprise architecture', 'solution architecture',
    'business intelligence', 'BI', 'analytics platform',
    'ETL', 'data pipeline', 'data warehouse', 'data lake'
}

# Exclusion Keywords (Layer 4)
EXCLUSION_KEYWORDS = {
    # Janitorial
    'janitorial', 'custodial', 'cleaning service', 'sanitation', 'housekeeping',
    'waste removal', 'trash', 'garbage', 'recycling service',
    
    # Construction/Facilities
    'construction', 'renovation', 'building maintenance', 'hvac', 'plumbing',
    'electrical work', 'carpentry', 'painting', 'roofing', 'flooring',
    'demolition', 'facilities maintenance', 'grounds maintenance',
    'landscaping', 'lawn care', 'pest control', 'snow removal',
    
    # Security (physical, not cyber)
    'security guard', 'physical security officer', 'armed guard',
    'unarmed guard', 'security patrol',
    
    # Food/Transportation
    'food service', 'cafeteria', 'transportation', 'moving service',
    'shipping', 'delivery', 'courier',
    
    # Other non-IT
    'bottled', 'juice', 'beverage', 'water', 'fuel', 'diesel', 'gasoline',
    'oil tank', 'propane', 'chlorine', 'chemical',
    'door maintenance', 'automatic door', 'gate', 'fence',
    'parking', 'vehicle', 'automobile', 'truck',
    'medical equipment', 'hospital', 'clinic',
    'textiles', 'uniforms', 'laundry',
    'office supplies', 'furniture', 'fixtures'
}

# IT NAICS Codes (Layer 1)
IT_NAICS = {'541511', '541512', '541519', '518210'}

# IT PSC Codes (Layer 2) - D3XX series
IT_PSC_PREFIXES = ['D3', '7030', 'R4']

def is_it_opportunity(opp):
    """Determine if opportunity is genuine IT work"""
    
    title = (opp.get('title') or '').lower()
    description = (opp.get('description') or '')[:500].lower()  # First 500 chars
    naics = str(opp.get('naicsCode') or opp.get('naics') or '')
    psc = str(opp.get('pscCode') or opp.get('classificationCode') or '')
    
    combined_text = f"{title} {description}"
    
    # Layer 1: IT NAICS code (strong signal)
    if naics in IT_NAICS:
        # Even with IT NAICS, check for exclusions
        exclusion_count = sum(1 for word in EXCLUSION_KEYWORDS if word in combined_text)
        if exclusion_count == 0:
            return True, "IT NAICS code"
        elif exclusion_count == 1:
            # One exclusion word, but check for strong IT signals
            it_count = sum(1 for word in IT_KEYWORDS if word in combined_text)
            if it_count >= 3:
                return True, "IT NAICS + multiple IT keywords override exclusion"
    
    # Layer 2: IT PSC code (strong signal)
    if any(psc.startswith(prefix) for prefix in IT_PSC_PREFIXES):
        exclusion_count = sum(1 for word in EXCLUSION_KEYWORDS if word in combined_text)
        if exclusion_count == 0:
            return True, "IT PSC code"
    
    # Layer 3 & 4: Keyword analysis
    it_keyword_count = sum(1 for word in IT_KEYWORDS if word in combined_text)
    exclusion_count = sum(1 for word in EXCLUSION_KEYWORDS if word in combined_text)
    
    # Strong exclusion signals
    if exclusion_count >= 2:
        return False, f"{exclusion_count} exclusion keywords"
    
    # Has exclusions but also strong IT signals
    if exclusion_count == 1 and it_keyword_count >= 3:
        return True, f"{it_keyword_count} IT keywords override 1 exclusion"
    
    # Has exclusions
    if exclusion_count >= 1:
        return False, f"Exclusion keyword present"
    
    # Pure IT keywords check
    if it_keyword_count >= 2:
        return True, f"{it_keyword_count} IT keywords"
    
    # Not enough IT signals
    return False, f"Only {it_keyword_count} IT keywords (need 2+)"

# Find scout data
scout_files = list(Path('knowledge_graph').glob('scout_data_*.json'))
if not scout_files:
    scout_files = list(Path('.').glob('scout_data_*.json'))

if not scout_files:
    print("❌ No scout data files found!")
    sys.exit(1)

scout_file = sorted(scout_files, reverse=True)[0]
print("="*70)
print("🔍 FILTERING EXISTING OPPORTUNITIES FOR IT-ONLY")
print("="*70)
print(f"\n📂 Processing: {scout_file}")

# Load data
with open(scout_file) as f:
    data = json.load(f)

opportunities = data.get('opportunities', [])
scores = data.get('scores', [])

print(f"\n📊 Before filtering: {len(opportunities)} opportunities")

# Filter opportunities
it_opportunities = []
it_scores = []
removed = []

for i, opp in enumerate(opportunities):
    is_it, reason = is_it_opportunity(opp)
    
    if is_it:
        it_opportunities.append(opp)
        if i < len(scores):
            it_scores.append(scores[i])
    else:
        title = opp.get('title', 'Unknown')[:60]
        removed.append({'title': title, 'reason': reason})

print(f"✅ After filtering: {len(it_opportunities)} IT opportunities")
print(f"🗑️  Removed: {len(removed)} non-IT opportunities")

if removed:
    print(f"\n📋 Sample of removed opportunities:")
    for item in removed[:10]:
        print(f"   ❌ {item['title']}...")
        print(f"      Reason: {item['reason']}")
    
    if len(removed) > 10:
        print(f"   ... and {len(removed) - 10} more")

# Save backup
backup_file = str(scout_file) + '.before_it_filter'
print(f"\n💾 Saving backup to: {backup_file}")
with open(backup_file, 'w') as f:
    json.dump(data, f, indent=2)

# Save filtered data
data['opportunities'] = it_opportunities
data['scores'] = it_scores

print(f"💾 Saving IT-only data to: {scout_file}")
with open(scout_file, 'w') as f:
    json.dump(data, f, indent=2)

print("\n" + "="*70)
print("✅ FILTERING COMPLETE!")
print("="*70)
print(f"\nResults:")
print(f"  Original:  {len(opportunities)} opportunities")
print(f"  IT-only:   {len(it_opportunities)} opportunities")
print(f"  Removed:   {len(removed)} non-IT")
print(f"  Success:   {len(it_opportunities)/len(opportunities)*100:.1f}% are genuine IT")

print("\n🚀 Restart the dashboard to see clean IT opportunities:")
print("   python team_dashboard_integrated.py")
