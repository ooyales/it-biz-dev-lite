#!/usr/bin/env python3
"""
Contact and Relationship Network System
Manages agency contacts, relationships, and interaction history
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path

DB_PATH = "data/team_dashboard.db"

def create_network_tables():
    """Create database tables for contact network management"""
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Contacts table - people at agencies
    c.execute('''
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            title TEXT,
            organization TEXT NOT NULL,
            department TEXT,
            email TEXT,
            phone TEXT,
            linkedin_url TEXT,
            agency TEXT NOT NULL,
            office_symbol TEXT,
            location TEXT,
            clearance_level TEXT,
            role_type TEXT,
            influence_level TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Relationships between contacts
    c.execute('''
        CREATE TABLE IF NOT EXISTS contact_relationships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contact_id_1 INTEGER NOT NULL,
            contact_id_2 INTEGER NOT NULL,
            relationship_type TEXT NOT NULL,
            strength TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (contact_id_1) REFERENCES contacts(id),
            FOREIGN KEY (contact_id_2) REFERENCES contacts(id)
        )
    ''')
    
    # Contact interactions/touchpoints
    c.execute('''
        CREATE TABLE IF NOT EXISTS interactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contact_id INTEGER NOT NULL,
            interaction_type TEXT NOT NULL,
            interaction_date DATE NOT NULL,
            subject TEXT,
            summary TEXT,
            outcome TEXT,
            next_action TEXT,
            next_action_date DATE,
            our_team_member TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (contact_id) REFERENCES contacts(id)
        )
    ''')
    
    # Opportunity-Contact associations
    c.execute('''
        CREATE TABLE IF NOT EXISTS opportunity_contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            opportunity_id TEXT NOT NULL,
            contact_id INTEGER NOT NULL,
            role TEXT,
            decision_authority TEXT,
            importance TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (contact_id) REFERENCES contacts(id)
        )
    ''')
    
    # Contact tags for categorization
    c.execute('''
        CREATE TABLE IF NOT EXISTS contact_tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contact_id INTEGER NOT NULL,
            tag TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (contact_id) REFERENCES contacts(id)
        )
    ''')
    
    conn.commit()
    conn.close()
    
    print("✓ Contact network tables created")

def add_sample_contacts():
    """Add sample contacts for demonstration"""
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Sample contacts
    contacts = [
        # DoD contacts
        {
            'first_name': 'Sarah',
            'last_name': 'Johnson',
            'title': 'Contracting Officer',
            'organization': 'Defense Information Systems Agency',
            'department': 'Procurement Division',
            'email': 'sarah.johnson@mail.mil',
            'phone': '(703) 555-0123',
            'agency': 'Department of Defense',
            'office_symbol': 'DISA/GC',
            'location': 'Fort Meade, MD',
            'clearance_level': 'TS/SCI',
            'role_type': 'Decision Maker',
            'influence_level': 'High',
            'notes': 'Key decision maker for IT modernization contracts. Attended same conference last year.'
        },
        {
            'first_name': 'Michael',
            'last_name': 'Chen',
            'title': 'Program Manager',
            'organization': 'Defense Information Systems Agency',
            'department': 'Cloud Services',
            'email': 'michael.chen@mail.mil',
            'phone': '(703) 555-0124',
            'agency': 'Department of Defense',
            'office_symbol': 'DISA/CS',
            'location': 'Fort Meade, MD',
            'clearance_level': 'Secret',
            'role_type': 'Technical Lead',
            'influence_level': 'Medium',
            'notes': 'Manages cloud migration projects. Reports to Sarah Johnson.'
        },
        
        # VA contacts
        {
            'first_name': 'Jennifer',
            'last_name': 'Williams',
            'title': 'CTO',
            'organization': 'Veterans Affairs',
            'department': 'Office of Information Technology',
            'email': 'jennifer.williams@va.gov',
            'phone': '(202) 555-0125',
            'agency': 'Department of Veterans Affairs',
            'location': 'Washington, DC',
            'clearance_level': None,
            'role_type': 'Executive',
            'influence_level': 'Very High',
            'notes': 'Sets strategic direction for all VA IT initiatives. Speaks at AFCEA events.'
        },
        
        # DHS contacts
        {
            'first_name': 'Robert',
            'last_name': 'Martinez',
            'title': 'Chief Information Security Officer',
            'organization': 'Department of Homeland Security',
            'department': 'Cybersecurity Division',
            'email': 'robert.martinez@hq.dhs.gov',
            'phone': '(202) 555-0126',
            'agency': 'Department of Homeland Security',
            'location': 'Washington, DC',
            'clearance_level': 'TS',
            'role_type': 'Decision Maker',
            'influence_level': 'High',
            'notes': 'Oversees all cybersecurity procurements. Former CISO at Fortune 500 company.'
        },
        
        # GSA contacts
        {
            'first_name': 'Emily',
            'last_name': 'Davis',
            'title': 'Category Manager',
            'organization': 'General Services Administration',
            'department': 'IT Category',
            'email': 'emily.davis@gsa.gov',
            'phone': '(202) 555-0127',
            'agency': 'General Services Administration',
            'location': 'Washington, DC',
            'clearance_level': None,
            'role_type': 'Influencer',
            'influence_level': 'Medium',
            'notes': 'Manages IT category for GSA Schedule. Gateway to multiple agencies.'
        }
    ]
    
    contact_ids = []
    for contact in contacts:
        c.execute('''
            INSERT INTO contacts (
                first_name, last_name, title, organization, department,
                email, phone, agency, office_symbol, location,
                clearance_level, role_type, influence_level, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            contact['first_name'], contact['last_name'], contact['title'],
            contact['organization'], contact['department'], contact['email'],
            contact['phone'], contact['agency'], contact.get('office_symbol'),
            contact['location'], contact.get('clearance_level'),
            contact['role_type'], contact['influence_level'], contact['notes']
        ))
        contact_ids.append(c.lastrowid)
    
    # Add relationships
    relationships = [
        # Sarah manages Michael
        (contact_ids[0], contact_ids[1], 'Supervisor-Subordinate', 'Strong', 'Sarah is Michael\'s direct supervisor'),
        # Sarah and Jennifer know each other
        (contact_ids[0], contact_ids[2], 'Professional Peer', 'Medium', 'Met at AFCEA conference'),
        # Robert and Sarah collaborate
        (contact_ids[0], contact_ids[3], 'Cross-Agency Partner', 'Medium', 'Work together on joint initiatives'),
    ]
    
    for rel in relationships:
        c.execute('''
            INSERT INTO contact_relationships (
                contact_id_1, contact_id_2, relationship_type, strength, notes
            ) VALUES (?, ?, ?, ?, ?)
        ''', rel)
    
    # Add sample interactions
    interactions = [
        {
            'contact_id': contact_ids[0],  # Sarah Johnson
            'interaction_type': 'Meeting',
            'interaction_date': '2026-01-15',
            'subject': 'Cloud modernization strategy discussion',
            'summary': 'Discussed upcoming cloud migration projects. Sarah mentioned 3 RFPs coming in Q2.',
            'outcome': 'Positive',
            'next_action': 'Send white paper on zero-trust architecture',
            'next_action_date': '2026-01-22',
            'our_team_member': 'John Smith'
        },
        {
            'contact_id': contact_ids[2],  # Jennifer Williams
            'interaction_type': 'Conference',
            'interaction_date': '2026-01-10',
            'subject': 'AFCEA TechNet - VA Modernization Panel',
            'summary': 'Jennifer spoke on panel about VA IT modernization priorities. Approached afterward to introduce our company.',
            'outcome': 'Neutral',
            'next_action': 'Follow up via LinkedIn and request meeting',
            'next_action_date': '2026-01-17',
            'our_team_member': 'Jane Doe'
        },
        {
            'contact_id': contact_ids[0],  # Sarah Johnson
            'interaction_type': 'Email',
            'interaction_date': '2026-01-20',
            'subject': 'Sent zero-trust white paper',
            'summary': 'Sent requested white paper. Received positive feedback.',
            'outcome': 'Positive',
            'next_action': 'Schedule demo of our platform',
            'next_action_date': '2026-02-01',
            'our_team_member': 'John Smith'
        }
    ]
    
    for interaction in interactions:
        c.execute('''
            INSERT INTO interactions (
                contact_id, interaction_type, interaction_date, subject,
                summary, outcome, next_action, next_action_date, our_team_member
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            interaction['contact_id'], interaction['interaction_type'],
            interaction['interaction_date'], interaction['subject'],
            interaction['summary'], interaction['outcome'],
            interaction['next_action'], interaction['next_action_date'],
            interaction['our_team_member']
        ))
    
    # Add tags
    tags = [
        (contact_ids[0], 'decision-maker'),
        (contact_ids[0], 'cloud'),
        (contact_ids[0], 'cybersecurity'),
        (contact_ids[2], 'executive'),
        (contact_ids[2], 'strategic'),
        (contact_ids[3], 'cybersecurity'),
        (contact_ids[3], 'influencer'),
    ]
    
    for tag in tags:
        c.execute('INSERT INTO contact_tags (contact_id, tag) VALUES (?, ?)', tag)
    
    conn.commit()
    conn.close()
    
    print(f"✓ Added {len(contacts)} sample contacts")
    print(f"✓ Added {len(relationships)} relationships")
    print(f"✓ Added {len(interactions)} interactions")

def export_network_data():
    """Export network data for visualization"""
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Get all contacts
    c.execute('''
        SELECT id, first_name, last_name, title, organization, agency,
               role_type, influence_level
        FROM contacts
    ''')
    
    contacts = []
    for row in c.fetchall():
        contacts.append({
            'id': row[0],
            'name': f"{row[1]} {row[2]}",
            'title': row[3],
            'organization': row[4],
            'agency': row[5],
            'role_type': row[6],
            'influence_level': row[7]
        })
    
    # Get all relationships
    c.execute('''
        SELECT contact_id_1, contact_id_2, relationship_type, strength
        FROM contact_relationships
    ''')
    
    relationships = []
    for row in c.fetchall():
        relationships.append({
            'source': row[0],
            'target': row[1],
            'type': row[2],
            'strength': row[3]
        })
    
    conn.close()
    
    # Export to JSON
    network_data = {
        'nodes': contacts,
        'links': relationships
    }
    
    output_dir = Path("data/network")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_path = output_dir / "contact_network.json"
    with open(output_path, 'w') as f:
        json.dump(network_data, f, indent=2)
    
    print(f"✓ Exported network data to {output_path}")
    return network_data

def main():
    """Initialize contact network system"""
    
    print("\n" + "="*60)
    print("Contact Network System Setup")
    print("="*60 + "\n")
    
    create_network_tables()
    add_sample_contacts()
    export_network_data()
    
    print("\n" + "="*60)
    print("Setup Complete!")
    print("="*60)
    print("\nContact network system is ready.")
    print("\nNext steps:")
    print("1. Access contact management: http://localhost:8080/contacts")
    print("2. View network diagram: http://localhost:8080/network")
    print("3. Add your own contacts via the web interface")
    print("\n")

if __name__ == "__main__":
    main()
