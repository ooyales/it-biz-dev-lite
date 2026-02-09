# FPDS Contract Data Integration Guide

## Overview

This guide shows you how to populate your Neo4j database with real federal contract award data from FPDS (Federal Procurement Data System), enabling the Competitive Intelligence agent to show real incumbents and market data.

---

## What is FPDS?

**FPDS** (Federal Procurement Data System) is the U.S. government's repository of all federal contract awards over $10,000. It contains:

- **Contractor names** - Who won the contracts
- **Contract values** - Dollar amounts
- **Agencies** - Which departments awarded them
- **NAICS codes** - Type of work
- **Award dates** - When contracts were signed
- **Performance locations** - Where work happens

**Public Access:** FPDS data is publicly available through fpds.gov

---

## Quick Start (Recommended)

### Step 1: Run Quick Setup

```bash
# Copy the scripts
cp /mnt/user-data/outputs/fpds_contract_collector.py .
cp /mnt/user-data/outputs/quick_fpds_setup.py .

# Run quick setup (imports 100 recent contracts)
python quick_fpds_setup.py
```

This will:
- ✅ Fetch 100 recent IT contracts from past 30 days
- ✅ Import them into Neo4j
- ✅ Create proper indexes
- ✅ Link to Organization nodes
- ✅ Take about 2-3 minutes

### Step 2: Test It

```bash
# Restart dashboard
python team_dashboard_integrated.py

# Visit: http://localhost:8080/bd-intelligence
# Click any opportunity → "Competitive Intel"
# Should now show REAL incumbents! 🎉
```

---

## Advanced: Import More Data

### Import Specific Agency

```python
from fpds_contract_collector import FPDSCollector
from datetime import datetime, timedelta

collector = FPDSCollector()

# Get all DoD contracts from past year
one_year_ago = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')

contracts = collector.fetch_contracts(
    agency='DEPT OF DEFENSE',
    start_date=one_year_ago,
    max_records=1000
)

collector.import_to_neo4j(contracts)
collector.close()
```

### Import Specific NAICS

```python
# Get all cybersecurity contracts (NAICS 541512)
contracts = collector.fetch_contracts(
    naics='541512',
    start_date='2024-01-01',
    max_records=500
)

collector.import_to_neo4j(contracts)
```

### Import Multiple Agencies

```python
agencies = [
    'DEPT OF DEFENSE',
    'DEPT OF HOMELAND SECURITY',
    'VETERANS AFFAIRS, DEPARTMENT OF',
    'DEPT OF ENERGY'
]

for agency in agencies:
    print(f"\nCollecting {agency}...")
    contracts = collector.fetch_contracts(
        agency=agency,
        start_date='2024-01-01',
        max_records=200
    )
    collector.import_to_neo4j(contracts)
```

---

## Neo4j Schema

### Nodes Created

**Contract:**
```cypher
(:Contract {
  contract_id: 'W912DY23C0001',
  agency: 'DEPT OF DEFENSE',
  agency_code: '9700',
  naics: '541512',
  psc: 'D301',
  value: 2500000.00,
  award_date: date('2025-01-15'),
  description: 'Cybersecurity Services',
  place_of_performance: 'Fort Meade, MD',
  contract_type: 'FIRM FIXED PRICE',
  imported_at: datetime()
})
```

**Organization:**
```cypher
(:Organization {
  name: 'Booz Allen Hamilton',
  duns: '006928857',
  created_at: datetime()
})
```

### Relationships

```cypher
(contract:Contract)-[:AWARDED_TO]->(org:Organization)
```

### Indexes

```cypher
CREATE INDEX contract_id FOR (c:Contract) ON (c.contract_id)
CREATE INDEX contract_agency FOR (c:Contract) ON (c.agency)
CREATE INDEX contract_naics FOR (c:Contract) ON (c.naics)
```

---

## Querying the Data

### View Statistics

```python
from fpds_contract_collector import FPDSCollector

collector = FPDSCollector()
stats = collector.get_statistics()

print(f"Total Contracts: {stats['total_contracts']}")
print(f"Total Value: ${stats['total_value']:,.0f}")
print(f"\nTop Agencies:")
for agency in stats['top_agencies'][:5]:
    print(f"  {agency['agency']}: {agency['count']} contracts")
```

### Neo4j Browser Queries

