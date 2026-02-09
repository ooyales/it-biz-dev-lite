#!/usr/bin/env python3
"""
Test: Full Pipeline - SAM.gov → Entity Extraction → Knowledge Graph
Watch real opportunity data populate your graph!
"""

import sys
import os
sys.path.append('..')

from nlp.minimal_claude_extractor import MinimalClaudeExtractor
from graph.neo4j_client import KnowledgeGraphClient, generate_person_id, generate_org_id
import requests
import json
from datetime import datetime

print("\n" + "="*70)
print("FULL PIPELINE TEST: SAM.gov → Claude → Neo4j")
print("="*70 + "\n")

# Configuration
#SAM_API_KEY = input("Enter your SAM.gov API key (or press Enter to use sample data): ").strip()
#NEO4J_PASSWORD = input("Enter your Neo4j password: ").strip()

SAM_API_KEY = os.getenv('SAM_API_KEY')
NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD')

# Initialize
print("\n1. Initializing components...")
extractor = MinimalClaudeExtractor()
kg = KnowledgeGraphClient(
    uri="bolt://localhost:7687/contactsgraphdb",
    user="neo4j",
    password=NEO4J_PASSWORD
)
print("   ✓ Entity extractor ready")
print("   ✓ Knowledge graph connected")

# Get opportunity data
print("\n2. Fetching SAM.gov opportunity...")

if SAM_API_KEY:
    # Fetch real data
    try:
        url = "https://api.sam.gov/opportunities/v2/search"
        params = {
            'api_key': SAM_API_KEY,
            'postedFrom': '01/01/2026',
            'postedTo': '01/28/2026',
            'limit': 1
        }
        
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        opportunities = data.get('opportunitiesData', [])
        
        if opportunities:
            opp = opportunities[0]
            print(f"   ✓ Fetched: {opp.get('title', 'Untitled')[:60]}...")
        else:
            print("   ⚠️  No opportunities found, using sample data")
            opp = None
    except Exception as e:
        print(f"   ⚠️  Error fetching: {e}")
        print("   Using sample data instead")
        opp = None
else:
    opp = None

# Use sample data if needed
if not opp:
    print("   Using sample opportunity data...")
    opp = {
        'noticeId': 'SAMPLE-2026-001',
        'title': 'Cloud Infrastructure Modernization Services',
        'organizationName': 'Defense Information Systems Agency',
        'description': '''
        The Defense Information Systems Agency (DISA) seeks qualified contractors 
        to provide cloud infrastructure modernization services. This is a full and 
        open competition under NAICS code 541512.
        
        The Government intends to award a single Firm-Fixed-Price contract with a 
        base period of 12 months and four 12-month option periods.
        
        Estimated contract value: $8,200,000
        
        Point of Contact:
        Sarah M. Johnson
        Contracting Officer
        Defense Information Systems Agency
        Email: sarah.johnson@disa.mil
        Phone: (703) 555-0123
        
        Technical Point of Contact:
        Michael Chen, Program Manager
        Email: michael.chen@disa.mil
        Phone: (703) 555-0145
        
        Questions must be submitted in writing to the Contracting Officer at least 
        10 days prior to the proposal due date.
        ''',
        'postedDate': '2026-01-15',
        'responseDeadLine': '2026-03-15'
    }
    print(f"   ✓ Sample: {opp['title']}")

# Build text for extraction
print("\n3. Preparing text for extraction...")
text_parts = [
    f"Title: {opp.get('title', '')}",
    f"Organization: {opp.get('organizationName', '')}",
    f"Description: {opp.get('description', '')}"
]
text = '\n'.join(filter(None, text_parts))
print(f"   ✓ Text length: {len(text)} characters")

# Extract entities
print("\n4. Extracting entities with Claude...")
print("   (This will cost ~$0.02)")
entities, relationships = extractor.extract(text, extract_relationships=True)

print(f"   ✓ Extracted {len(entities)} entities")
print(f"   ✓ Extracted {len(relationships)} relationships")

# Show what was extracted
print("\n   Entities found:")
for entity in entities[:5]:  # Show first 5
    print(f"      • {entity.type}: {entity.text}")
    if entity.metadata:
        for key, val in entity.metadata.items():
            if val:
                print(f"        - {key}: {val}")

