# Contact Knowledge Graph Architecture
## End-to-End Pipeline for Federal Contracting BD

## 🎯 Why This Is Game-Changing

**Current System:**
- 10 contacts, manually entered
- Basic relationships
- Limited intelligence capture

**Knowledge Graph System:**
- Auto-ingest from multiple sources
- AI extracts relationships automatically
- Entity resolution merges duplicates
- Graph analytics reveals hidden connections
- **10x faster BD intelligence gathering**

## 🏗️ Four-Layer Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    LAYER 4: APPLICATIONS                     │
│  Network Viz │ Contact Mgmt │ Opportunity Intel │ Analytics │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────┴─────────────────────────────────┐
│                    LAYER 3: GRAPH STORE                      │
│        Neo4j Graph Database with 250k+ nodes/edges          │
│  Person ─WORKS_AT→ Org ─AWARDED→ Contract ─RELATED_TO→ Opp │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────┴─────────────────────────────────┐
│              LAYER 2: ENTITY RESOLUTION & NLP                │
│  Name Matching │ Email Dedup │ Company Normalization │ AI   │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────┴─────────────────────────────────┐
│                   LAYER 1: INGESTION                         │
│ LinkedIn │ SAM.gov │ FPDS │ Email │ Docs │ Conference PDFs │
└─────────────────────────────────────────────────────────────┘
```

## 📥 LAYER 1: Ingestion Sources

### Priority Sources for Federal Contracting

**1. SAM.gov (Highest Priority)**
```python
# Already have this!
- Opportunity data with agency contacts
- Past performance with contract officers
- Vendor profiles with key personnel
- Auto-extract: Names, titles, agencies, emails
```

**2. FPDS (Contract Award Data)**
```python
# Goldmine of relationship data
- Who awarded contracts to whom
- Program managers on contracts
- Contracting officers
- Award amounts and dates
- Auto-extract: Build relationship graph of who works with whom
```

**3. LinkedIn (Moderate Priority)**
```python
# For compliance, use:
- LinkedIn Sales Navigator exports (if you have license)
- Manual exports of profiles (CSV)
- Your CRM's LinkedIn integration
- Auto-extract: Current roles, past employers, connections
```

**4. Email Archives**
```python
# Your sent/received emails
- Parse .mbox or Outlook .pst files
- Extract: Who you've talked to, when, about what
- Build interaction timeline automatically
- Privacy: Keep on-premise, don't send to cloud
```

**5. Conference Materials**
```python
# Industry days, conferences, panels
- Speaker lists (PDF)
- Attendee lists (PDF/Excel)
- Panel recordings (YouTube)
- Auto-extract: Who spoke, what panels, who attended
```

**6. Internal Documents**
```python
# Your existing intel
- Proposal documents (who we mentioned as partners)
- Past performance docs (who worked with us)
- Meeting notes (who attended)
- Capture plans (who we're targeting)
```

### Implementation: Microservices Architecture

```python
# Each source = separate collector
collectors/
├── sam_collector.py          # SAM.gov opportunities & contacts
├── fpds_collector.py         # Contract award data
├── linkedin_collector.py     # Profile exports
├── email_collector.py        # Email archive parsing
├── conference_collector.py   # PDF/YouTube extraction
├── document_collector.py     # Internal docs
└── web_collector.py          # Agency websites, news

# Each outputs to common format
{
    "source_id": "sam-2026-001",
    "source_type": "sam_opportunity",
    "timestamp": "2026-01-28T10:00:00",
    "raw_text": "...",
    "structured_data": {...},
    "metadata": {
        "url": "...",
        "agency": "...",
        "confidence": 0.95
    }
}
```

## 🤖 LAYER 2: NLP Extraction & Entity Resolution

### A. Named Entity Recognition (NER)

**Extract these entity types:**

```python
PERSON:
- Full name: "Sarah Johnson"
- Title: "Contracting Officer"
- Email: "sarah.johnson@disa.mil"
- Phone: "(703) 555-0123"
- LinkedIn: "linkedin.com/in/sarahjohnson"

ORGANIZATION:
- Name: "Defense Information Systems Agency"
- Abbreviation: "DISA"
- Parent: "Department of Defense"
- Location: "Fort Meade, MD"

ROLE:
- Position: "Contracting Officer"
- Level: "GS-14"
- Office: "Contracting Division"

EVENT:
- Type: "Industry Day"
- Date: "2025-06-15"
- Location: "DISA Headquarters"
- Participants: ["Sarah Johnson", "Michael Chen", ...]

CONTRACT:
- Number: "N00178-23-C-1234"
- Value: "$5,000,000"
- Agency: "DISA"
- Vendor: "TechCorp Solutions"
```

**Implementation Options:**

**Option 1: spaCy (Fast, Free)**
```python
import spacy
nlp = spacy.load("en_core_web_lg")

# Add custom entity types
ruler = nlp.add_pipe("entity_ruler")
patterns = [
    {"label": "CONTRACTING_OFFICER", "pattern": [
        {"TEXT": {"REGEX": "Contracting"}},
        {"TEXT": "Officer"}
    ]},
    # ... more patterns
]
```

**Option 2: GPT-4 (Accurate, Paid)**
```python
from openai import OpenAI
client = OpenAI()

prompt = """
Extract all people, organizations, roles, and relationships from:

{text}

Return JSON:
{{
    "people": [{{"name": "...", "title": "...", "email": "..."}}],
    "organizations": [{{"name": "...", "type": "..."}}],
    "relationships": [{{"from": "...", "relation": "...", "to": "..."}}]
}}
"""

response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": prompt}]
)
```

**Option 3: Fine-tuned Model (Best Long-term)**
```python
# Train on federal contracting corpus
# Labels: PERSON, AGENCY, CONTRACT_OFFICER, PROGRAM_MANAGER, etc.
# Highest accuracy for domain-specific extraction
```

### B. Relationship Extraction

**Key Relationship Types:**

```python
PROFESSIONAL:
- WORKS_AT: Person → Organization
- REPORTS_TO: Person → Person
- MANAGES: Person → Person
- COLLEAGUE_OF: Person → Person

