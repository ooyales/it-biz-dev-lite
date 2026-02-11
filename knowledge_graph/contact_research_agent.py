#!/usr/bin/env python3
"""
Contact Research Agent
========================
Researches a contact's public professional presence — blog posts,
articles, conference talks, LinkedIn activity, YouTube — and
summarizes what they care about in their professional life.

This is the same kind of background prep a BD developer would do
manually before an engagement. The agent automates it.

Flow:
  1. Receive contact info (name, title, agency, email)
  2. Build targeted search queries
  3. Search the web for their public writings and appearances
  4. Feed results to Claude for synthesis
  5. Store the research profile in SQLite via KnowledgeGraphClient
  6. Return structured results to the dashboard

Design decisions:
  - Framed as "Professional Research" not monitoring
  - Only surfaces PUBLIC information
  - Summarizes themes/interests, not personal details
  - Cached in SQLite so we don't re-research every time
  - Respects a staleness window (re-research after 180 days)
"""

import os
import sys
import json
import time
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()

from graph.graph_client import KnowledgeGraphClient


# ---------------------------------------------------------------------------
# Core research function — Claude with web_search tool
# ---------------------------------------------------------------------------
# Design note: Rather than running searches ourselves and feeding snippets
# to Claude, we give Claude the web_search tool and let it search AND
# synthesize in one session. Claude picks queries adaptively based on what
# it finds, which is more effective than static query templates.
# Result: fewer API calls, better research quality.

