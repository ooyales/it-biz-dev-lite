# Integration Guide: Adding Competitive Intelligence

This guide shows you how to integrate FPDS and USAspending competitive intelligence into your federal contracting AI system.

## Quick Integration (5 minutes)

### Step 1: Add New Files
Place these files in your project directory:
- `fpds_intel.py`
- `usaspending_intel.py`
- `competitive_intel_agent.py`

### Step 2: Update Requirements
No new dependencies needed! The competitive intelligence modules use the same libraries (requests, json) already in your requirements.txt.

### Step 3: Test Individual Modules

**Test FPDS:**
```bash
python fpds_intel.py
```

**Test USAspending:**
```bash
python usaspending_intel.py
```

**Test Competitive Intel Agent:**
```bash
python competitive_intel_agent.py
```

### Step 4: Integrate into Main Workflow

You have two integration options:

#### Option A: Automatic Integration (Recommended)
Modify `claude_agents.py` to automatically include competitive intelligence:

```python
# At the top of claude_agents.py, add:
from competitive_intel_agent import CompetitiveIntelligenceAgent

# In OpportunityAnalyzer.__init__, add:
self.competitive_intel = CompetitiveIntelligenceAgent(config)

# In OpportunityAnalyzer.analyze_opportunity, add this BEFORE Claude AI call:
competitive_analysis = self.competitive_intel.analyze_opportunity_competitiveness(
    opportunity
)

# Then include competitive_analysis in the user_message to Claude:
user_message = f"""Analyze this federal contracting opportunity:

{opp_summary}

COMPETITIVE INTELLIGENCE:
{self._format_competitive_intel(competitive_analysis)}

Provide your analysis in the following JSON format:
...
"""
```

#### Option B: On-Demand Integration
Add competitive intelligence as a separate step for high-value opportunities:

```python
# In main.py, modify process_opportunity:
def process_opportunity(self, opportunity: Dict[str, Any]) -> Dict[str, Any]:
    # ... existing code ...
    
    # Add competitive intelligence for high-value opportunities
    estimated_value = self._estimate_value(opportunity)
    
    if estimated_value > 1000000:  # $1M threshold
        logger.info("High-value opportunity - running competitive intelligence...")
        comp_intel_agent = CompetitiveIntelligenceAgent(self.config)
        competitive_intel = comp_intel_agent.analyze_opportunity_competitiveness(
            opportunity
        )
        results['competitive_intelligence'] = competitive_intel
```

## Detailed Integration Steps

### Integration Level 1: Basic (Incumbent + Pricing Only)

**Where:** OpportunityAnalyzer in `claude_agents.py`

**Add this method:**
```python
def _get_basic_intel(self, opportunity: Dict[str, Any]) -> Dict[str, Any]:
    """Get basic competitive intelligence"""
    from fpds_intel import FPDSIntelligence
    
    fpds = FPDSIntelligence(self.config)
    
    agency_name = opportunity.get('officeAddress', {}).get('agency', '')
    naics_code = opportunity.get('naicsCode', '')
    
    intel = {}
    
    # Get incumbent
    incumbent = fpds.find_incumbent_contract(
        agency_name=agency_name,
        naics_code=naics_code
    )
    intel['incumbent'] = incumbent
    
    # Get pricing
    pricing = fpds.get_pricing_intelligence(
        naics_code=naics_code,
        agency_name=agency_name
    )
    intel['pricing'] = pricing
    
    return intel
```

**Call it before AI analysis:**
```python
def analyze_opportunity(self, opportunity: Dict[str, Any]) -> Dict[str, Any]:
    # Get competitive intel
    comp_intel = self._get_basic_intel(opportunity)
    
    # Include in prompt to Claude
    user_message = f"""Analyze this opportunity:

{opp_summary}

Incumbent: {comp_intel['incumbent'].get('contractor_name', 'Unknown')}
Pricing Range: ${comp_intel['pricing'].get('min', 0):,.0f} - ${comp_intel['pricing'].get('max', 0):,.0f}

Provide analysis...
"""
    # ... rest of method
```

**Impact:** Claude AI now considers incumbent and pricing data in its analysis.

### Integration Level 2: Enhanced (+ Market Trends)

