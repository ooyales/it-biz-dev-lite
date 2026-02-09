#!/usr/bin/env python3
"""
Competitive Intelligence API Routes
Queries Neo4j for contract data to power the competitive intelligence dashboard
"""
from flask import Blueprint, jsonify, request
from neo4j import GraphDatabase
import os
from dotenv import load_dotenv
from collections import defaultdict

load_dotenv()

comp_intel_bp = Blueprint('competitive_intel', __name__)

# Neo4j connection
NEO4J_URI = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD', 'password')
NEO4J_DATABASE = os.getenv('NEO4J_DATABASE', 'contactsgraphdb')


def get_neo4j_driver():
    """Get Neo4j driver instance"""
    return GraphDatabase.driver(NEO4J_URI, auth=("neo4j", NEO4J_PASSWORD))


@comp_intel_bp.route('/api/competitive/stats')
def get_stats():
    """Get high-level stats: total contracts, contractors, agencies, value"""
    try:
        driver = get_neo4j_driver()
        
        with driver.session(database=NEO4J_DATABASE) as session:
            result = session.run("""
                MATCH (c:Contract)
                WITH count(c) as contract_count,
                     sum(c.value) as total_value
                MATCH (org:Organization)
                WITH contract_count, total_value,
                     count(DISTINCT org) as contractor_count
                MATCH (c2:Contract)
                WITH contract_count, total_value, contractor_count,
                     count(DISTINCT c2.agency) as agency_count
                RETURN contract_count, total_value, contractor_count, agency_count
            """)
            
            record = result.single()
            if record:
                return jsonify({
                    'contract_count': record['contract_count'] or 0,
                    'total_value': float(record['total_value'] or 0),
                    'contractor_count': record['contractor_count'] or 0,
                    'agency_count': record['agency_count'] or 0
                })
        
        return jsonify({'error': 'No data found'}), 404
        
    except Exception as e:
        print(f"Error getting stats: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        driver.close()


@comp_intel_bp.route('/api/competitive/incumbents')
def get_incumbents():
    """
    Get top contractors ranked by contract count and total value.
    Returns contractor name, contract count, total value, avg value,
    top agency, and NAICS codes they work in.
    """
    try:
        driver = get_neo4j_driver()
        
        with driver.session(database=NEO4J_DATABASE) as session:
            result = session.run("""
                MATCH (c:Contract)-[:AWARDED_TO]->(org:Organization)
                WHERE org.name IS NOT NULL AND org.name <> ''
                WITH org.name as contractor,
                     count(c) as contract_count,
                     sum(c.value) as total_value,
                     avg(c.value) as avg_value,
                     collect(DISTINCT c.agency) as agencies,
                     collect(DISTINCT c.naics) as naics_codes
                WHERE contract_count > 0
                WITH contractor, contract_count, total_value, avg_value,
                     [a IN agencies WHERE a IS NOT NULL AND a <> ''][0] as top_agency,
                     [n IN naics_codes WHERE n IS NOT NULL AND n <> ''] as naics_list
                RETURN contractor, contract_count, total_value, avg_value,
                       top_agency, naics_list as naics_codes
                ORDER BY total_value DESC
                LIMIT 100
            """)
            
            incumbents = []
            for record in result:
                incumbents.append({
                    'contractor': record['contractor'],
                    'contract_count': record['contract_count'],
                    'total_value': float(record['total_value'] or 0),
                    'avg_value': float(record['avg_value'] or 0),
                    'top_agency': record['top_agency'],
                    'naics_codes': record['naics_codes']
                })
            
            return jsonify({'incumbents': incumbents})
        
    except Exception as e:
        print(f"Error getting incumbents: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
    finally:
        driver.close()


@comp_intel_bp.route('/api/competitive/filter-options')
def get_filter_options():
    """Get distinct agencies and NAICS codes for filter dropdowns"""
    try:
        driver = get_neo4j_driver()
        
        with driver.session(database=NEO4J_DATABASE) as session:
            # Get agencies
            agencies_result = session.run("""
                MATCH (c:Contract)
                WHERE c.agency IS NOT NULL AND c.agency <> ''
                RETURN DISTINCT c.agency as agency
                ORDER BY agency
                LIMIT 100
            """)
            agencies = [r['agency'] for r in agencies_result]
            
            # Get NAICS codes
            naics_result = session.run("""
                MATCH (c:Contract)
                WHERE c.naics IS NOT NULL AND c.naics <> ''
                RETURN DISTINCT c.naics as naics
                ORDER BY naics
            """)
            naics_codes = [r['naics'] for r in naics_result]
            
            return jsonify({
                'agencies': agencies,
                'naics_codes': naics_codes
            })
        
    except Exception as e:
        print(f"Error getting filter options: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        driver.close()


@comp_intel_bp.route('/api/competitive/contractor/<contractor_name>')
def get_contractor_detail(contractor_name):
    """
    Get detailed analysis for a specific contractor:
    - All contracts with details
    - Timeline of awards (monthly aggregation)
    - Agency breakdown (which agencies, how much)
    - NAICS distribution
    - Performance stats (avg value, max value, etc.)
    """
    try:
        driver = get_neo4j_driver()
        
        with driver.session(database=NEO4J_DATABASE) as session:
            # Get all contracts for this contractor
            contracts_result = session.run("""
                MATCH (c:Contract)-[:AWARDED_TO]->(org:Organization)
                WHERE org.name = $contractor_name
                RETURN c.contract_id as contract_id,
                       c.agency as agency,
                       c.naics as naics,
                       c.psc as psc,
                       c.value as value,
                       c.date_signed as date_signed,
                       c.description as description,
                       c.place_of_performance as place
                ORDER BY c.date_signed DESC
            """, contractor_name=contractor_name)
            
            contracts = []
            for r in contracts_result:
                contracts.append({
                    'contract_id': r['contract_id'],
                    'agency': r['agency'],
                    'naics': r['naics'],
                    'psc': r['psc'],
                    'value': float(r['value'] or 0),
                    'date_signed': r['date_signed'],
                    'description': r['description'],
                    'place': r['place']
                })
            
            if not contracts:
                return jsonify({'error': 'Contractor not found'}), 404
            
            # Calculate stats
            total_value = sum(c['value'] for c in contracts)
            avg_value = total_value / len(contracts) if contracts else 0
            max_value = max((c['value'] for c in contracts), default=0)
            
            # Agency breakdown
            agencies = {}
            for c in contracts:
                agency = c['agency'] or 'Unknown'
                agencies[agency] = agencies.get(agency, 0) + c['value']
            agency_list = [
                {'agency': k, 'value': v}
                for k, v in sorted(agencies.items(), key=lambda x: x[1], reverse=True)
            ]
            
            # NAICS distribution
            naics_counts = {}
            for c in contracts:
                naics = c['naics'] or 'Unknown'
                naics_counts[naics] = naics_counts.get(naics, 0) + 1
            naics_list = [
                {'code': k, 'count': v}
                for k, v in sorted(naics_counts.items(), key=lambda x: x[1], reverse=True)
            ]
            
            # Timeline (monthly aggregation)
            timeline = {}
            for c in contracts:
                if c['date_signed']:
                    month = c['date_signed'][:7]  # YYYY-MM
                    timeline[month] = timeline.get(month, 0) + c['value']
            timeline_list = [
                {'month': k, 'value': v}
                for k, v in sorted(timeline.items())
            ]
            
            # Recent contracts (last 12 months)
            from datetime import datetime, timedelta
            cutoff = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
            recent_count = sum(1 for c in contracts if c['date_signed'] and c['date_signed'] >= cutoff)
            
            return jsonify({
                'contractor_name': contractor_name,
                'contracts': contracts,
                'total_contracts': len(contracts),
                'total_value': total_value,
                'avg_value': avg_value,
                'max_value': max_value,
                'agency_count': len(agencies),
                'recent_count': recent_count,
                'top_agency': agency_list[0]['agency'] if agency_list else None,
                'primary_naics': naics_list[0]['code'] if naics_list else None,
                'agencies': agency_list,
                'naics_distribution': naics_list,
                'timeline': timeline_list
            })
        
    except Exception as e:
        print(f"Error getting contractor detail: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
    finally:
        driver.close()


@comp_intel_bp.route('/api/competitive/partners')
def get_teaming_partners():
    """
    Identify potential teaming partners based on:
    - Working in similar NAICS codes
    - Awards from same agencies
    - Complementary (not directly competitive) capabilities
    """
    try:
        # TODO: Implement teaming partner algorithm
        # For now, return placeholder
        return jsonify({
            'naics_partners': [],
            'agency_partners': [],
            'recommended': []
        })
        
    except Exception as e:
        print(f"Error getting partners: {e}")
        return jsonify({'error': str(e)}), 500


@comp_intel_bp.route('/api/competitive/trends')
def get_market_trends():
    """
    Get market trends data:
    - Contract awards timeline (monthly aggregation)
    - Market share by contractor
    - Top agencies by value
    - NAICS distribution
    """
    try:
        driver = get_neo4j_driver()
        
        with driver.session(database=NEO4J_DATABASE) as session:
            # Timeline: contracts by month
            timeline_result = session.run("""
                MATCH (c:Contract)
                WHERE c.date_signed IS NOT NULL AND c.date_signed <> ''
                WITH substring(c.date_signed, 0, 7) as month,
                     count(c) as contracts,
                     sum(c.value) as value
                RETURN month, contracts, value
                ORDER BY month DESC
                LIMIT 24
            """)
            timeline = [
                {
                    'month': r['month'],
                    'contracts': r['contracts'],
                    'value': float(r['value'] or 0)
                }
                for r in timeline_result
            ]
            
            # Top agencies by value
            agencies_result = session.run("""
                MATCH (c:Contract)
                WHERE c.agency IS NOT NULL
                WITH c.agency as agency,
                     count(c) as contracts,
                     sum(c.value) as total_value
                RETURN agency, contracts, total_value
                ORDER BY total_value DESC
                LIMIT 10
            """)
            agencies = [
                {
                    'agency': r['agency'],
                    'contracts': r['contracts'],
                    'value': float(r['total_value'] or 0)
                }
                for r in agencies_result
            ]
            
            return jsonify({
                'timeline': timeline,
                'top_agencies': agencies
            })
        
    except Exception as e:
        print(f"Error getting trends: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        driver.close()
