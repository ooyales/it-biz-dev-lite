#!/usr/bin/env python3
"""
Capability Matching Agent
Matches staff skills and experience to opportunity requirements

Features:
- Staff skills database
- Requirement extraction from opportunity descriptions
- Capability gap analysis
- Teaming partner recommendations
- Technical win probability scoring
"""

import sys
import os
import re
from typing import Dict, List, Set
from dataclasses import dataclass, field
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# For Claude API calls to extract requirements
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    print("⚠️  anthropic package not installed. Install with: pip install anthropic")


@dataclass
class StaffMember:
    """Represents a staff member with their capabilities"""
    name: str
    title: str
    clearance: str = None
    certifications: List[str] = field(default_factory=list)
    skills: List[str] = field(default_factory=list)
    experience_years: int = 0
    past_projects: List[str] = field(default_factory=list)
    availability: str = "Available"  # Available, Partial, Unavailable
    
    def matches_requirement(self, requirement: str) -> bool:
        """Check if this staff member matches a requirement"""
        req_lower = requirement.lower()
        
        # Experience requirements — "N+ years of experience required"
        exp_match = re.search(r'(\d+)\+?\s*years', req_lower)
        if exp_match and 'experience' in req_lower:
            needed = int(exp_match.group(1))
            return self.experience_years >= needed
        
        # Clearance requirements — match by hierarchy
        clearance_hierarchy = {'top secret/sci': 4, 'top secret': 3, 'secret': 2, 'public trust': 1}
        if 'clearance' in req_lower or 'secret' in req_lower:
            # Extract what level is being asked for
            needed_level = 0
            for label, rank in clearance_hierarchy.items():
                if label in req_lower:
                    needed_level = rank
                    break
            # What does this staff member hold?
            staff_level = clearance_hierarchy.get((self.clearance or '').lower(), 0)
            return staff_level >= needed_level
        
        # Skills — check if any of this person's skills appear in the requirement text
        for skill in self.skills:
            if skill.lower() in req_lower:
                return True
        
        # Certifications
        for cert in self.certifications:
            if cert.lower() in req_lower:
                return True
        
        return False


@dataclass
class Requirement:
    """Represents a capability requirement"""
    description: str
    category: str  # Technical, Clearance, Certification, Experience
    mandatory: bool = True
    matched_by: List[str] = field(default_factory=list)


