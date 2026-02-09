#!/usr/bin/env python3
"""
Practical Network Examples
Run this to see how the network features work
"""

import sqlite3
from datetime import datetime, timedelta

DB_PATH = "data/team_dashboard.db"

def show_current_network():
    """Display your current network status"""
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    print("\n" + "="*70)
    print("YOUR RELATIONSHIP NETWORK - CURRENT STATUS")
    print("="*70 + "\n")
    
    # Total contacts
    c.execute("SELECT COUNT(*) FROM contacts")
    total = c.fetchone()[0]
    print(f"📊 Total Contacts: {total}")
    
    # By role
    c.execute("SELECT role_type, COUNT(*) FROM contacts GROUP BY role_type")
    print("\n📋 By Role:")
    for role, count in c.fetchall():
        print(f"  • {role}: {count}")
    
    # By agency
    c.execute("SELECT agency, COUNT(*) FROM contacts GROUP BY agency")
    print("\n🏢 By Agency:")
    for agency, count in c.fetchall():
        print(f"  • {agency}: {count}")
    
    # Relationships
    c.execute("SELECT COUNT(*) FROM contact_relationships")
    rel_count = c.fetchone()[0]
    print(f"\n🤝 Total Relationships: {rel_count}")
    
    if rel_count > 0:
        c.execute("""
            SELECT 
                c1.first_name || ' ' || c1.last_name as person1,
                c2.first_name || ' ' || c2.last_name as person2,
                cr.relationship_type,
                cr.strength
            FROM contact_relationships cr
            JOIN contacts c1 ON cr.contact_id_1 = c1.id
            JOIN contacts c2 ON cr.contact_id_2 = c2.id
        """)
        
        print("\n🔗 Relationship Map:")
        for p1, p2, rel_type, strength in c.fetchall():
            strength_icon = "━━━" if strength == "Strong" else "───" if strength == "Medium" else "┈┈┈"
            print(f"  {p1} {strength_icon} {rel_type} {strength_icon} {p2}")
    
    # Interactions
    c.execute("SELECT COUNT(*) FROM interactions")
    int_count = c.fetchone()[0]
    print(f"\n📝 Total Interactions Logged: {int_count}")
    
    if int_count > 0:
        c.execute("""
            SELECT 
                c.first_name || ' ' || c.last_name as contact,
                i.interaction_type,
                i.interaction_date,
                i.subject
            FROM interactions i
            JOIN contacts c ON i.contact_id = c.id
            ORDER BY i.interaction_date DESC
            LIMIT 5
        """)
        
        print("\n📅 Recent Interactions:")
        for contact, itype, date, subject in c.fetchall():
            print(f"  • {date}: {itype} with {contact}")
            print(f"    Subject: {subject[:50]}...")
    
    conn.close()
    
    print("\n" + "="*70)
    print("VIEW YOUR NETWORK")
    print("="*70)
    print("\n🌐 Interactive Network Diagram:")
    print("   http://localhost:8080/network")
    print("\n📇 Contact Management:")
    print("   http://localhost:8080/contacts/manage")
    print()


def example_add_relationship():
    """Example: Adding a relationship between contacts"""
    
    print("\n" + "="*70)
    print("EXAMPLE: ADDING RELATIONSHIPS")
    print("="*70 + "\n")
    
    print("To add a relationship between two contacts:")
    print()
    print("```python")
    print("import sqlite3")
    print()
    print("conn = sqlite3.connect('data/team_dashboard.db')")
    print("c = conn.cursor()")
    print()
    print("# Example: Sarah reports to Tom")
    print("c.execute('''")
    print("    INSERT INTO contact_relationships (")
    print("        contact_id_1, contact_id_2, relationship_type, strength, notes")
    print("    ) VALUES (?, ?, ?, ?, ?)")
    print("''', (")
    print("    sarah_id,  # Sarah Johnson")
    print("    tom_id,    # Tom Wilson")
    print("    'Reports To',")
    print("    'Strong',")
    print("    'Sarah reports directly to Tom, he has final approval authority'")
    print("))")
    print()
    print("conn.commit()")
    print("conn.close()")
    print("```")
    print()
    print("Relationship Types:")
    print("  • Reports To / Supervisor")
    print("  • Peer / Colleague")
    print("  • Works With")
    print("  • Mentor / Mentee")
    print("  • Friends / Alumni")
    print()
    print("Strength Levels:")
    print("  • Strong: Regular contact, established trust")
    print("  • Medium: Occasional contact, professional")
    print("  • Weak: Aware of each other, minimal interaction")
    print()


