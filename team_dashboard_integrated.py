#!/usr/bin/env python3
"""
Integrated BD Intelligence Dashboard
Combines Team Dashboard + Opportunity Scout + Competitive Intelligence

Features:
- Contact Management
- Opportunity Intelligence
- Competitive Analysis
- Knowledge Graph Integration
- Real-time Scoring
"""

from flask import Flask, render_template, jsonify, request, send_file
from flask_cors import CORS
import sqlite3
import os
import sys
import json
from datetime import datetime
from pathlib import Path

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()  # This loads .env from current directory

# Verify critical environment variables are loaded
if os.getenv('ANTHROPIC_API_KEY'):
    print("✓ ANTHROPIC_API_KEY loaded")
if os.getenv('NEO4J_URI'):
    print(f"✓ NEO4J_URI loaded: {os.getenv('NEO4J_URI')}")
if os.getenv('NEO4J_PASSWORD'):
    print("✓ NEO4J_PASSWORD loaded")

# Add knowledge_graph to path
sys.path.append('knowledge_graph')

# Import agents
try:
    from opportunity_scout import OpportunityScout
    from competitive_intel import CompetitiveIntelAgent
    from graph.neo4j_client import KnowledgeGraphClient
    AGENTS_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  Warning: Some agents not available: {e}")
    AGENTS_AVAILABLE = False

# Check if Neo4j is available
NEO4J_AVAILABLE = False
try:
    from neo4j import GraphDatabase
    if os.getenv('NEO4J_PASSWORD'):
        NEO4J_AVAILABLE = True
        print("✓ Neo4j driver available")
except ImportError:
    print("⚠️  Warning: Neo4j driver not installed")

app = Flask(__name__)
CORS(app)

# Register competitive intelligence API routes
try:
    from competitive_intel_api import comp_intel_bp
    app.register_blueprint(comp_intel_bp)
    print("✓ Competitive Intelligence API routes registered")
except ImportError as e:
    print(f"⚠️  Competitive Intel API not available: {e}")

# Database path
DATABASE = 'data/contacts.db'

def init_database():
    """Initialize database if it doesn't exist"""
    os.makedirs('data', exist_ok=True)
    
    if not os.path.exists(DATABASE):
        print("📝 Creating new database...")
        db = sqlite3.connect(DATABASE)
        
        # Create contacts table
        db.execute('''
            CREATE TABLE IF NOT EXISTS contacts (
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
            CREATE TABLE IF NOT EXISTS interactions (
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
            CREATE TABLE IF NOT EXISTS contact_relationships (
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
        db.close()
        print("✓ Database created successfully")
        return True
    
    return False

def get_db():
    """Get database connection"""
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db


# ============================================================================
# MAIN PAGES
# ============================================================================

@app.route('/')
def index():
    """Dashboard home page - integrated view"""
    return render_template('dashboard-home.html')


@app.route('/contacts')
def contacts():
    """Contacts management page"""
    return render_template('contacts-enhanced.html')


@app.route('/contact/<int:contact_id>')
def contact_detail(contact_id):
    """Contact detail page"""
    return render_template('contact-detail.html', contact_id=contact_id)


@app.route('/staff')
def staff_management():
    """Staff management page"""
    return render_template('staff-management.html')


@app.route('/opportunities/timeline')
def opportunities_timeline():
    """Timeline view of opportunities"""
    return render_template('opportunities-timeline.html')


@app.route('/opportunities/network')
def opportunities_network():
    """Network view of opportunities"""
    return render_template('opportunities-network.html')


@app.route('/opportunities/kanban')
def opportunities_kanban():
    """Kanban board view of opportunities"""
    return render_template('opportunities-kanban.html')


@app.route('/admin')
def admin_panel():
    """Admin panel for system settings"""
    return render_template('admin-panel.html')


@app.route('/competitive-intel')
def competitive_intel():
    """Competitive intelligence page"""
    return render_template('competitive-intel.html')


@app.route('/competitive-intel/contractor/<contractor_name>')
def contractor_detail(contractor_name):
    """Contractor detail page"""
    return render_template('contractor-detail.html', contractor_name=contractor_name)


@app.route('/agents/dashboard')
def agents_dashboard():
    """AI agents dashboard"""
    return render_template('agents-dashboard.html')


@app.route('/bd-intelligence')
def bd_intelligence():
    """BD Intelligence Hub page - integrated with dashboard"""
    return render_template('bd-intelligence-integrated.html')


# ============================================================================
# CONTACT API (Existing)
# ============================================================================

@app.route('/api/contacts', methods=['GET'])
def get_contacts():
    """Get all contacts"""
    db = get_db()
    
    # Build query with filters
    query = "SELECT * FROM contacts WHERE 1=1"
    params = []
    
    # Search filter
    search = request.args.get('search', '').strip()
    if search:
        query += " AND (name LIKE ? OR email LIKE ? OR organization LIKE ?)"
        search_pattern = f"%{search}%"
        params.extend([search_pattern, search_pattern, search_pattern])
    
    # Organization filter
    org = request.args.get('organization')
    if org:
        query += " AND organization = ?"
        params.append(org)
    
    # Role filter
    role = request.args.get('role')
    if role:
        query += " AND role = ?"
        params.append(role)
    
    # Sorting
    sort_by = request.args.get('sort', 'name')
    sort_order = request.args.get('order', 'asc')
    valid_columns = ['name', 'organization', 'role', 'last_contact', 'relationship_strength']
    
    if sort_by in valid_columns:
        query += f" ORDER BY {sort_by} {sort_order.upper()}"
    
    contacts = db.execute(query, params).fetchall()
    db.close()
    
    # Convert to list of dicts
    contacts_list = [dict(contact) for contact in contacts]
    
    # Check which contacts have research profiles in Neo4j (optional enhancement)
    researched_names = set()
    try:
        if NEO4J_AVAILABLE:
            from neo4j import GraphDatabase
            driver = GraphDatabase.driver(
                os.getenv('NEO4J_URI', 'bolt://localhost:7687'),
                auth=('neo4j', os.getenv('NEO4J_PASSWORD'))
            )
            
            with driver.session(database="contactsgraphdb") as session:
                result = session.run("""
                    MATCH (p:Person)
                    WHERE p.research_profile IS NOT NULL
                    RETURN p.name as name
                """)
                researched_names = set(record['name'] for record in result)
            
            driver.close()
            
            # Debug: print what we found
            if researched_names:
                print(f"DEBUG: Found {len(researched_names)} contacts with research: {list(researched_names)[:5]}")
            else:
                print("DEBUG: No contacts with research found in Neo4j")
    except Exception as e:
        # Neo4j lookup failed, continue without research indicators
        print(f"Neo4j research lookup failed: {e}")
        researched_names = set()
    
    # Mark contacts that have research
    for contact in contacts_list:
        contact['has_research'] = contact.get('name', '') in researched_names
    
    return jsonify({
        'contacts': contacts_list,
        'total': len(contacts_list)
    })


@app.route('/api/contacts/<int:contact_id>', methods=['GET'])
def get_contact(contact_id):
    """Get single contact"""
    db = get_db()
    contact = db.execute('SELECT * FROM contacts WHERE id = ?', (contact_id,)).fetchone()
    
    if not contact:
        return jsonify({'error': 'Contact not found'}), 404
    
    # Get interactions
    interactions = db.execute('''
        SELECT * FROM interactions 
        WHERE contact_id = ? 
        ORDER BY interaction_date DESC
    ''', (contact_id,)).fetchall()
    
    # Get relationships
    relationships = db.execute('''
        SELECT r.*, c.name as related_contact_name 
        FROM contact_relationships r
        JOIN contacts c ON (c.id = r.contact_id_2)
        WHERE r.contact_id_1 = ?
    ''', (contact_id,)).fetchall()
    
    db.close()
    
    return jsonify({
        'contact': dict(contact),
        'interactions': [dict(i) for i in interactions],
        'relationships': [dict(r) for r in relationships]
    })


@app.route('/api/contacts/<int:contact_id>/research', methods=['GET'])
def get_contact_research(contact_id):
    """Get research profile for a contact from Neo4j"""
    try:
        # Get contact name from SQLite
        db = get_db()
        contact = db.execute('SELECT name FROM contacts WHERE id = ?', (contact_id,)).fetchone()
        db.close()
        
        if not contact:
            return jsonify({'error': 'Contact not found'}), 404
        
        name = contact['name']
        
        # Get research from Neo4j
        if not NEO4J_AVAILABLE:
            return jsonify({'contact_id': contact_id, 'name': name, 'research_profile': None})
        
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(
            os.getenv('NEO4J_URI', 'bolt://localhost:7687'),
            auth=('neo4j', os.getenv('NEO4J_PASSWORD'))
        )
        
        with driver.session(database="contactsgraphdb") as session:
            result = session.run(
                "MATCH (p:Person) WHERE p.name = $name RETURN p.research_profile as profile",
                name=name
            )
            row = result.single()
            
            if row and row['profile']:
                profile = json.loads(row['profile']) if isinstance(row['profile'], str) else row['profile']
                driver.close()
                return jsonify({
                    'contact_id': contact_id,
                    'name': name,
                    'research_profile': profile
                })
        
        driver.close()
        return jsonify({'contact_id': contact_id, 'name': name, 'research_profile': None})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/contacts', methods=['POST'])
def create_contact():
    """Create new contact"""
    data = request.get_json()
    
    db = get_db()
    cursor = db.execute('''
        INSERT INTO contacts (name, email, phone, organization, role, notes, 
                            linkedin_url, relationship_strength, last_contact)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data.get('name'),
        data.get('email'),
        data.get('phone'),
        data.get('organization'),
        data.get('role'),
        data.get('notes'),
        data.get('linkedin_url'),
        data.get('relationship_strength', 'New'),
        data.get('last_contact')
    ))
    
    contact_id = cursor.lastrowid
    db.commit()
    db.close()
    
    return jsonify({'id': contact_id, 'status': 'success'})


