#!/usr/bin/env python3
"""
Claude Agent Orchestrator
Coordinates multiple specialized AI agents for federal contracting workflow
"""

import os
import json
import yaml
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
import anthropic


class ClaudeAgent:
    """Base class for specialized Claude agents"""
    
    def __init__(self, config: Dict, agent_type: str):
        self.config = config
        self.agent_type = agent_type
        self.client = anthropic.Anthropic(api_key=config['claude']['api_key'])
        self.model = config['claude']['model']
        self.max_tokens = config['claude']['max_tokens']
        
        self.logger = logging.getLogger(f"{__name__}.{agent_type}")
    
    def _call_claude(self, system_prompt: str, user_message: str, 
                     temperature: float = 1.0) -> str:
        """
        Make a call to Claude API
        
        Args:
            system_prompt: System instructions for Claude
            user_message: User message/query
            temperature: Sampling temperature (0-1)
        
        Returns:
            Claude's response text
        """
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
            
            # Extract text from response
            response_text = ""
            for block in message.content:
                if block.type == "text":
                    response_text += block.text
            
            return response_text
            
        except Exception as e:
            self.logger.error(f"Error calling Claude API: {e}")
            return f"Error: {str(e)}"


class OpportunityAnalyzer(ClaudeAgent):
    """Analyzes opportunities and scores them for fit"""
    
    def __init__(self, config: Dict):
        super().__init__(config, "opportunity_analyzer")
        self.system_prompt = self._build_system_prompt()
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt for opportunity analysis"""
        company_info = self.config['company']
        scoring = self.config['agents']['opportunity_scout']['scoring_weights']
        
        return f"""You are an expert federal contracting business development analyst specializing in opportunity qualification.

Your company details:
- NAICS Codes: {', '.join(company_info['naics_codes'])}
- Set-Asides: {', '.join(company_info['set_asides'])}
- Contract Vehicles: {', '.join(company_info.get('contract_vehicles', []))}

Your task is to analyze federal contracting opportunities and provide:

1. **Fit Score (0-10)**: Overall assessment of opportunity fit
2. **Key Strengths**: Why this is a good match (3-5 bullet points)
3. **Concerns/Risks**: Potential challenges or gaps (3-5 bullet points)
4. **Recommendation**: PURSUE / MONITOR / PASS with brief rationale
5. **Next Actions**: Specific recommended steps if pursuing

Scoring criteria weights (out of 10):
- NAICS Match: {scoring['naics_match']}
- Set-Aside Match: {scoring['set_aside_match']}
- Contract Value Appropriateness: {scoring['value_appropriate']}
- Keyword/Capability Match: {scoring['keyword_match']}
- Incumbent Intelligence Available: {scoring['incumbent_intel']}

Be analytical and honest. Focus on strategic business decisions, not just technical capability.
Format your response as structured JSON for easy parsing."""
    
    def analyze_opportunity(self, opportunity: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a single opportunity
        
        Args:
            opportunity: Opportunity data from SAM.gov
        
        Returns:
            Analysis results including score and recommendations
        """
        # Format opportunity data for Claude
        opp_summary = self._format_opportunity(opportunity)
        
        user_message = f"""Analyze this federal contracting opportunity:

{opp_summary}

Provide your analysis in the following JSON format:
{{
  "fit_score": <0-10>,
  "strengths": ["strength 1", "strength 2", ...],
  "concerns": ["concern 1", "concern 2", ...],
  "recommendation": "PURSUE|MONITOR|PASS",
  "rationale": "brief explanation of recommendation",
  "next_actions": ["action 1", "action 2", ...]
}}"""
        
        response = self._call_claude(self.system_prompt, user_message, temperature=0.3)
        
        # Parse JSON response
        try:
            # Extract JSON from response (handle cases where Claude adds explanation)
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
            
            return analysis
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse Claude response as JSON: {e}")
            return {
                "fit_score": 0,
                "error": "Failed to parse analysis",
                "raw_response": response
            }
    
    def _format_opportunity(self, opp: Dict[str, Any]) -> str:
        """Format opportunity data for Claude"""
        return f"""
Title: {opp.get('title', 'N/A')}
Notice ID: {opp.get('noticeId', 'N/A')}
Type: {opp.get('type', 'N/A')}
NAICS Code: {opp.get('naicsCode', 'N/A')}
Set-Aside: {opp.get('typeOfSetAside', 'N/A')}
Posted Date: {opp.get('postedDate', 'N/A')}
Response Deadline: {opp.get('responseDeadLine', 'N/A')}
Award Amount: {opp.get('award', {}).get('amount', 'N/A')}

Description:
{opp.get('description', 'No description available')[:2000]}

Additional Details:
{opp.get('additionalInfoText', '')[:1000]}
"""


