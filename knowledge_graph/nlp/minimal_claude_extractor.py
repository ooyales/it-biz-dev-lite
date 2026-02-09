#!/usr/bin/env python3
"""
Minimal Claude Extractor - No anthropic package required!
Uses direct HTTP requests to Claude API
"""

import requests
import json
import logging
import os
from typing import Dict, List, Tuple
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class Entity:
    """Extracted entity"""
    text: str
    type: str
    confidence: float
    metadata: Dict = None


@dataclass
class Relationship:
    """Extracted relationship"""
    subject: str
    relation: str
    object: str
    confidence: float
    metadata: Dict = None


class MinimalClaudeExtractor:
    """
    Claude extractor using only HTTP requests
    No anthropic package required!
    
    Uses requests library (standard with Python)
    """
    
    def __init__(self, api_key: str = None):
        """
        Initialize extractor
        
        Args:
            api_key: Anthropic API key (or set ANTHROPIC_API_KEY env var)
        """
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        
        if not self.api_key:
            raise ValueError(
                "Anthropic API key required. "
                "Set ANTHROPIC_API_KEY env var or pass api_key parameter. "
                "Get key at: https://console.anthropic.com/"
            )
        
        self.api_url = "https://api.anthropic.com/v1/messages"
        self.headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        # Track usage
        self.usage_stats = {
            'extractions': 0,
            'tokens_input': 0,
            'tokens_output': 0,
            'estimated_cost': 0.0
        }
        
        logger.info("✓ Minimal Claude extractor initialized (HTTP-only)")
    
    def extract(
        self, 
        text: str, 
        extract_relationships: bool = True
    ) -> Tuple[List[Entity], List[Relationship]]:
        """Extract entities and relationships"""
        
        logger.info(f"Extracting from {len(text)} characters...")
        
        try:
            # Build prompt
            prompt = self._build_prompt(text, extract_relationships)
            
            # Make API request
            payload = {
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 4000,
                "temperature": 0,
                "messages": [{
                    "role": "user",
                    "content": prompt
                }]
            }
            
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=payload,
                timeout=60
            )
            
            # Check for errors
            if response.status_code != 200:
                logger.error(f"API error {response.status_code}: {response.text}")
                return [], []
            
            data = response.json()
            
            # Track usage
            usage = data.get('usage', {})
            self.usage_stats['extractions'] += 1
            self.usage_stats['tokens_input'] += usage.get('input_tokens', 0)
            self.usage_stats['tokens_output'] += usage.get('output_tokens', 0)
            
            # Calculate cost
            input_cost = (usage.get('input_tokens', 0) / 1_000_000) * 3.00
            output_cost = (usage.get('output_tokens', 0) / 1_000_000) * 15.00
            self.usage_stats['estimated_cost'] += input_cost + output_cost
            
            # Parse response
            content = data.get('content', [])
            if not content:
                logger.error("No content in response")
                return [], []
            
            response_text = content[0].get('text', '')
            
            # Clean JSON
            if '```json' in response_text:
                response_text = response_text.split('```json')[1].split('```')[0]
            elif '```' in response_text:
                response_text = response_text.split('```')[1].split('```')[0]
            
            result = json.loads(response_text.strip())
            
            # Convert to objects
            entities = [
                Entity(
                    text=e['text'],
                    type=e['type'],
                    confidence=e.get('confidence', 0.95),
                    metadata=e.get('metadata', {})
                )
                for e in result.get('entities', [])
            ]
            
            relationships = [
                Relationship(
                    subject=r['subject'],
                    relation=r['relation'],
                    object=r['object'],
                    confidence=r.get('confidence', 0.90),
                    metadata=r.get('metadata', {})
                )
                for r in result.get('relationships', [])
            ] if extract_relationships else []
            
            logger.info(f"✓ Extracted {len(entities)} entities, {len(relationships)} relationships")
            logger.info(f"  Cost: ${input_cost + output_cost:.4f}")
            
            return entities, relationships
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse response: {e}")
            logger.error(f"Response: {response_text[:500]}...")
            return [], []
        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            return [], []
    
    def _build_prompt(self, text: str, extract_relationships: bool) -> str:
        """Build extraction prompt"""
        
        prompt = f"""Extract structured contact information from this text:

<text>
{text}
</text>

Extract:
1. PEOPLE - Names, titles, emails, phones
2. ORGANIZATIONS - Agencies, companies
3. TITLES - Job titles
4. LOCATIONS - Cities, states"""

        if extract_relationships:
            prompt += """
5. RELATIONSHIPS - WORKS_AT, REPORTS_TO, etc."""

        prompt += """

Return ONLY valid JSON:

{
  "entities": [
    {
      "text": "Sarah Johnson",
      "type": "PERSON",
      "confidence": 0.95,
      "metadata": {
        "email": "sarah.j@disa.mil",
        "title": "Contracting Officer"
      }
    }
  ],"""

        if extract_relationships:
            prompt += """
  "relationships": [
    {
      "subject": "Sarah Johnson",
      "relation": "WORKS_AT",
      "object": "DISA",
      "confidence": 0.95
    }
  ]"""
        else:
            prompt += """
  "relationships": []"""

        prompt += """
}

IMPORTANT:
- Use full names
- Normalize titles (CO → Contracting Officer)
- Extract all available info
- Be accurate!"""

        return prompt
    
    def get_cost_estimate(self) -> Dict:
        """Get usage statistics"""
        return {
            'extractions': self.usage_stats['extractions'],
            'tokens_input': self.usage_stats['tokens_input'],
            'tokens_output': self.usage_stats['tokens_output'],
            'tokens_total': self.usage_stats['tokens_input'] + self.usage_stats['tokens_output'],
            'estimated_cost': round(self.usage_stats['estimated_cost'], 2),
            'avg_cost_per_extraction': round(
                self.usage_stats['estimated_cost'] / max(self.usage_stats['extractions'], 1), 
                4
            )
        }


# Test it
if __name__ == "__main__":
    print("\n" + "="*70)
    print("MINIMAL CLAUDE EXTRACTOR TEST (No anthropic package!)")
    print("="*70 + "\n")
    
    if not os.getenv('ANTHROPIC_API_KEY'):
        print("⚠️  Set ANTHROPIC_API_KEY environment variable first")
        print("export ANTHROPIC_API_KEY='your-key-here'")
        exit(1)
    
    extractor = MinimalClaudeExtractor()
    
    text = """
    Sarah Johnson
    Contracting Officer
    Defense Information Systems Agency (DISA)
    Email: sarah.johnson@disa.mil
    Phone: (703) 555-0123
    """
    
    print("Extracting from sample text...\n")
    
    entities, relationships = extractor.extract(text)
    
    print("Entities:")
    for e in entities:
        print(f"  {e.type}: {e.text}")
        if e.metadata:
            for k, v in e.metadata.items():
                print(f"    {k}: {v}")
    
    print(f"\nRelationships: {len(relationships)}")
    for r in relationships:
        print(f"  {r.subject} --{r.relation}--> {r.object}")
    
    stats = extractor.get_cost_estimate()
    print(f"\nCost: ${stats['estimated_cost']:.4f}")
    print("\n✓ Working! No anthropic package needed!")
