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
        """Run Agent 2: Competitive Intelligence"""
        try:
            print(f"🔍 Attempting to import CompetitiveIntelAgent...")
            from knowledge_graph.competitive_intel import CompetitiveIntelAgent
            print(f"✓ Import successful!")
            
            print(f"🔍 Creating CompetitiveIntelAgent instance...")
            intel = CompetitiveIntelAgent()
            print(f"✓ Instance created!")
            
            print(f"🔍 Running analysis for agency='{agency}', naics='{naics}'")
            
            # Call the correct methods
            incumbents = []
            teaming_partners = []
            market_analysis = {}
            
            if agency:
                print(f"→ Identifying incumbents for {agency}...")
                incumbents = intel.identify_incumbents(agency, naics)
                
                print(f"→ Analyzing agency spending...")
                market_analysis = intel.analyze_agency_spending(agency, years=2)
            
            if naics:
                print(f"→ Finding teaming partners for NAICS {naics}...")
                teaming_partners = intel.find_teaming_partners(naics)
            
            results = {
                'incumbents': incumbents,
                'teaming_partners': teaming_partners,
                'market_analysis': market_analysis
            }
            
            print(f"✓ Real agent completed successfully!")
            print(f"   Found {len(incumbents)} incumbents")
            print(f"   Found {len(teaming_partners)} teaming partners")
            return {'status': 'success', **results}
            
        except Exception as e:
            print(f"⚠️ Competitive intel error (using fallback data):")
            print(f"   Error type: {type(e).__name__}")
            print(f"   Error message: {str(e)}")
            import traceback
            print("   Full traceback:")
            traceback.print_exc()
            
            # Return mock data as fallback
            return {
                'status': 'success',
                'note': 'Using demo data - real agent unavailable',
                'error_detail': f'{type(e).__name__}: {str(e)}',
                'incumbents': [
                    {
                        'company': 'Demo Incumbent Inc.',
                        'past_performance': 'Excellent',
                        'contract_value': '$2.5M',
                        'awards': 3
                    },
                    {
                        'company': 'Example Solutions LLC',
                        'past_performance': 'Good',
                        'contract_value': '$1.8M',
                        'awards': 2
                    }
                ],
                'teaming_partners': [
                    {
                        'company': 'Demo Small Business Partner',
                        'capabilities': ['Cloud Computing', 'Cybersecurity'],
                        'certifications': ['8(a)', 'SDVOSB'],
                        'relevance_score': 85
                    }
                ],
                'market_analysis': {
                    'competition_level': 'High',
                    'avg_contract_value': '$2.1M',
                    'num_competitors': 15,
                    'market_trend': 'Growing'
                },
                'recommendations': [
                    '💡 Real agent requires: Neo4j connection + FPDS access',
                    f'💡 Error detail: {type(e).__name__}: {str(e)}',
                    '💡 Consider teaming with 8(a) small business',
                    '💡 Highlight past performance in proposal'
                ]
            }
    
    def run_capability_match(self, opportunity_data: dict):
        """Run Agent 3: Capability Matching"""
        try:
            from knowledge_graph.capability_matcher import CapabilityMatcher
            
            matcher = CapabilityMatcher()
            results = matcher.analyze_opportunity(opportunity_data)
            
            return {'status': 'success', **results}
            
        except Exception as e:
            print(f"⚠️ Capability match error (using fallback): {e}")
            return {
                'status': 'success',
                'note': 'Using demo data - real agent unavailable',
                'matches': [
                    {
                        'name': 'Demo Staff Member',
                        'score': 95,
                        'matching_skills': ['Cloud', 'Security', 'Python'],
                        'clearance': 'Top Secret',
                        'years_experience': 8
                    }
                ],
                'recommendations': [
                    '💡 Real agent requires: Staff database + requirements analysis',
                    '💡 Consider hiring additional cloud expertise'
                ]
            }
    
    def run_rfi_generator(self, notice_id: str, opportunity_data: dict):
        """Run Agent 4: RFI Generator"""
        try:
            from knowledge_graph.rfi_generator import RFIResponseGenerator
            
            generator = RFIResponseGenerator()
            
            # Generate RFI
            output_file = generator.generate_response(
                opportunity_title=opportunity_data.get('title', 'Opportunity'),
                agency=opportunity_data.get('agency', ''),
                requirements=opportunity_data.get('description', ''),
                notice_id=notice_id
            )
            
            return {
                'status': 'success',
                'file_path': str(output_file),
                'message': 'RFI response generated successfully'
            }
            
        except Exception as e:
            print(f"⚠️ RFI generator error (using demo message): {e}")
            return {
                'status': 'success',
                'note': 'Demo mode - real agent requires Claude API key',
                'message': 'RFI generation requires:\n• ANTHROPIC_API_KEY environment variable\n• Claude AI API access\n\nReal agent would generate a professional .docx RFI response.',
                'recommendations': [
                    '💡 Set ANTHROPIC_API_KEY in your environment',
                    '💡 Real agent uses Claude AI to write professional RFI',
                    '💡 Output would be saved as RFI_[title].docx'
                ]
            }
    
    def run_proposal_writer(self, notice_id: str, opportunity_data: dict):
        """Run Agent 5: Proposal Writer"""
        try:
            from knowledge_graph.proposal_assistant import ProposalAssistant
            
            assistant = ProposalAssistant()
            
            # Generate proposal
            output_file = assistant.generate_proposal(
                opportunity_title=opportunity_data.get('title', 'Opportunity'),
                agency=opportunity_data.get('agency', ''),
                requirements=opportunity_data.get('description', ''),
                notice_id=notice_id
            )
            
            return {
                'status': 'success',
                'file_path': str(output_file),
                'message': 'Proposal generated successfully'
            }
            
        except Exception as e:
            print(f"⚠️ Proposal writer error (using demo message): {e}")
            return {
                'status': 'success',
                'note': 'Demo mode - real agent requires Claude API key',
                'message': 'Proposal generation requires Claude API.\n\nReal agent would create:\n• Technical Approach\n• Management Plan\n• Staffing Plan\n• Past Performance\n\nOutput: Proposal_[title].docx',
                'recommendations': [
                    '💡 Configure ANTHROPIC_API_KEY',
                    '💡 Real agent uses Claude AI for professional proposals'
                ]
            }
    
    def run_pricing_generator(self, notice_id: str, opportunity_data: dict):
        """Run Agent 6: Pricing Generator"""
        try:
            from knowledge_graph.pricing_generator import PricingModel
            
            pricer = PricingModel()
            
            # Generate pricing
            output_file = pricer.generate_pricing(
                opportunity_title=opportunity_data.get('title', 'Opportunity'),
                requirements=opportunity_data.get('description', ''),
                notice_id=notice_id
            )
            
            return {
                'status': 'success',
                'file_path': str(output_file),
                'message': 'Pricing model generated successfully'
            }
            
        except Exception as e:
            print(f"⚠️ Pricing generator error (using demo message): {e}")
            return {
                'status': 'success',
                'note': 'Demo mode - real agent requires configuration',
                'message': 'Pricing generation would create:\n• Labor Categories & Rates\n• BOE (Basis of Estimate)\n• IGCE calculations\n• Cost breakdown\n\nOutput: Pricing_[title].xlsx',
                'recommendations': [
                    '💡 Configure labor rates and ODC costs',
                    '💡 Real agent generates Excel workbook with pricing model'
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