class CapabilityMatcher(ClaudeAgent):
    """Matches staff capabilities to opportunity requirements"""
    
    def __init__(self, config: Dict):
        super().__init__(config, "capability_matcher")
        self.staff_database = self._load_staff_database()
        self.system_prompt = self._build_system_prompt()
    
    def _load_staff_database(self) -> List[Dict]:
        """Load staff database from JSON file"""
        staff_path = self.config['staff']['database_path']
        
        if not os.path.exists(staff_path):
            self.logger.warning(f"Staff database not found at {staff_path}")
            return []
        
        with open(staff_path, 'r') as f:
            data = json.load(f)
            return data.get('staff_members', [])
    
    def _build_system_prompt(self) -> str:
        """Build system prompt for capability matching"""
        return """You are an expert resource manager for federal contracting proposals.

Your task is to analyze opportunity requirements and match them against available staff capabilities.

For each analysis, provide:
1. **Required Skills/Capabilities**: Extract key requirements from the opportunity
2. **Recommended Team**: List staff members who best match, with match percentage
3. **Coverage Analysis**: Which requirements are well-covered vs. gaps
4. **Team Composition**: Suggested org chart and roles
5. **Gaps & Mitigation**: Missing capabilities and how to address them (hire, subcontract, teaming)

Be specific about why each person is recommended. Consider:
- Technical skills match
- Clearance requirements
- Domain experience
- Past performance relevance
- Labor category appropriateness

Format as structured JSON for parsing."""
    
    def match_capabilities(self, opportunity: Dict[str, Any], 
                          analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Match staff capabilities to opportunity requirements
        
        Args:
            opportunity: Opportunity data
            analysis: Prior analysis from OpportunityAnalyzer
        
        Returns:
            Capability match results
        """
        # Format staff data
        staff_summary = self._format_staff_database()
        
        # Format opportunity requirements
        opp_summary = f"""
Title: {opportunity.get('title')}
NAICS: {opportunity.get('naicsCode')}
Description: {opportunity.get('description', '')[:1500]}

Prior Analysis:
Fit Score: {analysis.get('fit_score', 'N/A')}
Key Strengths: {', '.join(analysis.get('strengths', []))}
Concerns: {', '.join(analysis.get('concerns', []))}
"""
        
        user_message = f"""Match our staff capabilities to this opportunity:

OPPORTUNITY:
{opp_summary}

AVAILABLE STAFF:
{staff_summary}

Provide analysis in JSON format:
{{
  "required_capabilities": ["capability 1", "capability 2", ...],
  "recommended_team": [
    {{
      "staff_id": "EMP001",
      "name": "Name",
      "role": "Proposed Role",
      "match_percentage": 85,
      "strengths": ["why they fit"],
      "concerns": ["any gaps"]
    }}
  ],
  "coverage_score": <0-100>,
  "well_covered": ["requirement 1", ...],
  "gaps": ["missing capability 1", ...],
  "gap_mitigation": ["hire specialist in X", "subcontract for Y", ...],
  "team_size_estimate": <number>
}}"""
        
        response = self._call_claude(self.system_prompt, user_message, temperature=0.3)
        
        # Parse response
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
            self.logger.error(f"Failed to parse capability match: {e}")
            return {
                "error": "Failed to parse match results",
                "raw_response": response
            }
    
    def _format_staff_database(self) -> str:
        """Format staff database for Claude"""
        if not self.staff_database:
            return "No staff data available"
        
        staff_lines = []
        for person in self.staff_database:
            if person.get('id') == 'TEMPLATE':
                continue  # Skip template entries
            
            staff_lines.append(f"""
ID: {person.get('id')}
Name: {person.get('name')}
Title: {person.get('title')}
Clearance: {person.get('clearance')}
Skills: {', '.join(person.get('skills', {}).get('technical', []))}
Certifications: {', '.join(person.get('skills', {}).get('certifications', []))}
Domains: {', '.join(person.get('skills', {}).get('domains', []))}
Experience: {person.get('experience_years')} years
NAICS Experience: {', '.join(person.get('naics_experience', []))}
""")
        
        return '\n---\n'.join(staff_lines)


class RFIResponder(ClaudeAgent):
    """Generates responses to Requests for Information"""
    
    def __init__(self, config: Dict):
        super().__init__(config, "rfi_responder")
        self.system_prompt = self._build_system_prompt()
    
    def _build_system_prompt(self) -> str:
        company_info = self.config['company']
        
        return f"""You are an expert federal contracting proposal writer specializing in RFI responses.

Company Information:
- NAICS Codes: {', '.join(company_info['naics_codes'])}
- Set-Asides: {', '.join(company_info['set_asides'])}

Your task is to draft professional RFI (Request for Information) responses that:
1. Demonstrate capability without revealing proprietary information
2. Position the company favorably for future solicitation
3. Are concise and directly address questions asked
4. Follow federal contracting best practices
5. Maintain appropriate tone and professionalism

IMPORTANT: 
- Do not overcommit or make promises
- Focus on past performance and proven capabilities
- Be specific but not exhaustive
- Leave room for follow-up discussion"""
    
    def draft_rfi_response(self, opportunity: Dict[str, Any],
                          analysis: Dict[str, Any],
                          capability_match: Dict[str, Any]) -> str:
        """
        Draft an RFI response
        
        Args:
            opportunity: Opportunity details
            analysis: Opportunity analysis
            capability_match: Capability match results
        
        Returns:
            Drafted RFI response text
        """
        context = f"""
OPPORTUNITY: {opportunity.get('title')}
NOTICE ID: {opportunity.get('noticeId')}

DESCRIPTION:
{opportunity.get('description', '')[:2000]}

OUR ANALYSIS:
Fit Score: {analysis.get('fit_score')}/10
Strengths: {', '.join(analysis.get('strengths', []))}

CAPABILITY MATCH:
Coverage Score: {capability_match.get('coverage_score', 'N/A')}%
Recommended Team Size: {capability_match.get('team_size_estimate', 'N/A')}
Well-Covered Requirements: {', '.join(capability_match.get('well_covered', []))}
"""
        
        user_message = f"""Draft a professional RFI response for this opportunity:

{context}

The response should include:
1. Brief company introduction and capabilities overview
2. Relevant past performance highlights
3. Technical approach overview (high-level)
4. Team qualifications summary
5. Expression of interest in pursuing the opportunity

Keep the response to 1-2 pages. Be professional but conversational."""
        
        return self._call_claude(self.system_prompt, user_message, temperature=0.7)


class AgentOrchestrator:
    """Orchestrates all agents to process opportunities"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config = self._load_config(config_path)
        self._setup_logging()
        
        # Initialize agents
        self.opportunity_analyzer = OpportunityAnalyzer(self.config)
        self.capability_matcher = CapabilityMatcher(self.config)
        self.rfi_responder = RFIResponder(self.config)
        
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
    
    def process_opportunity(self, opportunity: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single opportunity through all agents
        
        Args:
            opportunity: Opportunity data from SAM.gov
        
        Returns:
            Complete analysis package
        """
        notice_id = opportunity.get('noticeId', 'unknown')
        self.logger.info(f"Processing opportunity: {notice_id}")
        
        results = {
            'notice_id': notice_id,
            'title': opportunity.get('title'),
            'processed_at': datetime.now().isoformat(),
            'opportunity_data': opportunity
        }
        
        # Step 1: Analyze opportunity
        if self.config['agents']['opportunity_scout']['enabled']:
            self.logger.info("Running opportunity analysis...")
            analysis = self.opportunity_analyzer.analyze_opportunity(opportunity)
            results['analysis'] = analysis
        else:
            analysis = {}
        
        # Step 2: Match capabilities (if score is high enough)
        fit_score = analysis.get('fit_score', 0)
        if (self.config['agents']['capability_matcher']['enabled'] and 
            fit_score >= self.config['agents']['capability_matcher']['min_match_threshold'] / 10):
            
            self.logger.info("Running capability match...")
            capability_match = self.capability_matcher.match_capabilities(
                opportunity, analysis
            )
            results['capability_match'] = capability_match
        else:
            self.logger.info("Skipping capability match (score too low)")
            capability_match = {}
        
        # Step 3: Draft RFI if appropriate
        if (self.config['agents']['rfi_responder']['enabled'] and 
            fit_score >= self.config['agents']['rfi_responder']['auto_draft_threshold'] and
            capability_match):
            
            self.logger.info("Drafting RFI response...")
            rfi_draft = self.rfi_responder.draft_rfi_response(
                opportunity, analysis, capability_match
            )
            results['rfi_draft'] = rfi_draft
        
        # Save results
        self._save_analysis(results)
        
        return results
    
    def _save_analysis(self, results: Dict[str, Any]):
        """Save analysis results to file"""
        notice_id = results.get('notice_id', 'unknown')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{notice_id}_{timestamp}_analysis.json"
        
        filepath = os.path.join(
            self.config['storage']['analysis_path'],
            filename
        )
        
        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2)
        
        self.logger.info(f"Saved analysis to {filepath}")
    
    def process_opportunities_from_file(self, opportunities_file: str) -> List[Dict[str, Any]]:
        """
        Process all opportunities from a saved JSON file
        
        Args:
            opportunities_file: Path to opportunities JSON file
        
        Returns:
            List of analysis results
        """
        with open(opportunities_file, 'r') as f:
            data = json.load(f)
            opportunities = data.get('opportunities', [])
        
        results = []
        for opp in opportunities:
            try:
                result = self.process_opportunity(opp)
                results.append(result)
            except Exception as e:
                self.logger.error(f"Error processing opportunity: {e}")
                continue
        
        return results


def main():
    """Main execution"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python claude_agents.py <opportunities_file.json>")
        sys.exit(1)
    
    opportunities_file = sys.argv[1]
    
    orchestrator = AgentOrchestrator()
    results = orchestrator.process_opportunities_from_file(opportunities_file)
    
    print(f"\n✓ Processed {len(results)} opportunities")
    print(f"✓ Results saved to {orchestrator.config['storage']['analysis_path']}")
    
    # Print summary
    high_scores = [r for r in results if r.get('analysis', {}).get('fit_score', 0) >= 7]
    print(f"\n{len(high_scores)} high-priority opportunities (score >= 7)")


if __name__ == "__main__":
    main()
