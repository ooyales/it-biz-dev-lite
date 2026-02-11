#!/usr/bin/env python3
"""
Organization Research Agent
============================
Researches a contractor/company's public presence for teaming purposes:
- Company overview, size, certifications
- Key contracts and agency relationships
- Specializations and capabilities
- Leadership and key personnel
- Press releases and news

This helps BD professionals evaluate potential teaming partners.

Flow:
  1. Receive organization info (name, NAICS codes, agencies)
  2. Build targeted search queries
  3. Search the web for company information
  4. Feed results to Claude for synthesis
  5. Store the research profile in Neo4j on the Organization node
  6. Return structured results to the dashboard
"""

import os
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()


def _research_org_with_claude(org: Dict) -> Dict:
    """
    Single Claude session with web_search enabled.
    Claude searches adaptively, reads results, and synthesizes.
    Returns a structured research profile for an organization.
    """
    import requests

    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        print("   ⚠️  ANTHROPIC_API_KEY not set — cannot research")
        return _fallback_org_summary(org)

    name = org.get('name', 'Unknown')
    naics_codes = org.get('naics_codes', [])
    top_agencies = org.get('top_agencies', [])
    contract_count = org.get('contract_count', 0)
    total_value = org.get('total_value', 0)

    naics_str = ', '.join(naics_codes[:5]) if naics_codes else 'Not specified'
    agencies_str = ', '.join(top_agencies[:3]) if top_agencies else 'Not specified'

    prompt = f"""You are a BD (Business Development) research assistant helping evaluate potential teaming partners in federal contracting.

Research this contractor's PUBLIC information to help assess them as a potential teaming partner.

CONTRACTOR TO RESEARCH:
  Name: {name}
  NAICS Codes: {naics_str}
  Known Agencies: {agencies_str}
  Known Contracts: {contract_count} contracts worth ${total_value:,.0f}

SEARCH STRATEGY:
  1. Search for the company name to find their website and overview
  2. Search for their certifications (8(a), HUBZone, SDVOSB, WOSB, small business status)
  3. Search for recent press releases or news about them
  4. Search for their leadership team or key personnel
  5. Search for any notable contract wins or capabilities

After searching, synthesize your findings into this EXACT JSON structure (return ONLY this JSON, no other text):

{{
  "company_overview": "2-3 sentence description of what the company does",
  "headquarters": "City, State if found",
  "employee_count": "Number or range if found, otherwise 'Unknown'",
  "certifications": ["List of certifications like 8(a), HUBZone, SDVOSB, ISO, CMMI, etc."],
  "capabilities": ["List of 3-5 key service/product capabilities"],
  "key_agencies": ["List of federal agencies they work with"],
  "notable_contracts": ["List of 2-3 notable contract wins if found"],
  "leadership": ["List of key executives with titles if found"],
  "recent_news": ["1-2 recent news items or press releases if found"],
  "teaming_fit": "1-2 sentences on why they might be a good teaming partner",
  "website": "Company website URL if found",
  "sources": ["URLs of sources used"],
  "confidence": "high/medium/low based on how much info you found"
}}

IMPORTANT:
- Focus on FACTS from search results, not speculation
- If you can't find information for a field, use empty list [] or "Unknown"
- Return ONLY the JSON object, no explanation before or after
"""

    # Call Claude API with web_search tool
    headers = {
        "x-api-key": api_key,
        "content-type": "application/json",
        "anthropic-version": "2023-06-01"
    }

    payload = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 2048,
        "tools": [
            {
                "type": "web_search_20250305",
                "name": "web_search",
                "max_uses": 10
            }
        ],
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }

    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=payload,
            timeout=120
        )
        response.raise_for_status()
        data = response.json()

        # Count search rounds (tool_use blocks)
        tool_uses = sum(1 for block in data.get('content', []) if block.get('type') == 'tool_use')
        print(f"   ✓ Claude finished research in {max(1, tool_uses)} round(s)")

        # Extract the text response
        text_content = ""
        for block in data.get('content', []):
            if block.get('type') == 'text':
                text_content += block.get('text', '')

        # Parse JSON from response
        if text_content:
            # Find JSON in the response
            import re
            json_match = re.search(r'\{[\s\S]*\}', text_content)
            if json_match:
                profile = json.loads(json_match.group())
                profile['researched_at'] = datetime.now().isoformat()
                profile['method'] = 'claude_web_search'
                return profile

        return _fallback_org_summary(org)

    except requests.exceptions.HTTPError as e:
        print(f"   ⚠️  Claude research error: {e}")
        return _fallback_org_summary(org)
    except json.JSONDecodeError as e:
        print(f"   ⚠️  Failed to parse Claude response: {e}")
        return _fallback_org_summary(org)
    except Exception as e:
        print(f"   ⚠️  Research error: {e}")
        return _fallback_org_summary(org)


