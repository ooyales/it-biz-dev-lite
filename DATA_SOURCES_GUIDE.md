# Federal Contracting Data Sources - Integration Guide

## Overview

While SAM.gov is essential for finding NEW opportunities, integrating additional data sources provides critical competitive intelligence that dramatically improves your win probability.

## Critical Data Sources

### 1. **FPDS (Federal Procurement Data System)** ⭐ ESSENTIAL
**URL**: https://www.fpds.gov/  
**API**: https://www.fpds.gov/wiki/index.php/ATOM_Feed_Usage

**What It Provides:**
- Historical contract awards (who won what)
- Contract modifications and extensions
- Pricing data (award amounts)
- Incumbent contractor identification
- Contract vehicle used
- NAICS code breakdowns
- Agency spending patterns

**Why You Need It:**
- **Incumbent Intelligence**: Know who currently holds the contract
- **Pricing Intelligence**: Understand typical award amounts for similar work
- **Agency Preferences**: Which contractors do agencies repeatedly choose
- **Recompete Timing**: Identify contracts approaching end dates
- **Team Partner Discovery**: Find companies winning similar work

**API Access**: FREE via ATOM feeds

**Use Cases:**
```
Scenario 1: New Solicitation appears on SAM.gov
→ Query FPDS for previous awards in same NAICS at that agency
→ Identify incumbent (your competition)
→ See their award amount (pricing intelligence)
→ Check if they're a small business (teaming opportunity vs. competition)

Scenario 2: Sources Sought notice
→ Find related historical contracts
→ See who responded before
→ Understand agency's buying patterns
```

---

### 2. **USAspending.gov** ⭐ ESSENTIAL
**URL**: https://www.usaspending.gov/  
**API**: https://api.usaspending.gov/

**What It Provides:**
- More granular spending data than FPDS
- Sub-award information (prime-sub relationships)
- Grant data (if you do R&D)
- Contract actions by company
- Congressional district spending
- Better search and filtering

**Why You Need It:**
- **Prime-Sub Discovery**: See who works together
- **Company Research**: Total government revenue of competitors
- **Teaming Opportunities**: Find primes who subcontract in your area
- **Market Sizing**: How much does agency spend on your NAICS
- **Trend Analysis**: Is spending increasing or decreasing

**API Access**: FREE with robust REST API

**Use Cases:**
```
Scenario: You're considering pursuing a large opportunity
→ Query USAspending for the agency's historical spending in that NAICS
→ See if spending is trending up or down
→ Identify prime contractors who might need subs
→ Check if agency has IDIQ vehicles you could get on
```

---

### 3. **Beta.SAM.gov Entity API** ⭐ RECOMMENDED
**URL**: https://open.gsa.gov/api/entity-api/  
**API**: Same as opportunities API

**What It Provides:**
- Detailed company information (competitors, partners)
- NAICS codes companies are registered for
- Socioeconomic certifications
- Points of contact
- Capability statements (if uploaded)
- Past performance ratings
- Financial stability indicators

**Why You Need It:**
- **Competitor Research**: What NAICS codes are they registered for
- **Teaming Partner Discovery**: Find certified small businesses
- **Due Diligence**: Verify potential partners are active and compliant
- **Market Intelligence**: How many companies compete in your NAICS

**API Access**: FREE (same key as opportunities API)

---

### 4. **GovWin IQ / Deltek** 💰 COMMERCIAL (Optional but Powerful)
**URL**: https://www.deltek.com/en/products/govwin-iq  
**Cost**: $3,000-10,000/year depending on features

**What It Provides:**
- Pipeline intelligence (pre-solicitation opportunities)
- Procurement forecasts
- Agency contact information
- Incumbent expiration dates
- Win/loss analysis
- Teaming announcements

**Why You Might Want It:**
- 6-12 month advance notice of opportunities
- Direct agency contact information
- More comprehensive incumbent intelligence

**Alternative**: You can get similar intelligence manually by:
- Monitoring agency forecast schedules
- FOIA requests for contract award dates
- LinkedIn research for agency contacts

---

### 5. **FPDS-NG Data Warehouse** ⭐ RECOMMENDED
**URL**: https://www.fpds.gov/fpdsng_cms/index.php/en/

**What It Provides:**
- Bulk downloads of all contract data
- Historical trends (10+ years)
- More detailed queries than ATOM feeds
- Custom reporting

**Why You Need It:**
- Deep market research
- Historical win rate analysis
- Competitive landscape mapping
- Agency spending trend analysis

**Access**: FREE (requires registration)

---

### 6. **Beta.SAM.gov Contract Opportunities Archive**
**URL**: https://sam.gov/content/opportunities  
**API**: Part of opportunities API with date ranges

**What It Provides:**
- Historical solicitations (closed)
- Amendment history
- Q&A from previous solicitations
- Winning proposal page counts (sometimes)

**Why You Need It:**
- Learn from past solicitations
- See what questions were asked
- Understand evaluation criteria evolution
- Estimate level of effort

---

### 7. **Agency-Specific Forecast Schedules** ⭐ RECOMMENDED
**Examples:**
- DoD: https://www.acq.osd.mil/
- VA: https://www.va.gov/oamm/forecast/
- DHS: https://www.dhs.gov/acquisition-forecasts
- GSA: https://www.gsaelibrary.gsa.gov/ElibMain/home.do

**What They Provide:**
- 6-12 month procurement forecasts
- Estimated award dates
- Anticipated contract values
- Type of procurement (8(a), competitive, etc.)

**Why You Need Them:**
- Early pipeline development
- Relationship building before solicitation
- Market research timing
- Teaming partner identification

---

## Integration Priority