CONTRACTUAL:
- AWARDED_BY: Contract → Person (Contracting Officer)
- AWARDED_TO: Contract → Organization (Vendor)
- PROGRAM_MANAGER: Contract → Person
- TECHNICAL_POC: Contract → Person

INTERACTION:
- MET_AT: Person → Event → Person
- CO_SPOKE: Person → Event → Person
- EMAILED: Person → Person (with date)
- CALLED: Person → Person (with date)

ORGANIZATIONAL:
- PART_OF: Organization → Organization (subdivision)
- LOCATED_IN: Organization → Location
- CONTRACTED_WITH: Organization → Organization
```

**Extraction Methods:**

```python
# Method 1: Pattern matching
if "reports to" in sentence.lower():
    extract_relationship(subject, "REPORTS_TO", object)

# Method 2: Dependency parsing
import spacy
doc = nlp(text)
for token in doc:
    if token.dep_ == "nsubj" and token.head.lemma_ == "work":
        # "Sarah works at DISA"
        person = token.text
        org = [child for child in token.head.children if child.dep_ == "prep"][0]

# Method 3: GPT-4 relationship extraction
prompt = """
Find all relationships in: "{text}"
Format: [Person/Org 1] --[Relationship]--> [Person/Org 2]
"""
```

### C. Entity Resolution (Deduplication)

**The Problem:**
```
Source 1: "Sarah Johnson, sarah.johnson@disa.mil"
Source 2: "S. Johnson, DISA Contracting"
Source 3: "Sarah M. Johnson, linkedin.com/in/sarahjohnson"

→ All the same person!
```

**Resolution Strategy:**

**Phase 1: Deterministic Matching (High Confidence)**
```python
def deterministic_match(entity1, entity2):
    """100% match if any of these are identical"""
    
    # Email match (highest confidence)
    if entity1.email == entity2.email and entity1.email:
        return True, 1.0
    
    # LinkedIn URL match
    if entity1.linkedin == entity2.linkedin and entity1.linkedin:
        return True, 1.0
    
    # Phone match
    if normalize_phone(entity1.phone) == normalize_phone(entity2.phone):
        return True, 0.95
    
    # Name + Company + Location
    if (normalize_name(entity1.name) == normalize_name(entity2.name) and
        entity1.organization == entity2.organization and
        entity1.location == entity2.location):
        return True, 0.90
    
    return False, 0.0
