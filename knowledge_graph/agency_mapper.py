#!/usr/bin/env python3
"""
Agency Name Mapper
Maps SAM.gov agency names to your Neo4j organization names

This solves the problem where:
- SAM.gov says "DEPT OF DEFENSE" 
- But your contacts are at "Army", "Navy", "DLA", etc.
"""

# Agency mapping dictionary
AGENCY_MAPPINGS = {
    # Department of Defense and sub-agencies
    'DEPT OF DEFENSE': ['Army', 'U.S. Army', 'NAVY', 'US NAVY', 'U.S. Air Force', 
                        'US Air Force', 'DLA', 'DTRA', 'Defense Information Systems Agency',
                        'USACE'],
    'DEPARTMENT OF DEFENSE': ['Army', 'U.S. Army', 'NAVY', 'US NAVY', 'U.S. Air Force',
                              'US Air Force', 'DLA', 'DTRA', 'Defense Information Systems Agency',
                              'USACE'],
    'DEFENSE LOGISTICS AGENCY': ['DLA'],
    'ARMY': ['Army', 'U.S. Army', 'USACE'],
    'NAVY': ['NAVY', 'US NAVY'],
    'AIR FORCE': ['U.S. Air Force', 'US Air Force'],
    
    # Homeland Security
    'DEPT OF HOMELAND SECURITY': ['Department of Homeland Security', 'USCG'],
    'DEPARTMENT OF HOMELAND SECURITY': ['Department of Homeland Security', 'USCG'],
    'USCG': ['USCG'],
    'COAST GUARD': ['USCG'],
    
    # General Services Administration
    'GENERAL SERVICES ADMINISTRATION': ['GSA', 'General Services Administration'],
    'GSA': ['GSA', 'General Services Administration'],
    
    # NASA
    'NASA': ['NASA'],
    'NATIONAL AERONAUTICS AND SPACE ADMINISTRATION': ['NASA'],
    
    # Treasury
    'BUREAU OF ENGRAVING AND PRINTING': ['Bureau of Engraving and Printing'],
    
    # Interior
    'U.S. FISH AND WILDLIFE SERVICE': ['U.S. Fish and Wildlife Service'],
    'FISH AND WILDLIFE SERVICE': ['U.S. Fish and Wildlife Service'],
    
    # Agriculture
    'AGRICULTURE, DEPARTMENT OF': ['USDA'],
    'DEPARTMENT OF AGRICULTURE': ['USDA'],

    # Justice
    'JUSTICE, DEPARTMENT OF': ['DOJ', 'Department of Justice', 'FBI'],
    'DEPARTMENT OF JUSTICE': ['DOJ', 'Department of Justice', 'FBI'],
    'FEDERAL BUREAU OF INVESTIGATION': ['FBI'],
    'FEDERAL PRISON SYSTEM / BUREAU OF PRISONS': ['Bureau of Prisons', 'BOP'],

    # Veterans Affairs
    'VETERANS AFFAIRS, DEPARTMENT OF': ['VA', 'Department of Veterans Affairs'],
    'DEPARTMENT OF VETERANS AFFAIRS': ['VA', 'Department of Veterans Affairs'],

    # Health and Human Services
    'HEALTH AND HUMAN SERVICES, DEPARTMENT OF': ['HHS', 'Department of Health and Human Services'],

    # State Department
    'STATE, DEPARTMENT OF': ['DOS', 'Department of State', 'State Department'],

    # Transportation
    'TRANSPORTATION, DEPARTMENT OF': ['DOT', 'Department of Transportation', 'FAA'],
    'FEDERAL AVIATION ADMINISTRATION': ['FAA'],

    # Energy
    'ENERGY, DEPARTMENT OF': ['DOE', 'Department of Energy'],

    # Commerce
    'COMMERCE, DEPARTMENT OF': ['DOC', 'Department of Commerce', 'NOAA'],
    'NATIONAL OCEANIC AND ATMOSPHERIC ADMINISTRATION': ['NOAA'],

    # Homeland Security sub-agencies
    'HOMELAND SECURITY, DEPARTMENT OF': ['Department of Homeland Security', 'DHS', 'TSA', 'USCG'],
    'TRANSPORTATION SECURITY ADMINISTRATION': ['TSA'],

    # Social Security
    'SSA': ['SSA'],
    'SOCIAL SECURITY ADMINISTRATION': ['SSA'],

    # National Park Service
    'NPS': ['NPS'],
    'NATIONAL PARK SERVICE': ['NPS'],

    # Other agencies in scout data
    'FEDERAL COMMUNICATIONS COMMISSION': ['FCC'],
    'FEDERAL DEPOSIT INSURANCE CORPORATION': ['FDIC'],
    'LIBRARY OF CONGRESS': ['Library of Congress'],
    'DEFENSE INFORMATION SYSTEMS AGENCY (DISA)': ['DISA', 'Defense Information Systems Agency'],
    'NATIONAL GEOSPATIAL-INTELLIGENCE AGENCY (NGA)': ['NGA'],
}

