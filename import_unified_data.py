#!/usr/bin/env python3
"""
Import Unified Collection Data

Imports data from unified_samgov_collector.py into:
- SQLite (contacts.db)
- Neo4j (contracts, opportunities)

Usage:
    python import_unified_data.py knowledge_graph/unified_collection_*.json
"""

import sys
import json
import sqlite3
from pathlib import Path
from typing import Dict, List


def import_contacts_to_sqlite(contacts: List[Dict], db_path: str = 'data/contacts.db'):
    """Import contacts to SQLite database"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Ensure agency column exists
    try:
        cursor.execute("ALTER TABLE contacts ADD COLUMN agency TEXT")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    added = 0
    skipped = 0
    
    for contact in contacts:
        # Check for duplicates
        cursor.execute("""
            SELECT id FROM contacts 
            WHERE name = ? AND organization = ?
        """, (contact['name'], contact['organization']))
        
        if cursor.fetchone():
            skipped += 1
            continue
        
        # Prepare notes
        notes = f"Contracts: {contact.get('contract_count', 0)}\n"
        notes += f"Total value: ${contact.get('total_value', 0):,.2f}\n"
        
        if contact.get('agencies'):
            notes += f"Agencies: {', '.join(contact['agencies'][:3])}\n"
        
        if contact.get('vendors'):
            notes += f"Top vendors: {', '.join(contact['vendors'][:3])}\n"
        
        # Insert
        cursor.execute("""
            INSERT INTO contacts (
                name, title, organization, role, 
                relationship_strength, notes, agency,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
        """, (
            contact['name'],
            contact.get('role', ''),
            contact['organization'],
            contact.get('type', ''),
            contact.get('relationship_strength', 'New'),
            notes.strip(),
            contact.get('agencies', [''])[0] if contact.get('agencies') else ''
        ))
        
        added += 1
    
    conn.commit()
    conn.close()
    
    return added, skipped


def import_to_neo4j(contracts: List[Dict], opportunities: List[Dict]):
    """Import contracts and opportunities to Neo4j"""
    try:
        from neo4j import GraphDatabase
        import os
        from dotenv import load_dotenv
        
        load_dotenv()
        NEO4J_URI = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
        NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD')
        
        driver = GraphDatabase.driver(NEO4J_URI, auth=('neo4j', NEO4J_PASSWORD))
        
        with driver.session(database="neo4j") as session:
            # Import contracts
            contract_count = 0
            for contract in contracts:
                session.run("""
                    MERGE (org:Organization {name: $vendor_name})
                    
                    MERGE (c:Contract {contract_id: $contract_id})
                    SET c.agency = $agency,
                        c.value = $value,
                        c.date_signed = $date_signed
                    
                    MERGE (c)-[:AWARDED_TO]->(org)
                """, contract)
                contract_count += 1
            
            # Import opportunities (basic - can be enhanced)
            opp_count = 0
            for opp in opportunities[:100]:  # Limit to 100 for now
                session.run("""
                    MERGE (o:Opportunity {notice_id: $noticeId})
                    SET o.title = $title,
                        o.agency = $department,
                        o.posted_date = $postedDate
                """, {
                    'noticeId': opp.get('noticeId', ''),
                    'title': opp.get('title', ''),
                    'department': opp.get('department', {}).get('name', ''),
                    'postedDate': opp.get('postedDate', '')
                })
                opp_count += 1
        
        driver.close()
        return contract_count, opp_count
        
    except ImportError:
        print("⚠️  Neo4j driver not installed, skipping Neo4j import")
        return 0, 0
    except Exception as e:
        print(f"⚠️  Neo4j import error: {e}")
        return 0, 0


def main():
    if len(sys.argv) < 2:
        print("Usage: python import_unified_data.py <unified_collection_file.json>")
        sys.exit(1)
    
    filepath = sys.argv[1]
    
    if not Path(filepath).exists():
        print(f"❌ File not found: {filepath}")
        sys.exit(1)
    
    print("=" * 70)
    print("IMPORTING UNIFIED COLLECTION DATA")
    print("=" * 70)
    print(f"  Source: {filepath}")
    print()
    
    # Load data
    with open(filepath) as f:
        data = json.load(f)
    
    print(f"  Loaded:")
    print(f"    {len(data.get('opportunities', []))} opportunities")
    print(f"    {len(data.get('contracts', []))} contracts")
    print(f"    {len(data.get('contacts', []))} contacts")
    print()
    
    # Import contacts to SQLite
    print("💾 Importing contacts to SQLite...")
    added, skipped = import_contacts_to_sqlite(data.get('contacts', []))
    print(f"   ✓ Added: {added}, Skipped: {skipped}")
    print()
    
    # Import to Neo4j
    print("💾 Importing to Neo4j...")
    contracts_imported, opps_imported = import_to_neo4j(
        data.get('contracts', []),
        data.get('opportunities', [])
    )
    print(f"   ✓ Contracts: {contracts_imported}")
    print(f"   ✓ Opportunities: {opps_imported}")
    print()
    
    print("=" * 70)
    print("IMPORT COMPLETE")
    print("=" * 70)
    print()
    print("✓ Data imported successfully!")
    print("  Refresh your dashboard to see the updates")
    print()


if __name__ == '__main__':
    main()
