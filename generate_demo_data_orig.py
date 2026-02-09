#!/usr/bin/env python3
"""
Generate Dummy Data for Team Dashboard Demo
Creates realistic federal contracting opportunities for demonstration
"""

import json
import sqlite3
from datetime import datetime, timedelta
import random
import os
from pathlib import Path

# Realistic federal contracting data
AGENCIES = [
    "Department of Defense", "Department of Veterans Affairs", 
    "Department of Homeland Security", "General Services Administration",
    "Department of Energy", "NASA", "Department of Health and Human Services",
    "Department of Transportation", "Department of Justice", "Department of State"
]

OPPORTUNITY_TITLES = [
    "Cloud Infrastructure Migration Services",
    "Cybersecurity Operations and Monitoring",
    "Software Development and Maintenance",
    "IT Help Desk Support Services",
    "Data Analytics Platform Implementation",
    "Network Infrastructure Upgrade",
    "Enterprise Resource Planning System",
    "Artificial Intelligence/Machine Learning Solutions",
    "Agile Software Development Support",
    "DevSecOps Platform Services",
    "Zero Trust Architecture Implementation",
    "Mainframe Modernization Services",
    "Endpoint Security Management",
    "Identity and Access Management",
    "Cloud Security Posture Management",
    "Application Security Testing",
    "Incident Response and Forensics",
    "Risk Management Framework Support",
    "Continuous Integration/Deployment Pipeline",
    "Container Orchestration Services"
]

NAICS_CODES = ["541512", "541519", "541330", "541611", "541618", "541690"]

INCUMBENT_COMPANIES = [
    "TechCorp Solutions", "Federal IT Services Inc", "SecureGov Technologies",
    "CloudFirst Federal", "DataSystems LLC", "CyberDefense Group",
    "AgileGov Solutions", "NextGen Federal IT", "InnovateTech Corp",
    "PrimeContract Services", "FedTech Partners", "Digital Transform LLC"
]

SET_ASIDES = ["Small Business", "8(a)", "HUBZone", "SDVOSB", "WOSB", None]

def create_dummy_opportunity(index):
    """Create a single realistic opportunity"""
    
    # Random dates
    posted_date = datetime.now() - timedelta(days=random.randint(1, 30))
    deadline = posted_date + timedelta(days=random.randint(15, 90))
    
    # Random contract value
    min_value = random.choice([50000, 100000, 250000, 500000, 1000000, 2500000])
    max_value = min_value * random.uniform(1.5, 3.0)
    contract_value = random.randint(int(min_value), int(max_value))
    
    # Fit score and win probability (correlated)
    fit_score = round(random.uniform(4.0, 9.5), 1)
    
    # Win probability based on fit score
    if fit_score >= 8.0:
        win_probability = random.randint(65, 85)
    elif fit_score >= 7.0:
        win_probability = random.randint(50, 70)
    elif fit_score >= 6.0:
        win_probability = random.randint(35, 55)
    else:
        win_probability = random.randint(20, 40)
    
    # Status based on fit score
    if fit_score >= 8.0:
        status = random.choice(['pursuing', 'pursuing', 'new', 'watch'])
    elif fit_score >= 7.0:
        status = random.choice(['pursuing', 'watch', 'new', 'new'])
    elif fit_score >= 6.0:
        status = random.choice(['watch', 'new', 'new', 'passed'])
    else:
        status = random.choice(['new', 'passed', 'passed'])
    
    # Recommendation
    if fit_score >= 7.5:
        recommendation = "PURSUE"
    elif fit_score >= 6.5:
        recommendation = "WATCH"
    else:
        recommendation = "PASS"
    
    notice_id = f"DEMO-{datetime.now().year}-{index:04d}"
    
    return {
        'notice_id': notice_id,
        'title': random.choice(OPPORTUNITY_TITLES),
        'type': random.choice(['Solicitation', 'Solicitation', 'Presolicitation', 'Sources Sought']),
        'agency': random.choice(AGENCIES),
        'naics_code': random.choice(NAICS_CODES),
        'set_aside': random.choice(SET_ASIDES),
        'posted_date': posted_date.strftime('%Y-%m-%d'),
        'deadline': deadline.strftime('%Y-%m-%d'),
        'contract_value': contract_value,
        'fit_score': fit_score,
        'win_probability': win_probability,
        'recommendation': recommendation,
        'status': status,
        'incumbent': random.choice(INCUMBENT_COMPANIES) if random.random() > 0.3 else None,
        'incumbent_revenue': random.randint(500000, 5000000) if random.random() > 0.5 else None,
        'market_trend': random.choice(['Growing', 'Growing', 'Stable', 'Declining']),
        'avg_price': contract_value * random.uniform(0.8, 1.2)
    }

