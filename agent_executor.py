#!/usr/bin/env python3
"""
Agent API Wrapper
Handles imports and execution of all 6 AI agents
"""

import sys
import os
from pathlib import Path
import json
import importlib.util

# Get the project root (parent of knowledge_graph)
project_root = Path(__file__).parent
kg_path = project_root / 'knowledge_graph'

# Add project root to path (so we can do: from knowledge_graph.graph.neo4j_client import ...)
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# CRITICAL: Manually load graph.neo4j_client and add to sys.modules
# This makes "from graph.neo4j_client import ..." work inside competitive_intel.py
neo4j_client_path = kg_path / 'graph' / 'neo4j_client.py'
if neo4j_client_path.exists():
    spec = importlib.util.spec_from_file_location("graph.neo4j_client", neo4j_client_path)
    if spec and spec.loader:
        neo4j_module = importlib.util.module_from_spec(spec)
        sys.modules['graph.neo4j_client'] = neo4j_module
        sys.modules['graph'] = type(sys)('graph')  # Create fake graph module
        try:
            spec.loader.exec_module(neo4j_module)
        except Exception as e:
            print(f"Warning: Could not load neo4j_client: {e}")


class AgentExecutor:
    """Wrapper to execute agents with proper error handling"""
    
    def __init__(self):
        self.kg_path = kg_path
        
    def run_competitive_intel(self, agency: str, naics: str):
        """Run Agent 2: Competitive Intelligence via USAspending.gov API"""
        try:
            from usaspending_intel import USAspendingIntelligence, normalize_agency_name

            print(f"🔍 Running Competitive Intel via USAspending.gov API")
            print(f"   Agency (raw): {agency}")
            print(f"   NAICS: {naics}")

            usa = USAspendingIntelligence()
            normalized_agency = normalize_agency_name(agency)
            print(f"   Agency (normalized): {normalized_agency}")

            # 1. Get incumbents (top contractors at this agency+NAICS)
            incumbents = []
            if agency or naics:
                print(f"→ Identifying incumbents...")
                incumbents = usa.get_incumbents_at_agency(agency, naics, limit=10)
                print(f"  ✓ Found {len(incumbents)} incumbents")

            # 2. Get teaming partners (smaller companies in same NAICS)
            teaming_partners_raw = []
            if naics:
                print(f"→ Finding teaming partners for NAICS {naics}...")
                teaming_partners_raw = usa.find_teaming_partners(
                    naics_code=str(naics),
                    small_business_only=False,
                    min_revenue=500_000,
                    max_revenue=30_000_000
                )
                print(f"  ✓ Found {len(teaming_partners_raw)} teaming candidates")

            # Format teaming partners to match frontend expectations
            teaming_partners = []
            for p in teaming_partners_raw[:5]:
                tv = p.get('total_value', 0)
                teaming_partners.append({
                    'company': p['name'],
                    'capabilities': [f'NAICS {naics}'],
                    'certifications': [],
                    'relevance_score': min(99, max(50, int(70 + (p.get('award_count', 0) * 2)))),
                    'total_value': f"${tv/1_000_000:.1f}M" if tv >= 1_000_000 else f"${tv:,.0f}",
                    'award_count': p.get('award_count', 0)
                })

            # 3. Get market trends
            market_analysis = {}
            if naics:
                print(f"→ Analyzing market trends...")
                trends = usa.get_market_trends(str(naics), normalized_agency, years=3)
                if 'error' not in trends and 'message' not in trends:
                    total = trends.get('total_spending', 0)
                    avg_annual = trends.get('average_annual_spending', 0)
                    num_competitors = len(incumbents)
                    trend_dir = trends.get('trend_direction', 'stable')
                    growth = trends.get('growth_rate_percent', 0)

                    trend_label = 'Growing' if trend_dir == 'increasing' else \
                                  'Declining' if trend_dir == 'decreasing' else 'Stable'

                    competition = 'High' if num_competitors >= 8 else \
                                  'Moderate' if num_competitors >= 4 else 'Low'

                    market_analysis = {
                        'competition_level': competition,
                        'avg_contract_value': f"${avg_annual/max(num_competitors,1)/1_000_000:.1f}M" if avg_annual >= 1_000_000 else f"${avg_annual/max(num_competitors,1):,.0f}",
                        'num_competitors': num_competitors,
                        'market_trend': f"{trend_label} ({growth:+.0f}%)",
                        'total_3yr_spending': f"${total/1_000_000:.1f}M" if total >= 1_000_000 else f"${total:,.0f}",
                        'yearly_spending': trends.get('yearly_spending', {})
                    }
                    print(f"  ✓ Market: {competition} competition, {trend_label} trend")

            # 4. Generate recommendations
            recommendations = []
            if incumbents:
                top = incumbents[0]['company']
                recommendations.append(f"Top incumbent: {top} — study their past performance for differentiation")
            if len(incumbents) >= 5:
                recommendations.append("Competitive field is crowded — consider teaming or niche differentiation")
            if teaming_partners:
                recommendations.append(f"Potential teaming partner: {teaming_partners[0]['company']} ({teaming_partners[0]['total_value']} in NAICS {naics})")
            if market_analysis.get('market_trend', '').startswith('Growing'):
                recommendations.append("Market is growing — good time to invest in capture effort")
            elif market_analysis.get('market_trend', '').startswith('Declining'):
                recommendations.append("Market is declining — ensure strong differentiation and pricing")
            if not recommendations:
                recommendations.append("Limited data available — consider broadening NAICS search")

            recommendations.append(f"Source: USAspending.gov (3-year contract data for {normalized_agency})")

            print(f"✓ Competitive intel completed successfully!")
            return {
                'status': 'success',
                'incumbents': incumbents,
                'teaming_partners': teaming_partners,
                'market_analysis': market_analysis,
                'recommendations': recommendations
            }

        except Exception as e:
            print(f"⚠️ Competitive intel error: {e}")
            import traceback
            traceback.print_exc()
            return {
                'status': 'error',
                'error': f'Competitive intel failed: {str(e)}',
                'incumbents': [],
                'teaming_partners': [],
                'market_analysis': {},
                'recommendations': [
                    f'Error: {str(e)}',
                    'USAspending.gov API may be temporarily unavailable',
                    'Check your internet connection and try again'
                ]
            }
    
    def run_capability_match(self, opportunity_data: dict):
        """Run Agent 3: Capability Matching"""
        try:
            from knowledge_graph.capability_matcher import CapabilityMatcher

            matcher = CapabilityMatcher()
            analysis = matcher.analyze_opportunity(opportunity_data)

            # Format staff_assignments into 'matches' for the frontend
            matches = []
            for staff_name, assigned_reqs in analysis.get('staff_assignments', {}).items():
                # Look up the staff member for details
                staff = next((s for s in matcher.staff if s.name == staff_name), None)
                matches.append({
                    'name': staff_name,
                    'score': min(100, len(assigned_reqs) * 20),
                    'matching_skills': assigned_reqs,
                    'clearance': staff.clearance if staff else 'N/A',
                    'years_experience': staff.experience_years if staff else 0,
                    'title': staff.title if staff else ''
                })
            matches.sort(key=lambda x: x['score'], reverse=True)

            # Format gaps into recommendations
            recommendations = []
            for gap in analysis.get('capability_gaps', []):
                sev = gap.get('severity', 'Medium')
                recommendations.append(f"[{sev}] {gap['requirement']} — {gap['recommendation']}")
            recommendations.append(analysis.get('recommendation', ''))

            req_info = analysis.get('requirements', {})
            return {
                'status': 'success',
                'matches': matches,
                'capability_score': analysis.get('capability_score', 0),
                'technical_win_probability': analysis.get('technical_win_probability', 'N/A'),
                'requirements_summary': {
                    'total': req_info.get('total', 0),
                    'matched': req_info.get('matched', 0),
                    'unmatched': req_info.get('unmatched', 0),
                    'details': req_info.get('details', [])
                },
                'recommendations': recommendations
            }

        except Exception as e:
            print(f"⚠️ Capability match error: {e}")
            import traceback
            traceback.print_exc()
            return {
                'status': 'error',
                'error': f'Capability match failed: {str(e)}',
                'matches': [],
                'recommendations': [f'Error: {str(e)}']
            }
    
    def run_rfi_generator(self, notice_id: str, opportunity_data: dict):
        """Run Agent 4: RFI Generator"""
        try:
            from knowledge_graph.rfi_generator import RFIResponseGenerator

            generator = RFIResponseGenerator()

            # Build opportunity dict the generator expects
            opp = {
                'title': opportunity_data.get('title', 'Opportunity'),
                'agency': opportunity_data.get('fullParentPathName', '') or opportunity_data.get('agency', ''),
                'notice_id': notice_id,
                'description': opportunity_data.get('description', ''),
            }

            output_file = generator.generate_rfi_response(opp)

            return {
                'status': 'success',
                'file_path': str(output_file),
                'message': 'RFI response generated successfully'
            }

        except Exception as e:
            print(f"⚠️ RFI generator error: {e}")
            import traceback
            traceback.print_exc()
            return {
                'status': 'error',
                'error': f'RFI generation failed: {str(e)}',
                'recommendations': [
                    f'Error: {str(e)}',
                    'Ensure ANTHROPIC_API_KEY is set and python-docx is installed'
                ]
            }
    
    def run_proposal_writer(self, notice_id: str, opportunity_data: dict):
        """Run Agent 5: Proposal Writer"""
        try:
            from knowledge_graph.proposal_assistant import ProposalAssistant

            assistant = ProposalAssistant()

            # Build opportunity dict the assistant expects
            opp = {
                'title': opportunity_data.get('title', 'Opportunity'),
                'agency': opportunity_data.get('fullParentPathName', '') or opportunity_data.get('agency', ''),
                'notice_id': notice_id,
                'description': opportunity_data.get('description', ''),
            }

            output_file = assistant.generate_proposal(opp)

            return {
                'status': 'success',
                'file_path': str(output_file),
                'message': 'Proposal generated successfully'
            }

        except Exception as e:
            print(f"⚠️ Proposal writer error: {e}")
            import traceback
            traceback.print_exc()
            return {
                'status': 'error',
                'error': f'Proposal generation failed: {str(e)}',
                'recommendations': [
                    f'Error: {str(e)}',
                    'Ensure ANTHROPIC_API_KEY is set and python-docx is installed'
                ]
            }
    
    def run_pricing_generator(self, notice_id: str, opportunity_data: dict):
        """Run Agent 6: Pricing Generator"""
        try:
            from knowledge_graph.pricing_generator import PricingModel

            pricer = PricingModel()

            # Build opportunity dict
            opp = {
                'title': opportunity_data.get('title', 'Opportunity'),
                'agency': opportunity_data.get('fullParentPathName', '') or opportunity_data.get('agency', ''),
            }

            # Default staffing plan (reasonable for a mid-size IT contract)
            staffing = {
                'Program Manager': 1.0,
                'Senior Software Engineer': 2.0,
                'Software Engineer': 3.0,
                'Cloud Architect': 1.0,
                'DevOps Engineer': 1.0,
                'Cybersecurity Analyst': 1.0,
                'Business Analyst': 1.0,
            }

            odc = {
                'Travel': 30000,
                'Software Licenses': 50000,
                'Training': 15000,
            }

            igce = pricer.generate_igce(opp, staffing, duration_months=12, odc=odc)
            output_file = pricer.generate_pricing_excel(igce)

            # Return structured data for the frontend
            labor_summary = []
            for cat in igce['labor']['labor_categories']:
                labor_summary.append({
                    'category': cat['name'],
                    'fte': cat['fte'],
                    'rate': f"${cat['rate']:,.2f}/hr",
                    'annual_cost': f"${cat['cost']:,.0f}",
                    'clearance': cat.get('clearance', 'None')
                })

            return {
                'status': 'success',
                'file_path': str(output_file),
                'message': f"Pricing model generated: ${igce['total_value']:,.0f} total",
                'pricing': {
                    'total_value': f"${igce['total_value']:,.0f}",
                    'labor_cost': f"${igce['labor']['total_cost']:,.0f}",
                    'odc_cost': f"${igce['odc_total']:,.0f}",
                    'monthly_burn': f"${igce['monthly_burn']:,.0f}",
                    'duration_months': igce['duration_months'],
                    'labor_categories': labor_summary
                },
                'recommendations': [
                    f"Total contract value: ${igce['total_value']:,.0f} ({igce['duration_months']} months)",
                    f"Monthly burn rate: ${igce['monthly_burn']:,.0f}",
                    f"Download the Excel workbook for detailed labor rates and IGCE"
                ]
            }

        except Exception as e:
            print(f"⚠️ Pricing generator error: {e}")
            import traceback
            traceback.print_exc()
            return {
                'status': 'error',
                'error': f'Pricing generation failed: {str(e)}',
                'recommendations': [
                    f'Error: {str(e)}',
                    'Ensure openpyxl is installed: pip install openpyxl'
                ]
            }

    def run_contact_research(self, contact: dict, force_refresh: bool = False) -> dict:
        """Run Contact Research Agent — researches a contact's public professional presence"""
        try:
            print(f"🔍 Attempting to import ContactResearchAgent...")
            from knowledge_graph.contact_research_agent import ContactResearchAgent
            print(f"✓ Import successful!")

            agent = ContactResearchAgent()
            result = agent.research_contact(contact, force_refresh=force_refresh)
            agent.close()

            return {'status': 'success', **result}

        except Exception as e:
            print(f"⚠️ Contact research error (using fallback): {e}")
            import traceback
            traceback.print_exc()

            return {
                'status': 'success',
                'note': 'Demo mode - real agent requires ANTHROPIC_API_KEY + Neo4j',
                'summary': f"Research for {contact.get('name', 'this contact')} would analyze their public professional presence including blog posts, articles, conference talks, and industry contributions.",
                'key_interests': ['Federal IT Modernization', 'Cloud Migration', 'Cybersecurity'],
                'technical_focus': ['Zero Trust Architecture', 'DevSecOps', 'Cloud-Native Solutions'],
                'priorities': ['Reducing technical debt', 'Accelerating digital transformation', 'Improving interoperability'],
                'talking_points': [
                    'Their recent interest in cloud-native approaches suggests highlighting your team\'s container/microservices experience',
                    'Frame your solution around the agency\'s stated modernization goals'
                ],
                'sources': [],
                'confidence': 'demo',
                'researched_at': '2026-01-31',
                'method': 'fallback',
                'recommendations': [
                    '💡 Real agent requires: ANTHROPIC_API_KEY + Neo4j',
                    '💡 Will search public web for professional writings and talks',
                    '💡 Claude synthesizes findings into actionable BD context'
                ]
            }