# Keywords for fuzzy matching
KEYWORD_MAPPINGS = {
    'DEFENSE': ['Army', 'U.S. Army', 'NAVY', 'US NAVY', 'U.S. Air Force', 'US Air Force', 
                'DLA', 'DTRA', 'Defense Information Systems Agency', 'USACE'],
    'ARMY': ['Army', 'U.S. Army', 'USACE'],
    'NAVY': ['NAVY', 'US NAVY'],
    'AIR FORCE': ['U.S. Air Force', 'US Air Force'],
    'COAST GUARD': ['USCG'],
    'HOMELAND': ['Department of Homeland Security', 'USCG'],
    'GSA': ['GSA', 'General Services Administration'],
    'NASA': ['NASA'],
    'ENGRAVING': ['Bureau of Engraving and Printing'],
    'FISH': ['U.S. Fish and Wildlife Service'],
    'WILDLIFE': ['U.S. Fish and Wildlife Service'],
    'SOCIAL SECURITY': ['SSA'],
    'PARK': ['NPS'],
    'JUSTICE': ['DOJ', 'Department of Justice', 'FBI'],
    'VETERANS': ['VA', 'Department of Veterans Affairs'],
    'HEALTH AND HUMAN': ['HHS', 'Department of Health and Human Services'],
    'STATE': ['DOS', 'Department of State', 'State Department'],
    'TRANSPORTATION': ['DOT', 'Department of Transportation', 'FAA'],
    'ENERGY': ['DOE', 'Department of Energy'],
    'COMMERCE': ['DOC', 'Department of Commerce', 'NOAA'],
    'DISA': ['DISA', 'Defense Information Systems Agency'],
    'NGA': ['NGA'],
    'FBI': ['FBI'],
    'TSA': ['TSA'],
    'NOAA': ['NOAA'],
    'FAA': ['FAA'],
    'FCC': ['FCC'],
    'FDIC': ['FDIC'],
    'PRISON': ['Bureau of Prisons', 'BOP'],
    'NAVAIR': ['NAVY', 'US NAVY', 'NAVAIR'],
    'NAVSEA': ['NAVY', 'US NAVY', 'NAVSEA'],
    'SPAWAR': ['NAVY', 'US NAVY', 'SPAWAR', 'NIWC'],
}


def map_agency_to_orgs(agency_name: str) -> list:
    """
    Map a SAM.gov agency name to possible Neo4j organization names
    
    Args:
        agency_name: Agency name from SAM.gov (e.g., "DEPT OF DEFENSE")
        
    Returns:
        List of possible organization names in Neo4j
    """
    if not agency_name:
        return []
    
    agency_upper = agency_name.upper().strip()
    
    # Try exact mapping first
    if agency_upper in AGENCY_MAPPINGS:
        return AGENCY_MAPPINGS[agency_upper]
    
    # Try keyword matching
    possible_orgs = set()
    for keyword, orgs in KEYWORD_MAPPINGS.items():
        if keyword in agency_upper:
            possible_orgs.update(orgs)
    
    return list(possible_orgs)


def get_contacts_for_agency(kg_client, agency_name: str) -> dict:
    """
    Get contacts for an agency using fuzzy matching
    
    Args:
        kg_client: KnowledgeGraphClient instance
        agency_name: Agency name from SAM.gov
        
    Returns:
        Dict with contacts categorized by role
    """
    # Map agency to possible organizations
    possible_orgs = map_agency_to_orgs(agency_name)
    
    if not possible_orgs:
        return {
            'total_contacts': 0,
            'decision_makers': [],
            'technical_leads': [],
            'executives': [],
            'influencers': [],
            'all_contacts': []
        }
    
    # Query for contacts at any of these organizations (SQLite)
    placeholders = ','.join('?' for _ in possible_orgs)
    conn = kg_client._conn()
    rows = conn.execute(f"""
        SELECT c.name, c.email, c.phone, c.title,
               c.role as role_type,
               c.relationship_strength as influence_level,
               COALESCE(o.name, c.organization) as organization
        FROM contacts c
        LEFT JOIN graph_edges e ON e.from_id = c.graph_id AND e.rel_type = 'WORKS_AT'
        LEFT JOIN organizations o ON o.id = e.to_id
        WHERE o.name IN ({placeholders})
           OR c.organization IN ({placeholders})
           OR c.agency IN ({placeholders})
    """, possible_orgs + possible_orgs + possible_orgs).fetchall()
    conn.close()
    contacts = [dict(row) for row in rows]
    
    # Categorize contacts
    decision_makers = [c for c in contacts if c.get('role_type') == 'Decision Maker']
    technical_leads = [c for c in contacts if c.get('role_type') == 'Technical Lead']
    executives = [c for c in contacts if c.get('role_type') == 'Executive']
    influencers = [c for c in contacts if c.get('role_type') == 'Influencer']
    
    return {
        'total_contacts': len(contacts),
        'decision_makers': decision_makers,
        'technical_leads': technical_leads,
        'executives': executives,
        'influencers': influencers,
        'all_contacts': contacts,
        'matched_orgs': possible_orgs  # For debugging
    }


if __name__ == '__main__':
    # Test the mapping
    test_agencies = [
        "DEPT OF DEFENSE",
        "GENERAL SERVICES ADMINISTRATION",
        "DEPARTMENT OF HOMELAND SECURITY",
        "NASA",
        "ARMY",
        "Unknown Agency"
    ]
    
    print("Agency Mapping Test:")
    print("="*70)
    for agency in test_agencies:
        orgs = map_agency_to_orgs(agency)
        print(f"\n{agency}")
        print(f"  → Maps to: {orgs}")