### Phase 1 (Immediate - Week 1)
1. ✅ SAM.gov Opportunities API (already built)
2. ⭐ FPDS ATOM Feed (add incumbent intelligence)
3. ⭐ USAspending API (add pricing and teaming intel)

### Phase 2 (Month 1)
4. Beta.SAM.gov Entity API (competitor research)
5. Agency forecast schedules (manual monitoring initially)

### Phase 3 (Month 2-3)
6. FPDS-NG Data Warehouse (deep market analysis)
7. Historical SAM.gov archive (learn from past)

### Phase 4 (Optional - Month 3+)
8. GovWin or similar commercial tools (if budget allows)

---

## Recommended Enhancements to Your System

### Enhancement 1: Incumbent Intelligence Agent
**New Agent**: `CompetitiveIntelAgent`

**Workflow:**
```
1. Opportunity found on SAM.gov
   ↓
2. Extract NAICS code and agency
   ↓
3. Query FPDS for recent awards in same NAICS at agency
   ↓
4. Identify incumbent contractor
   ↓
5. Query USAspending for incumbent's total gov revenue
   ↓
6. Query Entity API for incumbent's details (size, NAICS codes)
   ↓
7. Generate competitive assessment:
   - Is incumbent a small business? (protected recompete?)
   - What's their total gov revenue? (can you compete?)
   - Do they have multiple NAICS? (diversified or focused?)
   - Recent wins/losses in this NAICS?
```

### Enhancement 2: Pricing Intelligence Agent
**New Agent**: `PricingIntelAgent`

**Workflow:**
```
1. Opportunity found
   ↓
2. Query FPDS for similar contracts (same NAICS, similar scope)
   ↓
3. Extract award amounts
   ↓
4. Calculate:
   - Average award amount
   - Range (min/max)
   - Trend (increasing/decreasing)
   - Typical contract length
   ↓
5. Generate price-to-win estimate
```

### Enhancement 3: Teaming Partner Finder
**New Agent**: `TeamingAgent`

**Workflow:**
```
1. Capability gap identified
   ↓
2. Query USAspending for companies winning in that capability area
   ↓
3. Filter by:
   - Small business status (if you need SB teaming)
   - Geographic location
   - Prime vs. sub history
   ↓
4. Query Entity API for contact information
   ↓
5. Generate teaming partner recommendations
```

### Enhancement 4: Market Intelligence Dashboard
**New Component**: `market_analyzer.py`

**Features:**
- Agency spending trends in your NAICS codes
- Market share analysis (who's winning)
- Contract vehicle analysis (which GWACs/IDIQs are popular)
- Geographic hotspots (where is work concentrated)
- Set-aside utilization (how much goes to small business)

---

## Data Source Comparison

| Source | Cost | Update Frequency | Best For | API Quality |
|--------|------|------------------|----------|-------------|
| SAM.gov | FREE | Real-time | New opportunities | Excellent |
| FPDS | FREE | Daily | Historical awards | Good |
| USAspending | FREE | Monthly | Spending analysis | Excellent |
| Entity API | FREE | Real-time | Company research | Good |
| GovWin | $$$$ | Real-time | Pipeline/forecasts | Excellent |
| Agency Forecasts | FREE | Quarterly | Early pipeline | N/A (manual) |

---

## Implementation Roadmap

### Week 1: Add FPDS Integration
```python
# New module: fpds_intel.py
# - Query FPDS for incumbent contracts
# - Extract pricing data
# - Identify contract end dates
```

### Week 2: Add USAspending Integration
```python
# New module: usaspending_intel.py
# - Company spending analysis
# - Prime-sub relationship discovery
# - Market trend analysis
```

### Week 3: Enhance Opportunity Analyzer
```python
# Modify OpportunityAnalyzer to include:
# - Incumbent strength assessment
# - Pricing competitiveness score
# - Teaming recommendation
```

### Month 2: Build Market Intelligence
```python
# New module: market_intel.py
# - Agency spending dashboards
# - Competitive landscape reports
# - Win probability models
```

---

## Sample Enhanced Analysis Output

```
OPPORTUNITY: Cloud Infrastructure Modernization
Score: 8.5/10 (↑ from 7/10 with intel)

COMPETITIVE INTELLIGENCE:
  Incumbent: TechCorp Solutions Inc.
  - Current Contract: $2.4M (Sep 2022 - Sep 2025)
  - Incumbent Revenue: $45M total gov contracts
  - Small Business: No (disadvantage for us if set-aside)
  - Recent Performance: 3 similar wins, 1 loss
  - Assessment: Strong incumbent, but approaching 3-year mark

PRICING INTELLIGENCE:
  Similar Contracts (last 3 years):
  - Average: $2.8M
  - Range: $1.2M - $4.5M
  - Trend: +15% YoY (increasing)
  - Our Price-to-Win Estimate: $2.5M - $3.0M

TEAMING INTELLIGENCE:
  Capability Gaps: Cloud Security (FEDRAMP)
  Recommended Partners:
  1. SecureCloud Inc. (FEDRAMP authorized, $12M revenue)
  2. FedSecurity Partners (8(a), strong past perf)
  
  Prime Opportunities:
  - This appears sized for small business prime
  - Incumbent is large business (recompete advantage)

RECOMMENDATION: STRONGLY PURSUE
  Rationale: 
  - High fit + favorable competitive position
  - We can prime with right security partner
  - Pricing is within our range
  - Incumbent vulnerable to small business challenge
```

---

## Quick Implementation: FPDS Integration

Want me to build the FPDS integration module right now? It would add:

1. **Incumbent identification** for each opportunity
2. **Pricing intelligence** from similar past awards
3. **Contract expiration tracking** (recompete timing)
4. **Agency preference analysis** (who do they typically choose)

This would take your system from "finding opportunities" to "finding WINNABLE opportunities with competitive intelligence."

Should I create this enhanced version?
