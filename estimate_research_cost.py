#!/usr/bin/env python3
"""
Contact Research Cost Estimator

Shows how much it would cost to research your contacts before you run it.

Usage:
    python estimate_research_cost.py
    python estimate_research_cost.py --filter "Navy"
"""

import sqlite3
import argparse
from typing import Dict


def estimate_costs(db_path: str = 'data/contacts.db', filter_text: str = None) -> Dict:
    """Estimate research costs for contacts"""
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Count total contacts
    query = "SELECT COUNT(*) FROM contacts WHERE name IS NOT NULL AND name != ''"
    params = []
    
    if filter_text:
        query += " AND (name LIKE ? OR organization LIKE ? OR agency LIKE ?)"
        pattern = f"%{filter_text}%"
        params.extend([pattern, pattern, pattern])
    
    cursor.execute(query, params)
    total_contacts = cursor.fetchone()[0]
    
    # Count by relationship strength
    cursor.execute("""
        SELECT relationship_strength, COUNT(*) 
        FROM contacts 
        WHERE name IS NOT NULL AND name != ''
        GROUP BY relationship_strength
    """)
    by_strength = dict(cursor.fetchall())
    
    # Count by agency (top 10)
    cursor.execute("""
        SELECT agency, COUNT(*) 
        FROM contacts 
        WHERE name IS NOT NULL AND name != '' AND agency IS NOT NULL
        GROUP BY agency 
        ORDER BY COUNT(*) DESC 
        LIMIT 10
    """)
    by_agency = cursor.fetchall()
    
    conn.close()
    
    # Cost calculations
    cost_per_contact = 0.017  # ~$0.017 per contact
    time_per_contact = 4  # ~4 seconds (3s API + 1s rate limit)
    
    total_cost = total_contacts * cost_per_contact
    total_time_minutes = (total_contacts * time_per_contact) / 60
    
    return {
        'total_contacts': total_contacts,
        'cost_per_contact': cost_per_contact,
        'total_cost': total_cost,
        'total_time_minutes': total_time_minutes,
        'by_strength': by_strength,
        'by_agency': by_agency
    }


def main():
    parser = argparse.ArgumentParser(
        description='Estimate contact research costs'
    )
    parser.add_argument(
        '--filter',
        type=str,
        default=None,
        help='Filter by name/org/agency'
    )
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("CONTACT RESEARCH COST ESTIMATOR")
    print("=" * 70)
    print()
    
    estimates = estimate_costs(filter_text=args.filter)
    
    print(f"📊 Database Overview:")
    print(f"   Total contacts: {estimates['total_contacts']:,}")
    print()
    
    print(f"💰 Cost Estimate:")
    print(f"   Per contact: ${estimates['cost_per_contact']:.3f}")
    print(f"   Total: ${estimates['total_cost']:.2f}")
    print()
    
    print(f"⏱️  Time Estimate:")
    print(f"   Total time: {estimates['total_time_minutes']:.1f} minutes ({estimates['total_time_minutes']/60:.1f} hours)")
    print(f"   Recommendation: Run overnight or during lunch")
    print()
    
    if estimates['by_strength']:
        print(f"📈 By Relationship Strength:")
        for strength, count in sorted(estimates['by_strength'].items()):
            cost = count * estimates['cost_per_contact']
            print(f"   {strength or 'Unknown':15s}: {count:4d} contacts (${cost:.2f})")
        print()
    
    if estimates['by_agency']:
        print(f"🏛️  Top Agencies:")
        for agency, count in estimates['by_agency'][:10]:
            cost = count * estimates['cost_per_contact']
            agency_name = agency[:40] if agency else 'Unknown'
            print(f"   {count:4d} @ ${cost:5.2f}  {agency_name}")
        print()
    
    print("=" * 70)
    print("RECOMMENDATION")
    print("=" * 70)
    print()
    
    if estimates['total_cost'] < 5:
        print(f"✓ Low cost (${estimates['total_cost']:.2f}) — run whenever convenient")
    elif estimates['total_cost'] < 20:
        print(f"✓ Moderate cost (${estimates['total_cost']:.2f}) — good investment for full BD intel")
    else:
        print(f"⚠️  Higher cost (${estimates['total_cost']:.2f}) — consider filtering:")
        print(f"   • Start with 'Strong' relationships only")
        print(f"   • Filter by key agencies (e.g., --filter 'Navy')")
        print(f"   • Research in batches with --limit 100")
    
    print()
    print("Example commands:")
    print(f"  python batch_contact_research.py --limit 100")
    print(f"  python batch_contact_research.py --filter 'Navy'")
    print(f"  python batch_contact_research.py --all  # All {estimates['total_contacts']} contacts")
    print()


if __name__ == '__main__':
    main()