class CapabilityMatcher:
    """Matches staff capabilities to opportunity requirements"""
    
    def __init__(self):
        self.staff: List[StaffMember] = []
        self.load_staff_database()
    
    def load_staff_database(self):
        """Load staff from database (for now, sample data)"""
        # In production, this would load from a database
        # For now, using sample data
        
        self.staff = [
            StaffMember(
                name="John Smith",
                title="Senior Software Engineer",
                clearance="Secret",
                certifications=["CISSP", "AWS Certified Solutions Architect"],
                skills=["Python", "Java", "Cloud Architecture", "Kubernetes", "DevOps",
                        "Systems Integration"],
                experience_years=10,
                past_projects=["DOD Cloud Migration", "Army HR System"],
                availability="Available"
            ),
            StaffMember(
                name="Sarah Johnson",
                title="Data Scientist & BI Lead",
                clearance="Top Secret",
                certifications=["Security+", "PMP"],
                skills=["Machine Learning", "Python", "Data Science", "AI/ML",
                        "Business Intelligence", "Analytics", "Data Architecture"],
                experience_years=8,
                past_projects=["Navy AI Analytics", "DHS Fraud Detection"],
                availability="Partial"
            ),
            StaffMember(
                name="Mike Williams",
                title="Cybersecurity & Compliance Manager",
                clearance="Secret",
                certifications=["CISSP", "CEH", "Security+"],
                skills=["Cybersecurity", "Network Security", "SIEM",
                        "FedRAMP", "FISMA Compliance", "Risk Management", "CMMC"],
                experience_years=12,
                past_projects=["DOD Cyber Defense", "GSA Security Assessment",
                               "FedRAMP High Authorization"],
                availability="Available"
            ),
            StaffMember(
                name="Emily Davis",
                title="Program Manager & Agile Coach",
                clearance="Secret",
                certifications=["PMP", "Agile Certified", "CSM"],
                skills=["Project Management", "Program Management", "Agile", "Scrum",
                        "Contract Management", "Stakeholder Management", "Change Management"],
                experience_years=15,
                past_projects=["Multiple DOD Programs", "NASA IT Modernization"],
                availability="Available"
            ),
            StaffMember(
                name="Robert Chen",
                title="Cloud Architect & FinOps Lead",
                clearance=None,
                certifications=["AWS Solutions Architect", "Azure Architect"],
                skills=["Cloud Computing", "AWS", "Azure", "Cloud Migration",
                        "Infrastructure as Code", "FinOps", "IT Budget & Planning",
                        "Cost-Benefit Analysis", "ROI Modeling"],
                experience_years=7,
                past_projects=["HHS Cloud Migration", "VA Infrastructure Upgrade",
                               "Cloud cost optimization — saved $2.4M/yr"],
                availability="Available"
            ),
            StaffMember(
                name="Lisa Park",
                title="IT Strategy & TBM Advisor",
                clearance="Public Trust",
                certifications=["ITIL v4", "PMP"],
                skills=["IT Strategy", "Technology Business Management", "Digital Transformation",
                        "Enterprise Architecture", "Vendor Management", "Business Analysis",
                        "IT Modernization", "ROI Modeling"],
                experience_years=11,
                past_projects=["DHS IT Modernization Roadmap", "VA Digital Strategy",
                               "OPM TBM Implementation"],
                availability="Available"
            )
        ]
    
    def extract_requirements(self, opportunity: Dict) -> List[Requirement]:
        """Extract requirements from opportunity description"""
        
        description = opportunity.get('description', '')
        title = opportunity.get('title', '')
        full_text = f"{title}\n\n{description}"
        
        requirements = []
        
        # Pattern-based extraction (simple approach)
        # Look for common requirement keywords
        
        # Clearance requirements
        if re.search(r'\b(secret|top secret|ts|sci)\b', full_text, re.IGNORECASE):
            clearance_match = re.search(r'\b(secret|top secret|ts/sci)\b', full_text, re.IGNORECASE)
            if clearance_match:
                requirements.append(Requirement(
                    description=f"{clearance_match.group(1)} clearance required",
                    category="Clearance",
                    mandatory=True
                ))
        
        # Certification requirements
        cert_patterns = [
            r'\bCISSP\b', r'\bSecurity\+\b', r'\bCEH\b', r'\bPMP\b',
            r'\bAWS Certified\b', r'\bAzure Certified\b'
        ]
        for pattern in cert_patterns:
            if re.search(pattern, full_text, re.IGNORECASE):
                match = re.search(pattern, full_text, re.IGNORECASE)
                requirements.append(Requirement(
                    description=f"{match.group(0)} certification",
                    category="Certification",
                    mandatory=False
                ))
        
        # Categorized skill keywords — mirrors the 6 domains in the UI capability matrix.
        # Each tuple is (search_term, display_label, category).
        # search_term is what we look for in the opportunity text;
        # display_label is what shows up in the requirement report.
        skill_keywords = [
            # IT Technical
            ('python',              'Python',                       'Technical'),
            ('java',                'Java',                         'Technical'),
            ('cybersecurity',       'Cybersecurity',                'Technical'),
            ('devops',              'DevOps',                       'Technical'),
            ('ci/cd',               'CI/CD',                        'Technical'),
            ('network security',    'Network Security',             'Technical'),
            ('network engineering', 'Network Engineering',          'Technical'),
            ('systems integration', 'Systems Integration',          'Technical'),
            ('quality assurance',   'Quality Assurance',            'Technical'),
            ('help desk',           'IT Support / Help Desk',       'Technical'),
            ('siem',                'SIEM',                         'Technical'),

            # Cloud & Infrastructure
            ('cloud',               'Cloud Computing',              'Cloud'),
            ('aws',                 'AWS',                          'Cloud'),
            ('azure',               'Azure',                        'Cloud'),
            ('kubernetes',          'Kubernetes',                   'Cloud'),
            ('terraform',           'Infrastructure as Code',       'Cloud'),
            ('cloud migration',     'Cloud Migration',              'Cloud'),
            ('zero trust',          'Zero Trust',                   'Cloud'),

            # Management & Leadership
            ('agile',               'Agile',                        'Management'),
            ('scrum',               'Scrum',                        'Management'),
            ('project management',  'Project Management',           'Management'),
            ('program management',  'Program Management',           'Management'),
            ('contract management', 'Contract Management',          'Management'),
            ('change management',   'Change Management',            'Management'),
            ('stakeholder',         'Stakeholder Management',       'Management'),

            # Financial & Compliance
            ('finops',              'FinOps',                       'Financial'),
            ('cloud financial',     'FinOps',                       'Financial'),
            ('tbm',                 'Technology Business Management', 'Financial'),
            ('technology business management', 'Technology Business Management', 'Financial'),
            ('it budget',           'IT Budget & Planning',         'Financial'),
            ('cost-benefit',        'Cost-Benefit Analysis',        'Financial'),
            ('cost benefit',        'Cost-Benefit Analysis',        'Financial'),
            ('roi',                 'ROI Modeling',                 'Financial'),
            ('fisma',               'FISMA Compliance',             'Financial'),
            ('fedramp',             'FedRAMP',                      'Financial'),
            ('cmmc',                'CMMC',                         'Financial'),
            ('risk management',     'Risk Management',              'Financial'),
            ('rmf',                 'Risk Management (RMF)',        'Financial'),
            ('nist',                'NIST Framework',               'Financial'),

            # Data & Analytics
            ('machine learning',    'Machine Learning',             'Data & Analytics'),
            ('ai ',                 'AI/ML',                        'Data & Analytics'),  # trailing space avoids matching "said"
            ('data science',        'Data Science',                 'Data & Analytics'),
            ('business intelligence','Business Intelligence',       'Data & Analytics'),
            ('data architecture',   'Data Architecture',            'Data & Analytics'),
            ('etl',                 'ETL / Data Pipelines',         'Data & Analytics'),
            ('data pipeline',       'Data Pipelines',               'Data & Analytics'),
            ('analytics',           'Analytics',                    'Data & Analytics'),

            # Consulting & Advisory
            ('it strategy',         'IT Strategy',                  'Consulting'),
            ('digital transformation','Digital Transformation',     'Consulting'),
            ('enterprise architecture','Enterprise Architecture',   'Consulting'),
            ('vendor management',   'Vendor Management',            'Consulting'),
            ('business analysis',   'Business Analysis',            'Consulting'),
            ('modernization',       'IT Modernization',             'Consulting'),
            ('roadmap',             'IT Roadmapping',               'Consulting'),
        ]

        seen_labels = set()  # dedupe — e.g. 'cloud financial' and 'finops' both map to FinOps
        for search_term, label, category in skill_keywords:
            if label in seen_labels:
                continue
            if search_term in full_text.lower():
                seen_labels.add(label)
                requirements.append(Requirement(
                    description=f"{label} experience",
                    category=category,
                    mandatory=False
                ))
        
        # Experience requirements
        exp_match = re.search(r'(\d+)\+?\s*years?\s*of\s*experience', full_text, re.IGNORECASE)
        if exp_match:
            years = int(exp_match.group(1))
            requirements.append(Requirement(
                description=f"{years}+ years of experience required",
                category="Experience",
                mandatory=True
            ))
        
        return requirements
    
    def match_staff_to_requirements(self, requirements: List[Requirement]) -> Dict:
        """Match staff to requirements"""
        
        matches = {
            'matched_requirements': [],
            'unmatched_requirements': [],
            'staff_assignments': {},
            'capability_score': 0
        }
        
        for req in requirements:
            matched = False
            
            for staff in self.staff:
                if staff.matches_requirement(req.description):
                    req.matched_by.append(staff.name)
                    matched = True
                    
                    # Track staff assignments
                    if staff.name not in matches['staff_assignments']:
                        matches['staff_assignments'][staff.name] = []
                    matches['staff_assignments'][staff.name].append(req.description)
            
            if matched:
                matches['matched_requirements'].append(req)
            else:
                matches['unmatched_requirements'].append(req)
        
        # Calculate capability score
        total_reqs = len(requirements)
        matched_reqs = len(matches['matched_requirements'])
        mandatory_matched = sum(1 for r in matches['matched_requirements'] if r.mandatory)
        mandatory_total = sum(1 for r in requirements if r.mandatory)
        
        if total_reqs > 0:
            # Weight mandatory requirements more heavily
            if mandatory_total > 0:
                mandatory_score = (mandatory_matched / mandatory_total) * 70
            else:
                mandatory_score = 70
            
            optional_matched = matched_reqs - mandatory_matched
            optional_total = total_reqs - mandatory_total
            if optional_total > 0:
                optional_score = (optional_matched / optional_total) * 30
            else:
                optional_score = 30
            
            matches['capability_score'] = int(mandatory_score + optional_score)
        else:
            matches['capability_score'] = 100  # No requirements found
        
        return matches
    
    def analyze_opportunity(self, opportunity: Dict) -> Dict:
        """Complete capability analysis for an opportunity"""
        
        # Extract requirements
        requirements = self.extract_requirements(opportunity)
        
        # Match staff
        matches = self.match_staff_to_requirements(requirements)
        
        # Identify gaps
        gaps = []
        for req in matches['unmatched_requirements']:
            if req.mandatory:
                gaps.append({
                    'requirement': req.description,
                    'severity': 'High',
                    'recommendation': 'Must hire or team for this capability'
                })
            else:
                gaps.append({
                    'requirement': req.description,
                    'severity': 'Medium',
                    'recommendation': 'Nice to have, consider hiring or teaming'
                })
        
        # Build recommendation
        score = matches['capability_score']
        if score >= 80:
            recommendation = "STRONG MATCH - You have the capabilities to perform this work"
            technical_win_prob = "High (75-90%)"
        elif score >= 60:
            recommendation = "GOOD MATCH - Minor gaps can be filled through hiring or teaming"
            technical_win_prob = "Medium (50-75%)"
        elif score >= 40:
            recommendation = "PARTIAL MATCH - Significant gaps, teaming strongly recommended"
            technical_win_prob = "Low (25-50%)"
        else:
            recommendation = "WEAK MATCH - Major capability gaps, reconsider or find strong partner"
            technical_win_prob = "Very Low (<25%)"
        
        return {
            'opportunity_title': opportunity.get('title', 'Unknown'),
            'agency': opportunity.get('agency', 'Unknown'),
            'requirements': {
                'total': len(requirements),
                'matched': len(matches['matched_requirements']),
                'unmatched': len(matches['unmatched_requirements']),
                'details': [
                    {
                        'description': r.description,
                        'category': r.category,
                        'mandatory': r.mandatory,
                        'matched': len(r.matched_by) > 0,
                        'matched_by': r.matched_by
                    }
                    for r in requirements
                ]
            },
            'staff_assignments': matches['staff_assignments'],
            'capability_score': score,
            'technical_win_probability': technical_win_prob,
            'capability_gaps': gaps,
            'recommendation': recommendation
        }
    
    def generate_report(self, analysis: Dict) -> str:
        """Generate a text report of capability analysis"""
        
        report = []
        report.append("="*70)
        report.append("CAPABILITY MATCH ANALYSIS")
        report.append("="*70)
        report.append(f"\nOpportunity: {analysis['opportunity_title']}")
        report.append(f"Agency: {analysis['agency']}")
        report.append(f"\nCapability Score: {analysis['capability_score']}/100")
        report.append(f"Technical Win Probability: {analysis['technical_win_probability']}")
        report.append(f"\nRecommendation: {analysis['recommendation']}")
        
        report.append(f"\n\nREQUIREMENTS ANALYSIS")
        report.append("-"*70)
        report.append(f"Total Requirements: {analysis['requirements']['total']}")
        report.append(f"Matched: {analysis['requirements']['matched']}")
        report.append(f"Unmatched: {analysis['requirements']['unmatched']}")
        
        report.append(f"\n\nDETAILED REQUIREMENTS:")
        for req in analysis['requirements']['details']:
            status = "✓" if req['matched'] else "✗"
            mandatory = "[MANDATORY]" if req['mandatory'] else "[OPTIONAL]"
            report.append(f"\n{status} {mandatory} {req['description']}")
            if req['matched']:
                report.append(f"   Matched by: {', '.join(req['matched_by'])}")
        
        if analysis['staff_assignments']:
            report.append(f"\n\nSTAFF ASSIGNMENTS:")
            report.append("-"*70)
            for staff, reqs in analysis['staff_assignments'].items():
                report.append(f"\n{staff}:")
                for req in reqs:
                    report.append(f"  • {req}")
        
        if analysis['capability_gaps']:
            report.append(f"\n\nCAPABILITY GAPS:")
            report.append("-"*70)
            for gap in analysis['capability_gaps']:
                report.append(f"\n[{gap['severity']}] {gap['requirement']}")
                report.append(f"  → {gap['recommendation']}")
        
        report.append("\n" + "="*70)
        
        return "\n".join(report)


