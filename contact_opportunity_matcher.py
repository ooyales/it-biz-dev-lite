#!/usr/bin/env python3
"""
Contact-Opportunity Matching Engine
Automatically links opportunities to contacts and calculates advantage
"""

import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Any
import re
import json
from pathlib import Path

DB_PATH = "data/team_dashboard.db"


class ContactOpportunityMatcher:
    """Matches opportunities to contacts and calculates competitive advantage"""
    
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
    
    def match_opportunity(self, opportunity: Dict) -> Dict[str, Any]:
        """
        Match opportunity to contacts and calculate advantage
        
        Returns enriched opportunity with:
        - matched_contacts: List of relevant contacts
        - contact_advantage: Low/Medium/High
        - win_probability_bonus: Points added to base win probability
        - recommended_actions: What to do based on contact situation
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        notice_id = opportunity.get('notice_id', '')
        
        # Try to get agency from opportunity dict
        agency = opportunity.get('agency', '')
        
        # If no agency in dict, try to load from analysis file
        if not agency:
            analysis_file = Path(f"data/analysis/{notice_id}_analysis.json")
            if analysis_file.exists():
                try:
                    with open(analysis_file, 'r') as f:
                        analysis_data = json.load(f)
                        agency = analysis_data.get('agency', '')
                except:
                    pass
        
        # If still no agency, we can't match contacts
        if not agency:
            return {
                'matched_contacts': [],
                'contact_advantage': 'Unknown',
                'win_probability_bonus': 0,
                'advantage_details': 'No agency information available',
                'recommended_actions': [{
                    'priority': 'Info',
                    'title': 'Agency Information Needed',
                    'description': 'Cannot match contacts without agency information',
                    'actions': ['Review opportunity details for agency information']
                }]
            }
        
        naics = opportunity.get('naics_code', '')
        
        # Find matching contacts
        matches = []
        
        # Match by agency (primary)
        c.execute("""
            SELECT id, first_name, last_name, title, organization, department,
                   agency, role_type, influence_level, email, phone
            FROM contacts
            WHERE agency LIKE ?
        """, (f'%{agency}%',))
        
        for row in c.fetchall():
            contact = {
                'id': row[0],
                'name': f"{row[1]} {row[2]}",
                'title': row[3],
                'organization': row[4],
                'department': row[5],
                'agency': row[6],
                'role_type': row[7],
                'influence_level': row[8],
                'email': row[9],
                'phone': row[10],
                'match_reason': 'Agency match'
            }
            
            # Get relationship strength
            c.execute("""
                SELECT strength FROM contact_relationships
                WHERE contact_id_1 = ? OR contact_id_2 = ?
                ORDER BY created_at DESC LIMIT 1
            """, (contact['id'], contact['id']))
            
            strength_row = c.fetchone()
            contact['relationship_strength'] = strength_row[0] if strength_row else 'Unknown'
            
            # Get last interaction
            c.execute("""
                SELECT interaction_date FROM interactions
                WHERE contact_id = ?
                ORDER BY interaction_date DESC LIMIT 1
            """, (contact['id'],))
            
            last_interaction = c.fetchone()
            if last_interaction:
                contact['last_interaction'] = last_interaction[0]
                contact['days_since_contact'] = (
                    datetime.now() - datetime.fromisoformat(last_interaction[0])
                ).days
            else:
                contact['last_interaction'] = None
                contact['days_since_contact'] = 999
            
            matches.append(contact)
        
        conn.close()
        
        # Calculate advantage
        advantage_result = self._calculate_contact_advantage(matches)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            opportunity, matches, advantage_result
        )
        
        return {
            'matched_contacts': matches,
            'contact_advantage': advantage_result['level'],
            'win_probability_bonus': advantage_result['bonus'],
            'advantage_details': advantage_result['details'],
            'recommended_actions': recommendations
        }
    
    def _calculate_contact_advantage(self, contacts: List[Dict]) -> Dict:
        """Calculate competitive advantage from contact relationships"""
        
        if not contacts:
            return {
                'level': 'None',
                'bonus': -10,
                'details': 'No contacts at this agency'
            }
        
        bonus = 0
        details = []
        
        # Count by role and influence
        decision_makers = [c for c in contacts if c['role_type'] == 'Decision Maker']
        technical_leads = [c for c in contacts if c['role_type'] == 'Technical Lead']
        executives = [c for c in contacts if c['role_type'] == 'Executive']
        
        # Decision makers (highest value)
        for dm in decision_makers:
            if dm['influence_level'] == 'Very High':
                if dm['relationship_strength'] == 'Strong':
                    bonus += 25
                    details.append(f"✓ Strong relationship with {dm['name']} (Decision Maker, Very High Influence)")
                elif dm['relationship_strength'] == 'Medium':
                    bonus += 15
                    details.append(f"○ Medium relationship with {dm['name']} (Decision Maker)")
            elif dm['influence_level'] == 'High':
                if dm['relationship_strength'] == 'Strong':
                    bonus += 15
                    details.append(f"✓ Strong relationship with {dm['name']} (Decision Maker)")
                elif dm['relationship_strength'] == 'Medium':
                    bonus += 10
                    details.append(f"○ Medium relationship with {dm['name']} (Decision Maker)")
        
        # Technical leads
        for tl in technical_leads:
            if tl['relationship_strength'] == 'Strong':
                bonus += 10
                details.append(f"✓ Strong relationship with {tl['name']} (Technical Lead)")
            elif tl['relationship_strength'] == 'Medium':
                bonus += 5
                details.append(f"○ Medium relationship with {tl['name']} (Technical Lead)")
        
        # Executives
        for ex in executives:
            if ex['relationship_strength'] == 'Strong':
                bonus += 8
                details.append(f"✓ Strong relationship with {ex['name']} (Executive)")
        
        # Recent engagement bonus
        recent_contacts = [c for c in contacts if c.get('days_since_contact', 999) < 90]
        if len(recent_contacts) >= 3:
            bonus += 5
            details.append(f"✓ Active engagement ({len(recent_contacts)} contacts in last 90 days)")
        elif len(recent_contacts) >= 1:
            bonus += 2
            details.append(f"○ Some recent engagement ({len(recent_contacts)} contacts in last 90 days)")
        
        # Determine level
        if bonus >= 25:
            level = 'Very High'
        elif bonus >= 15:
            level = 'High'
        elif bonus >= 5:
            level = 'Medium'
        else:
            level = 'Low'
        
        # Cap bonus
        bonus = min(30, bonus)
        
        return {
            'level': level,
            'bonus': bonus,
            'details': '\n'.join(details) if details else 'Limited contact relationships'
        }
    
    def _generate_recommendations(
        self, 
        opportunity: Dict, 
        contacts: List[Dict], 
        advantage: Dict
    ) -> List[Dict]:
        """Generate recommended actions based on contact situation"""
        
        recommendations = []
        
        # Scenario 1: No contacts
        if not contacts:
            recommendations.append({
                'priority': 'Critical',
                'title': 'Build Agency Relationships',
                'description': 'You have no contacts at this agency',
                'impact': 'Could increase win probability by 20-30%',
                'timeline': 'Start immediately (6-12 months before RFP)',
                'actions': [
                    'Research program office POCs using LinkedIn',
                    'Attend next agency industry day or conference',
                    'Request warm introductions through existing network',
                    'Send capability statement to contracting office',
                    'Offer technical briefing or demo'
                ]
            })
            return recommendations
        
        # Scenario 2: No decision makers
        decision_makers = [c for c in contacts if c['role_type'] == 'Decision Maker']
        if not decision_makers:
            recommendations.append({
                'priority': 'High',
                'title': 'Cultivate Decision Maker Relationships',
                'description': f'You have {len(contacts)} contacts but no decision makers',
                'impact': 'Could increase win probability by 15-25%',
                'timeline': '3-6 months before RFP',
                'actions': [
                    f'Ask {contacts[0]["name"]} for introduction to contracting officer',
                    'Attend contracting officer forums/events',
                    'Provide value through market research or technical insights',
                    'Build credibility through smaller engagements'
                ]
            })
        
        # Scenario 3: Stale relationships
        stale_contacts = [c for c in contacts if c.get('days_since_contact', 0) > 90]
        if len(stale_contacts) > len(contacts) * 0.5:  # More than half stale
            recommendations.append({
                'priority': 'Medium',
                'title': 'Re-engage Relationships',
                'description': f'{len(stale_contacts)} of {len(contacts)} contacts not engaged recently',
                'impact': 'Maintain current advantage',
                'timeline': 'Within 2 weeks',
                'actions': [
                    f'Email {stale_contacts[0]["name"]} with relevant case study',
                    'Share industry insights or white papers',
                    'Request quarterly check-in call',
                    'Invite to upcoming webinar or event'
                ]
            })
        
        # Scenario 4: Strong position - leverage it
        if advantage['level'] in ['High', 'Very High']:
            recommendations.append({
                'priority': 'Maintain',
                'title': 'Leverage Strong Position',
                'description': 'You have good contacts - use them strategically',
                'impact': f'Maintain {advantage["bonus"]}% win probability advantage',
                'timeline': 'Ongoing',
                'actions': [
                    'Request early vendor engagement or RFI participation',
                    'Offer technical briefing to program office',
                    'Share relevant white papers and thought leadership',
                    'Position to influence requirements before RFP',
                    'Build teaming relationships if needed'
                ]
            })
        
        # Scenario 5: Medium position - strengthen
        elif advantage['level'] == 'Medium':
            recommendations.append({
                'priority': 'Medium',
                'title': 'Strengthen Position',
                'description': 'You have some contacts - build on this foundation',
                'impact': 'Could increase win probability by 10-15%',
                'timeline': '2-4 months before RFP',
                'actions': [
                    'Deepen relationships with existing contacts',
                    'Expand network to include decision makers',
                    'Increase engagement frequency',
                    'Provide more value (briefings, insights, demos)'
                ]
            })
        
        return recommendations
    
    def link_contact_to_opportunity(
        self, 
        opportunity_id: str, 
        contact_id: int, 
        role: str = None,
        notes: str = None
    ):
        """Create explicit link between contact and opportunity"""
        
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute("""
            INSERT INTO opportunity_contacts 
            (opportunity_id, contact_id, role, notes)
            VALUES (?, ?, ?, ?)
            ON CONFLICT DO NOTHING
        """, (opportunity_id, contact_id, role, notes))
        
        conn.commit()
        conn.close()
    
    def get_opportunities_for_contact(self, contact_id: int) -> List[Dict]:
        """Get all opportunities relevant to a contact"""
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        # Get contact's agency
        c.execute("SELECT agency FROM contacts WHERE id = ?", (contact_id,))
        row = c.fetchone()
        if not row:
            return []
        
        agency = row['agency']
        
        # Find opportunities at that agency
        c.execute("""
            SELECT notice_id, title, type, agency, naics_code, 
                   posted_date, deadline, contract_value
            FROM opportunities
            WHERE agency LIKE ?
            ORDER BY posted_date DESC
        """, (f'%{agency}%',))
        
        opportunities = [dict(row) for row in c.fetchall()]
        
        conn.close()
        
        return opportunities


def test_matching():
    """Test the matching engine"""
    
    print("\n" + "="*70)
    print("CONTACT-OPPORTUNITY MATCHING TEST")
    print("="*70 + "\n")
    
    matcher = ContactOpportunityMatcher()
    
    # Get a sample opportunity
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("""
        SELECT notice_id, title, naics_code
        FROM opportunities
        LIMIT 1
    """)
    
    row = c.fetchone()
    if not row:
        print("No opportunities in database")
        print("Run: python generate_demo_data.py")
        return
    
    notice_id = row[0]
    title = row[1]
    naics_code = row[2]
    
    conn.close()
    
    # Load agency from analysis file
    import json
    from pathlib import Path
    
    analysis_file = Path(f"data/analysis/{notice_id}_analysis.json")
    agency = "Unknown"
    contract_value = 0
    
    if analysis_file.exists():
        try:
            with open(analysis_file, 'r') as f:
                analysis_data = json.load(f)
                agency = analysis_data.get('agency', 'Unknown')
                contract_value = analysis_data.get('contract_value', 0)
        except Exception as e:
            print(f"Note: Could not load analysis file: {e}")
    
    opportunity = {
        'notice_id': notice_id,
        'title': title,
        'agency': agency,
        'naics_code': naics_code,
        'contract_value': contract_value
    }
    
    print(f"Testing opportunity: {opportunity['title']}")
    print(f"Agency: {opportunity['agency']}")
    print(f"NAICS: {opportunity['naics_code']}")
    print(f"Value: ${contract_value:,}" if contract_value else "Value: Unknown")
    print()
    
    # Match contacts
    result = matcher.match_opportunity(opportunity)
    
    print(f"Contact Advantage: {result['contact_advantage']}")
    print(f"Win Probability Bonus: +{result['win_probability_bonus']}%")
    print()
    
    print("Matched Contacts:")
    print("-" * 70)
    if result['matched_contacts']:
        for contact in result['matched_contacts']:
            print(f"• {contact['name']} - {contact['title']}")
            print(f"  Role: {contact['role_type']} | Influence: {contact['influence_level']}")
            print(f"  Relationship: {contact['relationship_strength']}")
            if contact.get('days_since_contact'):
                days = contact['days_since_contact']
                if days < 999:
                    print(f"  Last contact: {days} days ago")
                else:
                    print(f"  Last contact: Never")
            print()
    else:
        print("No contacts found at this agency")
        print()
    
    print("Advantage Details:")
    print("-" * 70)
    print(result['advantage_details'])
    print()
    
    print("Recommended Actions:")
    print("-" * 70)
    for rec in result['recommended_actions']:
        print(f"\n[{rec['priority']}] {rec['title']}")
        print(f"Description: {rec['description']}")
        if 'impact' in rec:
            print(f"Impact: {rec['impact']}")
        if 'timeline' in rec:
            print(f"Timeline: {rec['timeline']}")
        print("\nActions:")
        for action in rec.get('actions', []):
            print(f"  • {action}")
    
    print("\n" + "="*70)
    print("TEST COMPLETE")
    print("="*70)
    print("\nTo see contact matching in action:")
    print("1. Add contacts: python setup_contact_network.py")
    print("2. Run test again: python contact_opportunity_matcher.py")
    print("3. View in dashboard: http://localhost:8080")
    print()


if __name__ == "__main__":
    test_matching()
