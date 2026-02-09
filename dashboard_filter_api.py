"""
Dashboard API Endpoints for Local Filtering
Add these to team_dashboard_app.py
"""

# Add this import at the top
from bulk_fetch_and_filter import LocalOpportunityFilter

# Add these routes to team_dashboard_app.py

@app.route('/api/filter/options')
def get_filter_options():
    """Get available filter options from local database"""
    try:
        filter_engine = LocalOpportunityFilter()
        stats = filter_engine.get_filter_stats()
        filter_engine.close()
        
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error getting filter options: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/opportunities/filter', methods=['POST'])
def filter_opportunities_local():
    """
    Filter opportunities from local database - instant results!
    
    POST body example:
    {
        "naics_codes": ["541512", "541519"],
        "agencies": ["Department of Defense"],
        "opportunity_types": ["Solicitation"],
        "min_value": 100000,
        "max_value": 5000000,
        "keywords": ["cloud", "cybersecurity"],
        "set_asides": ["Small Business"]
    }
    """
    try:
        filters = request.json
        
        filter_engine = LocalOpportunityFilter()
        results = filter_engine.filter_opportunities(
            naics_codes=filters.get('naics_codes'),
            agencies=filters.get('agencies'),
            opportunity_types=filters.get('opportunity_types'),
            min_value=filters.get('min_value'),
            max_value=filters.get('max_value'),
            keywords=filters.get('keywords'),
            set_asides=filters.get('set_asides'),
            posted_after=filters.get('posted_after'),
            deadline_before=filters.get('deadline_before')
        )
        filter_engine.close()
        
        return jsonify({
            'count': len(results),
            'opportunities': results
        })
        
    except Exception as e:
        logger.error(f"Error filtering opportunities: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/fetch/status')
def get_fetch_status():
    """Get status of last bulk fetch"""
    try:
        conn = db.get_connection()
        c = conn.cursor()
        
        # Get last fetch info
        c.execute('''
            SELECT fetch_date, total_fetched, inserted, updated
            FROM fetch_history
            ORDER BY fetch_date DESC
            LIMIT 1
        ''')
        
        row = c.fetchone()
        
        if row:
            status = {
                'last_fetch': row[0],
                'total_fetched': row[1],
                'inserted': row[2],
                'updated': row[3]
            }
        else:
            status = {
                'last_fetch': None,
                'message': 'No bulk fetch has been run yet'
            }
        
        # Get total in database
        c.execute('SELECT COUNT(*) FROM raw_opportunities')
        total = c.fetchone()[0]
        status['total_in_database'] = total
        
        conn.close()
        
        return jsonify(status)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/fetch/run', methods=['POST'])
def trigger_bulk_fetch():
    """Trigger a bulk fetch manually from dashboard"""
    import subprocess
    
    try:
        # Run bulk fetch script in background
        subprocess.Popen(['python', 'bulk_fetch_and_filter.py'])
        
        return jsonify({
            'status': 'started',
            'message': 'Bulk fetch started in background. Check /api/fetch/status for progress.'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