def _research_with_claude(contact: Dict) -> Dict:
    """
    Single Claude session with web_search enabled.
    Claude searches adaptively, reads results, and synthesizes.
    Returns a structured research profile.
    """
    import requests

    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        print("   ⚠️  ANTHROPIC_API_KEY not set — cannot research")
        return _fallback_summary(contact, [])

    name = contact.get('name', 'Unknown')
    title = contact.get('title', '')
    agency = contact.get('agency', '') or contact.get('organization', '')

    prompt = f"""You are a BD (Business Development) research assistant. Your job is to do background research on a federal government contact — the same kind of prep a BD professional would do manually before an engagement.

Search the web for this person's PUBLIC professional presence: blog posts, articles, conference talks, YouTube appearances, industry publications, LinkedIn activity. Focus on what they write and talk about professionally.

CONTACT TO RESEARCH:
  Name:   {name}
  Title:  {title}
  Agency: {agency}

SEARCH STRATEGY:
  1. Search for their name + agency to find their professional profile
  2. Search for their name + any technical topics they're known for
  3. Search for conference talks or presentations they've given
  4. Search for any blog posts or articles they've authored

After searching, synthesize your findings into this EXACT JSON structure (return ONLY this JSON, no other text):

{{
  "key_interests": ["3-5 professional topics they care about based on what you found"],
  "technical_focus": ["specific technologies or methodologies they write/speak about"],
  "priorities": ["what challenges or initiatives seem important to them"],
  "talking_points": ["2-3 suggested conversation topics that would resonate with this person"],
  "sources": ["the most relevant URLs you found"],
  "confidence": "high | medium | low — based on how much relevant info you actually found",
  "summary": "2-3 sentence plain-English summary of their professional focus and what they care about"
}}

IMPORTANT:
- Only reference PUBLIC, professional information
- Focus on professional/technical interests, not personal life
- If you can't find much, be honest — set confidence to "low" and say so
- This is professional research prep, not surveillance
- Return ONLY valid JSON, no preamble"""

    messages = [{'role': 'user', 'content': prompt}]
    raw_text = ""

    try:
        # Claude may do multiple search rounds before giving final answer.
        # We loop, passing tool results back each time.
        for attempt in range(8):  # Max 8 rounds of searching
            resp = requests.post(
                'https://api.anthropic.com/v1/messages',
                headers={
                    'x-api-key': api_key,
                    'anthropic-version': '2023-06-01',
                    'content-type': 'application/json',
                },
                json={
                    'model': 'claude-sonnet-4-20250514',
                    'max_tokens': 2000,
                    'tools': [{'type': 'web_search_20250305', 'name': 'web_search'}],
                    'messages': messages
                },
                timeout=60
            )
            resp.raise_for_status()
            response_data = resp.json()
            stop_reason = response_data.get('stop_reason', '')

            # Grab any text blocks from this response
            for block in response_data.get('content', []):
                if block.get('type') == 'text':
                    raw_text = block.get('text', '').strip()

            # Done — Claude finished and gave us the final answer
            if stop_reason == 'end_turn':
                print(f"   ✓ Claude finished research in {attempt + 1} round(s)")
                break

            # Claude wants to search more — pass the response back
            if stop_reason == 'tool_use':
                messages.append({'role': 'assistant', 'content': response_data['content']})
                # web_search_20250305 is server-side: results come back in the
                # next response automatically. We just need to pass a tool_result
                # placeholder so the API knows we acknowledged the tool call.
                tool_use_block = next(
                    (b for b in response_data['content'] if b.get('type') == 'tool_use'), None
                )
                if tool_use_block:
                    messages.append({
                        'role': 'user',
                        'content': [{
                            'type': 'tool_result',
                            'tool_use_id': tool_use_block['id'],
                            'content': ''
                        }]
                    })
                continue

            # Any other stop reason — bail
            print(f"   ⚠️  Unexpected stop_reason: {stop_reason}")
            break

        # Parse the structured JSON from Claude's final text.
        # Claude sometimes puts explanatory prose BEFORE the JSON block,
        # so we can't just assume the text starts with ```. Search for it.
        if not raw_text:
            print("   ⚠️  Claude returned no text")
            return _fallback_summary(contact, [])

        text = raw_text
        json_str = None

        # Strategy 1: find a ```json ... ``` fenced block anywhere in the text
        if '```json' in text:
            start = text.index('```json') + len('```json')
            remainder = text[start:]
            end = remainder.index('```') if '```' in remainder else len(remainder)
            json_str = remainder[:end].strip()

        # Strategy 2: find a bare ``` block (no language tag)
        elif text.count('```') >= 2:
            parts = text.split('```')
            # parts[1] is between the first pair of fences
            json_str = parts[1].strip()

        # Strategy 3: no fences at all — maybe the whole text is JSON
        else:
            json_str = text.strip()

        # Try to parse
        try:
            result = json.loads(json_str)
            result['researched_at'] = datetime.now().isoformat()
            result['method'] = 'claude_web_search'
            return result
        except (json.JSONDecodeError, TypeError):
            pass

        # Strategy 4: find a raw { ... } block (Claude skipped fences entirely)
        if '{' in text and '}' in text:
            brace_start = text.index('{')
            brace_end = text.rindex('}') + 1
            try:
                result = json.loads(text[brace_start:brace_end])
                result['researched_at'] = datetime.now().isoformat()
                result['method'] = 'claude_web_search'
                return result
            except (json.JSONDecodeError, TypeError):
                pass

        # All JSON extraction failed — return the prose portion only as summary.
        # Strip any JSON-looking fragments so the summary is clean.
        prose = text
        if '```' in prose:
            prose = prose[:prose.index('```')].strip()
        if '{' in prose:
            prose = prose[:prose.index('{')].strip()
        if not prose:
            prose = 'Research completed but could not extract structured results.'

        print(f"   ⚠️  Claude returned non-JSON, using prose as summary")
        return {
            'summary': prose[:500],
            'key_interests': [],
            'technical_focus': [],
            'priorities': [],
            'talking_points': [],
            'sources': [],
            'confidence': 'low',
            'researched_at': datetime.now().isoformat(),
            'method': 'claude_raw'
        }
    except Exception as e:
        print(f"   ⚠️  Claude research error: {e}")
        return _fallback_summary(contact, [])