```

**Phase 2: Probabilistic Matching (Medium Confidence)**
```python
from fuzzywuzzy import fuzz

def probabilistic_match(entity1, entity2):
    """Calculate match probability"""
    
    score = 0.0
    
    # Name similarity (Levenshtein distance)
    name_sim = fuzz.ratio(entity1.name, entity2.name) / 100
    score += name_sim * 0.4
    
    # Organization match
    if entity1.organization == entity2.organization:
        score += 0.3
    
    # Title similarity
    title_sim = fuzz.token_set_ratio(entity1.title, entity2.title) / 100
    score += title_sim * 0.2
    
    # Location proximity
    if entity1.location == entity2.location:
        score += 0.1
    
    # Threshold: 0.8 = likely match, 0.6-0.8 = manual review
    return score >= 0.8, score
```

**Phase 3: Graph-based Resolution**
```python
def graph_resolution(entity1, entity2, graph):
    """Use relationship context to confirm matches"""
    
    # If they share 2+ connections, likely same person
    shared_connections = graph.count_shared_neighbors(entity1, entity2)
    
    # If they worked at same places in overlapping periods
    career_overlap = check_career_timeline_overlap(entity1, entity2)
    
    # If mutual contacts refer to them identically
    reference_match = check_third_party_references(entity1, entity2)
    
    confidence = (
        min(shared_connections / 5.0, 0.4) +
        (0.3 if career_overlap else 0.0) +
        (0.3 if reference_match else 0.0)
    )
    
    return confidence >= 0.7, confidence
```

**Golden Record Creation:**
```python
def create_golden_record(matched_entities):
    """Merge all matches into single canonical entity"""
    
    golden = {
        'id': generate_uuid(),
        'source_ids': [e.id for e in matched_entities],
        
        # Take most complete/recent data
        'name': most_complete_name(matched_entities),
        'email': first_valid(e.email for e in matched_entities),
        'phone': first_valid(e.phone for e in matched_entities),
        'title': most_recent(e.title for e in matched_entities),
        'organization': most_recent(e.org for e in matched_entities),
        
        # Merge all sources
        'linkedin_profiles': unique([e.linkedin for e in matched_entities]),
        'mentioned_in': flatten([e.sources for e in matched_entities]),
        
        # Track confidence
        'confidence': calculate_merge_confidence(matched_entities),
        'last_updated': datetime.now()
    }
    
    return golden
```

## 🕸️ LAYER 3: Graph Storage

### Neo4j Schema Design

**Node Types:**

```cypher
// Person node
CREATE (p:Person {
    id: "person_12345",
    name: "Sarah Johnson",
    email: "sarah.johnson@disa.mil",
    phone: "+1-703-555-0123",
    linkedin: "linkedin.com/in/sarahjohnson",
    current_title: "Contracting Officer",
    current_organization: "DISA",
    clearance_level: "Secret",
    influence_score: 0.85,
    decision_maker: true,
    first_seen: "2024-01-15",
    last_updated: "2026-01-28",
    source_count: 15
})

// Organization node
CREATE (o:Organization {
    id: "org_789",
    name: "Defense Information Systems Agency",
    abbreviation: "DISA",
    type: "Federal Agency",
    parent: "Department of Defense",
    location: "Fort Meade, MD",
    budget: 2500000000,
    employee_count: 8000
})

// Event node
CREATE (e:Event {
    id: "event_456",
    type: "Industry Day",
    title: "Cloud Modernization Industry Day",
    date: "2025-06-15",
    location: "DISA HQ",
    agency: "DISA",
    attendee_count: 150
})

// Contract node
CREATE (c:Contract {
    id: "contract_N00178",
    contract_number: "N00178-23-C-1234",
    title: "Cloud Infrastructure Services",
    value: 5000000,
    award_date: "2023-03-15",
    start_date: "2023-04-01",
    end_date: "2026-03-31",
    agency: "DISA",
    vendor: "TechCorp Solutions"
})