```cypher
// Find incumbents at an agency
MATCH (c:Contract)-[:AWARDED_TO]->(org:Organization)
WHERE c.agency CONTAINS 'DEFENSE'
  AND c.naics = '541512'
RETURN org.name, count(c) as contracts, sum(c.value) as total_value
ORDER BY total_value DESC
LIMIT 10

// Find all contracts for a company
MATCH (c:Contract)-[:AWARDED_TO]->(org:Organization {name: 'Booz Allen Hamilton'})
RETURN c.agency, c.value, c.award_date
ORDER BY c.award_date DESC

// Market analysis by NAICS
MATCH (c:Contract)
WHERE c.naics = '541512'
RETURN c.agency, count(c) as contracts, sum(c.value) as total_value
ORDER BY total_value DESC
```

---

## Maintenance & Updates

### Weekly Update

Create a cron job to refresh data weekly:

```bash
# Add to crontab (crontab -e)
0 2 * * 0 cd /path/to/project && python quick_fpds_setup.py >> logs/fpds.log 2>&1
```

### Manual Refresh

```bash
# Get latest contracts
python quick_fpds_setup.py
```

### Delete Old Data

```cypher
// Delete contracts older than 2 years
MATCH (c:Contract)
WHERE c.award_date < date() - duration({months: 24})
DETACH DELETE c
```

---

## Troubleshooting

### "No contracts found"

**Cause:** FPDS API may be slow or temporarily unavailable

**Solutions:**
1. Try different date range
2. Wait and retry later
3. Check fpds.gov is accessible
4. Try fewer records at once

### "Connection refused to Neo4j"

**Cause:** Neo4j not running

**Solution:**
```bash
neo4j status
neo4j start
```

### "WARNING: Unknown property key: naics"

**Cause:** No contracts imported yet

**Solution:**
```bash
python quick_fpds_setup.py
```

### Slow Import

**Cause:** Large dataset or slow connection

**Solutions:**
1. Reduce `max_records`
2. Import in smaller batches
3. Use shorter date range

---

## Performance Optimization

### For Large Imports (1000+ contracts)

```python
# Import in batches
for i in range(0, 5):
    print(f"Batch {i+1}/5...")
    contracts = collector.fetch_contracts(
        start_date=f'2024-{i*2+1:02d}-01',
        end_date=f'2024-{i*2+2:02d}-28',
        max_records=200
    )
    collector.import_to_neo4j(contracts)
    time.sleep(60)  # Rate limiting
```

### Optimize Neo4j

```cypher
// Create composite indexes for common queries
CREATE INDEX contract_agency_naics 
FOR (c:Contract) ON (c.agency, c.naics)

// Analyze query performance
PROFILE MATCH (c:Contract)-[:AWARDED_TO]->(org)
WHERE c.agency CONTAINS 'DEFENSE'
RETURN org.name, count(c)
```

---

## Data Coverage

### What Gets Imported

- ✅ IT services contracts (NAICS 541511, 541512, 541519, 518210)
- ✅ Federal agencies
- ✅ Contracts > $10,000
- ✅ Awards (not solicitations)

### What Doesn't Get Imported

- ❌ Classified contracts
- ❌ Contracts < $10,000
- ❌ State/local government contracts
- ❌ Foreign military sales

---

## Next Steps

After importing FPDS data:

1. **Test Competitive Intel**
   - Should show real company names
   - Real contract values
   - Actual market data

2. **Explore Advanced Queries**
   - Market share analysis
   - Teaming patterns
   - Agency preferences

3. **Automate Updates**
   - Schedule weekly imports
   - Monitor data quality
   - Archive old contracts

---

## API Rate Limits

**FPDS API Limits:**
- ~10 requests per minute
- ~100 records per request
- May throttle during peak hours

**Best Practices:**
- Add delays between requests (done automatically)
- Import during off-peak hours
- Cache results
- Don't request same data repeatedly

---

## Questions?

- **FPDS Documentation:** https://www.fpds.gov/
- **Neo4j Cypher Guide:** https://neo4j.com/docs/cypher-manual/
- **SAM.gov API:** https://open.gsa.gov/api/

---

## Summary

**Quick Start:**
```bash
python quick_fpds_setup.py
python team_dashboard_integrated.py
# Test at http://localhost:8080
```

**Result:** Real competitive intelligence with actual incumbents! 🎉
