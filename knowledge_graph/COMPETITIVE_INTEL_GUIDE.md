# Competitive Intelligence Agent Guide

## 🎯 What It Does

The Competitive Intelligence Agent analyzes the competitive landscape using federal contract award data to help you:

✅ **Identify incumbents** - Who currently has contracts at your target agencies
✅ **Analyze competitors** - Total wins, contract sizes, agencies they work with
✅ **Find teaming partners** - Companies with complementary capabilities
✅ **Track spending patterns** - Which agencies spend how much on what
✅ **Competitor comparison** - Side-by-side analysis of your competition

## 🏗️ Two-Step Process

### Step 1: Collect FPDS Data (One Time Setup)

```bash
cd knowledge_graph

# Collect last 12 months of contract awards
python fpds_collector.py --months 12 --limit 100

# Or collect more data
python fpds_collector.py --months 24 --limit 500
```

**What this does:**
- Fetches contract awards from USASpending.gov (free API)
- Stores contracts in your knowledge graph
- Creates contractor organizations
- Links contracts to winners

**Expected output:**
```
======================================================================
FPDS CONTRACT DATA COLLECTION
======================================================================

→ Fetching contracts for NAICS 541512...
✓   Found 100 contracts
→ Fetching contracts for NAICS 541511...
✓   Found 100 contracts
→ Fetching contracts for NAICS 541519...
✓   Found 100 contracts

→ Storing 300 contracts in knowledge graph...

Storing: 100%|████████████| 300/300 [01:30<00:00,  3.33contract/s]

======================================================================
COLLECTION COMPLETE
======================================================================

Contracts:
  Fetched: 300
  Stored: 300
  Errors: 0

Graph Growth:
  Organizations: 50 → 230 (+180)

✓ FPDS data collection complete!

Now run: python competitive_intel.py --agency 'Your Agency'
```

### Step 2: Run Competitive Intelligence

```bash
# Analyze a specific agency
python competitive_intel.py --agency "Department of Defense"

# With NAICS filter
python competitive_intel.py --agency "NASA" --naics "541512"

# Show report in terminal
python competitive_intel.py --agency "VA" --show-report

# Compare specific competitors
python competitive_intel.py --compare "Lockheed Martin" "Northrop Grumman" "Raytheon"
```

## 📊 Sample Report

```
======================================================================
COMPETITIVE INTELLIGENCE REPORT
Generated: 2026-01-29 14:30
======================================================================

TARGET AGENCY: Department of Defense
----------------------------------------------------------------------

SPENDING ANALYSIS
  Total Contracts: 847
  Total Value: $12,450,000,000
  Average Contract: $14,700,000

  Top NAICS Codes by Spending:
    541512: $8,200,000,000
    541330: $2,100,000,000
    541519: $1,800,000,000

INCUMBENT CONTRACTORS
----------------------------------------------------------------------
1. Lockheed Martin Corporation
   Contracts: 127
   Total Value: $2,340,000,000
   Latest Award: 2025-12-15

2. Northrop Grumman Systems Corp
   Contracts: 98
   Total Value: $1,890,000,000
   Latest Award: 2026-01-10

3. Raytheon Technologies
   Contracts: 84
   Total Value: $1,650,000,000
   Latest Award: 2025-11-20

4. Booz Allen Hamilton
   Contracts: 156
   Total Value: $980,000,000
   Latest Award: 2026-01-05

5. CACI International Inc
   Contracts: 142
   Total Value: $760,000,000
   Latest Award: 2025-12-28

POTENTIAL TEAMING PARTNERS
----------------------------------------------------------------------
1. ManTech International Corporation
   Contracts at Agency: 89
   Total Value: $560,000,000

2. Leidos Inc
   Contracts at Agency: 76
   Total Value: $490,000,000

3. General Dynamics IT
   Contracts at Agency: 67
   Total Value: $420,000,000

======================================================================
RECOMMENDATIONS
======================================================================

1. INCUMBENT STRATEGY:
   • Research top 3 incumbents: Lockheed Martin, Northrop Grumman, Raytheon
   • Identify their strengths and weaknesses
   • Consider subcontracting or teaming

2. TEAMING STRATEGY:
   • Reach out to ManTech, Leidos, General Dynamics
   • Look for complementary capabilities
   • Propose joint pursuit on upcoming opportunities

3. RELATIONSHIP BUILDING:
   • Network with incumbent employees
   • Attend DoD industry days
   • Build contacts at the agency

======================================================================
```

## 💡 Strategic Use Cases

### Use Case 1: Opportunity Pursuit Decision

**Scenario:** New $10M cloud contract at NASA

**Intel Check:**
```bash
python competitive_intel.py --agency "NASA" --naics "541512"
```

**What you learn:**
- Who are the incumbents? (Do they have advantage?)
- What's the typical contract size? (Are you sized right?)
- Who could you team with? (Complement your gaps?)

**Decision:**
- Pursue alone if you're a strong player
- Team with incumbent if they dominate
- Pass if market is locked up

### Use Case 2: Teaming Partner Selection

**Scenario:** Need a partner for DoD opportunity

**Intel Check:**
```bash
python competitive_intel.py --agency "Department of Defense"
```

**What you look for:**
- Companies with 5-20 DoD contracts (experienced, not dominant)
- Different capabilities than yours (complementary)
- Similar company size (balanced partnership)

**Action:**
- Reach out to top 3 candidates
- Propose joint pursuit
- Negotiate teaming agreement

### Use Case 3: Market Entry Strategy

**Scenario:** Want to enter VA market

**Intel Check:**
```bash
python competitive_intel.py --agency "Department of Veterans Affairs"
```

**What you learn:**
- Total market size (is it worth it?)
- Incumbent concentration (how hard to break in?)
- Typical contract sizes (right for you?)
- NAICS breakdown (which services sell?)