def create_database_data(num_opportunities=30):
    """Create dummy data in the database"""
    
    print(f"\nGenerating {num_opportunities} dummy opportunities...")
    
    # Create database
    db_path = "data/team_dashboard.db"
    os.makedirs("data", exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # Create opportunities table
    c.execute('''
        CREATE TABLE IF NOT EXISTS opportunities (
            notice_id TEXT PRIMARY KEY,
            title TEXT,
            type TEXT,
            naics_code TEXT,
            posted_date TEXT,
            deadline TEXT,
            fit_score REAL,
            win_probability REAL,
            recommendation TEXT,
            status TEXT DEFAULT 'new',
            assigned_to TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create decisions table
    c.execute('''
        CREATE TABLE IF NOT EXISTS decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            notice_id TEXT,
            decision TEXT,
            rationale TEXT,
            decided_by TEXT,
            decided_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (notice_id) REFERENCES opportunities(notice_id)
        )
    ''')
    
    # Clear existing data
    c.execute('DELETE FROM opportunities')
    c.execute('DELETE FROM decisions')
    
    # Generate opportunities
    opportunities = []
    for i in range(1, num_opportunities + 1):
        opp = create_dummy_opportunity(i)
        opportunities.append(opp)
        
        # Insert into database
        c.execute('''
            INSERT INTO opportunities 
            (notice_id, title, type, naics_code, posted_date, deadline, 
             fit_score, win_probability, recommendation, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            opp['notice_id'],
            opp['title'],
            opp['type'],
            opp['naics_code'],
            opp['posted_date'],
            opp['deadline'],
            opp['fit_score'],
            opp['win_probability'],
            opp['recommendation'],
            opp['status']
        ))
        
        print(f"  {i}. {opp['title'][:50]:50s} | Score: {opp['fit_score']}/10 | Win: {opp['win_probability']}% | Status: {opp['status']}")
    
    # Add some sample decisions
    pursuing_opps = [o for o in opportunities if o['status'] == 'pursuing']
    for opp in pursuing_opps[:5]:
        c.execute('''
            INSERT INTO decisions (notice_id, decision, rationale, decided_by)
            VALUES (?, ?, ?, ?)
        ''', (
            opp['notice_id'],
            'pursue',
            'Strong technical fit and good win probability',
            'Team Lead'
        ))
    
    conn.commit()
    conn.close()
    
    print(f"\n✓ Database created: {db_path}")
    return opportunities