@app.route('/api/contacts/<int:contact_id>', methods=['PUT'])
def update_contact(contact_id):
    """Update contact"""
    data = request.get_json()
    
    db = get_db()
    db.execute('''
        UPDATE contacts 
        SET name=?, email=?, phone=?, organization=?, role=?, notes=?,
            linkedin_url=?, relationship_strength=?, last_contact=?
        WHERE id=?
    ''', (
        data.get('name'),
        data.get('email'),
        data.get('phone'),
        data.get('organization'),
        data.get('role'),
        data.get('notes'),
        data.get('linkedin_url'),
        data.get('relationship_strength'),
        data.get('last_contact'),
        contact_id
    ))
    
    db.commit()
    db.close()
    
    return jsonify({'status': 'success'})


@app.route('/api/contacts/<int:contact_id>', methods=['DELETE'])
def delete_contact(contact_id):
    """Delete contact"""
    db = get_db()
    db.execute('DELETE FROM contacts WHERE id = ?', (contact_id,))
    db.commit()
    db.close()
    
    return jsonify({'status': 'success'})


# ============================================================================
# CONTACT SYNC API
# ============================================================================

@app.route('/api/contacts/sync', methods=['POST'])
def sync_contacts_from_neo4j():
    """Sync contacts from Neo4j to SQLite"""
    if not AGENTS_AVAILABLE:
        return jsonify({'error': 'Neo4j connection not available'}), 503
    
    try:
        # Import the sync logic
        sys.path.append('.')
        
        # Connect to Neo4j
        kg = KnowledgeGraphClient(
            uri=os.getenv('NEO4J_URI', 'bolt://localhost:7687'),
            user=os.getenv('NEO4J_USER', 'neo4j'),
            password=os.getenv('NEO4J_PASSWORD')
        )
        
        # Get Neo4j contacts
        with kg.driver.session(database="contactsgraphdb") as session:
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
                   p.source as source
            ORDER BY p.name
            """
            result = session.run(query)
            neo4j_contacts = [dict(record) for record in result]
        
        kg.close()
        
        if not neo4j_contacts:
            return jsonify({
                'status': 'success',
                'message': 'No contacts found in Neo4j',
                'synced': 0,
                'created': 0,
                'updated': 0
            })
        
        # Sync to SQLite
        stats = {'created': 0, 'updated': 0, 'skipped': 0}
        db = get_db()
        
        for contact in neo4j_contacts:
            name = contact['name']
            email = contact['email']
            phone = contact['phone']
            organization = (contact['org_from_relationship'] or 
                          contact['organization'] or 
                          'Unknown')
            role = contact['title'] or contact['role_type'] or 'Contact'
            
            # Build notes
            notes_parts = []
            if contact['source']:
                notes_parts.append(f"Source: {contact['source']}")
            if contact['role_type']:
                notes_parts.append(f"Role: {contact['role_type']}")
            if contact['influence_level']:
                notes_parts.append(f"Influence: {contact['influence_level']}")
            notes = "\n".join(notes_parts) if notes_parts else "Imported from Neo4j"
            
            # Map influence to relationship strength
            strength_map = {
                'Very High': 'Strong',
                'High': 'Strong',
                'Medium': 'Warm',
                'Low': 'New',
                None: 'New'
            }
            relationship_strength = strength_map.get(contact['influence_level'], 'New')
            
            # Check if exists
            existing = None
            if email:
                existing = db.execute('SELECT id FROM contacts WHERE email = ?', (email,)).fetchone()
            if not existing and name:
                existing = db.execute('SELECT id FROM contacts WHERE name = ?', (name,)).fetchone()
            
            if existing:
                # Update
                db.execute('''
                    UPDATE contacts 
                    SET phone = COALESCE(?, phone),
                        organization = ?,
                        role = ?,
                        notes = ?,
                        relationship_strength = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (phone, organization, role, notes, relationship_strength, existing['id']))
                stats['updated'] += 1
            else:
                # Insert
                db.execute('''
                    INSERT INTO contacts (name, email, phone, organization, role, notes, relationship_strength)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (name, email, phone, organization, role, notes, relationship_strength))
                stats['created'] += 1
        
        db.commit()
        db.close()
        
        return jsonify({
            'status': 'success',
            'message': f"Synced {len(neo4j_contacts)} contacts from Neo4j",
            'synced': len(neo4j_contacts),
            'created': stats['created'],
            'updated': stats['updated'],
            'skipped': stats['skipped']
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500


# ============================================================================
# AGENT INTEGRATION ROUTES
# ============================================================================

@app.route('/api/agents/capability/analyze', methods=['POST'])
def analyze_capability():
    """Agent 3: Capability Matching"""
    if not AGENTS_AVAILABLE:
        return jsonify({'error': 'Agents not available'}), 503
    
    try:
        data = request.json
        notice_id = data.get('notice_id', '')
        requirements = data.get('requirements', '')
        
        # Build opportunity data
        opportunity_data = {
            'notice_id': notice_id,
            'requirements': requirements
        }
        
        # Use AgentExecutor wrapper
        from agent_executor import AgentExecutor
        executor = AgentExecutor()
        
        results = executor.run_capability_match(opportunity_data)
        
        return jsonify(results)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e), 'status': 'error'}), 500


@app.route('/api/agents/rfi/generate', methods=['POST'])
def generate_rfi():
    """Agent 4: RFI Response Generator"""
    if not AGENTS_AVAILABLE:
        return jsonify({'error': 'Agents not available'}), 503
    
    try:
        data = request.json
        notice_id = data.get('notice_id', '')
        
        if not notice_id:
            return jsonify({'error': 'notice_id required'}), 400
        
        # Load opportunity data
        scout_files = list(Path('knowledge_graph').glob('scout_data_*.json'))
        if not scout_files:
            scout_files = list(Path('.').glob('scout_data_*.json'))
        
        if scout_files:
            with open(sorted(scout_files, reverse=True)[0]) as f:
                scout_data = json.load(f)
            
            # Find opportunity
            opp = None
            for opportunity in scout_data.get('opportunities', []):
                opp_id = opportunity.get('notice_id') or opportunity.get('noticeId')
                if opp_id == notice_id:
                    opp = opportunity
                    break
        else:
            opp = None
        
        if not opp:
            opp = {'title': 'Opportunity', 'agency': '', 'description': ''}
        
        # Use AgentExecutor wrapper
        from agent_executor import AgentExecutor
        executor = AgentExecutor()
        
        results = executor.run_rfi_generator(notice_id, opp)
        
        return jsonify(results)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e), 'status': 'error'}), 500
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/agents/proposal/generate', methods=['POST'])
def generate_proposal():
    """Agent 5: Proposal Writing Assistant"""
    if not AGENTS_AVAILABLE:
        return jsonify({'error': 'Agents not available'}), 503
    
    try:
        data = request.json
        notice_id = data.get('notice_id', '')
        
        if not notice_id:
            return jsonify({'error': 'notice_id required'}), 400
        
        # Load opportunity data
        scout_files = list(Path('knowledge_graph').glob('scout_data_*.json'))
        if not scout_files:
            scout_files = list(Path('.').glob('scout_data_*.json'))
        
        if scout_files:
            with open(sorted(scout_files, reverse=True)[0]) as f:
                scout_data = json.load(f)
            
            opp = None
            for opportunity in scout_data.get('opportunities', []):
                opp_id = opportunity.get('notice_id') or opportunity.get('noticeId')
                if opp_id == notice_id:
                    opp = opportunity
                    break
        else:
            opp = None
        
        if not opp:
            opp = {'title': 'Opportunity', 'agency': '', 'description': ''}
        
        # Use AgentExecutor wrapper
        from agent_executor import AgentExecutor
        executor = AgentExecutor()
        
        results = executor.run_proposal_writer(notice_id, opp)
        
        return jsonify(results)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e), 'status': 'error'}), 500


@app.route('/api/agents/pricing/generate', methods=['POST'])
def generate_pricing():
    """Agent 6: Pricing & Budget Generator"""
    if not AGENTS_AVAILABLE:
        return jsonify({'error': 'Agents not available'}), 503
    
    try:
        data = request.json
        notice_id = data.get('notice_id', '')
        
        if not notice_id:
            return jsonify({'error': 'notice_id required'}), 400
        
        # Load opportunity data
        scout_files = list(Path('knowledge_graph').glob('scout_data_*.json'))
        if not scout_files:
            scout_files = list(Path('.').glob('scout_data_*.json'))
        
        if scout_files:
            with open(sorted(scout_files, reverse=True)[0]) as f:
                scout_data = json.load(f)
            
            opp = None
            for opportunity in scout_data.get('opportunities', []):
                opp_id = opportunity.get('notice_id') or opportunity.get('noticeId')
                if opp_id == notice_id:
                    opp = opportunity
                    break
        else:
            opp = None
        
        if not opp:
            opp = {'title': 'Opportunity', 'description': ''}
        
        # Use AgentExecutor wrapper
        from agent_executor import AgentExecutor
        executor = AgentExecutor()
        
        results = executor.run_pricing_generator(notice_id, opp)
        
        return jsonify(results)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e), 'status': 'error'}), 500


# ============================================================================
# COMPETITIVE INTELLIGENCE API ENDPOINTS
# ============================================================================

@app.route('/api/competitive/stats', methods=['GET'])
def get_competitive_stats():
    """Get overall competitive intelligence statistics from Neo4j"""
    try:
        if not NEO4J_AVAILABLE:
            return jsonify({'error': 'Neo4j not available'}), 503
        
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(
            os.getenv('NEO4J_URI', 'bolt://localhost:7687'),
            auth=('neo4j', os.getenv('NEO4J_PASSWORD'))
        )
        
        with driver.session(database="contactsgraphdb") as session:
            # Get contract stats
            result = session.run("""
                MATCH (c:Contract)
                OPTIONAL MATCH (c)-[:AWARDED_TO]->(org:Organization)
                WITH c, org
                RETURN 
                    count(DISTINCT c) as contract_count,
                    count(DISTINCT org) as contractor_count,
                    count(DISTINCT c.agency) as agency_count,
                    sum(toFloat(c.value)) as total_value
            """)
            row = result.single()
            
            stats = {
                'contract_count': row['contract_count'] if row else 0,
                'contractor_count': row['contractor_count'] if row else 0,
                'agency_count': row['agency_count'] if row else 0,
                'total_value': row['total_value'] if row and row['total_value'] else 0
            }
        
        driver.close()
        return jsonify(stats)
        
    except Exception as e:
        print(f"Error getting competitive stats: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/competitive/incumbents', methods=['GET'])
def get_competitive_incumbents():
    """Get top contractors ranked by contract value"""
    try:
        if not NEO4J_AVAILABLE:
            return jsonify({'error': 'Neo4j not available'}), 503
        
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(
            os.getenv('NEO4J_URI', 'bolt://localhost:7687'),
            auth=('neo4j', os.getenv('NEO4J_PASSWORD'))
        )
        
        with driver.session(database="contactsgraphdb") as session:
            result = session.run("""
                MATCH (c:Contract)-[:AWARDED_TO]->(org:Organization)
                WITH org.name as contractor, 
                     count(c) as contract_count,
                     sum(toFloat(c.value)) as total_value,
                     collect(DISTINCT c.agency)[0..3] as agencies,
                     collect(DISTINCT c.naics)[0..3] as naics_codes
                WHERE contractor IS NOT NULL
                RETURN contractor, contract_count, total_value, 
                       total_value / contract_count as avg_value,
                       agencies[0] as top_agency,
                       naics_codes
                ORDER BY total_value DESC
                LIMIT 50
            """)
            
            incumbents = []
            for record in result:
                incumbents.append({
                    'contractor': record['contractor'],
                    'contract_count': record['contract_count'],
                    'total_value': record['total_value'] or 0,
                    'avg_value': record['avg_value'] or 0,
                    'top_agency': record['top_agency'],
                    'naics_codes': record['naics_codes'] or []
                })
        
        driver.close()
        return jsonify({'incumbents': incumbents})
        
    except Exception as e:
        print(f"Error getting incumbents: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/competitive/filter-options', methods=['GET'])
def get_competitive_filter_options():
    """Get available filter options for competitive intel"""
    try:
        if not NEO4J_AVAILABLE:
            return jsonify({'agencies': [], 'naics': []})
        
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(
            os.getenv('NEO4J_URI', 'bolt://localhost:7687'),
            auth=('neo4j', os.getenv('NEO4J_PASSWORD'))
        )
        
        with driver.session(database="contactsgraphdb") as session:
            # Get unique agencies
            result = session.run("""
                MATCH (c:Contract)
                WHERE c.agency IS NOT NULL AND c.agency <> ''
                RETURN DISTINCT c.agency as agency
                ORDER BY agency
                LIMIT 100
            """)
            agencies = [record['agency'] for record in result]
            
            # Get unique NAICS
            result = session.run("""
                MATCH (c:Contract)
                WHERE c.naics IS NOT NULL AND c.naics <> ''
                RETURN DISTINCT c.naics as naics
                ORDER BY naics
            """)
            naics = [record['naics'] for record in result]
        
        driver.close()
        return jsonify({'agencies': agencies, 'naics': naics})
        
    except Exception as e:
        print(f"Error getting filter options: {e}")
        return jsonify({'agencies': [], 'naics': []})


@app.route('/api/competitive/teaming-partners', methods=['GET'])
def get_teaming_partners():
    """Get potential teaming partners based on complementary capabilities"""
    try:
        if not NEO4J_AVAILABLE:
            return jsonify({'error': 'Neo4j not available'}), 503
        
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(
            os.getenv('NEO4J_URI', 'bolt://localhost:7687'),
            auth=('neo4j', os.getenv('NEO4J_PASSWORD'))
        )
        
        with driver.session(database="contactsgraphdb") as session:
            # Partners by shared NAICS - contractors working in same space
            result = session.run("""
                MATCH (c:Contract)-[:AWARDED_TO]->(org:Organization)
                WHERE c.naics IS NOT NULL AND org.name IS NOT NULL
                WITH c.naics as naics, org.name as contractor, 
                     count(c) as contract_count,
                     sum(toFloat(c.value)) as total_value
                ORDER BY naics, total_value DESC
                WITH naics, collect({
                    contractor: contractor, 
                    contract_count: contract_count, 
                    total_value: total_value
                })[0..10] as top_contractors
                RETURN naics, top_contractors
                ORDER BY size(top_contractors) DESC
                LIMIT 10
            """)
            
            by_naics = []
            for record in result:
                by_naics.append({
                    'naics': record['naics'],
                    'contractors': record['top_contractors']
                })
            
            # Partners by shared agencies - contractors with same customers
            result = session.run("""
                MATCH (c:Contract)-[:AWARDED_TO]->(org:Organization)
                WHERE c.agency IS NOT NULL AND c.agency <> '' AND org.name IS NOT NULL
                WITH c.agency as agency, org.name as contractor,
                     count(c) as contract_count,
                     sum(toFloat(c.value)) as total_value
                ORDER BY agency, total_value DESC
                WITH agency, collect({
                    contractor: contractor,
                    contract_count: contract_count,
                    total_value: total_value
                })[0..10] as top_contractors
                WHERE size(top_contractors) >= 2
                RETURN agency, top_contractors
                ORDER BY size(top_contractors) DESC
                LIMIT 10
            """)
            
            by_agency = []
            for record in result:
                by_agency.append({
                    'agency': record['agency'],
                    'contractors': record['top_contractors']
                })
            
            # Recommended partners - mid-size contractors with diverse experience
            result = session.run("""
                MATCH (c:Contract)-[:AWARDED_TO]->(org:Organization)
                WITH org.name as contractor,
                     count(c) as contract_count,
                     sum(toFloat(c.value)) as total_value,
                     count(DISTINCT c.agency) as agency_diversity,
                     count(DISTINCT c.naics) as naics_diversity,
                     collect(DISTINCT c.agency)[0..3] as top_agencies,
                     collect(DISTINCT c.naics)[0..3] as naics_codes
                WHERE contractor IS NOT NULL 
                  AND contract_count >= 2 
                  AND contract_count <= 50
                RETURN contractor, contract_count, total_value, 
                       agency_diversity, naics_diversity,
                       top_agencies, naics_codes,
                       (agency_diversity * 2 + naics_diversity + contract_count) as partner_score
                ORDER BY partner_score DESC
                LIMIT 20
            """)
            
            recommended = []
            for record in result:
                recommended.append({
                    'contractor': record['contractor'],
                    'contract_count': record['contract_count'],
                    'total_value': record['total_value'] or 0,
                    'agency_diversity': record['agency_diversity'],
                    'naics_diversity': record['naics_diversity'],
                    'top_agencies': record['top_agencies'] or [],
                    'naics_codes': record['naics_codes'] or [],
                    'partner_score': record['partner_score']
                })
        
        driver.close()
        return jsonify({
            'by_naics': by_naics,
            'by_agency': by_agency,
            'recommended': recommended
        })
        
    except Exception as e:
        print(f"Error getting teaming partners: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/competitive/organization/<path:org_name>/research', methods=['GET'])
def get_organization_research(org_name):
    """Get research profile for an organization from Neo4j"""
    try:
        if not NEO4J_AVAILABLE:
            return jsonify({'error': 'Neo4j not available'}), 503
        
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(
            os.getenv('NEO4J_URI', 'bolt://localhost:7687'),
            auth=('neo4j', os.getenv('NEO4J_PASSWORD'))
        )
        
        with driver.session(database="contactsgraphdb") as session:
            # Get organization info and research profile
            result = session.run("""
                MATCH (o:Organization)
                WHERE o.name = $name
                OPTIONAL MATCH (c:Contract)-[:AWARDED_TO]->(o)
                WITH o, count(c) as contract_count, sum(toFloat(c.value)) as total_value,
                     collect(DISTINCT c.naics)[0..5] as naics_codes,
                     collect(DISTINCT c.agency)[0..5] as top_agencies
                RETURN o.name as name, o.research_profile as profile,
                       contract_count, total_value, naics_codes, top_agencies
            """, name=org_name)
            
            row = result.single()
            
            if not row:
                driver.close()
                return jsonify({
                    'name': org_name,
                    'research_profile': None,
                    'contract_count': 0,
                    'total_value': 0
                })
            
            profile = None
            if row['profile']:
                try:
                    profile = json.loads(row['profile']) if isinstance(row['profile'], str) else row['profile']
                except:
                    profile = None
            
            driver.close()
            return jsonify({
                'name': row['name'],
                'research_profile': profile,
                'contract_count': row['contract_count'],
                'total_value': row['total_value'] or 0,
                'naics_codes': row['naics_codes'] or [],
                'top_agencies': row['top_agencies'] or []
            })
        
    except Exception as e:
        print(f"Error getting organization research: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/competitive/organization/research', methods=['POST'])
def research_organization():
    """Run AI research on an organization"""
    try:
        data = request.get_json()
        org_name = data.get('name', '')
        
        if not org_name:
            return jsonify({'error': 'Organization name required'}), 400
        
        # Import the organization research agent
        sys.path.insert(0, 'knowledge_graph')
        from organization_research_agent import OrganizationResearchAgent
        
        # Get org details from Neo4j first
        if NEO4J_AVAILABLE:
            from neo4j import GraphDatabase
            driver = GraphDatabase.driver(
                os.getenv('NEO4J_URI', 'bolt://localhost:7687'),
                auth=('neo4j', os.getenv('NEO4J_PASSWORD'))
            )
            
            with driver.session(database="contactsgraphdb") as session:
                result = session.run("""
                    MATCH (o:Organization)
                    WHERE o.name = $name
                    OPTIONAL MATCH (c:Contract)-[:AWARDED_TO]->(o)
                    WITH o, count(c) as contract_count, sum(toFloat(c.value)) as total_value,
                         collect(DISTINCT c.naics)[0..5] as naics_codes,
                         collect(DISTINCT c.agency)[0..5] as top_agencies
                    RETURN contract_count, total_value, naics_codes, top_agencies
                """, name=org_name)
                
                row = result.single()
                org_info = {
                    'name': org_name,
                    'contract_count': row['contract_count'] if row else 0,
                    'total_value': row['total_value'] if row else 0,
                    'naics_codes': row['naics_codes'] if row else [],
                    'top_agencies': row['top_agencies'] if row else []
                }
            driver.close()
        else:
            org_info = {'name': org_name}
        
        # Research the organization
        agent = OrganizationResearchAgent()
        profile = agent.research_organization(org_info, force_refresh=data.get('force_refresh', False))
        agent.close()
        
        return jsonify({
            'status': 'success',
            'name': org_name,
            'research_profile': profile
        })
        
    except Exception as e:
        print(f"Error researching organization: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e), 'status': 'error'}), 500


@app.route('/api/competitive/market-trends', methods=['GET'])
def get_market_trends():
    """Get market trend data for charts"""
    try:
        if not NEO4J_AVAILABLE:
            return jsonify({'error': 'Neo4j not available'}), 503
        
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(
            os.getenv('NEO4J_URI', 'bolt://localhost:7687'),
            auth=('neo4j', os.getenv('NEO4J_PASSWORD'))
        )
        
        with driver.session(database="contactsgraphdb") as session:
            # Contract awards over time (by month)
            result = session.run("""
                MATCH (c:Contract)
                WHERE c.date_signed IS NOT NULL
                WITH c, 
                     substring(c.date_signed, 0, 7) as month
                RETURN month, 
                       count(c) as contract_count,
                       sum(toFloat(c.value)) as total_value
                ORDER BY month
            """)
            
            timeline = []
            for record in result:
                if record['month']:
                    timeline.append({
                        'month': record['month'],
                        'contract_count': record['contract_count'],
                        'total_value': record['total_value'] or 0
                    })
            
            # Market share by top contractors
            result = session.run("""
                MATCH (c:Contract)-[:AWARDED_TO]->(org:Organization)
                WITH org.name as contractor, sum(toFloat(c.value)) as total_value
                WHERE contractor IS NOT NULL AND total_value > 0
                RETURN contractor, total_value
                ORDER BY total_value DESC
                LIMIT 10
            """)
            
            market_share = []
            for record in result:
                market_share.append({
                    'contractor': record['contractor'],
                    'total_value': record['total_value'] or 0
                })
            
            # Top agencies by spend
            result = session.run("""
                MATCH (c:Contract)
                WHERE c.agency IS NOT NULL AND c.agency <> ''
                WITH c.agency as agency, 
                     count(c) as contract_count,
                     sum(toFloat(c.value)) as total_value
                RETURN agency, contract_count, total_value
                ORDER BY total_value DESC
                LIMIT 10
            """)
            
            top_agencies = []
            for record in result:
                top_agencies.append({
                    'agency': record['agency'],
                    'contract_count': record['contract_count'],
                    'total_value': record['total_value'] or 0
                })
            
            # NAICS distribution
            result = session.run("""
                MATCH (c:Contract)
                WHERE c.naics IS NOT NULL AND c.naics <> ''
                WITH c.naics as naics,
                     count(c) as contract_count,
                     sum(toFloat(c.value)) as total_value
                RETURN naics, contract_count, total_value
                ORDER BY total_value DESC
                LIMIT 10
            """)
            
            naics_distribution = []
            for record in result:
                naics_distribution.append({
                    'naics': record['naics'],
                    'contract_count': record['contract_count'],
                    'total_value': record['total_value'] or 0
                })
        
        driver.close()
        return jsonify({
            'timeline': timeline,
            'market_share': market_share,
            'top_agencies': top_agencies,
            'naics_distribution': naics_distribution
        })
        
    except Exception as e:
        print(f"Error getting market trends: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/competitive/contractor-details', methods=['GET'])
def get_contractor_details():
    """Get detailed information about a specific contractor"""
    try:
        contractor_name = request.args.get('name', '')
        
        if not contractor_name:
            return jsonify({'error': 'Contractor name required'}), 400
        
        if not NEO4J_AVAILABLE:
            return jsonify({'error': 'Neo4j not available'}), 503
        
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(
            os.getenv('NEO4J_URI', 'bolt://localhost:7687'),
            auth=('neo4j', os.getenv('NEO4J_PASSWORD'))
        )
        
        with driver.session(database="contactsgraphdb") as session:
            # Get contractor summary
            result = session.run("""
                MATCH (c:Contract)-[:AWARDED_TO]->(org:Organization)
                WHERE org.name = $name
                RETURN 
                    count(c) as contract_count,
                    sum(toFloat(c.value)) as total_value,
                    collect(DISTINCT c.agency) as agencies,
                    collect(DISTINCT c.naics) as naics_codes
            """, name=contractor_name)
            
            row = result.single()
            
            if not row or row['contract_count'] == 0:
                driver.close()
                return jsonify({
                    'contractor': contractor_name,
                    'contract_count': 0,
                    'total_value': 0,
                    'agencies': [],
                    'naics_codes': [],
                    'recent_contracts': []
                })
            
            # Get recent contracts
            result = session.run("""
                MATCH (c:Contract)-[:AWARDED_TO]->(org:Organization)
                WHERE org.name = $name
                RETURN c.agency as agency, 
                       c.description as description,
                       toFloat(c.value) as value,
                       c.date_signed as date_signed,
                       c.naics as naics
                ORDER BY c.date_signed DESC
                LIMIT 10
            """, name=contractor_name)
            
            recent_contracts = []
            for record in result:
                recent_contracts.append({
                    'agency': record['agency'],
                    'description': record['description'],
                    'value': record['value'] or 0,
                    'date_signed': record['date_signed'],
                    'naics': record['naics']
                })
        
        driver.close()
        
        # Filter out None values from lists
        agencies = [a for a in (row['agencies'] or []) if a]
        naics_codes = [n for n in (row['naics_codes'] or []) if n]
        
        return jsonify({
            'contractor': contractor_name,
            'contract_count': row['contract_count'],
            'total_value': row['total_value'] or 0,
            'agencies': agencies,
            'naics_codes': naics_codes,
            'recent_contracts': recent_contracts
        })
        
    except Exception as e:
        print(f"Error getting contractor details: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/agents/competitive/analyze', methods=['POST'])
def analyze_competitive():
    """Agent 2: Competitive Intelligence"""
    if not AGENTS_AVAILABLE:
        return jsonify({'error': 'Agents not available'}), 503
    
    try:
        data = request.json
        notice_id = data.get('notice_id', '')
        
        if not notice_id:
            return jsonify({'error': 'notice_id required'}), 400
        
        # Load opportunity data to get agency and NAICS
        scout_files = list(Path('knowledge_graph').glob('scout_data_*.json'))
        if not scout_files:
            scout_files = list(Path('.').glob('scout_data_*.json'))
        
        if not scout_files:
            return jsonify({'error': 'No opportunity data found'}), 404
        
        # Get most recent
        with open(sorted(scout_files, reverse=True)[0]) as f:
            scout_data = json.load(f)
        
        # Find the opportunity (handle both field names)
        opp = None
        for opportunity in scout_data.get('opportunities', []):
            opp_id = opportunity.get('notice_id') or opportunity.get('noticeId')
            if opp_id == notice_id:
                opp = opportunity
                break
        
        if not opp:
            return jsonify({'error': 'Opportunity not found'}), 404
        
        # Debug: Log opportunity fields
        print(f"📋 Opportunity fields: {list(opp.keys())}")
        print(f"📋 Title: {opp.get('title', 'N/A')}")
        print(f"📋 fullParentPathName: '{opp.get('fullParentPathName', 'NOT FOUND')}'")
        print(f"📋 NAICS Code field: '{opp.get('naicsCode', 'NOT FOUND')}'")
        
        # Extract agency from SAM.gov field structure
        agency = opp.get('fullParentPathName', '') or opp.get('agency', '')
        naics = opp.get('naicsCode', '') or opp.get('naics', '')
        
        # Use AgentExecutor wrapper
        from agent_executor import AgentExecutor
        executor = AgentExecutor()
        
        results = executor.run_competitive_intel(agency, naics)
        
        # Add opportunity info
        results['opportunity'] = {
            'title': opp.get('title'),
            'agency': agency,
            'naics': naics
        }
        
        return jsonify(results)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e), 'status': 'error'}), 500


@app.route('/api/agents/contacts/research', methods=['POST'])
def research_contact():
    """Contact Research Agent — researches a contact's public professional presence"""
    try:
        data = request.json or {}

        # Accept either a full contact object or just the fields we need
        contact = {
            'id': data.get('id', ''),
            'name': data.get('name', ''),
            'title': data.get('title', ''),
            'agency': data.get('agency', '') or data.get('organization', ''),
            'organization': data.get('organization', '') or data.get('agency', ''),
            'email': data.get('email', ''),
        }

        if not contact['name']:
            return jsonify({'error': 'Contact name is required'}), 400

        force_refresh = data.get('force_refresh', False)

        print(f"📋 Contact Research request: {contact['name']} (force_refresh={force_refresh})")

        from agent_executor import AgentExecutor
        executor = AgentExecutor()
        results = executor.run_contact_research(contact, force_refresh=force_refresh)

        return jsonify(results)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e), 'status': 'error'}), 500


