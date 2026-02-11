#!/usr/bin/env python3
"""
Sync SQLite Contacts to Neo4j

Creates Person nodes in Neo4j for all contacts in SQLite that don't
already exist. This allows research profiles to be cached.

Usage:
    python sync_contacts_to_neo4j.py
    python sync_contacts_to_neo4j.py --limit 100
"""

import os
import sqlite3
import argparse
from dotenv import load_dotenv

load_dotenv()


def sync_contacts(db_path: str = 'data/contacts.db', limit: int = None):
    """Sync SQLite contacts to Neo4j as Person nodes"""
    
    from neo4j import GraphDatabase
    
    # Connect to Neo4j
    driver = GraphDatabase.driver(
        os.getenv('NEO4J_URI', 'bolt://localhost:7687'),
        auth=('neo4j', os.getenv('NEO4J_PASSWORD'))
    )
    
    # Get existing Person names from Neo4j
    print("📊 Checking existing Person nodes in Neo4j...")
    with driver.session(database="neo4j") as session:
        result = session.run("MATCH (p:Person) RETURN p.name as name")
        existing_names = set(record['name'] for record in result if record['name'])
    
    print(f"   Found {len(existing_names)} existing Person nodes")
    
    # Get contacts from SQLite
    print("📋 Loading contacts from SQLite...")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    query = "SELECT * FROM contacts WHERE name IS NOT NULL AND name != ''"
    if limit:
        query += f" LIMIT {limit}"
    
    cursor.execute(query)
    contacts = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    print(f"   Found {len(contacts)} contacts in SQLite")
    
    # Find contacts that need to be created
    to_create = [c for c in contacts if c.get('name') not in existing_names]
    print(f"   {len(to_create)} contacts need Person nodes created")
    
    if not to_create:
        print("\n✓ All contacts already have Person nodes!")
        driver.close()
        return
    
    # Confirm
    print(f"\nWill create {len(to_create)} new Person nodes in Neo4j.")
    response = input("Continue? (y/n): ")
    if response.lower() != 'y':
        print("Cancelled.")
        driver.close()
        return
    
    # Create Person nodes
    print("\n🚀 Creating Person nodes...")
    created = 0
    errors = 0
    
    with driver.session(database="neo4j") as session:
        for i, contact in enumerate(to_create, 1):
            try:
                name = contact.get('name', '').strip()
                if not name:
                    continue
                
                session.run("""
                    CREATE (p:Person {
                        name: $name,
                        title: $title,
                        organization: $organization,
                        agency: $agency,
                        email: $email,
                        phone: $phone,
                        role_type: $role_type,
                        relationship_strength: $relationship_strength,
                        source: 'SQLite sync',
                        created_at: datetime(),
                        sqlite_id: $sqlite_id
                    })
                """, 
                    name=name,
                    title=contact.get('title', ''),
                    organization=contact.get('organization', ''),
                    agency=contact.get('agency', ''),
                    email=contact.get('email', ''),
                    phone=contact.get('phone', ''),
                    role_type=contact.get('role', ''),
                    relationship_strength=contact.get('relationship_strength', 'New'),
                    sqlite_id=contact.get('id')
                )
                created += 1
                
                if i % 100 == 0:
                    print(f"   Created {i}/{len(to_create)}...")
                    
            except Exception as e:
                errors += 1
                if errors <= 5:
                    print(f"   ❌ Error creating {name}: {e}")
    
    driver.close()
    
    print()
    print("=" * 60)
    print("SYNC COMPLETE")
    print("=" * 60)
    print(f"  Created: {created}")
    print(f"  Errors: {errors}")
    print(f"  Total Person nodes now: {len(existing_names) + created}")
    print()
    print("✓ Contacts synced! Research can now be cached for all contacts.")


def main():
    parser = argparse.ArgumentParser(description='Sync SQLite contacts to Neo4j')
    parser.add_argument('--limit', type=int, default=None, help='Limit number of contacts')
    args = parser.parse_args()
    
    sync_contacts(limit=args.limit)


if __name__ == '__main__':
    main()
