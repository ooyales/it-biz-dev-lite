# Quick Start Guide: Running Your First Collection

## 🚀 Setup (One Time)

### Step 1: Install Required Package

```bash
pip install tqdm pyyaml
```

### Step 2: Set Environment Variables (Recommended)

```bash
# Add these to your ~/.zshrc for persistence
export SAM_API_KEY='your_sam_api_key'
export NEO4J_PASSWORD='your_neo4j_password'
export ANTHROPIC_API_KEY='your_anthropic_api_key'

# Reload shell
source ~/.zshrc
```

**Or create a config file:**

```bash
# Copy template
cp config_template.yaml config.yaml

# Edit with your credentials
nano config.yaml
```

## 🎯 Running Collections

### Option 1: Start Small (10 opportunities)

```bash
cd knowledge_graph
python collect_opportunities.py --limit 10
```

**Expected:**
- Time: ~5 minutes
- Cost: ~$0.10-0.20
- New contacts: 20-30 people
- New orgs: 10-15 agencies

### Option 2: Medium Run (25 opportunities)

```bash
python collect_opportunities.py --limit 25
```

**Expected:**
- Time: ~10 minutes
- Cost: ~$0.30-0.50
- New contacts: 50-70 people
- New orgs: 20-30 agencies

### Option 3: Full Run (50 opportunities)

```bash
python collect_opportunities.py --limit 50
```

**Expected:**
- Time: ~15-20 minutes
- Cost: ~$0.50-1.00
- New contacts: 100-150 people
- New orgs: 40-50 agencies

### Option 4: Custom Run

```bash
# Custom limit and days back
python collect_opportunities.py --limit 100 --days 60
```

## 📊 What You'll See

```
======================================================================
SAM.GOV OPPORTUNITY COLLECTION
======================================================================

→ Starting graph state:
  People: 10
  Organizations: 7
  Relationships: 10

→ Fetching opportunities from SAM.gov (limit: 10)...
  NAICS 541512: 8 opportunities
  NAICS 541511: 2 opportunities
✓ Fetched 10 opportunities

→ Processing 10 opportunities...
Processing: 100%|████████████████| 10/10 [02:15<00:00, 13.5s/opp]

======================================================================
COLLECTION COMPLETE!
======================================================================

Opportunities:
  Fetched: 10
  Processed: 10
  Errors: 0

Entities Created:
  People: 23
  Organizations: 12
  Relationships: 31

Graph Growth:
  People: 10 → 33 (+23)
  Organizations: 7 → 19 (+12)
  Relationships: 10 → 41 (+31)

Cost:
  Extraction cost: $0.18
  Average per opportunity: $0.0180

Extraction Stats:
  Claude calls: 10
  Tokens used: 12,458

✓ Your knowledge graph is now 33 people strong!

View your graph:
  1. Open: http://localhost:7474
  2. Database: contactsgraphdb
  3. Query: MATCH (n) RETURN n LIMIT 100

Or see just the new contacts:
  MATCH (n) WHERE n.source CONTAINS 'SAM.gov' RETURN n

Summary saved to: collection_summary.json
```

## 🎨 Viewing Results in Neo4j

### Query 1: See All New Contacts

```cypher
MATCH (p:Person)
WHERE p.source CONTAINS 'SAM.gov'
RETURN p.name, p.title, p.organization, p.email
ORDER BY p.extracted_at DESC
LIMIT 50
```

### Query 2: See Network Connections

```cypher
MATCH (p:Person)-[r:WORKS_AT]->(o:Organization)
WHERE p.source CONTAINS 'SAM.gov'
RETURN p, r, o
```

### Query 3: Find Decision Makers

```cypher
MATCH (p:Person {role_type: "Decision Maker"})
WHERE p.source CONTAINS 'SAM.gov'
RETURN p.name, p.title, p.organization, p.email
```

### Query 4: See Which Agencies Have Most Contacts

```cypher
MATCH (p:Person)-[:WORKS_AT]->(o:Organization)
WHERE p.source CONTAINS 'SAM.gov'
RETURN o.name as Agency, count(p) as Contacts
ORDER BY Contacts DESC
LIMIT 10
```

### Query 5: Visualize Everything

```cypher
MATCH (n)
WHERE n.source CONTAINS 'SAM.gov'
RETURN n
LIMIT 100
```

## 💰 Cost Tracking

After each run, check `collection_summary.json`:

```json
{
  "timestamp": "2026-01-29T10:30:00",
  "opportunities_processed": 10,
  "people_created": 23,
  "orgs_created": 12,
  "relationships_created": 31,
  "cost": 0.18,
  "final_graph_size": {
    "people": 33,
    "organizations": 19,
    "relationships": 41
  }
}
```

## 🔧 Troubleshooting

### "No opportunities fetched"

- Check your SAM.gov API key is valid
- Try increasing `--days` parameter
- Try different NAICS codes

### "Connection refused to Neo4j"

```bash
# Check Neo4j is running
# In Neo4j Desktop, database should show "Active"

# Test connection
python -c "from neo4j import GraphDatabase; print('Neo4j OK')"
```

### "API error 429 (rate limit)"

- The script already includes delays
- If still hitting limits, reduce `--limit` or add more delays
- SAM.gov allows 1000 requests/hour

### "Extraction cost too high"

- The script only extracts from opportunities with substantial text
- Skips opportunities < 100 characters
- Cost is typically $0.01-0.03 per opportunity with contacts

## 📈 Recommended Collection Strategy

### Week 1: Build Foundation
```bash
# Day 1: Test with 10
python collect_opportunities.py --limit 10

# Day 3: Run 25 more
python collect_opportunities.py --limit 25

# Day 5: Run 50
python collect_opportunities.py --limit 50
```

### Week 2+: Maintain Fresh Data
```bash
# Weekly collection of new opportunities
python collect_opportunities.py --limit 50 --days 7
```

### Monthly: Deep Dive
```bash
# Monthly comprehensive collection
python collect_opportunities.py --limit 200 --days 30
```

## 🎯 Next Steps

After your first collection:

1. **Explore the graph** - Use Neo4j Browser to visualize
2. **Add more sources** - FPDS contracts, LinkedIn profiles
3. **Build dashboards** - Opportunity intelligence, relationship health
4. **Automate** - Set up daily/weekly cron jobs

## ⚡ Pro Tips

1. **Start small** - Run 10 first to see how it works
2. **Monitor costs** - Check collection_summary.json after each run
3. **Target specific agencies** - Modify NAICS codes for your focus areas
4. **Review data quality** - Check Neo4j Browser after each run
5. **Build gradually** - 10-50 opportunities per run is optimal

## 🎊 You're Ready!

Just run:

```bash
cd knowledge_graph
python collect_opportunities.py --limit 10
```

And watch your knowledge graph grow! 🌱
