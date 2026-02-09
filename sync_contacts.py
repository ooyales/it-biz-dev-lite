#!/usr/bin/env python3
"""
Neo4j to SQLite Contact Sync
Syncs contacts from Neo4j knowledge graph to SQLite contact management database

Usage:
    python sync_contacts.py              # Sync all contacts
    python sync_contacts.py --clear      # Clear SQLite and re-sync
    python sync_contacts.py --preview    # Show what would be synced
"""

import sys
sys.path.append('knowledge_graph')

from graph.neo4j_client import KnowledgeGraphClient
import sqlite3
import os
import argparse
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ANSI colors
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_success(text):
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")

def print_info(text):
    print(f"{Colors.CYAN}→ {text}{Colors.END}")

def print_warning(text):
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.END}")

def print_error(text):
    print(f"{Colors.RED}✗ {text}{Colors.END}")


class ContactSyncer:
    """Sync contacts from Neo4j to SQLite"""
    
    def __init__(self, sqlite_db='data/contacts.db'):
        self.sqlite_db = sqlite_db
        
        # Connect to Neo4j
        print_info("Connecting to Neo4j...")
        self.kg = KnowledgeGraphClient(
            uri=os.getenv('NEO4J_URI', 'bolt://localhost:7687'),
            user=os.getenv('NEO4J_USER', 'neo4j'),
            password=os.getenv('NEO4J_PASSWORD')
        )
        print_success("Connected to Neo4j")
        
        # Ensure SQLite database exists
        self._init_sqlite()
    
    def _init_sqlite(self):
        """Initialize SQLite database if needed"""
        os.makedirs('data', exist_ok=True)
        
        conn = sqlite3.connect(self.sqlite_db)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                organization TEXT,
                role TEXT,
                notes TEXT,
                linkedin_url TEXT,
                relationship_strength TEXT DEFAULT 'New',
                last_contact DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
        print_success("SQLite database ready")
    
    def get_neo4j_contacts(self):
        """Fetch all contacts from Neo4j"""
        print_info("Fetching contacts from Neo4j...")
        
        with self.kg.driver.session(database="contactsgraphdb") as session:
            query = """
            MATCH (p:Person)
            OPTIONAL MATCH (p)-[:WORKS_AT]->(o:Organization)
            RETURN p.id as id,
                   p.name as name,
                   p.email as email,
                   p.phone as phone,
                   p.title as title,
                   p.organization as organization,
                   o.name as org_from_relationship,
                   p.role_type as role_type,
                   p.influence_level as influence_level,
                   p.source as source,
                   p.extracted_at as extracted_at
            ORDER BY p.name
            """
            
            result = session.run(query)
            contacts = [dict(record) for record in result]
        
        print_success(f"Found {len(contacts)} contacts in Neo4j")
        return contacts
    
    def get_sqlite_contacts(self):
        """Get existing contacts from SQLite"""
        conn = sqlite3.connect(self.sqlite_db)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute('SELECT * FROM contacts')
        contacts = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return contacts
    
    def clear_sqlite(self):
        """Clear all contacts from SQLite"""
        print_warning("Clearing all contacts from SQLite...")
        conn = sqlite3.connect(self.sqlite_db)
        conn.execute('DELETE FROM contacts')
        conn.commit()
        conn.close()
        print_success("SQLite contacts cleared")
    
    def sync_contact(self, neo4j_contact, preview=False):
        """Sync a single contact from Neo4j to SQLite"""
        
        # Prepare contact data for SQLite
        name = neo4j_contact['name']
        email = neo4j_contact['email']
        phone = neo4j_contact['phone']
        
        # Determine organization (prefer relationship over property)
        organization = (neo4j_contact['org_from_relationship'] or 
                       neo4j_contact['organization'] or 
                       'Unknown')
        
        # Build role/title
        role = neo4j_contact['title'] or neo4j_contact['role_type'] or 'Contact'
        
        # Build notes from Neo4j metadata
        notes_parts = []
        if neo4j_contact['source']:
            notes_parts.append(f"Source: {neo4j_contact['source']}")
        if neo4j_contact['role_type']:
            notes_parts.append(f"Role Type: {neo4j_contact['role_type']}")
        if neo4j_contact['influence_level']:
            notes_parts.append(f"Influence: {neo4j_contact['influence_level']}")
        if neo4j_contact['extracted_at']:
            notes_parts.append(f"Extracted: {neo4j_contact['extracted_at']}")
        
        notes = "\n".join(notes_parts) if notes_parts else "Imported from Neo4j knowledge graph"
        
        # Determine relationship strength based on influence level
        relationship_strength_map = {
            'Very High': 'Strong',
            'High': 'Strong',
            'Medium': 'Warm',
            'Low': 'New',
            None: 'New'
        }
        relationship_strength = relationship_strength_map.get(
            neo4j_contact['influence_level'], 
            'New'
        )
        
        if preview:
            print(f"  Would sync: {name} ({email or 'no email'}) - {organization}")
            return True
        
        # Check if contact already exists (by email or name)
        conn = sqlite3.connect(self.sqlite_db)
        
        existing = None
        if email:
            cursor = conn.execute('SELECT id FROM contacts WHERE email = ?', (email,))
            existing = cursor.fetchone()
        
        if not existing and name:
            cursor = conn.execute('SELECT id FROM contacts WHERE name = ?', (name,))
            existing = cursor.fetchone()
        
        if existing:
            # Update existing contact
            conn.execute('''
                UPDATE contacts 
                SET phone = COALESCE(?, phone),
                    organization = ?,
                    role = ?,
                    notes = ?,
                    relationship_strength = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (phone, organization, role, notes, relationship_strength, existing[0]))
            result = 'updated'
        else:
            # Insert new contact
            conn.execute('''
                INSERT INTO contacts (name, email, phone, organization, role, notes, relationship_strength)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (name, email, phone, organization, role, notes, relationship_strength))
            result = 'created'
        
        conn.commit()
        conn.close()
        
        return result
    
    def sync_all(self, clear_first=False, preview=False):
        """Sync all contacts from Neo4j to SQLite"""
        
        print("\n" + "="*70)
        print(f"{Colors.BOLD}{Colors.CYAN}NEO4J TO SQLITE CONTACT SYNC{Colors.END}")
        print("="*70 + "\n")
        
        if preview:
            print_warning("PREVIEW MODE - No changes will be made")
            print()
        
        # Get initial stats
        initial_sqlite = self.get_sqlite_contacts()
        print_info(f"SQLite currently has {len(initial_sqlite)} contacts")
        
        if clear_first and not preview:
            self.clear_sqlite()
        
        # Get Neo4j contacts
        neo4j_contacts = self.get_neo4j_contacts()
        
        if not neo4j_contacts:
            print_warning("No contacts found in Neo4j!")
            return
        
        # Sync each contact
        print()
        print_info(f"Syncing {len(neo4j_contacts)} contacts...")
        print()
        
        stats = {'created': 0, 'updated': 0, 'skipped': 0}
        
        for contact in neo4j_contacts:
            try:
                result = self.sync_contact(contact, preview=preview)
                
                if preview:
                    stats['created'] += 1
                elif result == 'created':
                    stats['created'] += 1
                elif result == 'updated':
                    stats['updated'] += 1
                else:
                    stats['skipped'] += 1
                    
            except Exception as e:
                print_error(f"Error syncing {contact['name']}: {e}")
                stats['skipped'] += 1
        
        # Final stats
        final_sqlite = self.get_sqlite_contacts() if not preview else []
        
        print()
        print("="*70)
        print(f"{Colors.BOLD}SYNC COMPLETE{Colors.END}")
        print("="*70)
        print()
        
        if preview:
            print(f"Would create: {Colors.GREEN}{stats['created']}{Colors.END} contacts")
            print(f"Would update: {Colors.CYAN}{stats['updated']}{Colors.END} contacts")
            print(f"Would skip: {Colors.YELLOW}{stats['skipped']}{Colors.END} contacts")
        else:
            print(f"Created: {Colors.GREEN}{stats['created']}{Colors.END} new contacts")
            print(f"Updated: {Colors.CYAN}{stats['updated']}{Colors.END} existing contacts")
            print(f"Skipped: {Colors.YELLOW}{stats['skipped']}{Colors.END} contacts")
            print()
            print(f"SQLite now has: {Colors.BOLD}{len(final_sqlite)}{Colors.END} total contacts")
        
        print()
        print_success("Contact sync complete!")
        print()
        print(f"{Colors.CYAN}View contacts at: http://localhost:8080/contacts{Colors.END}")
        print()
    
    def close(self):
        """Close connections"""
        self.kg.close()


def main():
    parser = argparse.ArgumentParser(description='Sync Neo4j contacts to SQLite')
    parser.add_argument('--clear', action='store_true', 
                       help='Clear SQLite before syncing')
    parser.add_argument('--preview', action='store_true',
                       help='Preview changes without making them')
    
    args = parser.parse_args()
    
    try:
        syncer = ContactSyncer()
        syncer.sync_all(clear_first=args.clear, preview=args.preview)
        syncer.close()
        
    except Exception as e:
        print_error(f"Sync failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