def _fallback_summary(contact: Dict, findings: List[Dict]) -> Dict:
    """Fallback when Claude isn't available — just structure the raw findings."""
    return {
        'summary': f"Found {len(findings)} public sources for {contact.get('name', 'this contact')}. Claude synthesis unavailable — raw findings included.",
        'key_interests': [],
        'technical_focus': [],
        'priorities': [],
        'talking_points': [],
        'sources': [f.get('url') for f in findings if f.get('url')],
        'raw_findings': findings,
        'confidence': 'low',
        'researched_at': datetime.now().isoformat(),
        'method': 'fallback'
    }


# ---------------------------------------------------------------------------
# Main Agent Class
# ---------------------------------------------------------------------------

class ContactResearchAgent:
    """
    Researches a contact's public professional presence and
    stores the results in SQLite via KnowledgeGraphClient.
    """

    CACHE_TTL_DAYS = 180  # Re-research after this many days

    def __init__(self):
        self.kg = KnowledgeGraphClient()
        print("✓ ContactResearchAgent initialized (SQLite via KnowledgeGraphClient)")

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------
    def research_contact(self, contact: Dict, force_refresh: bool = False) -> Dict:
        """
        Main entry point. Researches a contact and returns the profile.

        Args:
            contact: Dict with at minimum 'name'. Optionally 'title',
                     'agency', 'organization', 'email', 'id'.
            force_refresh: Skip cache and re-research.

        Returns:
            Research profile dict with interests, themes, sources, etc.
        """
        name = contact.get('name', '').strip()
        if not name:
            return {'error': 'Contact name is required'}

        print(f"\n🔍 Researching: {name}")
        print(f"   Title: {contact.get('title', 'N/A')}")
        print(f"   Agency: {contact.get('agency', contact.get('organization', 'N/A'))}")

        # Check cache first
        if not force_refresh:
            cached = self._get_cached_research(contact)
            if cached:
                print(f"   ✓ Using cached research (from {cached.get('researched_at', 'unknown')})")
                return cached

        # Research via Claude + web search
        print(f"   🤖 Launching AI research...")
        profile = _research_with_claude(contact)

        # Cache in SQLite
        self._cache_research(contact, profile)

        print(f"   ✓ Research complete (confidence: {profile.get('confidence', 'unknown')})")
        return profile

    # ------------------------------------------------------------------
    # Cache layer (SQLite via KnowledgeGraphClient)
    # ------------------------------------------------------------------
    def _get_cached_research(self, contact: Dict) -> Optional[Dict]:
        """Check SQLite for cached research via KnowledgeGraphClient."""
        name = contact.get('name', '').strip()

        if not name:
            return None

        profile = None
        try:
            profile = self.kg.get_research_profile(name)
        except Exception:
            pass

        if not profile:
            return None

        # Check staleness
        researched_at = profile.get('researched_at')
        if researched_at:
            researched_date = datetime.fromisoformat(researched_at)
            if datetime.now() - researched_date > timedelta(days=self.CACHE_TTL_DAYS):
                print(f"   📅 Cached research is stale ({researched_at}) — refreshing")
                return None

        return profile

    def _cache_research(self, contact: Dict, profile: Dict):
        """Store research profile in SQLite via KnowledgeGraphClient."""
        name = contact.get('name', '').strip()

        if not name:
            print(f"   ⚠️  No name to cache research for")
            return

        try:
            if self.kg.set_research_profile(name, profile):
                print(f"   💾 Research cached in SQLite")
            else:
                print(f"   ⚠️  No matching contact in SQLite for '{name}'")
        except Exception as e:
            print(f"   ⚠️  SQLite cache write failed: {e}")

    def close(self):
        if self.kg:
            self.kg.close()


# ---------------------------------------------------------------------------
# Standalone test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    agent = ContactResearchAgent()

    # Example: research a test contact
    test_contact = {
        'name': 'John Smith',
        'title': 'Program Manager',
        'agency': 'Department of Defense',
        'organization': 'DEPT OF DEFENSE',
    }

    result = agent.research_contact(test_contact, force_refresh=True)

    print("\n" + "=" * 70)
    print("RESEARCH RESULTS")
    print("=" * 70)
    print(json.dumps(result, indent=2))

    agent.close()
