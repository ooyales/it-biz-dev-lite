#!/usr/bin/env python3
"""
Agent API Integration for Team Dashboard
Adds endpoints for Opportunity Scout and Competitive Intelligence

Add these routes to your team_dashboard_app.py
"""

from flask import jsonify, request
import sys
import os
import json
from datetime import datetime
from pathlib import Path

# Import agents
sys.path.append('knowledge_graph')
from opportunity_scout import OpportunityScout
from competitive_intel import CompetitiveIntelAgent

# Add these routes to your Flask app

# ============================================================================
# OPPORTUNITY SCOUT ROUTES
# ============================================================================

@app.route('/api/scout/opportunities', methods=['GET'])
def get_scout_opportunities():
    """
    Get scored opportunities from the scout
    
    Query params:
    - days: Days back to search (default: 7)
    - priority: Filter by priority (HIGH, MEDIUM, LOW)
    """
    try:
        days = request.args.get('days', 7, type=int)
        priority_filter = request.args.get('priority', None)
        
        # Check for cached scout data
        scout_files = sorted(Path('knowledge_graph').glob('scout_data_*.json'), reverse=True)
        
        if not scout_files:
            return jsonify({
                'error': 'No scout data available',
                'message': 'Run opportunity_scout.py first'
            }), 404
        
        # Load most recent scout data
        with open(scout_files[0]) as f:
            data = json.load(f)
        
        opportunities = data.get('opportunities', [])
        scores = data.get('scores', [])
        
        # Combine opportunities with scores
        scored_opps = []
        for opp, score in zip(opportunities, scores):
            if priority_filter and score['priority'] != priority_filter:
                continue
            
            scored_opps.append({
                'notice_id': opp.get('noticeId'),
                'title': opp.get('title'),
                'agency': opp.get('organizationName'),
                'posted_date': opp.get('postedDate'),
                'deadline': opp.get('responseDeadLine'),
                'setaside': opp.get('typeOfSetAside'),
                'naics': opp.get('naicsCode'),
                'score': score['total_score'],
                'win_probability': score['win_probability'],
                'priority': score['priority'],
                'recommendation': score['recommendation'],
                'contacts': score['contacts'],
                'reasoning': score['reasoning']
            })
        
        # Sort by score
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
    """Get summary statistics from latest scout run"""
    try:
        scout_files = sorted(Path('knowledge_graph').glob('scout_data_*.json'), reverse=True)
        
        if not scout_files:
            return jsonify({'error': 'No scout data available'}), 404
        
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
    """
    Trigger a scout run
    
    Body params:
    - days: Days back to search (default: 7)
    """
    try:
        data = request.get_json() or {}
        days = data.get('days', 7)
        
        # Run scout
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
# COMPETITIVE INTELLIGENCE ROUTES
# ============================================================================

@app.route('/api/intel/incumbents', methods=['GET'])
def get_incumbents():
    """
    Get incumbent contractors at an agency
    
    Query params:
    - agency: Agency name (required)
    - naics: NAICS code filter (optional)
    """
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


@app.route('/api/intel/competitors', methods=['POST'])
def analyze_competitors():
    """
    Analyze specific competitors
    
    Body params:
    - competitors: List of company names
    """
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


@app.route('/api/intel/teaming-partners', methods=['GET'])
def get_teaming_partners():
    """
    Get teaming partner recommendations
    
    Query params:
    - agency: Target agency (optional)
    - naics: NAICS code (optional)
    - min_contracts: Minimum contracts (default: 3)
    """
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
    """
    Get spending analysis for an agency
    
    Query params:
    - agency: Agency name (required)
    """
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


@app.route('/api/intel/report', methods=['POST'])
def generate_intel_report():
    """
    Generate full competitive intelligence report
    
    Body params:
    - agency: Target agency (optional)
    - naics: NAICS code (optional)
    """
    try:
        data = request.get_json() or {}
        agency = data.get('agency')
        naics = data.get('naics')
        
        agent = CompetitiveIntelAgent()
        report = agent.run_competitive_intel(agency, naics, save_report=True)
        agent.close()
        
        # Find the saved report file
        report_files = sorted(Path('knowledge_graph').glob('competitive_intel_*.txt'), reverse=True)
        report_file = str(report_files[0]) if report_files else None
        
        return jsonify({
            'status': 'success',
            'report': report,
            'report_file': report_file,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# DASHBOARD INTEGRATION ROUTES
# ============================================================================

@app.route('/api/dashboard/bd-intelligence', methods=['GET'])
def get_bd_intelligence_summary():
    """
    Get complete BD intelligence summary for dashboard
    Combines scout and intel data
    """
    try:
        # Get scout summary
        scout_files = sorted(Path('knowledge_graph').glob('scout_data_*.json'), reverse=True)
        scout_summary = None
        
        if scout_files:
            with open(scout_files[0]) as f:
                scout_data = json.load(f)
                scores = scout_data.get('scores', [])
                scout_summary = {
                    'total_opportunities': len(scores),
                    'high_priority': sum(1 for s in scores if s['priority'] == 'HIGH'),
                    'with_contacts': sum(1 for s in scores if s['contacts']['total_contacts'] > 0),
                    'last_run': scout_data.get('timestamp')
                }
        
        # Get intel summary (contracts in graph)
        from graph.graph_client import KnowledgeGraphClient
        kg = KnowledgeGraphClient()

        contract_count = kg.get_contract_count()
        intel_summary = {
            'total_contracts': contract_count,
            'total_value': 0,
            'total_agencies': 0
        }

        # Get contact network stats
        network_stats = kg.get_network_statistics()
        
        return jsonify({
            'scout': scout_summary,
            'intel': intel_summary,
            'network': network_stats,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/dashboard/recent-activity', methods=['GET'])
def get_recent_activity():
    """Get recent agent activity for dashboard feed"""
    try:
        activities = []
        
        # Check for recent scout runs
        scout_files = sorted(Path('knowledge_graph').glob('scout_report_*.txt'), reverse=True)
        for f in scout_files[:5]:
            activities.append({
                'type': 'scout',
                'title': 'Opportunity Scout Run',
                'timestamp': datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                'file': str(f)
            })
        
        # Check for recent intel reports
        intel_files = sorted(Path('knowledge_graph').glob('competitive_intel_*.txt'), reverse=True)
        for f in intel_files[:5]:
            activities.append({
                'type': 'intel',
                'title': 'Competitive Intelligence Report',
                'timestamp': datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                'file': str(f)
            })
        
        # Check for recent collections
        collection_files = sorted(Path('knowledge_graph').glob('collection_summary.json'), reverse=True)
        for f in collection_files[:5]:
            with open(f) as file:
                data = json.load(file)
                activities.append({
                    'type': 'collection',
                    'title': f"Collected {data.get('opportunities_processed', 0)} opportunities",
                    'timestamp': data.get('timestamp'),
                    'details': data
                })
        
        # Sort by timestamp
        activities.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return jsonify({
            'activities': activities[:20],
            'count': len(activities)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Add this to your main app initialization
def init_agent_routes(app):
    """Initialize agent routes - call this in your main app"""
    print("✓ Agent API routes initialized")
    print("  - Opportunity Scout endpoints")
    print("  - Competitive Intelligence endpoints")
    print("  - Dashboard integration endpoints")