def create_analysis_files(opportunities):
    """Create detailed analysis JSON files for each opportunity"""
    
    print("\nGenerating analysis files...")
    
    analysis_dir = Path("data/analysis")
    analysis_dir.mkdir(parents=True, exist_ok=True)
    
    for opp in opportunities:
        analysis_data = {
            'notice_id': opp['notice_id'],
            'title': opp['title'],
            'timestamp': datetime.now().isoformat(),
            
            'opportunity_data': {
                'noticeId': opp['notice_id'],
                'title': opp['title'],
                'type': opp['type'],
                'naicsCode': opp['naics_code'],
                'postedDate': opp['posted_date'],
                'responseDeadLine': opp['deadline'],
                'award': {
                    'amount': str(opp['contract_value'])
                },
                'typeOfSetAside': opp['set_aside'],
                'fullParentPathName': opp['agency']
            },
            
            'analysis': {
                'fit_score': opp['fit_score'],
                'recommendation': opp['recommendation'],
                'rationale': f"This opportunity aligns with our core capabilities. Win probability: {opp['win_probability']}%",
                'strengths': [
                    "Strong technical alignment with team capabilities",
                    "Favorable contract size for our capacity",
                    "Good relationship with agency"
                ],
                'weaknesses': [
                    "Competitive market with established incumbents",
                    "May require additional certifications"
                ] if opp['fit_score'] < 7.0 else [],
                'risks': [
                    "Timeline may be aggressive",
                    "Budget constraints possible"
                ] if opp['fit_score'] < 8.0 else []
            },
            
            'competitive_intelligence': {
                'incumbent': {
                    'contractor_name': opp['incumbent'],
                    'contract_value': opp.get('incumbent_revenue'),
                    'years_held': random.randint(1, 5)
                } if opp['incumbent'] else None,
                
                'incumbent_profile': {
                    'total_contract_value_3yr': opp.get('incumbent_revenue', 0) * 3,
                    'contract_count_3yr': random.randint(3, 15),
                    'strength_rating': random.choice(['weak', 'moderate', 'strong'])
                } if opp['incumbent'] else None,
                
                'pricing_intelligence': {
                    'similar_contracts_found': random.randint(5, 20),
                    'average_award_value': opp['avg_price'],
                    'price_range': {
                        'min': opp['avg_price'] * 0.7,
                        'max': opp['avg_price'] * 1.3
                    },
                    'trend': 'increasing' if opp['market_trend'] == 'Growing' else 'stable'
                },
                
                'market_trends': {
                    'naics_code': opp['naics_code'],
                    'trend_direction': opp['market_trend'].lower(),
                    'growth_rate_percent': random.uniform(-5, 25) if opp['market_trend'] == 'Growing' else random.uniform(-10, 5),
                    'total_spending_3yr': opp['contract_value'] * random.uniform(8, 15)
                },
                
                'competitive_assessment': {
                    'win_probability': opp['win_probability'],
                    'competitive_position': 'Strong' if opp['fit_score'] >= 7.5 else 'Moderate' if opp['fit_score'] >= 6.5 else 'Weak',
                    'strategy_recommendations': [
                        "Emphasize past performance in similar projects",
                        "Highlight cost-effective solution",
                        "Leverage small business status" if opp['set_aside'] else "Consider teaming with small business"
                    ]
                }
            },
            
            'capability_match': {
                'coverage_score': random.randint(70, 95),
                'team_size_estimate': random.randint(3, 12),
                'recommended_team': [
                    {'name': 'Senior Engineer', 'role': 'Technical Lead'},
                    {'name': 'Project Manager', 'role': 'PM'},
                    {'name': 'Developer', 'role': 'Developer'}
                ],
                'gaps': [
                    'May need additional clearances'
                ] if opp['fit_score'] < 7.0 else []
            }
        }
        
        filename = f"{opp['notice_id']}_analysis.json"
        filepath = analysis_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(analysis_data, f, indent=2)
    
    print(f"✓ Created {len(opportunities)} analysis files in data/analysis/")

def create_opportunities_file(opportunities):
    """Create opportunities JSON file"""
    
    print("\nGenerating opportunities file...")
    
    opps_dir = Path("data/opportunities")
    opps_dir.mkdir(parents=True, exist_ok=True)
    
    filename = f"opportunities_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    filepath = opps_dir / filename
    
    data = {
        'retrieved_at': datetime.now().isoformat(),
        'count': len(opportunities),
        'opportunities': opportunities
    }
    
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"✓ Created {filepath}")

