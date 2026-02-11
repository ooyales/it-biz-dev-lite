#!/usr/bin/env python3
"""
Extract Contacts from Contract Awards

Reads contract awards from Neo4j, extracts vendor contacts and agency POCs,
and syncs them to the SQLite contacts database.

This is a great way to build your contact database without hitting SAM.gov
API limits — you're mining data you've already collected.
"""

import os
import sqlite3
from typing import List, Dict
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

NEO4J_URI = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD', 'your-neo4j-password')
CONTACTS_DB = 'data/contacts.db'


class ContactExtractor:
    """Extract contacts from Neo4j contract awards and sync to SQLite"""
    
    def __init__(self):
        self.driver = GraphDatabase.driver(NEO4J_URI, auth=('neo4j', NEO4J_PASSWORD))
        self.conn = sqlite3.connect(CONTACTS_DB)
        self.cursor = self.conn.cursor()
    
    def close(self):
        self.driver.close()
        self.conn.close()
    
    def extract_vendor_contacts(self) -> List[Dict]:
        """
        Extract unique vendor organizations from contracts.
        
        Returns vendor name, agency, and contract count for each.
        """
        query = """
        MATCH (c:Contract)-[:AWARDED_TO]->(org:Organization)
        WHERE org.name IS NOT NULL AND org.name <> 'Unknown' AND org.name <> ''
        WITH org.name AS vendor, c.agency AS agency, count(*) AS contract_count
        RETURN vendor, agency, contract_count
        ORDER BY contract_count DESC
        """
        
        contacts = []
        with self.driver.session(database="neo4j") as session:
            result = session.run(query)
            for record in result:
                vendor = record['vendor']
                agency = record['agency'] or 'Unknown'
                count = record['contract_count']
                
                contacts.append({
                    'name': vendor,
                    'organization': vendor,
                    'agency': agency,
                    'role': 'Vendor',
                    'title': 'Contract Holder',
                    'relationship_strength': self._infer_strength(count),
                    'source': f'{count} contracts in system'
                })
        
        return contacts
    
    def extract_agency_contacts(self) -> List[Dict]:
        """
        Extract unique agencies from contracts as organizational contacts.
        
        These represent the buying organizations you could target.
        """
        query = """
        MATCH (c:Contract)
        WHERE c.agency IS NOT NULL AND c.agency <> 'Unknown' AND c.agency <> ''
        WITH c.agency AS agency, count(*) AS contract_count
        RETURN agency, contract_count
        ORDER BY contract_count DESC
        """
        
        contacts = []
        with self.driver.session(database="neo4j") as session:
            result = session.run(query)
            for record in result:
                agency = record['agency']
                count = record['contract_count']
                
                contacts.append({
                    'name': agency,
                    'organization': agency,
                    'agency': agency,
                    'role': 'Agency',
                    'title': 'Contracting Office',
                    'relationship_strength': 'New',
                    'source': f'{count} contracts awarded'
                })
        
        return contacts
    
    def _infer_strength(self, contract_count: int) -> str:
        """Infer relationship strength from contract count"""
        if contract_count >= 10:
            return 'Strong'
        elif contract_count >= 3:
            return 'Medium'
        else:
            return 'New'
    
    def sync_to_sqlite(self, contacts: List[Dict]):
        """
        Sync extracted contacts to SQLite contacts database.
        
        Skips duplicates based on name + organization.
        """
        # Add agency column if it doesn't exist (migration)
        try:
            self.cursor.execute("ALTER TABLE contacts ADD COLUMN agency TEXT")
            self.conn.commit()
            print("   ✓ Added 'agency' column to contacts table")
        except sqlite3.OperationalError as e:
            if 'duplicate column' in str(e).lower():
                pass  # Column already exists
            else:
                # Column doesn't exist and we couldn't add it
                # Fall back to storing agency in notes
                print("   ⚠️  Could not add 'agency' column, will store in notes")
        
        added = 0
        skipped = 0
        
        for contact in contacts:
            # Check if contact already exists (by name + organization)
            self.cursor.execute("""
                SELECT id FROM contacts 
                WHERE name = ? AND organization = ?
            """, (contact['name'], contact['organization']))
            
            if self.cursor.fetchone():
                skipped += 1
                continue
            
            # Prepare agency field
            agency = contact.get('agency', '')
            notes = contact.get('source', '')
            if agency and agency != contact.get('organization', ''):
                notes = f"Agency: {agency}\n{notes}".strip()
            
            # Try to insert with agency column first
            try:
                self.cursor.execute("""
                    INSERT INTO contacts (
                        name, title, organization, email, phone,
                        agency, role, relationship_strength, notes,
                        last_contact, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'), datetime('now'))
                """, (
                    contact['name'],
                    contact.get('title', ''),
                    contact.get('organization', ''),
                    contact.get('email', ''),
                    contact.get('phone', ''),
                    agency,
                    contact.get('role', ''),
                    contact.get('relationship_strength', 'New'),
                    notes
                ))
            except sqlite3.OperationalError:
                # Fall back to insert without agency column
                self.cursor.execute("""
                    INSERT INTO contacts (
                        name, title, organization, email, phone,
                        role, relationship_strength, notes,
                        last_contact, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'), datetime('now'))
                """, (
                    contact['name'],
                    contact.get('title', ''),
                    contact.get('organization', ''),
                    contact.get('email', ''),
                    contact.get('phone', ''),
                    contact.get('role', ''),
                    contact.get('relationship_strength', 'New'),
                    notes
                ))
            
            added += 1
        
        self.conn.commit()
        return added, skipped
    
    def run(self):
        """Full extraction and sync process"""
        print("=" * 70)
        print("EXTRACTING CONTACTS FROM CONTRACT AWARDS")
        print("=" * 70)
        print()
        
        # Extract vendor contacts
        print("📦 Extracting vendor contacts from contracts...")
        vendor_contacts = self.extract_vendor_contacts()
        print(f"   Found {len(vendor_contacts)} unique vendors")
        
        # Extract agency contacts
        print("🏛️  Extracting agency contacts from contracts...")
        agency_contacts = self.extract_agency_contacts()
        print(f"   Found {len(agency_contacts)} unique agencies")
        
        # Combine
        all_contacts = vendor_contacts + agency_contacts
        print(f"\n   Total contacts to sync: {len(all_contacts)}")
        
        # Sync to SQLite
        print("\n💾 Syncing to contacts database...")
        added, skipped = self.sync_to_sqlite(all_contacts)
        
        print(f"\n✓ Sync complete!")
        print(f"   Added: {added}")
        print(f"   Skipped (duplicates): {skipped}")
        print(f"   Total in database: {self._count_total()}")
        print()
        
        self.close()
    
    def _count_total(self) -> int:
        """Count total contacts in database"""
        self.cursor.execute("SELECT COUNT(*) FROM contacts")
        return self.cursor.fetchone()[0]


def main():
    extractor = ContactExtractor()
    try:
        extractor.run()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        extractor.close()


if __name__ == '__main__':
    main()