@app.route('/api/agents/excel/export', methods=['POST'])
def export_to_excel():
    """Export all data to Excel"""
    if not AGENTS_AVAILABLE:
        return jsonify({'error': 'Agents not available'}), 503
    
    try:
        # Import and run Excel exporter
        from excel_exporter import BDIntelligenceExporter
        exporter = BDIntelligenceExporter()
        filename = exporter.export()
        
        return jsonify({
            'status': 'success',
            'filename': filename,
            'message': f'Excel workbook generated: {filename}'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# AGENT LOGS API
# ============================================================================

@app.route('/api/agents/logs', methods=['GET'])
def get_agent_logs():
    """Get activity logs for agents"""
    try:
        from agent_logger import get_logger
        logger = get_logger()
        
        agent_id = request.args.get('agent_id', type=int)
        limit = request.args.get('limit', 50, type=int)
        
        logs = logger.get_recent_logs(agent_id=agent_id, limit=limit)
        
        return jsonify({
            'status': 'success',
            'logs': logs,
            'count': len(logs)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/agents/stats', methods=['GET'])
def get_agent_stats():
    """Get statistics for an agent"""
    try:
        from agent_logger import get_logger
        logger = get_logger()
        
        agent_id = request.args.get('agent_id', type=int)
        days = request.args.get('days', 7, type=int)
        
        if not agent_id:
            return jsonify({'error': 'agent_id required'}), 400
        
        stats = logger.get_agent_stats(agent_id=agent_id, days=days)
        
        return jsonify({
            'status': 'success',
            'stats': stats
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# OPPORTUNITY SCOUT API
# ============================================================================

@app.route('/api/scout/opportunities', methods=['GET'])
def get_scout_opportunities():
    """Get scored opportunities from scout"""
    if not AGENTS_AVAILABLE:
        return jsonify({'error': 'Agents not available'}), 503
    
    try:
        days = request.args.get('days', 7, type=int)
        priority_filter = request.args.get('priority', None)
        
        # Check for cached data in multiple locations
        scout_files = list(Path('knowledge_graph').glob('scout_data_*.json'))
        if not scout_files:
            # Try current directory
            scout_files = list(Path('.').glob('scout_data_*.json'))
        
        scout_files = sorted(scout_files, reverse=True)
        
        if not scout_files:
            return jsonify({
                'error': 'No scout data available',
                'message': 'Run opportunity scout first',
                'total_opportunities': 0,
                'opportunities': []
            }), 404
        
        # Load most recent
        with open(scout_files[0]) as f:
            data = json.load(f)
        
        opportunities = data.get('opportunities', [])
        scores = data.get('scores', [])
        
        # Fallback: if no scores, create basic entries for raw opportunities
        if not scores and opportunities:
            scored_opps = []
            for opp in opportunities:
                # Extract agency from multiple possible fields
                agency_obj = opp.get('department', {})
                agency = agency_obj.get('name', '') if isinstance(agency_obj, dict) else str(agency_obj or 'Unknown')
                
                scored_opps.append({
                    'notice_id': opp.get('noticeId'),
                    'title': opp.get('title'),
                    'agency': agency,
                    'posted_date': opp.get('postedDate'),
                    'deadline': opp.get('responseDeadLine'),
                    'setaside': opp.get('typeOfSetAsideDescription'),
                    'naics': opp.get('naicsCode'),
                    'description': opp.get('description', '')[:200],
                    'score': 0,
                    'win_probability': 0,
                    'priority': 'UNSCORED',
                    'recommendation': 'Run Opportunity Scout to score this opportunity',
                    'contacts': {'total': 0},
                    'reasoning': 'Not yet scored'
                })
            
            return jsonify({
                'timestamp': data.get('collection_date', datetime.now().isoformat()),
                'total_opportunities': len(scored_opps),
                'high_priority': 0,
                'medium_priority': 0,
                'opportunities': scored_opps
            })
        
        # Combine and filter scored opportunities
        scored_opps = []
        for opp, score in zip(opportunities, scores):
            if priority_filter and score['priority'] != priority_filter:
                continue
            
            # Extract agency from multiple possible fields
            agency = (opp.get('organizationName') or 
                     opp.get('fullParentPathName') or
                     opp.get('department') or
                     opp.get('subtier') or
                     opp.get('office') or
                     'Agency Not Specified')
            
            # Clean up agency name
            if agency and isinstance(agency, str) and '.' in agency:
                agency = agency.split('.')[0].strip()
            
            # Transform contacts to ensure consistent field names
            contacts = score.get('contacts', {})
            if 'total_contacts' in contacts and 'total' not in contacts:
                contacts['total'] = contacts['total_contacts']
            
            scored_opps.append({
                'notice_id': opp.get('noticeId'),
                'title': opp.get('title'),
                'agency': agency,
                'posted_date': opp.get('postedDate'),
                'deadline': opp.get('responseDeadLine'),
                'setaside': opp.get('typeOfSetAside'),
                'naics': opp.get('naicsCode'),
                'description': opp.get('description', '')[:200],
                'score': score['total_score'],
                'win_probability': score['win_probability'],
                'priority': score['priority'],
                'recommendation': score['recommendation'],
                'contacts': contacts,
                'reasoning': score['reasoning']
            })
        
        scored_opps.sort(key=lambda x: x['score'], reverse=True)
        
        return jsonify({
            'timestamp': data.get('timestamp'),
            'total_opportunities': len(scored_opps),
            'high_priority': sum(1 for o in scored_opps if o['priority'] == 'HIGH'),
            'medium_priority': sum(1 for o in scored_opps if o['priority'] == 'MEDIUM'),
            'opportunities': scored_opps
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/scout/summary', methods=['GET'])
def get_scout_summary():
    """Get scout summary statistics"""
    try:
        # Check multiple locations
        scout_files = list(Path('knowledge_graph').glob('scout_data_*.json'))
        if not scout_files:
            scout_files = list(Path('.').glob('scout_data_*.json'))
        
        scout_files = sorted(scout_files, reverse=True)
        
        if not scout_files:
            return jsonify({
                'total_opportunities': 0,
                'high_priority': 0,
                'with_contacts': 0,
                'message': 'No scout data available'
            })
        
        with open(scout_files[0]) as f:
            data = json.load(f)
        
        scores = data.get('scores', [])
        
        return jsonify({
            'timestamp': data.get('timestamp'),
            'total_opportunities': len(scores),
            'high_priority': sum(1 for s in scores if s['priority'] == 'HIGH'),
            'medium_priority': sum(1 for s in scores if s['priority'] == 'MEDIUM'),
            'low_priority': sum(1 for s in scores if s['priority'] == 'LOW'),
            'average_score': sum(s['total_score'] for s in scores) / len(scores) if scores else 0,
            'with_contacts': sum(1 for s in scores if s['contacts']['total_contacts'] > 0),
            'without_contacts': sum(1 for s in scores if s['contacts']['total_contacts'] == 0)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/scout/run', methods=['POST'])
def run_scout():
    """Trigger scout to run"""
    if not AGENTS_AVAILABLE:
        return jsonify({'error': 'Scout not available'}), 503
    
    try:
        data = request.get_json() or {}
        days = data.get('days', 7)
        
        scout = OpportunityScout()
        scout.run_daily_scout(days_back=days, save_report=True)
        scout.close()
        
        return jsonify({
            'status': 'success',
            'message': f'Scout completed for last {days} days',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# COMPETITIVE INTELLIGENCE API
# ============================================================================

@app.route('/api/intel/incumbents', methods=['GET'])
def get_incumbents():
    """Get incumbent contractors"""
    if not AGENTS_AVAILABLE:
        return jsonify({'error': 'Intel agent not available'}), 503
    
    try:
        agency = request.args.get('agency')
        naics = request.args.get('naics')
        
        if not agency:
            return jsonify({'error': 'Agency parameter required'}), 400
        
        agent = CompetitiveIntelAgent()
        incumbents = agent.identify_incumbents(agency, naics)
        agent.close()
        
        return jsonify({
            'agency': agency,
            'naics': naics,
            'incumbents': incumbents,
            'count': len(incumbents)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/intel/teaming-partners', methods=['GET'])
def get_intel_teaming_partners():
    """Get teaming partner recommendations"""
    if not AGENTS_AVAILABLE:
        return jsonify({'error': 'Intel agent not available'}), 503
    
    try:
        agency = request.args.get('agency')
        naics = request.args.get('naics')
        min_contracts = request.args.get('min_contracts', 3, type=int)
        
        agent = CompetitiveIntelAgent()
        partners = agent.find_teaming_partners(agency, naics, min_contracts)
        agent.close()
        
        return jsonify({
            'agency': agency,
            'naics': naics,
            'partners': partners,
            'count': len(partners)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/intel/agency-spending', methods=['GET'])
def get_agency_spending():
    """Get agency spending analysis"""
    if not AGENTS_AVAILABLE:
        return jsonify({'error': 'Intel agent not available'}), 503
    
    try:
        agency = request.args.get('agency')
        
        if not agency:
            return jsonify({'error': 'Agency parameter required'}), 400
        
        agent = CompetitiveIntelAgent()
        spending = agent.analyze_agency_spending(agency)
        agent.close()
        
        return jsonify(spending)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/intel/competitors', methods=['POST'])
def analyze_competitors():
    """Analyze competitors"""
    if not AGENTS_AVAILABLE:
        return jsonify({'error': 'Intel agent not available'}), 503
    
    try:
        data = request.get_json()
        competitors = data.get('competitors', [])
        
        if not competitors:
            return jsonify({'error': 'No competitors specified'}), 400
        
        agent = CompetitiveIntelAgent()
        comparison = agent.competitor_comparison(competitors)
        agent.close()
        
        return jsonify(comparison)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# DASHBOARD INTEGRATION API
# ============================================================================

@app.route('/api/dashboard/stats', methods=['GET'])
def dashboard_stats():
    """Get dashboard stats for sidebar"""
    try:
        db = get_db()
        
        # Count contacts
        contacts_count = db.execute('SELECT COUNT(*) FROM contacts').fetchone()[0]
        
        # Count opportunities (if available)
        opportunities_count = 0
        if AGENTS_AVAILABLE:
            scout_files = list(Path('knowledge_graph').glob('scout_data_*.json'))
            if not scout_files:
                scout_files = list(Path('.').glob('scout_data_*.json'))
            if scout_files:
                with open(sorted(scout_files, reverse=True)[0]) as f:
                    data = json.load(f)
                    opportunities_count = len(data.get('opportunities', []))
        
        db.close()
        
        return jsonify({
            'contacts': contacts_count,
            'opportunities': opportunities_count
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/dashboard/overview', methods=['GET'])
def dashboard_overview():
    """Complete dashboard overview"""
    try:
        overview = {
            'timestamp': datetime.now().isoformat(),
            'contacts': {},
            'opportunities': {},
            'intel': {},
            'agents_available': AGENTS_AVAILABLE
        }
        
        # Contact stats from SQLite
        db = get_db()
        contact_count = db.execute('SELECT COUNT(*) as count FROM contacts').fetchone()['count']
        org_count = db.execute('SELECT COUNT(DISTINCT organization) as count FROM contacts').fetchone()['count']
        db.close()
        
        overview['contacts'] = {
            'total': contact_count,
            'organizations': org_count
        }
        
        # Knowledge graph stats
        if AGENTS_AVAILABLE:
            try:
                kg = KnowledgeGraphClient(
                    uri=os.getenv('NEO4J_URI', 'bolt://localhost:7687'),
                    user=os.getenv('NEO4J_USER', 'neo4j'),
                    password=os.getenv('NEO4J_PASSWORD')
                )
                graph_stats = kg.get_network_statistics()
                kg.close()
                
                overview['contacts']['graph_people'] = graph_stats.get('total_people', 0)
                overview['contacts']['decision_makers'] = graph_stats.get('decision_makers', 0)
            except:
                pass
        
        # Scout stats
        scout_files = sorted(Path('knowledge_graph').glob('scout_data_*.json'), reverse=True)
        if scout_files:
            with open(scout_files[0]) as f:
                scout_data = json.load(f)
                scores = scout_data.get('scores', [])
                
                overview['opportunities'] = {
                    'total': len(scores),
                    'high_priority': sum(1 for s in scores if s['priority'] == 'HIGH'),
                    'with_contacts': sum(1 for s in scores if s['contacts']['total_contacts'] > 0),
                    'last_run': scout_data.get('timestamp')
                }
        
        # Intel stats
        if AGENTS_AVAILABLE:
            try:
                kg = KnowledgeGraphClient(
                    uri=os.getenv('NEO4J_URI', 'bolt://localhost:7687'),
                    user=os.getenv('NEO4J_USER', 'neo4j'),
                    password=os.getenv('NEO4J_PASSWORD')
                )
                
                with kg.driver.session(database="contactsgraphdb") as session:
                    result = session.run("MATCH (c:Contract) RETURN count(c) as count")
                    contract_count = result.single()['count'] if result.single() else 0
                
                kg.close()
                
                overview['intel'] = {
                    'contracts_tracked': contract_count
                }
            except:
                pass
        
        return jsonify(overview)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/dashboard/recent-activity', methods=['GET'])
def get_recent_activity():
    """Get recent agent activity"""
    try:
        activities = []
        
        # Scout runs - check multiple locations
        scout_files = list(Path('knowledge_graph').glob('scout_report_*.txt'))
        if not scout_files:
            scout_files = list(Path('.').glob('scout_report_*.txt'))
        scout_files = sorted(scout_files, reverse=True)
        
        for f in scout_files[:5]:
            activities.append({
                'type': 'scout',
                'title': 'Opportunity Scout Run',
                'timestamp': datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                'file': str(f.name)
            })
        
        # Intel reports - check multiple locations
        intel_files = list(Path('knowledge_graph').glob('competitive_intel_*.txt'))
        if not intel_files:
            intel_files = list(Path('.').glob('competitive_intel_*.txt'))
        intel_files = sorted(intel_files, reverse=True)
        
        for f in intel_files[:5]:
            activities.append({
                'type': 'intel',
                'title': 'Competitive Intelligence Report',
                'timestamp': datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                'file': str(f.name)
            })
        
        # Sort by timestamp
        activities.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return jsonify({
            'activities': activities[:20],
            'count': len(activities)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'agents_available': AGENTS_AVAILABLE,
        'database': os.path.exists(DATABASE)
    })



# ============================================================================
# FILE SERVING
# ============================================================================

@app.route('/outputs/<path:filename>')
def serve_output_file(filename):
    """Serve generated output files"""
    # Try different possible locations
    possible_paths = [
        Path('knowledge_graph') / filename,
        Path('knowledge_graph/outputs') / filename,
        Path('outputs') / filename,
        Path('.') / filename
    ]
    
    for path in possible_paths:
        if path.exists():
            return send_file(str(path), as_attachment=True)
    
    return jsonify({'error': 'File not found'}), 404


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    # Initialize database if needed
    db_created = init_database()
    
    print("\n" + "="*70)
    print("🚀 INTEGRATED BD INTELLIGENCE DASHBOARD")
    print("="*70)
    print(f"\nDashboard URL: http://localhost:8080")
    print(f"Agents Available: {'✓ Yes' if AGENTS_AVAILABLE else '✗ No (run from project root)'}")
    print(f"Database: {'✓ Connected' if os.path.exists(DATABASE) else '✗ Not found'}")
    if db_created:
        print("  📝 New database created at data/contacts.db")
    print("\nPages:")
    print("  • http://localhost:8080/                    (Home)")
    print("  • http://localhost:8080/contacts            (Contact Management)")
    print("  • http://localhost:8080/bd-intelligence     (BD Intelligence Hub)")
    print("\nAPI Endpoints:")
    print("  • GET  /api/dashboard/overview")
    print("  • GET  /api/scout/opportunities")
    print("  • GET  /api/intel/incumbents?agency=NASA")
    print("  • POST /api/scout/run")
    print("\n" + "="*70 + "\n")
    
    app.run(host='0.0.0.0', port=8080, debug=True)