if len(entities) > 5:
    print(f"      ... and {len(entities) - 5} more")

print("\n   Relationships found:")
for rel in relationships[:5]:  # Show first 5
    print(f"      • {rel.subject} --{rel.relation}--> {rel.object}")

if len(relationships) > 5:
    print(f"      ... and {len(relationships) - 5} more")

# Store in graph
print("\n5. Storing in knowledge graph...")

people_created = 0
orgs_created = 0
rels_created = 0

# Create nodes for each entity
for entity in entities:
    try:
        if entity.type == 'PERSON':
            person_id = generate_person_id(
                entity.text, 
                entity.metadata.get('email') if entity.metadata else None
            )
            
            person_data = {
                'id': person_id,
                'name': entity.text,
                'source': f"SAM.gov: {opp.get('noticeId', 'SAMPLE')}",
                'confidence': entity.confidence,
                'extracted_at': datetime.now().isoformat()
            }
            
            # Add metadata
            if entity.metadata:
                person_data.update({
                    k: v for k, v in entity.metadata.items() 
                    if v and k in ['email', 'phone', 'title', 'organization']
                })
            
            kg.create_person(person_data)
            people_created += 1
            
        elif entity.type == 'ORGANIZATION':
            org_id = generate_org_id(entity.text)
            
            org_data = {
                'id': org_id,
                'name': entity.text,
                'source': f"SAM.gov: {opp.get('noticeId', 'SAMPLE')}",
                'confidence': entity.confidence,
                'type': 'Federal Agency' if 'Department' in entity.text or 'Agency' in entity.text else 'Organization'
            }
            
            kg.create_organization(org_data)
            orgs_created += 1
            
    except Exception as e:
        print(f"      ⚠️  Error creating {entity.type} '{entity.text}': {e}")

# Create relationships
for rel in relationships:
    try:
        # Find the entities
        subject_matches = kg.search_people(rel.subject)
        
        if subject_matches:
            subject_id = subject_matches[0]['id']
            
            # Determine target
            if rel.relation in ['WORKS_AT', 'EMPLOYED_BY']:
                target_id = generate_org_id(rel.object)
            else:
                object_matches = kg.search_people(rel.object)
                if object_matches:
                    target_id = object_matches[0]['id']
                else:
                    continue
            
            kg.create_relationship(
                from_id=subject_id,
                to_id=target_id,
                rel_type=rel.relation,
                properties={
                    'confidence': rel.confidence,
                    'source': f"SAM.gov: {opp.get('noticeId', 'SAMPLE')}"
                }
            )
            rels_created += 1
            
    except Exception as e:
        print(f"      ⚠️  Error creating relationship: {e}")

print(f"   ✓ Created {people_created} people")
print(f"   ✓ Created {orgs_created} organizations")
print(f"   ✓ Created {rels_created} relationships")

# Get updated stats
print("\n6. Final statistics...")
stats = kg.get_network_statistics()
print(f"   Total people in graph: {stats.get('total_people', 0)}")
print(f"   Total organizations: {stats.get('total_organizations', 0)}")
print(f"   Total relationships: {stats.get('total_relationships', 0)}")
print(f"   Decision makers: {stats.get('decision_makers', 0)}")

# Cost
cost_stats = extractor.get_cost_estimate()
print(f"\n7. Cost for this extraction: ${cost_stats['estimated_cost']:.4f}")

# Show how to view
print("\n" + "="*70)
print("SUCCESS! Your graph has been updated!")
print("="*70)
print("\nView your updated graph:")
print("  1. Open: http://localhost:7474")
print("  2. Switch to: contactsgraphdb")
print("  3. Run: MATCH (n) RETURN n LIMIT 50")
print("\nYou should now see your new contacts!")
print("\nOr try this query to see just the new data:")
print(f"  MATCH (n) WHERE n.source CONTAINS '{opp.get('noticeId', 'SAMPLE')}' RETURN n")

kg.close()

print("\n✓ Pipeline test complete!")
print(f"✓ Cost: ${cost_stats['estimated_cost']:.4f}")
print("✓ Ready for full automation!")