**Strategy:**
- High concentration → Team with incumbent
- Fragmented market → Direct compete
- Small contracts → Good entry point

### Use Case 4: Competitive Positioning

**Scenario:** Competing against known firms

**Intel Check:**
```bash
python competitive_intel.py --compare "YourCompany" "Competitor1" "Competitor2"
```

**What you analyze:**
- Their total contract values (how big are they?)
- Their agency relationships (where are they strong?)
- Their NAICS focus (what do they do?)
- Their recent wins (momentum?)

**Positioning:**
- Emphasize your differentiators
- Highlight their weaknesses
- Show your complementary strengths

## 🔄 Integration with Opportunity Scout

**Powerful Combo:**

```bash
# 1. Scout finds high-priority opportunity
python opportunity_scout.py --days 7
# Output: NASA cloud contract - 73% win probability

# 2. Run competitive intel on that agency
python competitive_intel.py --agency "NASA" --show-report
# Output: Top 3 incumbents, spending patterns, teaming options

# 3. Make informed decision
# - You have contacts? (Scout found them)
# - Who are you up against? (Intel shows you)
# - Should you team? (Intel recommends partners)
```

## 📈 Data Collection Strategy

### Initial Setup (One Time)
```bash
# Collect 12 months of data across your NAICS codes
python fpds_collector.py --months 12 --limit 100

# Takes ~5 minutes, creates ~300 contracts
```

### Monthly Refresh
```bash
# Update with latest month
python fpds_collector.py --months 1 --limit 50

# Takes ~2 minutes, adds ~50 new contracts
```

### Deep Dive (Quarterly)
```bash
# Comprehensive update
python fpds_collector.py --months 3 --limit 200

# Takes ~10 minutes, comprehensive refresh
```

## 🎯 Advanced Queries

### Via Neo4j Browser

```cypher
// Find all contracts at an agency
MATCH (c:Contract)
WHERE c.agency CONTAINS "NASA"
RETURN c.title, c.value, c.award_date
ORDER BY c.value DESC
LIMIT 20

// See who wins at multiple agencies
MATCH (c:Contract)-[:AWARDED_TO]->(o:Organization)
WITH o, collect(DISTINCT c.agency) as agencies, count(c) as contract_count
WHERE size(agencies) > 3
RETURN o.name, agencies, contract_count
ORDER BY contract_count DESC

// Find teaming opportunities
MATCH (c1:Contract)-[:AWARDED_TO]->(your_partner:Organization)
MATCH (c2:Contract)-[:AWARDED_TO]->(potential_team:Organization)
WHERE c1.agency = c2.agency
  AND your_partner.name = "Your Target Partner"
  AND potential_team <> your_partner
RETURN potential_team.name, count(*) as shared_agencies
ORDER BY shared_agencies DESC
LIMIT 10
```

## 💰 Cost and Value

### Data Collection Cost
- **USASpending.gov API:** FREE (no API key required)
- **Time:** ~5 minutes for 300 contracts
- **Storage:** ~1MB in Neo4j per 1000 contracts

### Intelligence Value
- **Market research firms charge:** $5,000-50,000 per report
- **Your cost:** $0 (automated)
- **Update frequency:** As often as you want
- **Customization:** Unlimited

## 🎨 Next Level: Automation

### Daily Intel Updates

Create `intel_daily.py`:
```python
#!/usr/bin/env python3
import sys
from competitive_intel import CompetitiveIntelAgent

# Your target agencies
TARGET_AGENCIES = [
    "Department of Defense",
    "NASA",
    "Department of Veterans Affairs"
]

agent = CompetitiveIntelAgent()

for agency in TARGET_AGENCIES:
    report = agent.run_competitive_intel(
        target_agency=agency,
        save_report=True
    )

agent.close()
```

### Set up cron:
```bash
# Weekly intel refresh (Mondays at 9 AM)
0 9 * * 1 cd /path/to/knowledge_graph && python intel_daily.py
```

## 🔗 Integration Roadmap

**Current State:**
```
Agent 1: Opportunity Scout
    ↓
Agent 2: Competitive Intelligence ← YOU ARE HERE
```

**Full Integration:**
```
Agent 1: Opportunity Scout
    ↓ (identifies opportunities)
Agent 2: Competitive Intelligence
    ↓ (analyzes competition)
Agent 3: Capability Matching
    ↓ (checks your team)
Agent 4: Pursuit Decision
    ↓ (go/no-go)
Agent 5: Proposal Writing
    ↓ (if go)
Agent 6: Pricing Strategy
```

## 🎊 The Competitive Advantage

**Before Competitive Intel:**
```
New opportunity drops
→ "Wonder who we're competing against?"
→ "Should we team with someone?"
→ "What's the typical contract size here?"
→ Hours of manual research
→ Incomplete information
→ Gut-feel decisions
```

**After Competitive Intel:**
```
New opportunity drops
→ Run intel in 30 seconds
→ Know all incumbents
→ See typical contract sizes
→ Get teaming recommendations
→ Data-driven decisions
→ Competitive positioning
```

## 📊 Success Metrics

Track these over time:
- **Pursuit accuracy:** Are you choosing the right opportunities?
- **Win rate:** Improving with better intel?
- **Teaming success:** Are partnerships working?
- **Market share:** Growing in target agencies?

## 🚀 You Now Have

1. ✅ **Knowledge Graph** (150+ contacts)
2. ✅ **Opportunity Scout** (AI-powered opportunity scoring)
3. ✅ **Competitive Intelligence** (Market analysis + competitor tracking)

**Three agents working together to give you Fortune 500-level BD intelligence!** 🎯

---

Ready to collect FPDS data and run your first competitive analysis? 🔥