def example_track_interaction():
    """Example: Tracking an interaction"""
    
    print("\n" + "="*70)
    print("EXAMPLE: TRACKING INTERACTIONS")
    print("="*70 + "\n")
    
    print("After every meeting/call/email, log it:")
    print()
    print("```python")
    print("import sqlite3")
    print("from datetime import datetime")
    print()
    print("conn = sqlite3.connect('data/team_dashboard.db')")
    print("c = conn.cursor()")
    print()
    print("# Log a meeting")
    print("c.execute('''")
    print("    INSERT INTO interactions (")
    print("        contact_id, interaction_type, interaction_date,")
    print("        subject, summary, outcome, next_action, next_action_date")
    print("    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)")
    print("''', (")
    print("    sarah_id,")
    print("    'Meeting',")
    print("    '2026-01-27',")
    print("    'Cloud Modernization Strategy Discussion',")
    print("    '''Discussed agency's move to hybrid cloud. Sarah interested")
    print("       in our FedRAMP High capabilities. Mentioned Q2 RFP coming.")
    print("       Budget estimated $5-8M. Current vendor having issues.")
    print("       Key criteria: DoD experience, multi-cloud support.'''")
    print("    'Positive - Strong interest',")
    print("    'Send white paper on multi-cloud architecture',")
    print("    '2026-01-30'")
    print("))")
    print()
    print("conn.commit()")
    print("conn.close()")
    print("```")
    print()
    print("This creates an audit trail AND captures competitive intelligence!")
    print()


def example_find_path():
    """Example: Finding path to target contact"""
    
    print("\n" + "="*70)
    print("EXAMPLE: FINDING PATH TO TARGET")
    print("="*70 + "\n")
    
    print("Scenario: You want to reach Emily Davis at GSA (no direct relationship)")
    print()
    print("Network analysis reveals:")
    print()
    print("```")
    print("Path 1 (Recommended):")
    print("You → David Kim [Strong] → Emily Davis [Strong]")
    print("Confidence: HIGH")
    print()
    print("Path 2:")
    print("You → Sarah Johnson [Strong] → Tom Wilson [Medium] → Emily Davis [Strong]")
    print("Confidence: MEDIUM")
    print("```")
    print()
    print("Action:")
    print("1. Email David: 'David, I'm looking to connect with Emily Davis at GSA")
    print("   regarding their cloud initiative. I remember you mentioning you worked")
    print("   with her at VA. Would you be comfortable making an introduction?'")
    print()
    print("2. David introduces you")
    print()
    print("3. First email to Emily: 'Emily, David Kim suggested I reach out...")
    print("   [warm introduction vs cold call]'")
    print()
    print("Result: Relationship starts warm, not cold. Higher success rate.")
    print()


def show_network_gaps():
    """Identify gaps in your network"""
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    print("\n" + "="*70)
    print("NETWORK GAPS ANALYSIS")
    print("="*70 + "\n")
    
    # Target agencies (customize this list)
    target_agencies = [
        'Department of Defense',
        'Department of Veterans Affairs',
        'Department of Homeland Security',
        'General Services Administration',
        'NASA'
    ]
    
    print("🎯 Target Agency Coverage:\n")
    
    for agency in target_agencies:
        c.execute("""
            SELECT COUNT(*), 
                   SUM(CASE WHEN role_type = 'Decision Maker' THEN 1 ELSE 0 END)
            FROM contacts 
            WHERE agency LIKE ?
        """, (f'%{agency}%',))
        
        total, decision_makers = c.fetchone()
        
        status = "✓" if total >= 3 else "⚠️" if total >= 1 else "✗"
        dm_status = "✓" if decision_makers >= 1 else "✗"
        
        print(f"{status} {agency}")
        print(f"   Contacts: {total}  |  Decision Makers: {decision_makers} {dm_status}")
        
        if total == 0:
            print(f"   ⚠️  ACTION NEEDED: No contacts at this agency!")
        elif decision_makers == 0:
            print(f"   ⚠️  ACTION NEEDED: No decision makers!")
        print()
    
    conn.close()
    
    print("Goal: 3+ contacts per agency, including at least 1 decision maker")
    print()