// Opportunity node (from SAM.gov)
CREATE (op:Opportunity {
    id: "opp_sam_2026_001",
    notice_id: "NASA-2026-001",
    title: "Cloud Migration Services",
    agency: "NASA",
    value: 8200000,
    posted_date: "2026-01-15",
    deadline: "2026-03-15",
    naics: "541512"
})
```

**Relationship Types:**

```cypher
// Professional relationships
CREATE (sarah:Person)-[:WORKS_AT {
    start_date: "2020-01-01",
    title: "Contracting Officer",
    confidence: 0.95,
    source: "LinkedIn"
}]->(disa:Organization)

CREATE (sarah)-[:REPORTS_TO {
    since: "2020-01-01",
    source: "org_chart.pdf"
}]->(tom:Person)

// Contract relationships
CREATE (contract)-[:AWARDED_BY {
    role: "Contracting Officer",
    date: "2023-03-15"
}]->(sarah)

CREATE (contract)-[:AWARDED_TO]->(vendor:Organization)

CREATE (contract)-[:PROGRAM_MANAGER]->(michael:Person)

// Interaction relationships
CREATE (sarah)-[:MET_AT {
    date: "2025-06-15",
    context: "Industry Day",
    our_team: "John Smith"
}]->(event:Event)

CREATE (you)-[:SPOKE_WITH {
    date: "2025-06-15",
    type: "In-person",
    duration_minutes: 20,
    outcome: "Positive",
    next_action: "Send white paper"
}]->(sarah)

// Opportunity relationships
CREATE (opportunity)-[:EVALUATOR]->(sarah)
CREATE (opportunity)-[:TECHNICAL_LEAD]->(michael)
CREATE (opportunity)-[:DECISION_AUTHORITY]->(tom)

// Intelligence relationships
CREATE (sarah)-[:MENTIONED_IN {
    source_type: "SAM.gov opportunity",
    source_id: "sam_2026_001",
    context: "Listed as contracting officer",
    extracted_at: "2026-01-15"
}]->(source:Document)
```

### Graph Queries for BD Intelligence

**Query 1: "Who do I know that can intro me to X?"**
```cypher
// Find paths from You to Target
MATCH path = shortestPath(
    (you:Person {name: "Your Name"})-[*1..3]-(target:Person {name: "Sarah Johnson"})
)
RETURN path, length(path) as hops
ORDER BY hops
LIMIT 5

