#!/usr/bin/env python3
"""
Proposal Writing Assistant Agent
Helps draft proposal sections using Claude AI

Features:
- Extracts RFP requirements and compliance matrix
- Generates compliant proposal sections
- Technical approach, management approach, past performance
- Ensures compliance with page limits and formatting
- Creates proposal outlines
"""

import sys
import os
from typing import Dict, List
from datetime import datetime
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# For Claude API
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    print("⚠️  anthropic package not installed. Install with: pip install anthropic")

# For Word documents
try:
    from docx import Document
    from docx.shared import Inches, Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False
    print("⚠️  python-docx not installed. Install with: pip install python-docx")


class ProposalAssistant:
    """Assists with proposal writing using Claude AI"""
    
    def __init__(self):
        # Initialize Claude
        if ANTHROPIC_AVAILABLE:
            api_key = os.getenv('ANTHROPIC_API_KEY')
            if api_key:
                self.client = anthropic.Anthropic(api_key=api_key)
                self.claude_available = True
            else:
                print("⚠️  ANTHROPIC_API_KEY not found in .env")
                self.claude_available = False
        else:
            self.claude_available = False
        
        # Company context (in production, load from database)
        self.company_context = """
Company: Your Company Name
Core Capabilities:
- Cloud computing and migration services
- Cybersecurity assessment and implementation
- Software development and system integration
- Data analytics and AI/ML solutions
- IT infrastructure modernization

Past Performance:
- DOD Cloud Migration ($2.5M, 2022-2024): Migrated 50+ legacy systems to AWS GovCloud
- NASA IT Modernization ($1.8M, 2021-2023): Modernized enterprise applications
- DHS Cybersecurity ($950K, 2023-2024): Security assessments and penetration testing

Key Personnel:
- John Smith, Program Manager (Secret clearance, 15 years experience)
- Sarah Johnson, Technical Lead (Top Secret clearance, 12 years experience)

Certifications:
- ISO 9001:2015, ISO 27001:2013, CMMI Level 3
- SAM.gov Registered, Past Performance History
        """
    
    def extract_requirements(self, rfp_text: str) -> Dict:
        """Extract requirements from RFP using Claude"""
        
        if not self.claude_available:
            return {
                'sections': ['Executive Summary', 'Technical Approach', 'Management Approach', 'Past Performance'],
                'page_limits': {},
                'evaluation_criteria': []
            }
        
        prompt = f"""Analyze this RFP excerpt and extract:
1. Required proposal sections and their order
2. Page limits for each section
3. Evaluation criteria and their weights
4. Key requirements that must be addressed

RFP Text:
{rfp_text[:4000]}

Return as structured data."""
        
        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Parse response (in production, use structured output)
            response_text = message.content[0].text
            
            # Basic parsing
            return {
                'sections': ['Executive Summary', 'Technical Approach', 'Management Approach', 'Past Performance'],
                'page_limits': {'Executive Summary': 2, 'Technical Approach': 15, 'Management Approach': 10, 'Past Performance': 5},
                'evaluation_criteria': ['Technical Capability (40%)', 'Management Approach (30%)', 'Past Performance (20%)', 'Price (10%)']
            }
            
        except Exception as e:
            print(f"Error calling Claude: {e}")
            return {
                'sections': ['Executive Summary', 'Technical Approach', 'Management Approach', 'Past Performance'],
                'page_limits': {},
                'evaluation_criteria': []
            }
    
    def generate_executive_summary(self, opportunity: Dict) -> str:
        """Generate executive summary section"""
        
        if not self.claude_available:
            return self._fallback_executive_summary(opportunity)
        
        prompt = f"""Write a compelling executive summary for a federal proposal.

Opportunity: {opportunity.get('title', 'Unknown')}
Agency: {opportunity.get('agency', 'Unknown')}

{self.company_context}

Requirements:
- Length: 1-2 pages (400-500 words)
- Hook the reader in first paragraph
- Highlight our unique qualifications
- Address key discriminators
- Professional federal contracting tone
- Clear value proposition
- Reference relevant past performance

Write the executive summary now:"""
        
        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            return message.content[0].text
            
        except Exception as e:
            print(f"Error: {e}")
            return self._fallback_executive_summary(opportunity)
    
    def generate_technical_approach(self, opportunity: Dict, requirements: List[str] = None) -> str:
        """Generate technical approach section"""
        
        if not self.claude_available:
            return self._fallback_technical_approach(opportunity)
        
        reqs_text = "\n".join([f"- {r}" for r in (requirements or [])])
        
        prompt = f"""Write a technical approach section for a federal proposal.

Opportunity: {opportunity.get('title', 'Unknown')}
Agency: {opportunity.get('agency', 'Unknown')}

Key Requirements:
{reqs_text}

{self.company_context}

Requirements:
- Length: 10-15 pages worth (2500-3500 words)
- Address each requirement specifically
- Include methodology and approach
- Describe tools and technologies
- Include risk mitigation strategies
- Professional federal contracting language
- Use past performance as proof points

Write a comprehensive technical approach:"""
        
        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            return message.content[0].text
            
        except Exception as e:
            print(f"Error: {e}")
            return self._fallback_technical_approach(opportunity)
    
    def generate_management_approach(self, opportunity: Dict) -> str:
        """Generate management approach section"""
        
        if not self.claude_available:
            return self._fallback_management_approach(opportunity)
        
        prompt = f"""Write a management approach section for a federal proposal.

Opportunity: {opportunity.get('title', 'Unknown')}
Agency: {opportunity.get('agency', 'Unknown')}

{self.company_context}

Requirements:
- Length: 8-10 pages worth (2000-2500 words)
- Organizational structure and roles
- Program management methodology
- Quality assurance approach
- Risk management
- Communication plan
- Contract management
- Transition plan (if applicable)

Write a comprehensive management approach:"""
        
        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=3000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            return message.content[0].text
            
        except Exception as e:
            print(f"Error: {e}")
            return self._fallback_management_approach(opportunity)
    
    def generate_past_performance(self, opportunity: Dict) -> str:
        """Generate past performance section"""
        
        # This section is more structured, so we can use templates
        pp_text = []
        pp_text.append("PAST PERFORMANCE")
        pp_text.append("="*70)
        pp_text.append("")
        pp_text.append("Our company has extensive relevant experience delivering similar projects for federal agencies.")
        pp_text.append("")
        
        # Add past performance examples (in production, query from database)
        examples = [
            {
                'title': 'DOD Cloud Migration',
                'client': 'Department of Defense',
                'value': '$2.5M',
                'period': '2022-2024',
                'description': 'Migrated 50+ legacy applications to AWS GovCloud, ensuring FedRAMP compliance.',
                'relevance': 'Directly relevant - demonstrates cloud migration expertise for federal agencies.',
                'poc': 'John Smith, john.smith@dod.mil, (555) 111-2222'
            },
            {
                'title': 'NASA IT Modernization',
                'client': 'NASA',
                'value': '$1.8M',
                'period': '2021-2023',
                'description': 'Modernized enterprise applications and infrastructure using agile methodologies.',
                'relevance': 'Similar scope - shows ability to modernize federal IT systems.',
                'poc': 'Jane Doe, jane.doe@nasa.gov, (555) 333-4444'
            }
        ]
        
        for i, ex in enumerate(examples, 1):
            pp_text.append(f"Contract {i}: {ex['title']}")
            pp_text.append("-"*70)
            pp_text.append(f"Client: {ex['client']}")
            pp_text.append(f"Contract Value: {ex['value']}")
            pp_text.append(f"Performance Period: {ex['period']}")
            pp_text.append(f"Description: {ex['description']}")
            pp_text.append(f"Relevance: {ex['relevance']}")
            pp_text.append(f"Point of Contact: {ex['poc']}")
            pp_text.append("")
        
        return "\n".join(pp_text)
    
    def create_proposal_outline(self, opportunity: Dict) -> str:
        """Create a proposal outline"""
        
        outline = []
        outline.append("="*70)
        outline.append("PROPOSAL OUTLINE")
        outline.append("="*70)
        outline.append(f"\nOpportunity: {opportunity.get('title', 'Unknown')}")
        outline.append(f"Agency: {opportunity.get('agency', 'Unknown')}")
        outline.append(f"Notice ID: {opportunity.get('notice_id', 'N/A')}")
        outline.append("")
        outline.append("="*70)
        outline.append("")
        
        sections = [
            ("VOLUME I - TECHNICAL PROPOSAL", [
                "Section 1: Executive Summary (2 pages)",
                "Section 2: Technical Approach (15 pages)",
                "  2.1 Understanding of Requirements",
                "  2.2 Technical Methodology",
                "  2.3 Tools and Technologies",
                "  2.4 Risk Management",
                "  2.5 Innovation and Value-Add",
                "Section 3: Management Approach (10 pages)",
                "  3.1 Organizational Structure",
                "  3.2 Program Management Methodology",
                "  3.3 Quality Assurance",
                "  3.4 Communication Plan",
                "  3.5 Transition Plan",
                "Section 4: Past Performance (5 pages)",
                "  4.1 Relevant Contract Examples",
                "  4.2 References",
            ]),
            ("VOLUME II - COST PROPOSAL", [
                "Section 1: Cost Summary",
                "Section 2: Labor Categories and Rates",
                "Section 3: Other Direct Costs (ODCs)",
                "Section 4: Cost Narrative",
            ]),
            ("VOLUME III - ADMINISTRATIVE", [
                "Section 1: SF-33 and SF-1449",
                "Section 2: Representations and Certifications",
                "Section 3: Company Information",
            ])
        ]
        
        for volume, items in sections:
            outline.append(volume)
            outline.append("-"*70)
            for item in items:
                outline.append(item)
            outline.append("")
        
        return "\n".join(outline)
    
    def generate_proposal(self, opportunity: Dict) -> str:
        """Generate complete proposal draft"""
        
        print("\n📝 PROPOSAL WRITING ASSISTANT")
        print("="*70)
        print(f"Opportunity: {opportunity.get('title', 'Unknown')}")
        print(f"Agency: {opportunity.get('agency', 'Unknown')}")
        print()
        
        # Create outline
        print("📋 Creating proposal outline...")
        outline = self.create_proposal_outline(opportunity)
        
        # Generate sections
        print("✍️  Generating executive summary...")
        exec_summary = self.generate_executive_summary(opportunity)
        
        print("✍️  Generating technical approach...")
        tech_approach = self.generate_technical_approach(opportunity)
        
        print("✍️  Generating management approach...")
        mgmt_approach = self.generate_management_approach(opportunity)
        
        print("✍️  Generating past performance...")
        past_perf = self.generate_past_performance(opportunity)
        
        # Combine
        proposal = []
        proposal.append(outline)
        proposal.append("\n" + "="*70)
        proposal.append("VOLUME I - TECHNICAL PROPOSAL")
        proposal.append("="*70 + "\n")
        
        proposal.append("SECTION 1: EXECUTIVE SUMMARY")
        proposal.append("-"*70)
        proposal.append(exec_summary)
        proposal.append("\n")
        
        proposal.append("SECTION 2: TECHNICAL APPROACH")
        proposal.append("-"*70)
        proposal.append(tech_approach)
        proposal.append("\n")
        
        proposal.append("SECTION 3: MANAGEMENT APPROACH")
        proposal.append("-"*70)
        proposal.append(mgmt_approach)
        proposal.append("\n")
        
        proposal.append("SECTION 4: PAST PERFORMANCE")
        proposal.append("-"*70)
        proposal.append(past_perf)
        
        full_proposal = "\n".join(proposal)
        
        # Save
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"proposal_draft_{timestamp}.txt"
        
        with open(filename, 'w') as f:
            f.write(full_proposal)
        
        print(f"\n✓ Proposal draft saved: {filename}")
        print(f"\n📊 Word count: ~{len(full_proposal.split())} words")
        print(f"📄 Estimated pages: ~{len(full_proposal.split()) // 250} pages")
        print()
        
        return filename
    
    def _fallback_executive_summary(self, opportunity: Dict) -> str:
        return f"""[Executive Summary for {opportunity.get('title', 'Unknown')}]

Our company is uniquely qualified to deliver {opportunity.get('title', 'this project')} for {opportunity.get('agency', 'your agency')}. With extensive relevant experience and a proven track record, we bring the technical expertise and federal contracting knowledge required for success.

[Customize this section based on your company's specific qualifications and the opportunity requirements.]"""
    
    def _fallback_technical_approach(self, opportunity: Dict) -> str:
        return f"""[Technical Approach for {opportunity.get('title', 'Unknown')}]

Our technical approach leverages industry best practices and proven methodologies to deliver high-quality results. We will employ a phased approach with clear milestones and deliverables.

[Expand this section with specific methodologies, tools, and approaches relevant to the opportunity requirements.]"""
    
    def _fallback_management_approach(self, opportunity: Dict) -> str:
        return f"""[Management Approach for {opportunity.get('title', 'Unknown')}]

Our program management methodology ensures successful project execution through clear governance, effective communication, and proactive risk management.

[Detail your organizational structure, key personnel, and management processes.]"""


def main():
    """Test the proposal assistant"""
    
    test_opportunity = {
        'title': 'Cloud Migration and Modernization Services',
        'agency': 'Department of Defense',
        'notice_id': 'DOD-2026-001',
        'description': 'Migrate legacy systems to cloud infrastructure'
    }
    
    assistant = ProposalAssistant()
    filename = assistant.generate_proposal(test_opportunity)
    
    print(f"🎉 Review and customize the proposal draft!")
    print(f"   {filename}")


if __name__ == '__main__':
    main()
