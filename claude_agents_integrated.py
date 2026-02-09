#!/usr/bin/env python3
"""
Integrated Claude Agents with Competitive Intelligence
AI agents that natively incorporate competitive intelligence into analysis
"""

import os
import json
import yaml
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
import anthropic


class ClaudeAgentIntegrated:
    """Base class for integrated Claude agents with competitive intelligence"""
    
    def __init__(self, config: Dict, agent_type: str):
        self.config = config
        self.agent_type = agent_type
        self.client = anthropic.Anthropic(api_key=config['claude']['api_key'])
        self.model = config['claude']['model']
        self.max_tokens = config['claude']['max_tokens']
        
        self.logger = logging.getLogger(f"{__name__}.{agent_type}")
    
    def _call_claude(self, system_prompt: str, user_message: str, 
                     temperature: float = 1.0) -> str:
        """Make a call to Claude API"""
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_message}
                ]
            )
            
            response_text = ""
            for block in message.content:
                if block.type == "text":
                    response_text += block.text
            
            return response_text
            
        except Exception as e:
            self.logger.error(f"Error calling Claude API: {e}")
            return f"Error: {str(e)}"


class OpportunityAnalyzerIntegrated(ClaudeAgentIntegrated):
    """Analyzes opportunities WITH competitive intelligence context"""
    
    def __init__(self, config: Dict):
        super().__init__(config, "opportunity_analyzer_integrated")
        self.system_prompt = self._build_system_prompt()
    
    def _build_system_prompt(self) -> str:
        """Build enhanced system prompt that incorporates competitive intelligence"""
        company_info = self.config['company']
        scoring = self.config['agents']['opportunity_scout']['scoring_weights']
        
        return f"""You are an expert federal contracting business development analyst with access to competitive intelligence.

Your company details:
- NAICS Codes: {', '.join(company_info['naics_codes'])}
- Set-Asides: {', '.join(company_info['set_asides'])}
- Contract Vehicles: {', '.join(company_info.get('contract_vehicles', []))}

You receive TWO types of input:
1. The opportunity details from SAM.gov
2. Competitive intelligence (incumbent data, pricing data, market trends)

Your task is to provide a COMPREHENSIVE analysis that synthesizes both sources:

**ANALYSIS OUTPUT:**
1. **Fit Score (0-10)**: Base score adjusted by competitive factors
2. **Win Probability (0-100%)**: Realistic chance of winning based on competitive position
3. **Key Strengths**: Why this is a good match (include competitive advantages)
4. **Concerns/Risks**: Challenges including competitive threats
5. **Recommendation**: STRONGLY PURSUE / PURSUE / MONITOR / PASS with rationale
6. **Competitive Strategy**: How to position against incumbent/competitors
7. **Next Actions**: Specific steps prioritized by urgency

**COMPETITIVE INTELLIGENCE INTEGRATION:**
When competitive intelligence is available, you must:
- Assess incumbent strength and vulnerability
- Compare pricing position to market
- Factor in market growth/decline
- Identify competitive advantages and disadvantages
- Adjust fit score based on competitive position
- Provide win probability estimate
- Recommend specific competitive strategy

**SCORING CRITERIA:**
Base weights (out of 10):
- NAICS Match: {scoring['naics_match']}
- Set-Aside Match: {scoring['set_aside_match']}
- Contract Value: {scoring['value_appropriate']}
- Keyword Match: {scoring['keyword_match']}

Competitive adjustments (can add/subtract up to 2 points):
- Weak incumbent: +1 to +2 points
- Strong incumbent: -1 to -2 points  
- Favorable market trend: +0.5 to +1 point
- Declining market: -0.5 to -1 point
- Pricing advantage: +0.5 point
- Pricing disadvantage: -0.5 point

**WIN PROBABILITY FACTORS:**
- Start at 50% baseline
- Strong capability match: +20%
- Weak incumbent: +15%
- Small business advantage: +10%
- Growing market: +10%
- Strong incumbent: -20%
- Limited past performance: -15%
- Capability gaps: -10%

Be realistic, analytical, and strategic. Your analysis drives bid/no-bid decisions.

Format response as JSON for parsing."""
    
    def analyze_opportunity(self, 
                          opportunity: Dict[str, Any],
                          competitive_intel: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Analyze opportunity with competitive intelligence integration
        
        Args:
            opportunity: Opportunity data from SAM.gov
            competitive_intel: Competitive intelligence data (optional)
        
        Returns:
            Enhanced analysis with competitive context
        """
        # Format opportunity data
        opp_summary = self._format_opportunity(opportunity)
        
        # Format competitive intelligence if available
        comp_intel_summary = ""
        if competitive_intel:
            comp_intel_summary = self._format_competitive_intel(competitive_intel)
        
        user_message = f"""Analyze this federal contracting opportunity:

{opp_summary}

{comp_intel_summary}

Provide comprehensive analysis in JSON format:
{{
  "fit_score": <0-10>,
  "win_probability": <0-100>,
  "strengths": ["strength 1", "strength 2", ...],
  "concerns": ["concern 1", "concern 2", ...],
  "recommendation": "STRONGLY_PURSUE|PURSUE|MONITOR|PASS",
  "rationale": "detailed explanation",
  "competitive_strategy": "how to position against competition",
  "next_actions": ["action 1", "action 2", ...]
}}"""
        
        response = self._call_claude(self.system_prompt, user_message, temperature=0.3)
        
        # Parse JSON response
        try:
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start != -1 and json_end > json_start:
                json_str = response[json_start:json_end]
                analysis = json.loads(json_str)
            else:
                analysis = json.loads(response)
            
            # Add metadata
            analysis['analyzed_at'] = datetime.now().isoformat()
            analysis['notice_id'] = opportunity.get('noticeId')
            analysis['had_competitive_intel'] = bool(competitive_intel)
            
            return analysis
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse Claude response as JSON: {e}")
            return {
                "fit_score": 0,
                "win_probability": 0,
                "error": "Failed to parse analysis",
                "raw_response": response
            }
    
    def _format_opportunity(self, opp: Dict[str, Any]) -> str:
        """Format opportunity data for Claude"""
        return f"""
═══════════════════════════════════════════════════════════════
OPPORTUNITY DETAILS
═══════════════════════════════════════════════════════════════

Title: {opp.get('title', 'N/A')}
Notice ID: {opp.get('noticeId', 'N/A')}
Type: {opp.get('type', 'N/A')}
NAICS Code: {opp.get('naicsCode', 'N/A')}
Set-Aside: {opp.get('typeOfSetAside', 'N/A')}
Posted Date: {opp.get('postedDate', 'N/A')}
Response Deadline: {opp.get('responseDeadLine', 'N/A')}
Award Amount: {opp.get('award', {}).get('amount', 'N/A')}

Description:
{opp.get('description', 'No description available')[:2500]}

Additional Details:
{opp.get('additionalInfoText', 'N/A')[:1000]}
"""
    
    def _format_competitive_intel(self, comp_intel: Dict[str, Any]) -> str:
        """Format competitive intelligence for Claude"""
        
        if not comp_intel:
            return ""
        
        intel_text = """
═══════════════════════════════════════════════════════════════
COMPETITIVE INTELLIGENCE
═══════════════════════════════════════════════════════════════
"""
        
        # Incumbent information
        incumbent = comp_intel.get('incumbent', {})
        if incumbent and incumbent.get('contractor_name'):
            intel_text += f"""
INCUMBENT CONTRACTOR:
  Name: {incumbent.get('contractor_name')}
  Contract Date: {incumbent.get('signed_date', 'Unknown')}
  Award Amount: ${incumbent.get('award_amount', 'Unknown')}
"""
            
            # Incumbent profile
            incumbent_profile = comp_intel.get('incumbent_profile', {})
            if incumbent_profile.get('total_contract_value_3yr'):
                intel_text += f"""
  3-Year Gov Revenue: ${incumbent_profile['total_contract_value_3yr']:,.2f}
  Contract Count: {incumbent_profile.get('contract_count_3yr', 'N/A')}
  Top Agencies: {', '.join([a['name'] for a in incumbent_profile.get('top_agencies', [])[:3]])}
"""
        else:
            intel_text += "\nINCUMBENT: No current incumbent identified (greenfield opportunity)\n"
        
        # Pricing intelligence
        pricing = comp_intel.get('pricing_intelligence', {})
        if pricing and pricing.get('sample_size', 0) > 0:
            intel_text += f"""
PRICING INTELLIGENCE ({pricing['sample_size']} similar contracts):
  Average Award: ${pricing.get('average', 0):,.2f}
  Range: ${pricing.get('min', 0):,.2f} - ${pricing.get('max', 0):,.2f}
  Median: ${pricing.get('median', 0):,.2f}
"""
            
            if 'trend' in pricing:
                trend = pricing['trend']
                intel_text += f"  Trend: {trend['direction'].upper()} ({trend['percent_change']:+.1f}%)\n"
        
        # Market trends
        trends = comp_intel.get('market_trends', {})
        if trends and trends.get('trend_direction'):
            intel_text += f"""
MARKET TRENDS:
  Direction: {trends['trend_direction'].upper()}
  Growth Rate: {trends.get('growth_rate_percent', 0):+.1f}% annually
  Total Market Size: ${trends.get('total_spending', 0):,.2f}
  Years Analyzed: {trends.get('years_analyzed', 'N/A')}
"""
        
        # Competitive assessment
        assessment = comp_intel.get('competitive_assessment', {})
        if assessment:
            intel_text += f"""
COMPETITIVE ASSESSMENT:
  Incumbent Strength: {assessment.get('incumbent_strength', 'unknown').upper()}
  Market Position: {assessment.get('market_position', 'unknown').upper()}
"""
            
            key_factors = assessment.get('key_factors', [])
            if key_factors:
                intel_text += "  Key Factors:\n"
                for factor in key_factors:
                    intel_text += f"    • {factor}\n"
        
        return intel_text


class CapabilityMatcherIntegrated(ClaudeAgentIntegrated):
    """Matches capabilities with teaming recommendations from competitive intel"""
    
    def __init__(self, config: Dict):
        super().__init__(config, "capability_matcher_integrated")
        self.staff_database = self._load_staff_database()
        self.system_prompt = self._build_system_prompt()
    
    def _load_staff_database(self) -> List[Dict]:
        """Load staff database"""
        staff_path = self.config['staff']['database_path']
        
        if not os.path.exists(staff_path):
            self.logger.warning(f"Staff database not found at {staff_path}")
            return []
        
        with open(staff_path, 'r') as f:
            data = json.load(f)
            return data.get('staff_members', [])
    
    def _build_system_prompt(self) -> str:
        """Build system prompt"""
        return """You are an expert resource manager with competitive intelligence integration.

Analyze opportunity requirements and match against available staff, considering:
1. Technical capability match
2. Capability gaps that may require teaming
3. Competitive positioning (if intel available)

Provide:
1. Required capabilities extracted from opportunity
2. Recommended team with match percentages
3. Coverage analysis
4. Gaps and mitigation strategies (hiring, teaming, training)
5. If teaming partners are suggested in competitive intel, assess their fit

Format as structured JSON."""
    
    def match_capabilities(self, 
                          opportunity: Dict[str, Any], 
                          analysis: Dict[str, Any],
                          competitive_intel: Dict[str, Any] = None) -> Dict[str, Any]:
        """Match capabilities with competitive intelligence context"""
        
        staff_summary = self._format_staff_database()
        
        # Include teaming recommendations if available
        teaming_info = ""
        if competitive_intel and competitive_intel.get('teaming_recommendations'):
            teaming_info = "\n\nSUGGESTED TEAMING PARTNERS (from competitive intel):\n"
            for partner in competitive_intel['teaming_recommendations'][:3]:
                teaming_info += f"  • {partner.get('name', 'Unknown')}\n"
        
        opp_summary = f"""
Title: {opportunity.get('title')}
NAICS: {opportunity.get('naicsCode')}
Description: {opportunity.get('description', '')[:1500]}

Prior Analysis:
Fit Score: {analysis.get('fit_score', 'N/A')}
Win Probability: {analysis.get('win_probability', 'N/A')}%
Key Strengths: {', '.join(analysis.get('strengths', []))}
{teaming_info}
"""
        
        user_message = f"""Match capabilities for this opportunity:

OPPORTUNITY:
{opp_summary}

AVAILABLE STAFF:
{staff_summary}

Provide analysis in JSON:
{{
  "required_capabilities": ["cap 1", "cap 2", ...],
  "recommended_team": [
    {{
      "staff_id": "ID",
      "name": "Name",
      "role": "Role",
      "match_percentage": 85,
      "strengths": ["why they fit"],
      "concerns": ["gaps"]
    }}
  ],
  "coverage_score": <0-100>,
  "well_covered": ["requirement 1", ...],
  "gaps": ["gap 1", ...],
  "gap_mitigation": ["strategy 1", ...],
  "team_size_estimate": <number>,
  "teaming_recommended": true/false,
  "teaming_rationale": "why team or not"
}}"""
        
        response = self._call_claude(self.system_prompt, user_message, temperature=0.3)
        
        try:
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start != -1 and json_end > json_start:
                json_str = response[json_start:json_end]
                match_result = json.loads(json_str)
            else:
                match_result = json.loads(response)
            
            match_result['analyzed_at'] = datetime.now().isoformat()
            return match_result
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse match results: {e}")
            return {"error": "Failed to parse", "raw_response": response}
    
    def _format_staff_database(self) -> str:
        """Format staff database"""
        if not self.staff_database:
            return "No staff data available"
        
        staff_lines = []
        for person in self.staff_database:
            if person.get('id') == 'TEMPLATE':
                continue
            
            staff_lines.append(f"""
ID: {person.get('id')}
Name: {person.get('name')}
Title: {person.get('title')}
Clearance: {person.get('clearance')}
Skills: {', '.join(person.get('skills', {}).get('technical', [])[:10])}
Certs: {', '.join(person.get('skills', {}).get('certifications', []))}
Experience: {person.get('experience_years')} years
""")
        
        return '\n---\n'.join(staff_lines)


class AgentOrchestrator:
    """Orchestrates all agents with competitive intelligence integration"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config = self._load_config(config_path)
        self._setup_logging()
        
        # Initialize agents
        self.opportunity_analyzer = OpportunityAnalyzerIntegrated(self.config)
        self.capability_matcher = CapabilityMatcherIntegrated(self.config)
        
        self.logger = logging.getLogger(__name__)
    
    def _load_config(self, config_path: str) -> Dict:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def _setup_logging(self):
        log_dir = Path(self.config['logging']['file_path']).parent
        log_dir.mkdir(parents=True, exist_ok=True)
        
        logging.basicConfig(
            level=self.config['logging']['level'],
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.config['logging']['file_path']),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def process_opportunity(self, 
                          opportunity: Dict[str, Any],
                          competitive_intel: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Process opportunity with competitive intelligence
        
        Args:
            opportunity: Opportunity from SAM.gov
            competitive_intel: Competitive intelligence (optional)
        
        Returns:
            Complete analysis package
        """
        notice_id = opportunity.get('noticeId', 'unknown')
        self.logger.info(f"Processing: {notice_id}")
        
        results = {
            'notice_id': notice_id,
            'title': opportunity.get('title'),
            'processed_at': datetime.now().isoformat(),
            'opportunity_data': opportunity,
            'competitive_intelligence': competitive_intel
        }
        
        # AI Analysis with competitive context
        self.logger.info("  Running AI analysis...")
        analysis = self.opportunity_analyzer.analyze_opportunity(
            opportunity,
            competitive_intel
        )
        results['analysis'] = analysis
        
        # Capability matching if score is high enough
        fit_score = analysis.get('fit_score', 0)
        if fit_score >= self.config['agents']['capability_matcher']['min_match_threshold'] / 10:
            self.logger.info("  Running capability match...")
            capability_match = self.capability_matcher.match_capabilities(
                opportunity, 
                analysis,
                competitive_intel
            )
            results['capability_match'] = capability_match
        
        # Save results
        self._save_analysis(results)
        
        return results
    
    def _save_analysis(self, results: Dict[str, Any]):
        """Save analysis results"""
        notice_id = results.get('notice_id', 'unknown')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{notice_id}_{timestamp}_analysis.json"
        
        filepath = os.path.join(
            self.config['storage']['analysis_path'],
            filename
        )
        
        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2)
        
        self.logger.info(f"  Saved: {filepath}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Test
    orchestrator = AgentOrchestrator()
    
    test_opp = {
        'noticeId': 'TEST001',
        'title': 'IT Services',
        'naicsCode': '541512'
    }
    
    result = orchestrator.process_opportunity(test_opp)
    print(f"\n✓ Score: {result['analysis']['fit_score']}/10")