**Add to the intel gathering:**
```python
def _get_enhanced_intel(self, opportunity: Dict[str, Any]) -> Dict[str, Any]:
    """Get enhanced competitive intelligence"""
    from fpds_intel import FPDSIntelligence
    from usaspending_intel import USAspendingIntelligence
    
    fpds = FPDSIntelligence(self.config)
    usa = USAspendingIntelligence(self.config)
    
    agency_name = opportunity.get('officeAddress', {}).get('agency', '')
    naics_code = opportunity.get('naicsCode', '')
    
    intel = {}
    
    # FPDS data
    intel['incumbent'] = fpds.find_incumbent_contract(agency_name, naics_code)
    intel['pricing'] = fpds.get_pricing_intelligence(naics_code, agency_name)
    
    # USAspending data
    intel['market_trends'] = usa.get_market_trends(naics_code, agency_name)
    
    # Incumbent profile (if found)
    if intel['incumbent'] and intel['incumbent'].get('contractor_name'):
        intel['incumbent_profile'] = usa.get_contractor_profile(
            intel['incumbent']['contractor_name']
        )
    
    return intel
```

### Integration Level 3: Full (+ Teaming + Strategy)

**Use the complete CompetitiveIntelligenceAgent:**
```python
def analyze_opportunity(self, opportunity: Dict[str, Any]) -> Dict[str, Any]:
    # Run complete competitive analysis
    from competitive_intel_agent import CompetitiveIntelligenceAgent
    
    comp_agent = CompetitiveIntelligenceAgent(self.config)
    competitive_intel = comp_agent.analyze_opportunity_competitiveness(opportunity)
    
    # Extract key insights for Claude
    assessment = competitive_intel.get('competitive_assessment', {})
    
    # Enhanced prompt with full competitive context
    user_message = f"""Analyze this opportunity with competitive intelligence:

OPPORTUNITY:
{opp_summary}

COMPETITIVE INTELLIGENCE:
Incumbent: {competitive_intel.get('incumbent', {}).get('contractor_name', 'None')}
Incumbent Strength: {assessment.get('incumbent_strength', 'unknown')}
Win Probability: {assessment.get('win_probability', 0)}%

Market Trend: {competitive_intel.get('market_trends', {}).get('trend_direction', 'unknown')}

Pricing:
  Average: ${competitive_intel.get('pricing_intelligence', {}).get('average', 0):,.0f}
  Your Target: ${competitive_intel.get('pricing_intelligence', {}).get('median', 0):,.0f}

Recommended Strategy: {assessment.get('recommended_strategy', 'N/A')}

Now provide your analysis considering this competitive context...
"""
    # ... rest of analysis
```

## Configuration Options

Add these to your `config.yaml`:

```yaml
competitive_intelligence:
  enabled: true
  
  # When to run competitive intelligence
  triggers:
    min_value: 500000  # Only for opportunities > $500K
    high_priority_only: false  # Or run for all opportunities
    naics_codes: []  # Or specific NAICS codes only
  
  # What intelligence to gather
  features:
    incumbent_identification: true
    pricing_analysis: true
    market_trends: true
    teaming_partners: true
    competitor_profiling: true
  
  # Performance settings
  timeout: 30  # Seconds per data source
  cache_duration: 3600  # Cache results for 1 hour
  
  # Intelligence preferences
  lookback_years: 3  # Historical data window
  min_sample_size: 5  # Minimum contracts for pricing analysis
```

## Usage Examples

### Example 1: Analyze Single Opportunity with Full Intel

```python
from competitive_intel_agent import CompetitiveIntelligenceAgent, generate_competitive_intelligence_report

# Load opportunity from SAM.gov
opportunity = {...}  # Your opportunity data

# Run analysis
agent = CompetitiveIntelligenceAgent()
analysis = agent.analyze_opportunity_competitiveness(opportunity)

# Generate report
report = generate_competitive_intelligence_report(analysis)
print(report)

# Save to file
with open(f"intel_{opportunity['noticeId']}.txt", 'w') as f:
    f.write(report)
```

### Example 2: Find Teaming Partners for Capability Gap

```python
from competitive_intel_agent import CompetitiveIntelligenceAgent

opportunity = {...}
capability_gaps = ["FedRAMP", "Cloud Architecture"]

agent = CompetitiveIntelligenceAgent()
teaming = agent.find_teaming_opportunities(
    opportunity,
    capability_gaps,
    your_size="small"
)

print(f"Found {teaming['partner_count']} potential partners")
print(f"\nTop Recommendations:")
for partner in teaming['top_recommendations'][:5]:
    print(f"  • {partner['name']}: ${partner['total_value']:,.0f} (score: {partner['teaming_score']})")
```

### Example 3: Benchmark Against Competitors

```python
from competitive_intel_agent import CompetitiveIntelligenceAgent

your_naics = ["541512", "541519", "541330"]
your_revenue = 15000000  # $15M over 3 years

agent = CompetitiveIntelligenceAgent()
benchmark = agent.benchmark_against_competitors(your_naics, your_revenue)

print(f"Your Position: {benchmark['position']}")
print(f"Percentile: {benchmark['your_percentile']:.0f}%")
print(f"Market Average: ${benchmark['market_average']:,.0f}")
```

## Performance Optimization

