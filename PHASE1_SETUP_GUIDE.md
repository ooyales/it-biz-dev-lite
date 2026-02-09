# Phase 1 Setup Guide - Knowledge Graph Foundation

## Step 1: Install Neo4j Community Edition

### Option A: Desktop Application (Recommended for Mac)

**Download:**
```bash
# Visit https://neo4j.com/download/
# Download "Neo4j Desktop" for macOS
# Or direct link:
open https://neo4j.com/download-thanks-desktop/?edition=desktop&flavour=osx&release=1.5.9
```

**Installation:**
1. Open downloaded DMG
2. Drag Neo4j Desktop to Applications
3. Launch Neo4j Desktop
4. Create new project: "Federal Contracting Knowledge Graph"
5. Create new database: "contacts_graph"
6. Set password: (choose something secure, remember it!)
7. Click "Start" to launch database

**Connection details:**
```
Bolt URL: bolt://localhost:7687
HTTP URL: http://localhost:7474
Username: neo4j
Password: (your chosen password)
```

### Option B: Docker (Alternative)

```bash
# Pull Neo4j image
docker pull neo4j:latest

# Run container
docker run \
    --name neo4j-contacts \
    -p 7474:7474 -p 7687:7687 \
    -v $HOME/neo4j/data:/data \
    -v $HOME/neo4j/logs:/logs \
    -e NEO4J_AUTH=neo4j/your_password_here \
    neo4j:latest

# Access at http://localhost:7474
```

### Verify Installation

```bash
# Open browser
open http://localhost:7474

# You should see Neo4j Browser
# Login with: neo4j / your_password
# If successful, you'll see the Neo4j Browser interface
```

## Step 2: Python Environment Setup

### Install Dependencies

```bash
# Core graph libraries
pip install neo4j py2neo

# NLP libraries  
pip install spacy
python -m spacy download en_core_web_lg

# Anthropic Claude API
pip install anthropic

# Data processing
pip install pandas numpy

# Already have these, but confirming:
pip install requests python-dateutil

# Optional but useful
pip install networkx  # For graph algorithms
pip install tqdm      # Progress bars
```

### Get Anthropic API Key

```bash
# If you don't have one:
# 1. Go to https://console.anthropic.com/
# 2. Sign up or log in
# 3. Go to API Keys
# 4. Create new key
# 5. Copy key

# Set environment variable
export ANTHROPIC_API_KEY='your-key-here'

# Or add to .bashrc / .zshrc:
echo 'export ANTHROPIC_API_KEY="your-key-here"' >> ~/.zshrc
source ~/.zshrc
```

## Step 3: Test Connection

Create `test_neo4j.py`:

```python
#!/usr/bin/env python3
"""Test Neo4j connection"""

from neo4j import GraphDatabase

# Configuration
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "your_password_here"  # Change this!

def test_connection():
    print("Testing Neo4j connection...")
    
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        
        with driver.session() as session:
            result = session.run("RETURN 'Connection successful!' AS message")
            message = result.single()["message"]
            print(f"✓ {message}")
            
            # Get Neo4j version
            result = session.run("CALL dbms.components() YIELD name, versions RETURN name, versions[0] as version")
            for record in result:
                print(f"✓ {record['name']} version: {record['version']}")
        
        driver.close()
        return True
        
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False

if __name__ == "__main__":
    success = test_connection()
    
    if success:
        print("\n✓ Ready to build the knowledge graph!")
    else:
        print("\n✗ Please check Neo4j is running and credentials are correct")
        print("   Neo4j Browser: http://localhost:7474")
```

**Run test:**
```bash
python test_neo4j.py
```

**Expected output:**
```
Testing Neo4j connection...
✓ Connection successful!
✓ Neo4j Kernel version: 5.x.x

✓ Ready to build the knowledge graph!
```

## Step 4: Project Structure

```bash
# Create knowledge graph project structure
mkdir -p knowledge_graph
cd knowledge_graph

mkdir -p {config,collectors,nlp,graph,apps,tests,data,logs}

# Create structure
knowledge_graph/
├── config/
│   ├── neo4j_config.py      # Database connection config
│   └── api_keys.py           # API keys (gitignored)
├── collectors/
│   ├── sam_collector.py      # SAM.gov ingestion
│   ├── fpds_collector.py     # Contract data ingestion
│   └── base_collector.py     # Base class for collectors
├── nlp/
│   ├── entity_extractor.py   # spaCy + Claude NER
│   ├── relationship_extractor.py  # Relationship extraction
│   └── entity_resolver.py    # Deduplication logic
├── graph/
│   ├── neo4j_client.py       # Neo4j client wrapper
│   ├── schema.cypher         # Graph schema definition
│   └── queries.py            # Common graph queries
├── apps/
│   └── (visualization apps later)
├── tests/
│   ├── test_collectors.py
│   ├── test_nlp.py
│   └── test_graph.py
├── data/
│   ├── raw/                  # Raw collected data
│   ├── processed/            # Processed entities
│   └── cache/                # Cache for API responses
├── logs/
│   └── (log files)
└── main.py                   # Main orchestration script
```

## Troubleshooting

### Neo4j won't start

**Issue:** Port already in use
```bash
# Check what's using port 7474
lsof -i :7474

# Kill process if needed
kill -9 <PID>
```

**Issue:** Insufficient memory
```bash
# Edit Neo4j settings (in Neo4j Desktop)
# Settings → dbms.memory.heap.initial_size=512m
# Settings → dbms.memory.heap.max_size=1G
```

### Python dependencies conflict

```bash
# Use virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Can't connect to Neo4j

```bash
# Check Neo4j is running
# In Neo4j Desktop, database should show "Active"

# Verify in terminal
curl http://localhost:7474

# Should return HTML page
```

## Next Steps

Once everything is installed and tested:
1. ✓ Neo4j running
2. ✓ Python environment ready
3. ✓ Connection tested
4. → Ready to create graph schema (Step 5)

**Estimated setup time: 30 minutes**

Let me know when you've completed the installation and we'll move to creating the schema!
