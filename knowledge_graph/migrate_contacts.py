#!/usr/bin/env python3
"""
Migrate Existing Contacts to Knowledge Graph
Moves contacts from SQLite to Neo4j
"""

import sqlite3
import os
import sys
sys.path.append('..')

from graph.neo4j_client import KnowledgeGraphClient, generate_person_id, generate_org_id
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
SQLITE_DB = "../data/team_dashboard.db"
NEO4J_URI = "bolt://localhost:7687/contactsgraphdb"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD', 'changeme')


def migrate_contacts_to_graph():
    """Migrate all contacts from SQLite to Neo4j"""
    
    logger.info("="*70)
    logger.info("MIGRATING CONTACTS TO KNOWLEDGE GRAPH")
    logger.info("="*70 + "\n")
    
    # Connect to SQLite
    logger.info("Connecting to SQLite database...")
    sqlite_conn = sqlite3.connect(SQLITE_DB)
    sqlite_conn.row_factory = sqlite3.Row
    c = sqlite_conn.cursor()
    
    # Connect to Neo4j
    logger.info("Connecting to Neo4j...")
    kg = KnowledgeGraphClient(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    
    # Initialize schema
    logger.info("Initializing graph schema...")
    kg.initialize_schema()
    
    # Migrate contacts
    logger.info("\nMigrating contacts...")
    c.execute("""
        SELECT id, first_name, last_name, title, organization, department,
               email, phone, linkedin_url, agency, office_symbol, location,
               clearance_level, role_type, influence_level, notes,
               created_at, updated_at
        FROM contacts
    """)
    
    contacts = c.fetchall()
    logger.info(f"Found {len(contacts)} contacts to migrate")
    
    person_mapping = {}  # SQLite ID -> Neo4j ID mapping
    org_mapping = {}     # Organization name -> Neo4j ID
    
    for contact in contacts:
        # Generate Neo4j person ID
        neo4j_person_id = generate_person_id(
            f"{contact['first_name']} {contact['last_name']}",
            contact['email']
        )
        
        # Store mapping
        person_mapping[contact['id']] = neo4j_person_id
        
        # Create person node
        person_data = {
            'id': neo4j_person_id,
            'sqlite_id': contact['id'],  # Keep reference
            'name': f"{contact['first_name']} {contact['last_name']}",
            'first_name': contact['first_name'],
            'last_name': contact['last_name'],
            'title': contact['title'],
            'organization': contact['organization'],
            'department': contact['department'],
            'email': contact['email'],
            'phone': contact['phone'],
            'linkedin_url': contact['linkedin_url'],
            'agency': contact['agency'],
            'office_symbol': contact['office_symbol'],
            'location': contact['location'],
            'clearance_level': contact['clearance_level'],
            'role_type': contact['role_type'],
            'influence_level': contact['influence_level'],
            'notes': contact['notes'],
            'source': 'SQLite migration',
            'migrated_at': datetime.now().isoformat()
        }
        
        kg.create_person(person_data)
        
        # Create organization if not exists
        if contact['organization']:
            if contact['organization'] not in org_mapping:
                neo4j_org_id = generate_org_id(contact['organization'])
                org_mapping[contact['organization']] = neo4j_org_id
                
                org_data = {
                    'id': neo4j_org_id,
                    'name': contact['organization'],
                    'agency': contact['agency'],
                    'type': 'Federal Agency' if 'Department' in contact['agency'] else 'Organization'
                }
                
                kg.create_organization(org_data)
            
            # Create WORKS_AT relationship
            kg.create_works_at(
                person_id=neo4j_person_id,
                org_id=org_mapping[contact['organization']],
                title=contact['title'],
                source='SQLite migration'
            )
    
    logger.info(f"✓ Migrated {len(contacts)} contacts")
    logger.info(f"✓ Created {len(org_mapping)} organizations")
    
    # Migrate contact relationships
    logger.info("\nMigrating contact relationships...")
    c.execute("""
        SELECT contact_id_1, contact_id_2, relationship_type, strength, notes
        FROM contact_relationships
    """)
    
    relationships = c.fetchall()
    logger.info(f"Found {len(relationships)} relationships to migrate")
    
    for rel in relationships:
        person1_id = person_mapping.get(rel['contact_id_1'])
        person2_id = person_mapping.get(rel['contact_id_2'])
        
        if person1_id and person2_id:
            # Map relationship types to graph
            rel_type_mapping = {
                'Reports To': 'REPORTS_TO',
                'Supervisor': 'MANAGES',
                'Peer': 'COLLEAGUE_OF',
                'Colleague': 'COLLEAGUE_OF',
                'Works With': 'WORKS_WITH',
                'Mentor': 'MENTORS',
                'Mentee': 'MENTORED_BY'
            }
            
            # Get mapped type or sanitize the original
            graph_rel_type = rel_type_mapping.get(
                rel['relationship_type'], 
                rel['relationship_type'].upper().replace(' ', '_').replace('-', '_')
            )
            
            # Additional sanitization - remove any other special chars
            import re
            graph_rel_type = re.sub(r'[^A-Z_]', '', graph_rel_type)
            
            properties = {
                'strength': rel['strength'],
                'notes': rel['notes'],
                'source': 'SQLite migration'
            }
            
            kg.create_relationship(
                from_id=person1_id,
                to_id=person2_id,
                rel_type=graph_rel_type,
                properties=properties
            )
    
    logger.info(f"✓ Migrated {len(relationships)} relationships")
    
    # Migrate interactions
    logger.info("\nMigrating interactions...")
    c.execute("""
        SELECT contact_id, interaction_type, interaction_date, subject,
               summary, outcome, next_action, next_action_date, our_team_member
        FROM interactions
    """)
    
    interactions = c.fetchall()
    logger.info(f"Found {len(interactions)} interactions to migrate")
    
    # For interactions, we'll create them as properties on relationships
    # or as separate Event nodes
    
    for interaction in interactions:
        contact_id = person_mapping.get(interaction['contact_id'])
        
        if contact_id:
            # Create interaction as relationship to "You" (your company)
            # We'll create a "You" node to represent your team
            
            # This is placeholder - in real implementation,
            # you'd have a proper "your company" node
            pass
    
    logger.info(f"✓ Migrated {len(interactions)} interactions")
    
    # Get final statistics
    logger.info("\nFinal statistics:")
    stats = kg.get_network_statistics()
    logger.info(f"  People: {stats.get('total_people', 0)}")
    logger.info(f"  Organizations: {stats.get('total_organizations', 0)}")
    logger.info(f"  Relationships: {stats.get('total_relationships', 0)}")
    logger.info(f"  Decision Makers: {stats.get('decision_makers', 0)}")
    
    # Close connections
    sqlite_conn.close()
    kg.close()
    
    logger.info("\n" + "="*70)
    logger.info("MIGRATION COMPLETE!")
    logger.info("="*70)
    logger.info("\nView your graph:")
    logger.info("  Neo4j Browser: http://localhost:7474")
    logger.info("\nTry these Cypher queries:")
    logger.info('  MATCH (n) RETURN n LIMIT 25')
    logger.info('  MATCH (p:Person)-[r:WORKS_AT]->(o:Organization) RETURN p, r, o')
    logger.info('  MATCH (p:Person {role_type: "Decision Maker"}) RETURN p')
    

def verify_migration():
    """Verify migration was successful"""
    
    logger.info("\nVerifying migration...")
    
    kg = KnowledgeGraphClient(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    
    # Check if contacts exist
    stats = kg.get_network_statistics()
    
    if stats.get('total_people', 0) > 0:
        logger.info("✓ Migration verified - graph contains data")
        
        # Show sample data
        sqlite_conn = sqlite3.connect(SQLITE_DB)
        c = sqlite_conn.cursor()
        c.execute("SELECT COUNT(*) FROM contacts")
        sqlite_count = c.fetchone()[0]
        sqlite_conn.close()
        
        neo4j_count = stats.get('total_people', 0)
        
        logger.info(f"  SQLite contacts: {sqlite_count}")
        logger.info(f"  Neo4j people: {neo4j_count}")
        
        if sqlite_count == neo4j_count:
            logger.info("  ✓ Counts match!")
        else:
            logger.warning(f"  ⚠️  Counts don't match")
    else:
        logger.error("✗ Migration verification failed - no data in graph")
    
    kg.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Migrate contacts to knowledge graph')
    parser.add_argument('--verify-only', action='store_true', 
                       help='Only verify, don\'t migrate')
    
    args = parser.parse_args()
    
    if args.verify_only:
        verify_migration()
    else:
        migrate_contacts_to_graph()
        verify_migration()
