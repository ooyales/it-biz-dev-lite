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
    
    # Social Security
    'SSA': ['SSA'],
    'SOCIAL SECURITY ADMINISTRATION': ['SSA'],
    
    # National Park Service
    'NPS': ['NPS'],
    'NATIONAL PARK SERVICE': ['NPS'],
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
    
    # Query for contacts at any of these organizations
    with kg_client.driver.session(database="contactsgraphdb") as session:
        query = """
        MATCH (p:Person)-[:WORKS_AT]->(o:Organization)
        WHERE o.name IN $org_names
        RETURN p.name as name,
               p.email as email,
               p.phone as phone,
               p.title as title,
               p.role_type as role_type,
               p.influence_level as influence_level,
               o.name as organization
        """
        
        result = session.run(query, org_names=possible_orgs)
        contacts = [dict(record) for record in result]
    
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