def _fallback_org_summary(org: Dict) -> Dict:
    """Fallback when Claude research fails."""
    return {
        "company_overview": f"Federal contractor with government contracts",
        "headquarters": "Unknown",
        "employee_count": "Unknown",
        "certifications": [],
        "capabilities": [],
        "key_agencies": org.get('top_agencies', []),
        "notable_contracts": [],
        "leadership": [],
        "recent_news": [],
        "teaming_fit": "Unable to research - please try again later",
        "website": "",
        "sources": [],
        "confidence": "low",
        "researched_at": datetime.now().isoformat(),
        "method": "fallback"
    }


class OrganizationResearchAgent:
    """Agent that researches organizations for teaming partner evaluation."""

    CACHE_TTL_DAYS = 14  # Re-research after 2 weeks

    def __init__(self):
        from neo4j import GraphDatabase

        self.driver = GraphDatabase.driver(
            os.getenv('NEO4J_URI', 'bolt://localhost:7687'),
            auth=('neo4j', os.getenv('NEO4J_PASSWORD'))
        )
        print("✓ OrganizationResearchAgent initialized")

    def research_organization(self, org: Dict, force_refresh: bool = False) -> Dict:
        """
        Research an organization's public presence.
        
        Args:
            org: Dict with 'name' and optionally 'naics_codes', 'top_agencies', etc.
            force_refresh: If True, ignore cache and re-research
        
        Returns:
            Research profile dict
        """
        name = org.get('name', 'Unknown')
        print(f"\n🔍 Researching: {name}")

        # Check cache first
        if not force_refresh:
            cached = self._get_cached_research(org)
            if cached:
                print(f"   ✓ Using cached research (from {cached.get('researched_at', 'unknown')})")
                cached['method'] = 'cached'
                return cached

        # Research with Claude
        print(f"   🤖 Launching AI research...")
        profile = _research_org_with_claude(org)

        # Cache the results
        self._cache_research(org, profile)

        print(f"   ✓ Research complete (confidence: {profile.get('confidence', 'unknown')})")
        return profile

    def _get_cached_research(self, org: Dict) -> Optional[Dict]:
        """Check if we have fresh research cached on this Organization node."""
        name = org.get('name', '').strip()

        if not name:
            return None

        with self.driver.session(database="neo4j") as session:
            result = session.run(
                "MATCH (o:Organization) WHERE o.name = $name RETURN o.research_profile as profile",
                name=name
            )

            row = result.single()
            if not row or not row['profile']:
                return None

            # Parse cached profile
            try:
                profile = json.loads(row['profile']) if isinstance(row['profile'], str) else row['profile']
            except (json.JSONDecodeError, TypeError):
                return None

            # Check staleness
            researched_at = profile.get('researched_at')
            if researched_at:
                researched_date = datetime.fromisoformat(researched_at)
                if datetime.now() - researched_date > timedelta(days=self.CACHE_TTL_DAYS):
                    print(f"   📅 Cached research is stale ({researched_at}) — refreshing")
                    return None

            return profile

    def _cache_research(self, org: Dict, profile: Dict):
        """Store research profile on the Organization node in Neo4j."""
        name = org.get('name', '').strip()
        profile_json = json.dumps(profile)

        print(f"   DEBUG: Attempting to cache for org: [{name}]")

        if not name:
            print(f"   ⚠️  No name to cache research for")
            return

        with self.driver.session(database="neo4j") as session:
            # First check if the org exists
            check_result = session.run("""
                MATCH (o:Organization)
                WHERE o.name = $name
                RETURN count(o) as found
            """, name=name)
            check_row = check_result.single()
            print(f"   DEBUG: Found {check_row['found']} Organization nodes with name [{name}]")

            # Match by exact name
            result = session.run("""
                MATCH (o:Organization)
                WHERE o.name = $name
                SET o.research_profile = $profile,
                    o.research_updated_at = datetime()
                RETURN count(o) as updated
            """, name=name, profile=profile_json)

            row = result.single()
            print(f"   DEBUG: Updated {row['updated'] if row else 0} nodes")
            if row and row['updated'] > 0:
                print(f"   💾 Research cached in Neo4j")
            else:
                print(f"   ⚠️  No matching Organization node found for '{name}'")

    def close(self):
        self.driver.close()


# ---------------------------------------------------------------------------
# Standalone test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    agent = OrganizationResearchAgent()

    # Example: research a test organization
    test_org = {
        'name': 'BOOZ ALLEN HAMILTON',
        'naics_codes': ['541512', '541511'],
        'top_agencies': ['Department of Defense', 'Department of Homeland Security'],
        'contract_count': 50,
        'total_value': 100000000
    }

    result = agent.research_organization(test_org, force_refresh=True)
    print("\n📋 Research Results:")
    print(json.dumps(result, indent=2))

    agent.close()