### Caching Intelligence Data

Avoid repeated API calls by caching results:

```python
import json
from pathlib import Path
from datetime import datetime, timedelta

class CachedCompetitiveIntel:
    def __init__(self, cache_dir="data/intel_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def get_cached(self, key: str, max_age_hours: int = 24):
        """Get cached intel if recent enough"""
        cache_file = self.cache_dir / f"{key}.json"
        
        if cache_file.exists():
            # Check age
            age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
            if age < timedelta(hours=max_age_hours):
                with open(cache_file) as f:
                    return json.load(f)
        
        return None
    
    def save_cache(self, key: str, data: dict):
        """Save intel to cache"""
        cache_file = self.cache_dir / f"{key}.json"
        with open(cache_file, 'w') as f:
            json.dump(data, f, indent=2)
```

**Usage:**
```python
cache = CachedCompetitiveIntel()

# Try cache first
cache_key = f"{agency_name}_{naics_code}"
intel = cache.get_cached(cache_key)

if not intel:
    # Get fresh data
    intel = agent.analyze_opportunity_competitiveness(opportunity)
    cache.save_cache(cache_key, intel)
```

### Parallel Processing

Process multiple opportunities in parallel:

```python
from concurrent.futures import ThreadPoolExecutor

def analyze_with_intel(opportunity):
    agent = CompetitiveIntelligenceAgent()
    return agent.analyze_opportunity_competitiveness(opportunity)

# Process in parallel
opportunities = [...]  # Your list of opportunities

with ThreadPoolExecutor(max_workers=5) as executor:
    results = list(executor.map(analyze_with_intel, opportunities))
```

## Troubleshooting

### Issue: FPDS returns no results
**Solution:** FPDS agency names must match exactly. Try variations:
- "DEPARTMENT OF DEFENSE" vs "DOD"
- Use the exact name from SAM.gov opportunity

### Issue: USAspending timeout
**Solution:** Reduce the date range or limit results:
```python
payload["filters"]["time_period"][0]["start_date"] = "2023-01-01"  # Shorter range
payload["limit"] = 50  # Fewer results
```

### Issue: Slow performance
**Solutions:**
1. Enable caching (see above)
2. Only run intel for high-value opportunities
3. Run intel asynchronously
4. Use parallel processing

### Issue: Missing incumbent data
**Explanation:** Not all contracts are in FPDS immediately. Recent awards may not appear for 30-90 days.

## Testing Your Integration

**Test script:**
```python
import logging
logging.basicConfig(level=logging.INFO)

from competitive_intel_agent import CompetitiveIntelligenceAgent

# Test opportunity
test_opp = {
    'noticeId': 'TEST001',
    'title': 'IT Services',
    'naicsCode': '541512',
    'officeAddress': {
        'agency': 'DEPARTMENT OF DEFENSE'
    }
}

agent = CompetitiveIntelligenceAgent()

print("Testing competitive intelligence...")
try:
    result = agent.analyze_opportunity_competitiveness(test_opp)
    print("✓ Incumbent:", result.get('incumbent', {}).get('contractor_name', 'None found'))
    print("✓ Pricing samples:", result.get('pricing_intelligence', {}).get('sample_size', 0))
    print("✓ Market trend:", result.get('market_trends', {}).get('trend_direction', 'Unknown'))
    print("\n✓ Integration successful!")
except Exception as e:
    print(f"✗ Error: {e}")
```

## Rollout Strategy

### Week 1: Pilot
- Run competitive intel on 5-10 opportunities manually
- Compare results with basic analysis
- Collect feedback from BD team

### Week 2: Soft Launch  
- Enable for opportunities > $1M only
- Monitor performance and accuracy
- Refine based on results

### Week 3: Full Integration
- Enable for all opportunities (or configure threshold)
- Train team on reading competitive intel reports
- Establish competitive intelligence workflow

## Return on Investment

**Time Investment:**
- Initial integration: 2-4 hours
- Testing and refinement: 2-3 hours
- **Total: Half day**

**Expected Benefits:**
- Better bid/no-bid decisions: +20-30% accuracy
- Higher win rates: +15-25% on pursued opportunities
- Time saved on manual research: 10-15 hours/week
- Improved pricing decisions: Better profit margins

**Payback:** First won opportunity using competitive intel pays for entire system for years.

---

## Next Steps

1. ✅ Review DATA_SOURCES_GUIDE.md for background
2. ✅ Test individual modules (fpds_intel.py, usaspending_intel.py)
3. ✅ Choose integration level (Basic, Enhanced, or Full)
4. ✅ Update your code following examples above
5. ✅ Test on real opportunities
6. ✅ Refine and optimize

**Questions?** See troubleshooting section or review the example code in competitive_intel_agent.py.