// Example result:
You → Michael Chen [COLLEAGUE] → Sarah Johnson [WORKS_WITH]
(2 hops, warm intro via Michael)
```

**Query 2: "Map the decision-making network for this opportunity"**
```cypher
MATCH (opp:Opportunity {notice_id: "NASA-2026-001"})
MATCH (opp)-[:EVALUATOR|TECHNICAL_LEAD|DECISION_AUTHORITY]-(person:Person)
MATCH (person)-[:WORKS_AT]->(org:Organization)
MATCH (person)-[:REPORTS_TO|WORKS_WITH]-(colleague:Person)
RETURN person, org, colleague
```

**Query 3: "Who are the top influencers at this agency?"**
```cypher
MATCH (p:Person)-[:WORKS_AT]->(org:Organization {name: "DISA"})
MATCH (p)-[r:AWARDED_BY|EVALUATOR|DECISION_AUTHORITY]->(c:Contract)
WITH p, count(c) as contract_count
MATCH (p)-[:REPORTS_TO]->(:Person)
WITH p, contract_count, count(*) as reports
RETURN p.name, p.title, contract_count, reports
ORDER BY contract_count DESC, reports DESC
LIMIT 10
```

**Query 4: "Show me all contacts with warm paths to target agency"**
```cypher
MATCH (you:Person {name: "Your Name"})-[*1..2]-(contact:Person)
MATCH (contact)-[:WORKS_AT]->(org:Organization)
WHERE org.name CONTAINS "Defense"
RETURN contact, org, length(path) as hops
ORDER BY hops
```

**Query 5: "Find companies we both worked with (for teaming)"**
```cypher
MATCH (our_company:Organization {name: "Your Company"})
MATCH (our_company)-[:CONTRACTED_WITH|TEAMED_WITH]->(shared:Organization)
MATCH (target:Organization {name: "Target Company"})-[:CONTRACTED_WITH|TEAMED_WITH]->(shared)
RETURN shared.name, count(*) as connections
ORDER BY connections DESC
```

## 🎨 LAYER 4: Applications

### App 1: Network Visualization (Enhanced)

**Features:**
```javascript
// Interactive graph with:
- Node sizing by influence score
- Color coding by role/agency
- Relationship filtering (show only WORKS_AT, etc.)
- Path highlighting (show route from You → Target)
- Time slider (show network evolution over time)
- Clustering (group by agency/organization)
```

### App 2: Contact Intelligence Dashboard

**Features:**
```
┌─────────────────────────────────────────────────────┐
│ Sarah Johnson - Contracting Officer @ DISA         │
├─────────────────────────────────────────────────────┤
│ 📊 Influence Score: 85/100 (Very High)            │
│ 🎯 Decision Maker: Yes                             │
│ 📈 Contracts Awarded: 47 ($234M total)            │
│ 🤝 Your Relationship: Strong (12 interactions)     │
│ 🔗 Network Paths: 3 mutual connections            │
│                                                     │
│ 🕐 Timeline:                                       │
│ ├─ First Contact: Jun 2024 (Industry Day)         │
│ ├─ Technical Briefing: Sep 2024                   │
│ ├─ Demo: Dec 2024                                 │
│ └─ Last Contact: Jan 2026 (12 days ago)          │
│                                                     │
│ 💡 Intelligence:                                   │
│ • Currently evaluating cloud RFP ($8M)            │
│ • Frustrated with current vendor                  │
│ • Interested in FedRAMP High capabilities         │
│ • Decision timeline: Q2 2026                      │
│                                                     │
│ 🎯 Recommended Actions:                            │
│ • Send case study on similar DoD deployment       │
│ • Request early vendor engagement                 │
│ • Leverage Michael Chen for technical validation  │
└─────────────────────────────────────────────────────┘
```

### App 3: Opportunity Advantage Calculator

**Auto-analyze based on network:**
```python
def calculate_opportunity_advantage(opportunity_id):
    """Use graph to calculate win probability"""
    
    # Find all contacts at opportunity agency
    contacts = graph.query("""
        MATCH (opp:Opportunity {id: $opp_id})
        MATCH (person:Person)-[:WORKS_AT]->(org:Organization)
        WHERE org.name = opp.agency
        RETURN person
    """, opp_id=opportunity_id)
    
    advantage = {
        'base_score': 35,  # Industry average
        'bonuses': []
    }
    
    # Decision maker contact
    for contact in contacts:
        if contact.role_type == "Decision Maker":
            if contact.relationship_strength == "Strong":
                advantage['bonuses'].append({
                    'reason': f'Strong relationship with {contact.name}',
                    'value': 25
                })
    
    # Contract history
    contracts = graph.query("""
        MATCH (person)-[:AWARDED_BY]-(contract:Contract)
        WHERE person.id IN $contact_ids
        RETURN count(contract) as count
    """, contact_ids=[c.id for c in contacts])
    
    if contracts['count'] > 5:
        advantage['bonuses'].append({
            'reason': 'Established contract history with decision makers',
            'value': 15
        })
    
    # Recent interactions
    recent = graph.query("""
        MATCH (you)-[r:SPOKE_WITH|MET_AT]-(contact)
        WHERE r.date > date() - duration('P90D')
        RETURN count(r) as count
    """)
    
    if recent['count'] >= 3:
        advantage['bonuses'].append({
            'reason': 'Active engagement (3+ interactions in 90 days)',
            'value': 5
        })
    
    total_score = advantage['base_score'] + sum(b['value'] for b in advantage['bonuses'])
    
    return {
        'win_probability': min(total_score, 85),
        'advantage_level': 'High' if total_score > 60 else 'Medium' if total_score > 45 else 'Low',
        'breakdown': advantage['bonuses']
    }
```

### App 4: Relationship Health Monitor

**Auto-alerts:**
```
⚠️ Relationship Alert: Sarah Johnson

Last contact: 95 days ago
Relationship strength: Strong → Medium (declining)
Recommended action: Schedule check-in call within 7 days

📧 Suggested message:
"Sarah, hope you're doing well! Wanted to check in and see 
how the cloud modernization initiative is progressing..."
```

### App 5: Intelligence Feed

**Auto-generate insights:**
```
🔔 New Intelligence - Jan 28, 2026

• Michael Chen promoted to Program Director at VA
  → Opportunity: Reach out to congratulate + discuss new role
  