def generate_summary_report(opportunities):
    """Generate a summary report"""
    
    print("\nGenerating summary report...")
    
    reports_dir = Path("data/reports")
    reports_dir.mkdir(parents=True, exist_ok=True)
    
    # Calculate statistics
    total = len(opportunities)
    high_priority = len([o for o in opportunities if o['fit_score'] >= 7.0])
    pursuing = len([o for o in opportunities if o['status'] == 'pursuing'])
    watch = len([o for o in opportunities if o['status'] == 'watch'])
    new = len([o for o in opportunities if o['status'] == 'new'])
    passed = len([o for o in opportunities if o['status'] == 'passed'])
    
    # Upcoming deadlines
    today = datetime.now()
    upcoming = []
    for opp in opportunities:
        deadline = datetime.strptime(opp['deadline'], '%Y-%m-%d')
        days_until = (deadline - today).days
        if 0 <= days_until <= 7:
            upcoming.append(opp)
    
    filename = f"demo_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    filepath = reports_dir / filename
    
    with open(filepath, 'w') as f:
        f.write("="*80 + "\n")
        f.write("FEDERAL CONTRACTING OPPORTUNITIES - DEMO DATA SUMMARY\n")
        f.write("="*80 + "\n\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("OVERALL STATISTICS:\n")
        f.write(f"  Total Opportunities:    {total}\n")
        f.write(f"  High Priority (≥7.0):   {high_priority}\n")
        f.write(f"  Currently Pursuing:     {pursuing}\n")
        f.write(f"  Watch List:             {watch}\n")
        f.write(f"  New/Unreviewed:         {new}\n")
        f.write(f"  Passed:                 {passed}\n")
        f.write(f"  Upcoming Deadlines:     {len(upcoming)} (next 7 days)\n\n")
        
        f.write("="*80 + "\n")
        f.write("HIGH PRIORITY OPPORTUNITIES (Score ≥ 7.0):\n")
        f.write("="*80 + "\n\n")
        
        high_priority_opps = sorted(
            [o for o in opportunities if o['fit_score'] >= 7.0],
            key=lambda x: x['fit_score'],
            reverse=True
        )
        
        for i, opp in enumerate(high_priority_opps, 1):
            f.write(f"{i}. {opp['title']}\n")
            f.write(f"   Notice ID:        {opp['notice_id']}\n")
            f.write(f"   Fit Score:        {opp['fit_score']}/10\n")
            f.write(f"   Win Probability:  {opp['win_probability']}%\n")
            f.write(f"   Value:            ${opp['contract_value']:,}\n")
            f.write(f"   Deadline:         {opp['deadline']}\n")
            f.write(f"   Status:           {opp['status'].upper()}\n")
            f.write(f"   Recommendation:   {opp['recommendation']}\n")
            if opp['incumbent']:
                f.write(f"   Incumbent:        {opp['incumbent']}\n")
            f.write("\n")
    
    print(f"✓ Created {filepath}")

def main():
    """Main execution"""
    
    print("\n" + "="*80)
    print("FEDERAL CONTRACTING DUMMY DATA GENERATOR")
    print("="*80)
    
    # Ask for number of opportunities
    print("\nHow many opportunities would you like to generate?")
    print("  Recommended: 30-50 for good demo")
    num = input("Number of opportunities [30]: ").strip()
    num_opportunities = int(num) if num else 30
    
    # Generate data
    opportunities = create_database_data(num_opportunities)
    create_analysis_files(opportunities)
    create_opportunities_file(opportunities)
    generate_summary_report(opportunities)
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    total = len(opportunities)
    high_priority = len([o for o in opportunities if o['fit_score'] >= 7.0])
    pursuing = len([o for o in opportunities if o['status'] == 'pursuing'])
    
    print(f"\n✓ Generated {total} opportunities")
    print(f"  • {high_priority} high priority (score ≥ 7.0)")
    print(f"  • {pursuing} actively pursuing")
    print(f"\n✓ Created database: data/team_dashboard.db")
    print(f"✓ Created analysis files in: data/analysis/")
    print(f"✓ Created opportunities file in: data/opportunities/")
    print(f"✓ Created summary report in: data/reports/")
    
    print("\n" + "="*80)
    print("READY TO DEMO!")
    print("="*80)
    print("\nStart the dashboard:")
    print("  ./start_team_system.sh")
    print("\nThen access:")
    print("  http://localhost:8080")
    print("\nYou should see:")
    print(f"  • {total} total opportunities")
    print(f"  • {high_priority} high priority")
    print(f"  • {pursuing} active pursuits")
    print("  • Timeline populated with opportunities")
    print("\n")

if __name__ == "__main__":
    main()
