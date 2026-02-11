#!/usr/bin/env python3
"""
Competitive Intelligence API Routes
Queries Neo4j for contract data to power the competitive intelligence dashboard.

Graph structure:
  - (Contractor)-[:HAS_CONTRACT]->(Agency)  with {value, count, contract_name, award_date}
  - (Contract) nodes with {name, agency, value, naics, award_date, title, source}
  - (Opportunity) nodes from scout
"""
from flask import Blueprint, jsonify, request
from neo4j import GraphDatabase
import os
from dotenv import load_dotenv

load_dotenv()

comp_intel_bp = Blueprint('competitive_intel', __name__)

# Neo4j connection
NEO4J_URI = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD', 'password')
NEO4J_DATABASE = os.getenv('NEO4J_DATABASE', 'neo4j')


def get_neo4j_driver():
    """Get Neo4j driver instance"""
    return GraphDatabase.driver(NEO4J_URI, auth=("neo4j", NEO4J_PASSWORD))


@comp_intel_bp.route('/api/competitive/stats')
def get_stats():
    """Get high-level stats: total contracts, contractors, agencies, value"""
    driver = get_neo4j_driver()
    try:
        with driver.session(database=NEO4J_DATABASE) as session:
            result = session.run("""
                MATCH (c:Contract)
                WITH count(c) as contract_count, sum(toFloat(c.value)) as total_value
                OPTIONAL MATCH (ct:Contractor)
                WITH contract_count, total_value, count(ct) as contractor_count
                OPTIONAL MATCH (a:Agency)
                RETURN contract_count, contractor_count, count(a) as agency_count, total_value
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
    """Get top contractors ranked by contract value using Contractor-HAS_CONTRACT->Agency"""
    driver = get_neo4j_driver()
    try:
        with driver.session(database=NEO4J_DATABASE) as session:
            result = session.run("""
                MATCH (ct:Contractor)-[r:HAS_CONTRACT]->(a:Agency)
                WITH ct.name as contractor,
                     count(r) as contract_count,
                     sum(toFloat(COALESCE(r.value, 0))) as total_value,
                     collect(DISTINCT a.name) as agencies
                WHERE contractor IS NOT NULL
                RETURN contractor, contract_count, total_value,
                       total_value / contract_count as avg_value,
                       agencies[0] as top_agency,
                       agencies as agency_list
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
                    'naics_codes': []
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
    driver = get_neo4j_driver()
    try:
        with driver.session(database=NEO4J_DATABASE) as session:
            # Get agencies from Agency nodes
            agencies_result = session.run("""
                MATCH (a:Agency)
                WHERE a.name IS NOT NULL AND a.name <> ''
                RETURN DISTINCT a.name as agency
                ORDER BY agency
                LIMIT 100
            """)
            agencies = [r['agency'] for r in agencies_result]

            # Get NAICS codes from Contract nodes
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
    """Get detailed analysis for a specific contractor"""
    driver = get_neo4j_driver()
    try:
        with driver.session(database=NEO4J_DATABASE) as session:
            # Get contracts from HAS_CONTRACT relationships
            result = session.run("""
                MATCH (ct:Contractor {name: $name})-[r:HAS_CONTRACT]->(a:Agency)
                RETURN a.name as agency,
                       r.contract_name as contract_name,
                       toFloat(COALESCE(r.value, 0)) as value,
                       r.award_date as date_signed
                ORDER BY r.award_date DESC
            """, name=contractor_name)

            contracts = []
            for r in result:
                contracts.append({
                    'contract_id': r['contract_name'],
                    'agency': r['agency'],
                    'naics': None,
                    'psc': None,
                    'value': float(r['value'] or 0),
                    'date_signed': r['date_signed'],
                    'description': r['contract_name'],
                    'place': None
                })

            # Also check Contract nodes for richer data
            result2 = session.run("""
                MATCH (c:Contract)
                WHERE c.name STARTS WITH $prefix
                RETURN c.agency as agency, c.naics as naics,
                       toFloat(c.value) as value, c.award_date as date_signed,
                       c.title as description, c.name as contract_name
                ORDER BY c.award_date DESC
            """, prefix=contractor_name + '|')

            for r in result2:
                contracts.append({
                    'contract_id': r['contract_name'],
                    'agency': r['agency'],
                    'naics': r['naics'],
                    'psc': None,
                    'value': float(r['value'] or 0),
                    'date_signed': r['date_signed'],
                    'description': r['description'],
                    'place': None
                })

            if not contracts:
                return jsonify({'error': 'Contractor not found'}), 404

            # Deduplicate by contract_id
            seen = set()
            unique_contracts = []
            for c in contracts:
                key = c['contract_id']
                if key not in seen:
                    seen.add(key)
                    unique_contracts.append(c)
            contracts = unique_contracts

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

            # Timeline
            timeline = {}
            for c in contracts:
                if c['date_signed']:
                    month = str(c['date_signed'])[:7]
                    timeline[month] = timeline.get(month, 0) + c['value']
            timeline_list = [
                {'month': k, 'value': v}
                for k, v in sorted(timeline.items())
            ]

            from datetime import datetime, timedelta
            cutoff = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
            recent_count = sum(1 for c in contracts if c['date_signed'] and str(c['date_signed']) >= cutoff)

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
def get_partners():
    """Teaming partners placeholder — main logic in /api/competitive/teaming-partners"""
    driver = get_neo4j_driver()
    try:
        with driver.session(database=NEO4J_DATABASE) as session:
            # Recommended partners — contractors with diverse agency experience
            result = session.run("""
                MATCH (ct:Contractor)-[r:HAS_CONTRACT]->(a:Agency)
                WITH ct.name as contractor,
                     count(r) as contract_count,
                     sum(toFloat(COALESCE(r.value, 0))) as total_value,
                     count(DISTINCT a.name) as agency_diversity,
                     collect(DISTINCT a.name)[0..3] as top_agencies
                WHERE contractor IS NOT NULL
                  AND contract_count >= 2
                  AND contract_count <= 50
                RETURN contractor, contract_count, total_value,
                       agency_diversity, top_agencies,
                       (agency_diversity * 2 + contract_count) as partner_score
                ORDER BY partner_score DESC
                LIMIT 20
            """)

            recommended = []
            for record in result:
                recommended.append({
                    'contractor': record['contractor'],
                    'contract_count': record['contract_count'],
                    'total_value': float(record['total_value'] or 0),
                    'agency_diversity': record['agency_diversity'],
                    'top_agencies': record['top_agencies'] or []
                })

            return jsonify({
                'naics_partners': [],
                'agency_partners': [],
                'recommended': recommended
            })

    except Exception as e:
        print(f"Error getting partners: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        driver.close()


@comp_intel_bp.route('/api/competitive/trends')
def get_market_trends():
    """Get market trends: timeline, top agencies"""
    driver = get_neo4j_driver()
    try:
        with driver.session(database=NEO4J_DATABASE) as session:
            # Timeline: contracts by month using award_date
            timeline_result = session.run("""
                MATCH (c:Contract)
                WHERE c.award_date IS NOT NULL AND c.award_date <> ''
                WITH substring(c.award_date, 0, 7) as month,
                     count(c) as contracts,
                     sum(toFloat(c.value)) as value
                WHERE month =~ '\\d{4}-\\d{2}'
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
                     sum(toFloat(c.value)) as total_value
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
