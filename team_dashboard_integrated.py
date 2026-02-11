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
import time
from datetime import datetime
from pathlib import Path

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()  # This loads .env from current directory

# Verify critical environment variables are loaded
if os.getenv('ANTHROPIC_API_KEY'):
    print("✓ ANTHROPIC_API_KEY loaded")

# Add knowledge_graph to path
sys.path.append('knowledge_graph')

# Import agents
try:
    from opportunity_scout import OpportunityScout
    from competitive_intel import CompetitiveIntelAgent
    from graph.graph_client import KnowledgeGraphClient
    AGENTS_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  Warning: Some agents not available: {e}")
    AGENTS_AVAILABLE = False

app = Flask(__name__)
CORS(app)

print("✓ Competitive Intelligence routes (USAspending-based) active")

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


def ensure_schema_updates():
    """Apply schema migrations to existing database"""
    if not os.path.exists(DATABASE):
        return
    db = sqlite3.connect(DATABASE)
    db.execute('''
        CREATE TABLE IF NOT EXISTS opportunity_contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            opportunity_id TEXT NOT NULL,
            contact_id INTEGER NOT NULL,
            role TEXT,
            poc_type TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (contact_id) REFERENCES contacts (id),
            UNIQUE(opportunity_id, contact_id)
        )
    ''')
    db.execute('''
        CREATE TABLE IF NOT EXISTS opportunity_resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            opportunity_id TEXT NOT NULL,
            url TEXT NOT NULL,
            resource_type TEXT DEFAULT 'attachment',
            label TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(opportunity_id, url)
        )
    ''')
    db.execute('''
        CREATE TABLE IF NOT EXISTS opportunity_stage (
            opportunity_id TEXT PRIMARY KEY,
            stage TEXT NOT NULL DEFAULT 'new',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    db.execute('''
        CREATE TABLE IF NOT EXISTS organization_research (
            org_name TEXT PRIMARY KEY,
            research_profile TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Add research_profile column if missing
    try:
        db.execute('ALTER TABLE contacts ADD COLUMN research_profile TEXT')
        print("  ✓ Added research_profile column to contacts table")
    except sqlite3.OperationalError:
        pass  # Column already exists
    db.commit()
    db.close()


# Track which scout files have been synced (avoid re-running on every request)
_poc_synced_files = set()


def extract_and_store_poc_contacts(opportunities):
    """Extract POC contacts from scout opportunities and store in contacts DB."""
    db = get_db()
    stats = {'created': 0, 'updated': 0, 'linked': 0, 'resources': 0, 'skipped': 0}

    for opp in opportunities:
        notice_id = opp.get('noticeId')
        if not notice_id:
            continue

        # Extract and clean agency name
        agency = (opp.get('fullParentPathName') or
                  opp.get('organizationName') or
                  'Unknown Agency')
        agency_clean = agency.split('.')[0].strip() if '.' in agency else agency

        # Process each point of contact
        for poc in (opp.get('pointOfContact') or []):
            full_name = (poc.get('fullName') or '').strip()
            email = (poc.get('email') or '').strip()
            phone = (poc.get('phone') or '').strip()
            poc_type = poc.get('type', 'primary')
            poc_title = poc.get('title')

            if not full_name and not email:
                stats['skipped'] += 1
                continue

            role = 'Contracting Officer' if poc_type == 'primary' else 'Point of Contact'

            # Deduplicate: check by email first, then name+agency
            existing = None
            if email:
                existing = db.execute(
                    'SELECT id FROM contacts WHERE email = ?', (email,)
                ).fetchone()
            if not existing and full_name:
                existing = db.execute(
                    'SELECT id FROM contacts WHERE name = ? AND agency = ?',
                    (full_name, agency_clean)
                ).fetchone()

            if existing:
                contact_id = existing['id']
                if phone:
                    db.execute('''
                        UPDATE contacts SET phone = COALESCE(NULLIF(phone, ''), ?),
                                           updated_at = CURRENT_TIMESTAMP
                        WHERE id = ? AND (phone IS NULL OR phone = '')
                    ''', (phone, contact_id))
                stats['updated'] += 1
            else:
                cursor = db.execute('''
                    INSERT INTO contacts
                    (name, email, phone, title, organization, role,
                     source, agency, relationship_strength, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    full_name, email, phone, poc_title, agency_clean, role,
                    'SAM.gov POC', agency_clean, 'New',
                    f'Auto-imported from SAM.gov opportunity {notice_id}'
                ))
                contact_id = cursor.lastrowid
                stats['created'] += 1

            # Link contact to opportunity
            db.execute('''
                INSERT OR IGNORE INTO opportunity_contacts
                (opportunity_id, contact_id, role, poc_type)
                VALUES (?, ?, ?, ?)
            ''', (notice_id, contact_id, role, poc_type))
            stats['linked'] += 1

        # Store resource links
        for idx, url in enumerate(opp.get('resourceLinks') or []):
            if url:
                db.execute('''
                    INSERT OR IGNORE INTO opportunity_resources
                    (opportunity_id, url, resource_type, label)
                    VALUES (?, ?, ?, ?)
                ''', (notice_id, url, 'attachment', f'Attachment {idx + 1}'))
                stats['resources'] += 1

    db.commit()
    return stats


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
    
    # Check which contacts have research profiles
    researched_names = set()
    try:
        db2 = get_db()
        sqlite_researched = db2.execute(
            "SELECT name FROM contacts WHERE research_profile IS NOT NULL AND research_profile != ''"
        ).fetchall()
        db2.close()
        researched_names = set(row['name'] for row in sqlite_researched)
    except Exception as e:
        print(f"Research lookup failed: {e}")
    
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
    """Get research profile for a contact"""
    try:
        db = get_db()
        contact = db.execute('SELECT name, research_profile FROM contacts WHERE id = ?', (contact_id,)).fetchone()
        db.close()

        if not contact:
            return jsonify({'error': 'Contact not found'}), 404

        name = contact['name']
        profile = None

        if contact['research_profile']:
            try:
                profile = json.loads(contact['research_profile'])
            except (json.JSONDecodeError, TypeError):
                pass

        return jsonify({
            'contact_id': contact_id,
            'name': name,
            'research_profile': profile
        })

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
def sync_contacts():
    """Contact sync endpoint (legacy — all data is now in SQLite)"""
    db = get_db()
    count = db.execute("SELECT COUNT(*) FROM contacts").fetchone()[0]
    db.close()
    return jsonify({
        'status': 'success',
        'message': f'All {count} contacts already in SQLite',
        'synced': count,
        'created': 0,
        'updated': 0,
        'skipped': 0
    })


# ============================================================================
# AGENT INTEGRATION ROUTES
# ============================================================================

def _load_opportunity(notice_id: str) -> dict:
    """Load an opportunity from the most recent scout data file by notice_id."""
    if not notice_id:
        return None
    scout_files = list(Path('knowledge_graph').glob('scout_data_*.json'))
    if not scout_files:
        scout_files = list(Path('.').glob('scout_data_*.json'))
    if not scout_files:
        return None
    with open(sorted(scout_files, reverse=True)[0]) as f:
        scout_data = json.load(f)
    for opp in scout_data.get('opportunities', []):
        opp_id = opp.get('notice_id') or opp.get('noticeId')
        if opp_id == notice_id:
            return opp
    return None


@app.route('/api/agents/capability/analyze', methods=['POST'])
def analyze_capability():
    """Agent 3: Capability Matching"""
    if not AGENTS_AVAILABLE:
        return jsonify({'error': 'Agents not available'}), 503

    t0 = time.time()
    try:
        data = request.json
        notice_id = data.get('notice_id', '')

        # Load full opportunity data from scout file
        opp = _load_opportunity(notice_id)
        if not opp:
            opp = {'title': 'Opportunity', 'description': data.get('requirements', '')}

        opportunity_data = {
            'title': opp.get('title', ''),
            'description': opp.get('description', '') or data.get('requirements', ''),
            'agency': opp.get('fullParentPathName', '') or opp.get('agency', ''),
        }

        from agent_executor import AgentExecutor
        executor = AgentExecutor()
        results = executor.run_capability_match(opportunity_data)

        from agent_logger import get_logger
        get_logger().log_agent_activity(3, 'Capability Matching', f'Analyze: {opp.get("title", notice_id)[:80]}',
            'success' if results.get('status') == 'success' else 'error', time.time() - t0,
            input_data={'notice_id': notice_id}, output_data={'capability_score': results.get('capability_score')})

        return jsonify(results)

    except Exception as e:
        import traceback
        traceback.print_exc()
        from agent_logger import get_logger
        get_logger().log_agent_activity(3, 'Capability Matching', 'Analyze opportunity', 'error', time.time() - t0, error_message=str(e))
        return jsonify({'error': str(e), 'status': 'error'}), 500


@app.route('/api/agents/rfi/generate', methods=['POST'])
def generate_rfi():
    """Agent 4: RFI Response Generator"""
    if not AGENTS_AVAILABLE:
        return jsonify({'error': 'Agents not available'}), 503

    t0 = time.time()
    try:
        data = request.json
        notice_id = data.get('notice_id', '')

        if not notice_id:
            return jsonify({'error': 'notice_id required'}), 400

        opp = _load_opportunity(notice_id)
        if not opp:
            opp = {'title': 'Opportunity', 'agency': '', 'description': ''}

        from agent_executor import AgentExecutor
        executor = AgentExecutor()
        results = executor.run_rfi_generator(notice_id, opp)

        from agent_logger import get_logger
        get_logger().log_agent_activity(4, 'RFI Generator', f'Generate RFI: {opp.get("title", notice_id)[:80]}',
            'success' if results.get('status') == 'success' else 'error', time.time() - t0,
            input_data={'notice_id': notice_id}, output_data={'file_path': results.get('file_path')})

        return jsonify(results)

    except Exception as e:
        import traceback
        traceback.print_exc()
        from agent_logger import get_logger
        get_logger().log_agent_activity(4, 'RFI Generator', 'Generate RFI', 'error', time.time() - t0, error_message=str(e))
        return jsonify({'error': str(e), 'status': 'error'}), 500


@app.route('/api/agents/proposal/generate', methods=['POST'])
def generate_proposal():
    """Agent 5: Proposal Writing Assistant"""
    if not AGENTS_AVAILABLE:
        return jsonify({'error': 'Agents not available'}), 503

    t0 = time.time()
    try:
        data = request.json
        notice_id = data.get('notice_id', '')

        if not notice_id:
            return jsonify({'error': 'notice_id required'}), 400

        opp = _load_opportunity(notice_id)
        if not opp:
            opp = {'title': 'Opportunity', 'agency': '', 'description': ''}

        from agent_executor import AgentExecutor
        executor = AgentExecutor()
        results = executor.run_proposal_writer(notice_id, opp)

        from agent_logger import get_logger
        get_logger().log_agent_activity(5, 'Proposal Writer', f'Generate proposal: {opp.get("title", notice_id)[:80]}',
            'success' if results.get('status') == 'success' else 'error', time.time() - t0,
            input_data={'notice_id': notice_id}, output_data={'file_path': results.get('file_path')})

        return jsonify(results)

    except Exception as e:
        import traceback
        traceback.print_exc()
        from agent_logger import get_logger
        get_logger().log_agent_activity(5, 'Proposal Writer', 'Generate proposal', 'error', time.time() - t0, error_message=str(e))
        return jsonify({'error': str(e), 'status': 'error'}), 500


@app.route('/api/agents/pricing/generate', methods=['POST'])
def generate_pricing():
    """Agent 6: Pricing & Budget Generator"""
    if not AGENTS_AVAILABLE:
        return jsonify({'error': 'Agents not available'}), 503

    t0 = time.time()
    try:
        data = request.json
        notice_id = data.get('notice_id', '')

        if not notice_id:
            return jsonify({'error': 'notice_id required'}), 400

        opp = _load_opportunity(notice_id)
        if not opp:
            opp = {'title': 'Opportunity', 'description': ''}

        from agent_executor import AgentExecutor
        executor = AgentExecutor()
        results = executor.run_pricing_generator(notice_id, opp)

        from agent_logger import get_logger
        get_logger().log_agent_activity(6, 'Pricing Generator', f'Generate pricing: {opp.get("title", notice_id)[:80]}',
            'success' if results.get('status') == 'success' else 'error', time.time() - t0,
            input_data={'notice_id': notice_id}, output_data={'total_value': results.get('pricing', {}).get('total_value')})

        return jsonify(results)

    except Exception as e:
        import traceback
        traceback.print_exc()
        from agent_logger import get_logger
        get_logger().log_agent_activity(6, 'Pricing Generator', 'Generate pricing', 'error', time.time() - t0, error_message=str(e))
        return jsonify({'error': str(e), 'status': 'error'}), 500


# ============================================================================
# COMPETITIVE INTELLIGENCE API ENDPOINTS
# ============================================================================

@app.route('/api/competitive/stats', methods=['GET'])
def get_competitive_stats():
    """Get overall competitive intelligence statistics via USAspending.gov"""
    try:
        from usaspending_intel import USAspendingIntelligence
        usa = USAspendingIntelligence()

        # Get top contractors across all agencies to derive stats
        incumbents = usa.get_incumbents_at_agency('', '', limit=50)
        total_value = sum(i.get('contract_value_raw', 0) for i in incumbents)

        return jsonify({
            'contract_count': sum(i.get('awards', 0) for i in incumbents),
            'contractor_count': len(incumbents),
            'agency_count': len(set(i.get('agency', '') for i in incumbents if i.get('agency'))),
            'total_value': total_value
        })

    except Exception as e:
        print(f"Error getting competitive stats: {e}")
        return jsonify({'contract_count': 0, 'contractor_count': 0, 'agency_count': 0, 'total_value': 0})


@app.route('/api/competitive/incumbents', methods=['GET'])
def get_competitive_incumbents():
    """Get top contractors ranked by contract value via USAspending.gov"""
    try:
        from usaspending_intel import USAspendingIntelligence, normalize_agency_name
        usa = USAspendingIntelligence()

        agency = request.args.get('agency', '')
        naics = request.args.get('naics', '')
        if agency:
            agency = normalize_agency_name(agency)

        raw = usa.get_incumbents_at_agency(agency, naics, limit=50)

        incumbents = []
        for r in raw:
            tv = r.get('contract_value_raw', 0)
            awards = r.get('awards', 0)
            incumbents.append({
                'contractor': r['company'],
                'contract_count': awards,
                'total_value': tv,
                'avg_value': tv / awards if awards else 0,
                'top_agency': agency or 'All',
                'naics_codes': [naics] if naics else []
            })

        return jsonify({'incumbents': incumbents})

    except Exception as e:
        print(f"Error getting incumbents: {e}")
        return jsonify({'error': str(e), 'incumbents': []}), 500


@app.route('/api/competitive/filter-options', methods=['GET'])
def get_competitive_filter_options():
    """Get available filter options from scout data"""
    try:
        from usaspending_intel import normalize_agency_name
        scout_files = sorted(Path('knowledge_graph').glob('scout_data_*.json'), reverse=True)
        if not scout_files:
            scout_files = sorted(Path('.').glob('scout_data_*.json'), reverse=True)

        agencies = set()
        naics = set()

        if scout_files:
            with open(scout_files[0]) as f:
                data = json.load(f)
            for opp in data.get('opportunities', []):
                raw_agency = opp.get('fullParentPathName', '')
                if raw_agency:
                    agencies.add(normalize_agency_name(raw_agency))
                nc = opp.get('naicsCode', '')
                if nc:
                    naics.add(str(nc))

        return jsonify({
            'agencies': sorted(agencies),
            'naics': sorted(naics)
        })

    except Exception as e:
        print(f"Error getting filter options: {e}")
        return jsonify({'agencies': [], 'naics': []})


@app.route('/api/competitive/teaming-partners', methods=['GET'])
def get_teaming_partners():
    """Get potential teaming partners via USAspending.gov"""
    try:
        from usaspending_intel import USAspendingIntelligence, normalize_agency_name
        usa = USAspendingIntelligence()

        # Collect unique NAICS from scout data for partner search
        naics_codes = set()
        agencies_in_data = set()
        scout_files = sorted(Path('knowledge_graph').glob('scout_data_*.json'), reverse=True)
        if not scout_files:
            scout_files = sorted(Path('.').glob('scout_data_*.json'), reverse=True)
        if scout_files:
            with open(scout_files[0]) as f:
                data = json.load(f)
            for opp in data.get('opportunities', []):
                nc = opp.get('naicsCode', '')
                if nc:
                    naics_codes.add(str(nc))
                raw_agency = opp.get('fullParentPathName', '')
                if raw_agency:
                    agencies_in_data.add(normalize_agency_name(raw_agency))

        # Get partners for top NAICS codes
        by_naics = []
        for nc in sorted(naics_codes)[:5]:
            partners = usa.find_teaming_partners(naics_code=nc, small_business_only=False, min_revenue=500_000, max_revenue=50_000_000)
            if partners:
                contractors = [{'contractor': p['name'], 'contract_count': p.get('award_count', 0),
                                'total_value': p.get('total_value', 0)} for p in partners[:10]]
                by_naics.append({'naics': nc, 'contractors': contractors})

        # Get incumbents per agency as "by_agency"
        by_agency = []
        for agency in sorted(agencies_in_data)[:5]:
            incumbents = usa.get_incumbents_at_agency(agency, '', limit=10)
            if incumbents:
                contractors = [{'contractor': i['company'], 'contract_count': i.get('awards', 0),
                                'total_value': i.get('contract_value_raw', 0)} for i in incumbents]
                by_agency.append({'agency': agency, 'contractors': contractors})

        # Recommended = small-to-mid companies across all NAICS
        recommended = []
        seen = set()
        for nc in sorted(naics_codes)[:3]:
            partners = usa.find_teaming_partners(naics_code=nc, small_business_only=False, min_revenue=1_000_000, max_revenue=20_000_000)
            for p in partners[:10]:
                if p['name'] not in seen:
                    seen.add(p['name'])
                    recommended.append({
                        'contractor': p['name'],
                        'contract_count': p.get('award_count', 0),
                        'total_value': p.get('total_value', 0),
                        'agency_diversity': 1,
                        'naics_diversity': 1,
                        'top_agencies': [],
                        'naics_codes': [nc],
                        'partner_score': p.get('award_count', 0) * 2
                    })
        recommended.sort(key=lambda x: x['partner_score'], reverse=True)

        return jsonify({
            'by_naics': by_naics,
            'by_agency': by_agency,
            'recommended': recommended[:20]
        })

    except Exception as e:
        print(f"Error getting teaming partners: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'by_naics': [], 'by_agency': [], 'recommended': []})


@app.route('/api/competitive/organization/<path:org_name>/research', methods=['GET'])
def get_organization_research(org_name):
    """Get cached research profile for an organization from SQLite + USAspending context"""
    try:
        # Check SQLite cache for existing research
        db = get_db()
        row = db.execute(
            'SELECT research_profile, updated_at FROM organization_research WHERE org_name = ?',
            (org_name,)
        ).fetchone()
        db.close()

        profile = None
        if row and row['research_profile']:
            try:
                profile = json.loads(row['research_profile'])
                # Strip any <cite> tags from cached data
                import re
                def _strip_cite(val):
                    if isinstance(val, str):
                        return re.sub(r'</?cite[^>]*>', '', val)
                    if isinstance(val, list):
                        return [_strip_cite(v) for v in val]
                    if isinstance(val, dict):
                        return {k: _strip_cite(v) for k, v in val.items()}
                    return val
                profile = _strip_cite(profile)
            except (json.JSONDecodeError, TypeError):
                profile = None

        # Get contract context from USAspending
        contract_count = 0
        total_value = 0
        try:
            from usaspending_intel import USAspendingIntelligence
            usa = USAspendingIntelligence()
            results = usa.get_contractor_profile(org_name)
            contract_count = results.get('contract_count_3yr', 0)
            total_value = results.get('total_contract_value_3yr', 0)
        except Exception:
            pass

        return jsonify({
            'name': org_name,
            'research_profile': profile,
            'contract_count': contract_count,
            'total_value': total_value
        })

    except Exception as e:
        print(f"Error getting organization research: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/competitive/organization/research', methods=['POST'])
def research_organization():
    """Run AI research on an organization (USAspending context + Claude web search)"""
    try:
        data = request.get_json()
        org_name = data.get('name', '')
        force_refresh = data.get('force_refresh', False)

        if not org_name:
            return jsonify({'error': 'Organization name required'}), 400

        # Check SQLite cache first (unless force refresh)
        if not force_refresh:
            db = get_db()
            row = db.execute(
                'SELECT research_profile, updated_at FROM organization_research WHERE org_name = ?',
                (org_name,)
            ).fetchone()
            db.close()
            if row and row['research_profile']:
                try:
                    cached = json.loads(row['research_profile'])
                    from datetime import datetime, timedelta
                    researched_at = cached.get('researched_at', '')
                    if researched_at:
                        rdate = datetime.fromisoformat(researched_at)
                        if datetime.now() - rdate < timedelta(days=14):
                            cached['method'] = 'cached'
                            return jsonify({'status': 'success', 'name': org_name, 'research_profile': cached})
                except Exception:
                    pass

        # Build org context from USAspending
        org_info = {'name': org_name}
        try:
            from usaspending_intel import USAspendingIntelligence
            usa = USAspendingIntelligence()
            details = usa.get_contractor_profile(org_name)
            org_info['contract_count'] = details.get('contract_count_3yr', 0)
            org_info['total_value'] = details.get('total_contract_value_3yr', 0)
            org_info['top_agencies'] = [a['name'] for a in details.get('top_agencies', [])]
        except Exception:
            pass

        # Run AI research via Claude
        sys.path.insert(0, 'knowledge_graph')
        from organization_research_agent import _research_org_with_claude
        t0 = time.time()
        profile = _research_org_with_claude(org_info)

        # Strip <cite> tags from Claude web_search responses
        import re
        def _strip_cite(val):
            if isinstance(val, str):
                return re.sub(r'</?cite[^>]*>', '', val)
            if isinstance(val, list):
                return [_strip_cite(v) for v in val]
            if isinstance(val, dict):
                return {k: _strip_cite(v) for k, v in val.items()}
            return val
        profile = _strip_cite(profile)

        # Cache in SQLite
        try:
            db = get_db()
            db.execute(
                '''INSERT INTO organization_research (org_name, research_profile, updated_at)
                   VALUES (?, ?, CURRENT_TIMESTAMP)
                   ON CONFLICT(org_name) DO UPDATE SET
                       research_profile = excluded.research_profile,
                       updated_at = CURRENT_TIMESTAMP''',
                (org_name, json.dumps(profile))
            )
            db.commit()
            db.close()
        except Exception as cache_err:
            print(f"  Warning: failed to cache org research: {cache_err}")

        # Log agent activity
        try:
            from agent_logger import get_logger
            get_logger().log_agent_activity(
                2, 'Competitive Intel', f'Org research: {org_name[:60]}',
                'success', time.time() - t0,
                input_data={'org_name': org_name},
                output_data={'confidence': profile.get('confidence', 'unknown')}
            )
        except Exception:
            pass

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
    """Get market trend data via USAspending.gov"""
    try:
        from usaspending_intel import USAspendingIntelligence, normalize_agency_name
        usa = USAspendingIntelligence()

        # Collect NAICS and agencies from scout data
        naics_codes = set()
        agencies = set()
        scout_files = sorted(Path('knowledge_graph').glob('scout_data_*.json'), reverse=True)
        if not scout_files:
            scout_files = sorted(Path('.').glob('scout_data_*.json'), reverse=True)
        if scout_files:
            with open(scout_files[0]) as f:
                data = json.load(f)
            for opp in data.get('opportunities', []):
                nc = opp.get('naicsCode', '')
                if nc:
                    naics_codes.add(str(nc))
                raw = opp.get('fullParentPathName', '')
                if raw:
                    agencies.add(normalize_agency_name(raw))

        # Market trends for the first NAICS code (spending over time)
        timeline = []
        first_naics = sorted(naics_codes)[0] if naics_codes else ''
        first_agency = sorted(agencies)[0] if agencies else ''
        if first_naics:
            trends = usa.get_market_trends(first_naics, first_agency, years=3)
            for year, amount in trends.get('yearly_spending', {}).items():
                timeline.append({
                    'month': f'{year}-06',
                    'contract_count': 0,
                    'total_value': amount
                })

        # Market share = top incumbents across all agencies
        incumbents = usa.get_incumbents_at_agency(first_agency, first_naics, limit=10)
        market_share = [{'contractor': i['company'], 'total_value': i.get('contract_value_raw', 0)} for i in incumbents]

        # Top agencies = incumbents per agency
        top_agencies = []
        for agency in sorted(agencies)[:10]:
            inc = usa.get_incumbents_at_agency(agency, '', limit=1)
            if inc:
                top_agencies.append({
                    'agency': agency,
                    'contract_count': sum(i.get('awards', 0) for i in inc),
                    'total_value': sum(i.get('contract_value_raw', 0) for i in inc)
                })
        top_agencies.sort(key=lambda x: x['total_value'], reverse=True)

        # NAICS distribution
        naics_distribution = []
        for nc in sorted(naics_codes)[:10]:
            trends = usa.get_market_trends(nc, '', years=1)
            total = trends.get('total_spending', 0)
            if total > 0:
                naics_distribution.append({
                    'naics': nc,
                    'contract_count': 0,
                    'total_value': total
                })
        naics_distribution.sort(key=lambda x: x['total_value'], reverse=True)

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
        return jsonify({'timeline': [], 'market_share': [], 'top_agencies': [], 'naics_distribution': []})


@app.route('/api/competitive/contractor-details', methods=['GET'])
def get_contractor_details():
    """Get detailed information about a specific contractor via USAspending.gov"""
    try:
        contractor_name = request.args.get('name', '')

        if not contractor_name:
            return jsonify({'error': 'Contractor name required'}), 400

        from usaspending_intel import USAspendingIntelligence
        usa = USAspendingIntelligence()

        profile = usa.get_contractor_profile(contractor_name)

        if not profile or profile.get('error'):
            return jsonify({
                'contractor': contractor_name,
                'contract_count': 0,
                'total_value': 0,
                'agencies': [],
                'naics_codes': [],
                'recent_contracts': []
            })

        # Map USAspending field names to what the frontend modal expects
        agencies = [a['name'] for a in profile.get('top_agencies', []) if a.get('name') and a['name'] != 'Unknown']
        naics_codes = list(set(
            str(r.get('NAICS Code', '')) for r in profile.get('recent_awards', [])
            if r.get('NAICS Code')
        ))
        recent = []
        for award in profile.get('recent_awards', []):
            recent.append({
                'agency': award.get('Awarding Sub Agency') or award.get('Awarding Agency') or 'N/A',
                'description': award.get('Description') or award.get('Award ID', 'N/A'),
                'value': award.get('Award Amount', 0) or 0,
                'date_signed': award.get('Start Date') or None
            })

        return jsonify({
            'contractor': contractor_name,
            'contract_count': profile.get('contract_count_3yr', 0),
            'total_value': profile.get('total_contract_value_3yr', 0),
            'agencies': agencies,
            'naics_codes': naics_codes,
            'recent_contracts': recent
        })

    except Exception as e:
        print(f"Error getting contractor details: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/competitive/contractor/<path:contractor_name>', methods=['GET'])
def get_contractor_full_profile(contractor_name):
    """Full contractor profile for the detail page — timeline, agencies, NAICS, all contracts"""
    try:
        from usaspending_intel import USAspendingIntelligence
        usa = USAspendingIntelligence()

        # Fetch all awards (up to 100) with enriched fields
        import requests as req
        from datetime import datetime, timedelta
        payload = {
            "filters": {
                "recipient_search_text": [contractor_name],
                "award_type_codes": ["A", "B", "C", "D"],
                "time_period": [{
                    "start_date": (datetime.now() - timedelta(days=1095)).strftime('%Y-%m-%d'),
                    "end_date": datetime.now().strftime('%Y-%m-%d')
                }]
            },
            "fields": ["Award ID", "Recipient Name", "Award Amount", "Award Type",
                        "Awarding Agency", "Awarding Sub Agency", "Description",
                        "Start Date", "NAICS Code"],
            "limit": 100,
            "page": 1
        }
        resp = req.post("https://api.usaspending.gov/api/v2/search/spending_by_award/",
                        json=payload, timeout=30)
        resp.raise_for_status()
        results = resp.json().get('results', [])

        # Build contracts list matching frontend expected shape
        contracts = []
        for r in results:
            contracts.append({
                'contract_id': r.get('Award ID', ''),
                'agency': r.get('Awarding Sub Agency') or r.get('Awarding Agency') or 'N/A',
                'naics': r.get('NAICS Code') or None,
                'value': r.get('Award Amount', 0) or 0,
                'date_signed': r.get('Start Date') or None,
                'description': r.get('Description') or r.get('Award ID', '')
            })

        total_value = sum(c['value'] for c in contracts)
        avg_value = total_value / len(contracts) if contracts else 0
        max_value = max((c['value'] for c in contracts), default=0)

        # Agency breakdown: {agency: total_value}
        agency_map = {}
        for c in contracts:
            ag = c['agency'] or 'Unknown'
            agency_map[ag] = agency_map.get(ag, 0) + c['value']
        agencies = sorted(
            [{'agency': k, 'value': v} for k, v in agency_map.items()],
            key=lambda x: x['value'], reverse=True
        )

        # NAICS distribution: {code: count}
        naics_map = {}
        for c in contracts:
            n = c['naics'] or 'Unknown'
            naics_map[n] = naics_map.get(n, 0) + 1
        naics_distribution = sorted(
            [{'code': k, 'count': v} for k, v in naics_map.items()],
            key=lambda x: x['count'], reverse=True
        )

        # Timeline: {month: total_value}
        timeline_map = {}
        for c in contracts:
            ds = c['date_signed']
            if ds:
                month = str(ds)[:7]
                timeline_map[month] = timeline_map.get(month, 0) + c['value']
        timeline = [{'month': k, 'value': v} for k, v in sorted(timeline_map.items())]

        # Recent count (last 12 months)
        cutoff_12mo = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
        recent_count = sum(1 for c in contracts if c['date_signed'] and str(c['date_signed']) >= cutoff_12mo)

        top_agency = agencies[0]['agency'] if agencies else None
        primary_naics = naics_distribution[0]['code'] if naics_distribution and naics_distribution[0]['code'] != 'Unknown' else None

        return jsonify({
            'contractor_name': contractor_name,
            'contracts': contracts,
            'total_contracts': len(contracts),
            'total_value': total_value,
            'avg_value': avg_value,
            'max_value': max_value,
            'agency_count': len(agency_map),
            'recent_count': recent_count,
            'top_agency': top_agency,
            'primary_naics': primary_naics,
            'agencies': agencies,
            'naics_distribution': naics_distribution,
            'timeline': timeline
        })

    except Exception as e:
        print(f"Error getting full contractor profile: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/agents/competitive/analyze', methods=['POST'])
def analyze_competitive():
    """Agent 2: Competitive Intelligence"""
    if not AGENTS_AVAILABLE:
        return jsonify({'error': 'Agents not available'}), 503

    t0 = time.time()
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

        from agent_logger import get_logger
        get_logger().log_agent_activity(2, 'Competitive Intelligence', f'Analyze: {opp.get("title", notice_id)[:80]}',
            'success' if results.get('status') == 'success' else 'error', time.time() - t0,
            input_data={'notice_id': notice_id, 'agency': agency, 'naics': naics},
            output_data={'incumbents': len(results.get('incumbents', []))})

        return jsonify(results)

    except Exception as e:
        import traceback
        traceback.print_exc()
        from agent_logger import get_logger
        get_logger().log_agent_activity(2, 'Competitive Intelligence', 'Analyze competitive landscape', 'error', time.time() - t0, error_message=str(e))
        return jsonify({'error': str(e), 'status': 'error'}), 500


@app.route('/api/agents/contacts/research', methods=['POST'])
def research_contact():
    """Contact Research Agent — researches a contact's public professional presence"""
    t0 = time.time()
    try:
        data = request.json or {}

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

        from agent_logger import get_logger
        get_logger().log_agent_activity(7, 'Contact Research', f'Research: {contact["name"][:60]}',
            'success' if results.get('status') == 'success' else 'error', time.time() - t0,
            input_data={'name': contact['name'], 'agency': contact.get('agency')},
            output_data={'confidence': results.get('confidence'), 'method': results.get('method')})

        return jsonify(results)

    except Exception as e:
        import traceback
        traceback.print_exc()
        from agent_logger import get_logger
        get_logger().log_agent_activity(7, 'Contact Research', 'Research contact', 'error', time.time() - t0, error_message=str(e))
        return jsonify({'error': str(e), 'status': 'error'}), 500


@app.route('/api/contacts/ensure-and-research', methods=['POST'])
def ensure_and_research_contact():
    """Ensure a POC exists in SQLite contacts, then research them.
    Used from opportunity modal where POCs don't yet have a contact_id."""
    try:
        data = request.json or {}
        name = data.get('name', '').strip()
        if not name:
            return jsonify({'error': 'Contact name is required'}), 400

        title = data.get('title', '').strip()
        organization = data.get('organization', '').strip()
        email = data.get('email', '').strip()

        db = get_db()

        # Check if contact already exists by name
        existing = db.execute('SELECT id, research_profile FROM contacts WHERE name = ?', (name,)).fetchone()

        if existing:
            contact_id = existing['id']
            # If already has research, return it from cache
            if existing['research_profile']:
                try:
                    profile = json.loads(existing['research_profile'])
                    db.close()
                    return jsonify({
                        'status': 'success',
                        'contact_id': contact_id,
                        'name': name,
                        'cached': True,
                        **profile
                    })
                except (json.JSONDecodeError, TypeError):
                    pass
        else:
            # Create the contact record
            cursor = db.execute(
                '''INSERT INTO contacts (name, title, organization, email, source, relationship_strength)
                   VALUES (?, ?, ?, ?, 'SAM.gov POC', 'New')''',
                (name, title, organization, email)
            )
            db.commit()
            contact_id = cursor.lastrowid
            print(f"✓ Created new contact #{contact_id}: {name}")

        db.close()

        # Run research via AgentExecutor
        contact = {
            'id': contact_id,
            'name': name,
            'title': title,
            'organization': organization,
            'agency': organization,
            'email': email,
        }

        from agent_executor import AgentExecutor
        executor = AgentExecutor()
        results = executor.run_contact_research(contact, force_refresh=False)

        # Save research profile to SQLite for future cache hits
        if results.get('status') == 'success':
            profile_data = {k: v for k, v in results.items() if k != 'status'}
            db2 = get_db()
            db2.execute(
                'UPDATE contacts SET research_profile = ? WHERE id = ?',
                (json.dumps(profile_data), contact_id)
            )
            db2.commit()
            db2.close()

        return jsonify({
            'contact_id': contact_id,
            'name': name,
            'cached': False,
            **results
        })

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


@app.route('/api/agents/stats/all', methods=['GET'])
def get_all_agent_stats():
    """Get summary stats for all agents in one call (for the dashboard)"""
    try:
        from agent_logger import get_logger
        logger = get_logger()
        days = request.args.get('days', 30, type=int)

        agent_map = {
            1: 'Opportunity Scout',
            2: 'Competitive Intelligence',
            3: 'Capability Matching',
            4: 'RFI Generator',
            5: 'Proposal Writer',
            6: 'Pricing Generator',
            7: 'Contact Research',
        }

        agents = {}
        total_runs = 0
        total_successes = 0

        for aid, aname in agent_map.items():
            stats = logger.get_agent_stats(agent_id=aid, days=days)
            agents[aid] = {**stats, 'name': aname}
            total_runs += stats['total_runs']
            total_successes += stats['successes']

        return jsonify({
            'status': 'success',
            'agents': agents,
            'totals': {
                'total_runs': total_runs,
                'successes': total_successes,
                'success_rate': round(total_successes / total_runs * 100, 1) if total_runs > 0 else 0,
            }
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

        # Auto-sync POC contacts from scout data (once per file)
        scout_file_path = str(scout_files[0])
        if scout_file_path not in _poc_synced_files:
            try:
                poc_stats = extract_and_store_poc_contacts(opportunities)
                _poc_synced_files.add(scout_file_path)
                print(f"POC sync: {poc_stats['created']} created, {poc_stats['updated']} updated, {poc_stats['linked']} linked, {poc_stats['resources']} resources")
            except Exception as e:
                print(f"Warning: POC extraction failed: {e}")

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
                    'reasoning': 'Not yet scored',
                    'point_of_contact': opp.get('pointOfContact', []),
                    'resource_links': opp.get('resourceLinks') or []
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
                'reasoning': score['reasoning'],
                'point_of_contact': opp.get('pointOfContact', []),
                'resource_links': opp.get('resourceLinks') or []
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
    """Trigger scout to run — fetches SAM.gov opportunities, scores them,
    and collects FPDS contract data."""
    if not AGENTS_AVAILABLE:
        return jsonify({'error': 'Scout not available'}), 503

    t0 = time.time()
    try:
        data = request.get_json() or {}
        days = data.get('days', 7)

        scout = OpportunityScout()
        results = scout.run_daily_scout(days_back=days, save_report=True)
        scout.close()

        # Also sync POC contacts to SQLite
        poc_stats = {'created': 0, 'updated': 0, 'linked': 0}
        try:
            scout_files = sorted(Path('knowledge_graph').glob('scout_data_*.json'), reverse=True)
            if scout_files:
                with open(scout_files[0]) as f:
                    scout_data = json.load(f)
                poc_stats = extract_and_store_poc_contacts(scout_data.get('opportunities', []))
        except Exception as e:
            print(f"POC SQLite sync warning: {e}")

        fpds = results.get('fpds_contracts', {})
        db_contacts = results.get('db_contacts', results.get('neo4j_contacts', {}))

        from agent_logger import get_logger
        get_logger().log_agent_activity(1, 'Opportunity Scout',
            f'Scout run: {days}d back, {results.get("total", 0)} found, {results.get("scored", 0)} scored',
            'success', time.time() - t0,
            input_data={'days_back': days},
            output_data={
                'total': results.get('total', 0),
                'scored': results.get('scored', 0),
                'high_priority': results.get('high_priority', 0),
                'medium_priority': results.get('medium_priority', 0),
                'contacts_created': poc_stats.get('created', 0),
            })

        return jsonify({
            'status': 'success',
            'message': f'Scout completed for last {days} days',
            'opportunities_found': results.get('total', 0),
            'opportunities_scored': results.get('scored', 0),
            'high_priority': results.get('high_priority', 0),
            'medium_priority': results.get('medium_priority', 0),
            'fpds_contracts_fetched': fpds.get('contracts_fetched', 0),
            'fpds_contracts_stored': fpds.get('contracts_stored', 0),
            'opportunities_synced': results.get('db_opportunities', results.get('neo4j_opportunities', 0)),
            'contacts_synced': db_contacts.get('people', 0),
            'sqlite_contacts_created': poc_stats.get('created', 0),
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        from agent_logger import get_logger
        get_logger().log_agent_activity(1, 'Opportunity Scout', 'Scout run', 'error', time.time() - t0, error_message=str(e))
        return jsonify({'error': str(e)}), 500


@app.route('/api/scout/sync-contacts', methods=['POST'])
def sync_scout_contacts():
    """Force sync of POC contacts from scout data into contacts DB"""
    try:
        scout_files = list(Path('knowledge_graph').glob('scout_data_*.json'))
        if not scout_files:
            scout_files = list(Path('.').glob('scout_data_*.json'))
        scout_files = sorted(scout_files, reverse=True)

        if not scout_files:
            return jsonify({'error': 'No scout data available'}), 404

        with open(scout_files[0]) as f:
            data = json.load(f)

        opportunities = data.get('opportunities', [])
        stats = extract_and_store_poc_contacts(opportunities)

        return jsonify({
            'status': 'success',
            'file': str(scout_files[0]),
            'total_opportunities': len(opportunities),
            'contacts_created': stats['created'],
            'contacts_updated': stats['updated'],
            'links_created': stats['linked'],
            'resources_stored': stats['resources']
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/opportunities/<notice_id>/contacts', methods=['GET'])
def get_opportunity_contacts(notice_id):
    """Get contacts linked to a specific opportunity"""
    db = get_db()
    contacts = db.execute('''
        SELECT c.*, oc.role as opp_role, oc.poc_type
        FROM contacts c
        JOIN opportunity_contacts oc ON c.id = oc.contact_id
        WHERE oc.opportunity_id = ?
        ORDER BY oc.poc_type ASC
    ''', (notice_id,)).fetchall()
    return jsonify({
        'contacts': [dict(c) for c in contacts],
        'total': len(contacts)
    })


@app.route('/api/opportunities/<notice_id>/resources', methods=['GET'])
def get_opportunity_resources(notice_id):
    """Get resource links for a specific opportunity"""
    db = get_db()
    resources = db.execute('''
        SELECT * FROM opportunity_resources
        WHERE opportunity_id = ?
        ORDER BY created_at ASC
    ''', (notice_id,)).fetchall()
    return jsonify({
        'resources': [dict(r) for r in resources],
        'total': len(resources)
    })


# ============================================================================
# KANBAN STATE API
# ============================================================================

@app.route('/api/kanban/state', methods=['GET'])
def get_kanban_state():
    """Return all saved kanban stages as {opportunity_id: stage}"""
    db = get_db()
    rows = db.execute('SELECT opportunity_id, stage FROM opportunity_stage').fetchall()
    state = {row['opportunity_id']: row['stage'] for row in rows}
    return jsonify(state)


@app.route('/api/kanban/state', methods=['POST'])
def save_kanban_state():
    """Upsert a single opportunity's kanban stage"""
    data = request.get_json()
    opp_id = data.get('opportunity_id')
    stage = data.get('stage')

    if not opp_id or not stage:
        return jsonify({'error': 'opportunity_id and stage are required'}), 400

    valid_stages = {'new', 'analyzing', 'rfi', 'proposal', 'pricing', 'skipped'}
    if stage not in valid_stages:
        return jsonify({'error': f'Invalid stage. Must be one of: {", ".join(sorted(valid_stages))}'}), 400

    db = get_db()
    db.execute('''
        INSERT INTO opportunity_stage (opportunity_id, stage, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(opportunity_id) DO UPDATE SET stage = excluded.stage, updated_at = CURRENT_TIMESTAMP
    ''', (opp_id, stage))
    db.commit()
    return jsonify({'status': 'ok', 'opportunity_id': opp_id, 'stage': stage})


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
        try:
            kg = KnowledgeGraphClient()
            graph_stats = kg.get_network_statistics()
            overview['contacts']['graph_people'] = graph_stats.get('total_people', 0)
            overview['contacts']['decision_makers'] = graph_stats.get('decision_makers', 0)
        except Exception:
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
        try:
            kg = KnowledgeGraphClient()
            overview['intel'] = {
                'contracts_tracked': kg.get_contract_count()
            }
        except Exception:
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
    ensure_schema_updates()
    
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