• Sarah Johnson mentioned in DISA contract award (N00178-26-C-4567)
  → Context: Awarded to competitor TechCorp
  → Action: Research TechCorp's approach, identify differentiators
  
• Industry Day scheduled: DHS Cloud Security - Feb 15, 2026
  → Attendees: 3 of your target contacts confirmed
  → Action: Register and schedule 1-on-1 meetings
  
• New SAM.gov opportunity matches your NAICS
  → Agency: NASA
  → Evaluator: Emily Davis (2nd-degree connection via David Kim)
  → Action: Request warm intro through David
```

## 🚀 Implementation Roadmap

### Phase 1: Foundation (Week 1-2)

**Deliverables:**
- Neo4j setup and schema
- Basic ingestion from SAM.gov (already have)
- FPDS contract data ingestion
- Simple NER extraction (names, orgs)
- Entity resolution (email matching)

**Code to build:**
```
knowledge_graph/
├── collectors/
│   ├── sam_collector.py      ← Enhance existing
│   └── fpds_collector.py     ← New
├── nlp/
│   ├── ner_extractor.py
│   └── entity_resolver.py
├── graph/
│   ├── neo4j_client.py
│   └── schema.cypher
└── tests/
```

### Phase 2: Intelligence (Week 3-4)

**Deliverables:**
- Relationship extraction
- LinkedIn data import (manual CSV)
- Email archive parsing
- Conference PDF extraction
- Golden record merging

**Enhancement:**
```
├── nlp/
│   ├── relationship_extractor.py
│   └── confidence_scorer.py
├── collectors/
│   ├── linkedin_collector.py
│   ├── email_collector.py
│   └── pdf_collector.py
```

### Phase 3: Applications (Week 5-6)

**Deliverables:**
- Enhanced network visualization
- Contact intelligence dashboard
- Opportunity advantage calculator
- Relationship health monitor
- Intelligence feed

**UI Components:**
```
├── apps/
│   ├── network_viz/        ← Enhanced d3.js
│   ├── contact_intel/      ← New dashboard
│   ├── opportunity_calc/   ← Integrates with existing
│   └── health_monitor/     ← Alert system
```

### Phase 4: Automation (Week 7-8)

**Deliverables:**
- Scheduled data collection
- Auto-entity resolution
- Real-time intelligence alerts
- Graph analytics pipeline
- Privacy/compliance controls

## 💰 Cost Estimate

**Infrastructure:**
- Neo4j Community (Free) or Cloud ($65/month)
- Python libraries (Free)
- OpenAI GPT-4 API ($0.03/1K tokens, ~$50/month for extraction)
- Server/hosting ($20/month)

**Total: $135/month or free with community Neo4j + spaCy**

**ROI:**
- Current BD intelligence gathering: 20 hours/week
- With knowledge graph: 2 hours/week
- **Savings: 18 hours/week = $30K+/year** (at $35/hour)

## 🎯 Decision Points

**Technology Choices:**

**Graph Database:**
- **Neo4j** (Recommended): Most mature, great visualization, strong community
- TigerGraph: Better for very large graphs (millions of nodes)
- JanusGraph: Good if you're already on Cassandra
- **Recommendation: Neo4j Community Edition to start**

**NLP Stack:**
- **spaCy** (Free, fast): Good for basic NER
- **GPT-4** (Paid, accurate): Best for relation extraction
- Fine-tuned model (Best long-term): Requires training data
- **Recommendation: spaCy + GPT-4 hybrid**

**Hosting:**
- **Local** (Recommended for now): Full control, privacy
- Cloud (AWS Neptune, Azure Cosmos DB): Scalability
- **Recommendation: Start local, move to cloud if needed**

## 🎯 Next Steps

**Tomorrow we can:**
1. Set up Neo4j database
2. Create graph schema
3. Migrate your 10 contacts to graph
4. Build SAM.gov → Graph ingestion
5. Build FPDS → Graph ingestion

**This week:**
- Add relationship extraction
- Build entity resolution
- Create contact intelligence dashboard
- Enhance network visualization

**This month:**
- Add all data sources
- Build intelligence feed
- Create opportunity calculator
- Automate collection

**This is the system that will 10x your BD effectiveness!** 🚀

Ready to start building? Which phase would you like to tackle first?