def relationship_health_check():
    """Check relationship health"""
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    print("\n" + "="*70)
    print("RELATIONSHIP HEALTH CHECK")
    print("="*70 + "\n")
    
    # Get contacts with their last interaction
    c.execute("""
        SELECT 
            c.id,
            c.first_name || ' ' || c.last_name as name,
            c.agency,
            c.role_type,
            MAX(i.interaction_date) as last_interaction
        FROM contacts c
        LEFT JOIN interactions i ON c.id = i.contact_id
        GROUP BY c.id
    """)
    
    active = []
    stale = []
    dormant = []
    never_contacted = []
    
    today = datetime.now().date()
    
    for cid, name, agency, role, last_int in c.fetchall():
        if last_int is None:
            never_contacted.append((name, agency, role))
        else:
            last_date = datetime.strptime(last_int, '%Y-%m-%d').date()
            days_ago = (today - last_date).days
            
            if days_ago <= 90:
                active.append((name, agency, role, days_ago))
            elif days_ago <= 180:
                stale.append((name, agency, role, days_ago))
            else:
                dormant.append((name, agency, role, days_ago))
    
    total = len(active) + len(stale) + len(dormant) + len(never_contacted)
    
    print(f"✓ Active (0-90 days): {len(active)} contacts ({len(active)/total*100:.0f}%)")
    if active:
        for name, agency, role, days in active[:5]:
            print(f"    • {name} - {role} at {agency} (last contact {days} days ago)")
    
    print(f"\n⚠️  Stale (90-180 days): {len(stale)} contacts ({len(stale)/total*100:.0f}%)")
    if stale:
        for name, agency, role, days in stale:
            print(f"    • {name} - {role} at {agency} (last contact {days} days ago)")
            print(f"      ACTION: Re-engage within 2 weeks")
    
    print(f"\n✗ Dormant (180+ days): {len(dormant)} contacts ({len(dormant)/total*100:.0f}%)")
    if dormant:
        for name, agency, role, days in dormant:
            print(f"    • {name} - {role} at {agency} (last contact {days} days ago)")
            print(f"      ACTION: Major re-engagement needed")
    
    print(f"\n❌ Never Contacted: {len(never_contacted)} contacts")
    if never_contacted:
        for name, agency, role in never_contacted[:5]:
            print(f"    • {name} - {role} at {agency}")
            print(f"      ACTION: Schedule first interaction")
    
    print(f"\n🎯 Goal: 70% active | Current: {len(active)/total*100:.0f}%")
    
    if len(active)/total < 0.7:
        print("   ⚠️  Below target! Need to increase engagement frequency.")
    else:
        print("   ✓ On target! Good relationship health.")
    
    conn.close()
    print()


if __name__ == "__main__":
    show_current_network()
    show_network_gaps()
    relationship_health_check()
    example_add_relationship()
    example_track_interaction()
    example_find_path()
    
    print("\n" + "="*70)
    print("NEXT STEPS")
    print("="*70 + "\n")
    print("1. View your network: http://localhost:8080/network")
    print("2. Add relationships between contacts you know")
    print("3. Log all interactions (meetings, calls, emails)")
    print("4. Identify gaps (agencies with no contacts)")
    print("5. Build relationships 6-12 months before RFPs")
    print()
    print("The network is your competitive advantage! 🎯")
    print()