def main():
    """Test the capability matcher"""
    
    print("\n🎯 CAPABILITY MATCHING AGENT")
    print("="*70)
    
    # Test with sample opportunity that exercises multiple capability domains
    test_opportunity = {
        'title': 'Cloud Migration, FinOps, and IT Modernization Services',
        'agency': 'Department of Veterans Affairs',
        'description': '''
        The Department of Veterans Affairs requires a contractor to deliver a
        comprehensive cloud migration program with ongoing FinOps governance and
        IT modernization roadmapping.

        Requirements:
        - Secret clearance required for all personnel
        - 5+ years of experience with AWS or Azure cloud platforms
        - FedRAMP High authorization experience strongly preferred
        - FinOps capability to optimize cloud spend and deliver ROI modeling
        - Technology Business Management (TBM) framework experience
        - Cloud migration planning and execution
        - Zero Trust architecture alignment
        - DevOps and CI/CD pipeline experience
        - Enterprise architecture and IT strategy development
        - Digital transformation change management
        - Agile/Scrum delivery methodology
        - FISMA compliance and Risk Management Framework (RMF) experience
        - Business analysis and stakeholder management
        - PMP or equivalent certification preferred
        - CISSP or Security+ certification preferred
        '''
    }
    
    matcher = CapabilityMatcher()
    
    print(f"\nAnalyzing opportunity: {test_opportunity['title']}")
    print(f"Agency: {test_opportunity['agency']}")
    print(f"\nStaff database loaded: {len(matcher.staff)} staff members")
    
    # Perform analysis
    analysis = matcher.analyze_opportunity(test_opportunity)
    
    # Generate report
    report = matcher.generate_report(analysis)
    print(f"\n{report}")
    
    # Save report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"capability_analysis_{timestamp}.txt"
    
    with open(report_file, 'w') as f:
        f.write(report)
    
    print(f"\n✓ Report saved to: {report_file}")


if __name__ == '__main__':
    main()
