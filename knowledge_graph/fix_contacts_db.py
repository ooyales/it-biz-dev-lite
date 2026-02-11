#!/usr/bin/env python3
"""
Quick fix to initialize database and sync contacts from Neo4j
"""
import os
import sys
import sqlite3

# Remove old database
db_path = 'data/contacts.db'
if os.path.exists(db_path):
    print(f"🗑️  Removing old database: {db_path}")
    os.remove(db_path)

# Create data directory
os.makedirs('data', exist_ok=True)

# Create new database with schema
print("📝 Creating new database with schema...")
db = sqlite3.connect(db_path)

# Create contacts table
db.execute('''
    CREATE TABLE contacts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT,
        phone TEXT,
        title TEXT,
        organization TEXT,
        role TEXT,
        notes TEXT,
        linkedin_url TEXT,
        relationship_strength TEXT DEFAULT 'New',
        last_contact DATE,
        source TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')

# Create interactions table
db.execute('''
    CREATE TABLE interactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        contact_id INTEGER,
        interaction_date DATE NOT NULL,
        interaction_type TEXT,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (contact_id) REFERENCES contacts (id)
    )
''')

# Create relationships table
db.execute('''
    CREATE TABLE contact_relationships (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        contact_id_1 INTEGER,
        contact_id_2 INTEGER,
        relationship_type TEXT,
        strength INTEGER DEFAULT 5,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (contact_id_1) REFERENCES contacts (id),
        FOREIGN KEY (contact_id_2) REFERENCES contacts (id)
    )
''')

db.commit()
print("✓ Database created successfully")

# Now try to sync from Neo4j
print("\n🔄 Attempting to sync contacts from Neo4j...")

try:
    from graph.neo4j_client import KnowledgeGraphClient
    from dotenv import load_dotenv
    
    load_dotenv()
    
    kg = KnowledgeGraphClient(
        uri=os.getenv('NEO4J_URI', 'bolt://localhost:7687'),
        user=os.getenv('NEO4J_USER', 'neo4j'),
        password=os.getenv('NEO4J_PASSWORD')
    )
    
    # Get contacts from Neo4j
    with kg.driver.session(database="neo4j") as session:
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
               p.source as source
        ORDER BY p.name
        """
        result = session.run(query)
        neo4j_contacts = [dict(record) for record in result]
    
    kg.close()
    
    print(f"✓ Found {len(neo4j_contacts)} contacts in Neo4j")
    
    # Insert into SQLite
    if neo4j_contacts:
        for contact in neo4j_contacts:
            name = contact['name']
            email = contact['email']
            phone = contact['phone']
            title = contact['title'] or contact['role_type']
            organization = contact['org_from_relationship'] or contact['organization'] or 'Unknown'
            role = contact['role_type'] or 'Contact'
            source = contact['source'] or 'Neo4j'
            
            db.execute('''
                INSERT INTO contacts (name, email, phone, title, organization, role, source, relationship_strength)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (name, email, phone, title, organization, role, source, 'New'))
        
        db.commit()
        print(f"✓ Synced {len(neo4j_contacts)} contacts to database")
    else:
        print("⚠️  No contacts found in Neo4j")
        
except Exception as e:
    print(f"❌ Error syncing from Neo4j: {e}")
    print("   You can still add contacts manually through the dashboard")

# Show final count
count = db.execute('SELECT COUNT(*) FROM contacts').fetchone()[0]
print(f"\n✅ Database ready with {count} contacts")

db.close()

print("\n🚀 Now restart the dashboard:")
print("   python team_dashboard_integrated.py")
