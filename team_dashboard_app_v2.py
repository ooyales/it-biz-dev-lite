#!/usr/bin/env python3
"""
Federal Contracting Team Dashboard - Flask Backend
Provides API endpoints for team collaboration on opportunity management
"""

from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_cors import CORS
import json
import yaml
import os
from datetime import datetime, timedelta
from pathlib import Path
import sqlite3
from typing import Dict, List, Any
import subprocess
import threading

app = Flask(__name__, 
            static_folder='static',
            template_folder='templates')
CORS(app)

# Configuration
CONFIG_PATH = "config.yaml"
DB_PATH = "data/team_dashboard.db"


class DatabaseManager:
    """Manages team collaboration database"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize database schema"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Opportunities table
        c.execute('''
            CREATE TABLE IF NOT EXISTS opportunities (
                notice_id TEXT PRIMARY KEY,
                title TEXT,
                type TEXT,
                naics_code TEXT,
                posted_date TEXT,
                deadline TEXT,
                fit_score REAL,
                win_probability REAL,
                recommendation TEXT,
                status TEXT DEFAULT 'new',
                assigned_to TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Team decisions table
        c.execute('''
            CREATE TABLE IF NOT EXISTS decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                notice_id TEXT,
                decision TEXT,
                rationale TEXT,
                decided_by TEXT,
                decided_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (notice_id) REFERENCES opportunities(notice_id)
            )
        ''')
        
        # Staff updates table
        c.execute('''
            CREATE TABLE IF NOT EXISTS staff_updates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                staff_id TEXT,
                update_type TEXT,
                update_data TEXT,
                updated_by TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # System logs table
        c.execute('''
            CREATE TABLE IF NOT EXISTS system_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                log_type TEXT,
                message TEXT,
                details TEXT,
                logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def save_opportunity(self, opp_data: Dict):
        """Save or update opportunity"""
        conn = self.get_connection()
        c = conn.cursor()
        
        c.execute('''
            INSERT OR REPLACE INTO opportunities 
            (notice_id, title, type, naics_code, posted_date, deadline, 
             fit_score, win_probability, recommendation, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (
            opp_data.get('notice_id'),
            opp_data.get('title'),
            opp_data.get('type'),
            opp_data.get('naics_code'),
            opp_data.get('posted_date'),
            opp_data.get('deadline'),
            opp_data.get('fit_score'),
            opp_data.get('win_probability'),
            opp_data.get('recommendation')
        ))
        
        conn.commit()
        conn.close()
    
    def get_all_opportunities(self, status_filter: str = None) -> List[Dict]:
        """Get all opportunities with optional status filter"""
        conn = self.get_connection()
        c = conn.cursor()
        
        if status_filter:
            c.execute('SELECT * FROM opportunities WHERE status = ? ORDER BY fit_score DESC', (status_filter,))
        else:
            c.execute('SELECT * FROM opportunities ORDER BY fit_score DESC')
        
        rows = c.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def update_opportunity_status(self, notice_id: str, status: str, assigned_to: str = None):
        """Update opportunity status"""
        conn = self.get_connection()
        c = conn.cursor()
        
        if assigned_to:
            c.execute('''
                UPDATE opportunities 
                SET status = ?, assigned_to = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE notice_id = ?
            ''', (status, assigned_to, notice_id))
        else:
            c.execute('''
                UPDATE opportunities 
                SET status = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE notice_id = ?
            ''', (status, notice_id))
        
        conn.commit()
        conn.close()
    
    def add_decision(self, notice_id: str, decision: str, rationale: str, decided_by: str):
        """Record team decision"""
        conn = self.get_connection()
        c = conn.cursor()
        
        c.execute('''
            INSERT INTO decisions (notice_id, decision, rationale, decided_by)
            VALUES (?, ?, ?, ?)
        ''', (notice_id, decision, rationale, decided_by))
        
        conn.commit()
        conn.close()
    
    def log_system_event(self, log_type: str, message: str, details: str = None):
        """Log system event"""
        conn = self.get_connection()
        c = conn.cursor()
        
        c.execute('''
            INSERT INTO system_logs (log_type, message, details)
            VALUES (?, ?, ?)
        ''', (log_type, message, details))
        
        conn.commit()
        conn.close()


# Initialize database
db = DatabaseManager(DB_PATH)


# API Routes

@app.route('/')
def index():
    """Serve main dashboard"""
    return render_template('dashboard.html')

@app.route('/admin')
def admin():
    """Serve admin panel"""
    return render_template('admin.html')

@app.route('/api/config', methods=['GET'])
def get_config():
    """Get current configuration"""
    try:
        with open(CONFIG_PATH, 'r') as f:
            config = yaml.safe_load(f)
        return jsonify(config)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/config', methods=['POST'])
def save_config():
    """Save configuration"""
    try:
        config = request.json
        
        with open(CONFIG_PATH, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        
        db.log_system_event('config_updated', 'Configuration updated via admin panel')
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/staff/<staff_id>', methods=['DELETE'])
def delete_staff(staff_id):
    """Delete staff member"""
    try:
        staff_path = "data/staff_database.json"
        
        with open(staff_path, 'r') as f:
            staff_data = json.load(f)
        
        # Remove staff member
        staff_data['staff_members'] = [
            s for s in staff_data['staff_members'] 
            if s.get('id') != staff_id
        ]
        
        # Save back
        with open(staff_path, 'w') as f:
            json.dump(staff_data, f, indent=2)
        
        db.log_system_event('staff_deleted', f'Deleted staff {staff_id}')
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/opportunities')
def get_opportunities():
    """Get all opportunities"""
    status = request.args.get('status')
    opportunities = db.get_all_opportunities(status)
    return jsonify(opportunities)

@app.route('/api/opportunities/<notice_id>')
def get_opportunity(notice_id):
    """Get specific opportunity details"""
    # Load from analysis files
    analysis_path = f"data/analysis/{notice_id}_*_analysis.json"
    
    import glob
    files = glob.glob(analysis_path)
    
    if files:
        with open(files[0], 'r') as f:
            data = json.load(f)
        return jsonify(data)
    else:
        return jsonify({'error': 'Not found'}), 404

@app.route('/api/opportunities/<notice_id>/status', methods=['POST'])
def update_status(notice_id):
    """Update opportunity status"""
    data = request.json
    status = data.get('status')
    assigned_to = data.get('assigned_to')
    
    db.update_opportunity_status(notice_id, status, assigned_to)
    db.log_system_event('status_update', f'Updated {notice_id} to {status}')
    
    return jsonify({'success': True})

@app.route('/api/opportunities/<notice_id>/decision', methods=['POST'])
def make_decision(notice_id):
    """Record team decision"""
    data = request.json
    
    db.add_decision(
        notice_id,
        data.get('decision'),
        data.get('rationale'),
        data.get('decided_by')
    )
    
    # Update status based on decision
    if data.get('decision') == 'pursue':
        db.update_opportunity_status(notice_id, 'pursuing')
    elif data.get('decision') == 'pass':
        db.update_opportunity_status(notice_id, 'passed')
    
    db.log_system_event('decision_made', f'Decision on {notice_id}: {data.get("decision")}')
    
    return jsonify({'success': True})

@app.route('/api/staff')
def get_staff():
    """Get staff database"""
    staff_path = "data/staff_database.json"
    
    if os.path.exists(staff_path):
        with open(staff_path, 'r') as f:
            data = json.load(f)
        return jsonify(data.get('staff_members', []))
    else:
        return jsonify([])

@app.route('/api/staff/<staff_id>', methods=['PUT'])
def update_staff(staff_id):
    """Update staff member"""
    data = request.json
    
    # Load current staff database
    staff_path = "data/staff_database.json"
    with open(staff_path, 'r') as f:
        staff_data = json.load(f)
    
    # Update the specific staff member
    for i, member in enumerate(staff_data['staff_members']):
        if member.get('id') == staff_id:
            staff_data['staff_members'][i] = data
            break
    
    # Save back
    with open(staff_path, 'w') as f:
        json.dump(staff_data, f, indent=2)
    
    db.log_system_event('staff_update', f'Updated staff {staff_id}', json.dumps(data))
    
    return jsonify({'success': True})

@app.route('/api/dashboard/stats')
def get_dashboard_stats():
    """Get dashboard statistics"""
    opportunities = db.get_all_opportunities()
    
    # Calculate stats
    total = len(opportunities)
    high_priority = len([o for o in opportunities if o['fit_score'] and o['fit_score'] >= 7])
    pursuing = len([o for o in opportunities if o['status'] == 'pursuing'])
    
    # Upcoming deadlines (within 7 days)
    upcoming = []
    today = datetime.now()
    for opp in opportunities:
        if opp.get('deadline'):
            try:
                deadline = datetime.strptime(opp['deadline'], '%Y-%m-%d')
                days_until = (deadline - today).days
                if 0 <= days_until <= 7:
                    upcoming.append({
                        'notice_id': opp['notice_id'],
                        'title': opp['title'],
                        'days_until': days_until
                    })
            except:
                pass
    
    return jsonify({
        'total_opportunities': total,
        'high_priority': high_priority,
        'pursuing': pursuing,
        'upcoming_deadlines': upcoming
    })

@app.route('/api/dashboard/market-trends')
def get_market_trends():
    """Get market intelligence trends"""
    # Load recent analysis files
    analysis_dir = Path("data/analysis")
    
    trends = {
        'market_growth': [],
        'pricing_trends': [],
        'incumbents': {}
    }
    
    for file in analysis_dir.glob("*_analysis.json"):
        with open(file, 'r') as f:
            data = json.load(f)
            
            # Extract market trends
            comp_intel = data.get('competitive_intelligence', {})
            market = comp_intel.get('market_trends', {})
            
            if market.get('trend_direction'):
                trends['market_growth'].append({
                    'naics': data.get('opportunity_data', {}).get('naicsCode'),
                    'direction': market['trend_direction'],
                    'growth_rate': market.get('growth_rate_percent')
                })
            
            # Extract incumbent info
            incumbent = comp_intel.get('incumbent', {})
            if incumbent.get('contractor_name'):
                name = incumbent['contractor_name']
                trends['incumbents'][name] = trends['incumbents'].get(name, 0) + 1
    
    return jsonify(trends)

@app.route('/api/system/run-scout', methods=['POST'])
def run_scout():
    """Trigger opportunity scout"""
    
    def run_in_background():
        try:
            db.log_system_event('scout_started', 'Manual scout run triggered')
            
            # Run the main script
            result = subprocess.run(
                ['python', 'main_integrated.py'],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                db.log_system_event('scout_completed', 'Scout run completed successfully')
                # Import new opportunities into database
                import_new_opportunities()
            else:
                db.log_system_event('scout_failed', 'Scout run failed', result.stderr)
        
        except Exception as e:
            db.log_system_event('scout_error', f'Error running scout: {str(e)}')
    
    # Run in background thread
    thread = threading.Thread(target=run_in_background)
    thread.start()
    
    return jsonify({'success': True, 'message': 'Scout run started in background'})

@app.route('/api/system/logs')
def get_system_logs():
    """Get recent system logs"""
    conn = db.get_connection()
    c = conn.cursor()
    
    c.execute('''
        SELECT * FROM system_logs 
        ORDER BY logged_at DESC 
        LIMIT 50
    ''')
    
    rows = c.fetchall()
    conn.close()
    
    return jsonify([dict(row) for row in rows])


def import_new_opportunities():
    """Import new opportunities from analysis files into database"""
    analysis_dir = Path("data/analysis")
    
    for file in analysis_dir.glob("*_analysis.json"):
        with open(file, 'r') as f:
            data = json.load(f)
            
            opp_data = data.get('opportunity_data', {})
            analysis = data.get('analysis', {})
            comp_intel = data.get('competitive_intelligence', {})
            
            db.save_opportunity({
                'notice_id': data.get('notice_id'),
                'title': data.get('title'),
                'type': opp_data.get('type'),
                'naics_code': opp_data.get('naicsCode'),
                'posted_date': opp_data.get('postedDate'),
                'deadline': opp_data.get('responseDeadLine'),
                'fit_score': analysis.get('fit_score'),
                'win_probability': comp_intel.get('competitive_assessment', {}).get('win_probability'),
                'recommendation': analysis.get('recommendation')
            })


if __name__ == '__main__':
    # Import existing opportunities on startup
    import_new_opportunities()
    
    # Run server
    print("\n" + "="*80)
    print("Federal Contracting Team Dashboard")
    print("="*80)
    print("\nServer starting at http://localhost:5000")
    print("Press Ctrl+C to stop\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
