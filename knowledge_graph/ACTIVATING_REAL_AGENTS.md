# Activating Real AI Agents

## ✅ Current Status

**Working in Demo Mode:**
- ✓ Agent 2: Competitive Intelligence (shows demo data)
- ✓ Agent 3: Capability Matching (shows demo data)
- ✓ Agent 4: RFI Generator (shows requirements message)
- ✓ Agent 5: Proposal Writer (shows requirements message)
- ✓ Agent 6: Pricing Generator (shows requirements message)

---

## 🚀 Activate Real Agents

### Step 1: Fix competitive_intel.py Import

```bash
# Copy the fixed competitive_intel.py
cp /mnt/user-data/outputs/knowledge_graph/competitive_intel.py knowledge_graph/

# Restart dashboard
python team_dashboard_integrated.py
```

### Step 2: Ensure Neo4j is Running

**Competitive Intelligence needs Neo4j** for company/contact data.

```bash
# Check if Neo4j is running
neo4j status

# If not running, start it
neo4j start

# Verify connection
# Database should be: contactsgraphdb
# URI: bolt://localhost:7687
```

**Environment Variables:**
```bash
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USER="neo4j"
export NEO4J_PASSWORD="your_password"
```

### Step 3: Set Up Claude API for Document Generation

**RFI Generator, Proposal Writer** need Claude API:

```bash
# Get API key from: https://console.anthropic.com/
export ANTHROPIC_API_KEY="sk-ant-..."

# Add to your shell profile for persistence
echo 'export ANTHROPIC_API_KEY="sk-ant-..."' >> ~/.zshrc  # or ~/.bashrc
```

### Step 4: Configure Company Data

**For best results, agents need your company data:**

1. **Company Profile** (`knowledge_graph/company_profile.json`):
```json
{
  "name": "Your Company Name",
  "capabilities": ["Cloud", "Cybersecurity", "Software Dev"],
  "certifications": ["8(a)", "SDVOSB", "ISO 27001"],
  "past_performance": [
    {
      "client": "Agency Name",
      "project": "Project Description",
      "value": "$2.5M",
      "outcome": "Excellent"
    }
  ]
}
```

2. **Staff Database** (already in Neo4j via contacts sync)

3. **Labor Rates** (for pricing agent)

---

## 🧪 Testing Real Agents

Once configured:

### Test Competitive Intelligence:
```bash
# Should now query FPDS for real incumbents
# Should check Neo4j for existing relationships
# Should return actual competitor data
```

### Test RFI Generator:
```bash
# Should use Claude AI to write professional RFI
# Should download as .docx file
# Should include your company capabilities
```

### Test Proposal Writer:
```bash
# Should generate full proposal with:
# - Technical Approach
# - Management Plan
# - Staffing Plan
# - Past Performance
```

### Test Pricing Generator:
```bash
# Should create Excel workbook with:
# - Labor categories & rates
# - BOE calculations
# - IGCE estimate
```

---

## 🔍 Troubleshooting

### Competitive Intel Still Shows Demo Data

**Check:**
1. Neo4j is running: `neo4j status`
2. Database exists: `contactsgraphdb`
3. Fixed import was applied: `grep "knowledge_graph.graph" knowledge_graph/competitive_intel.py`

### RFI/Proposal Generation Fails

**Check:**
1. API key is set: `echo $ANTHROPIC_API_KEY`
2. Key has credits: Check Anthropic console
3. File permissions: Can write to `knowledge_graph/outputs/`

### Import Errors Persist

**Solution:**
```bash
# Ensure __init__.py files exist
touch knowledge_graph/__init__.py
touch knowledge_graph/graph/__init__.py

# Verify agent_executor.py is in root
ls -la agent_executor.py
```

---

## 📊 Success Indicators

**Real Agents Working:**
- ✅ Competitive Intel shows actual companies from FPDS
- ✅ RFI downloads a .docx file
- ✅ Proposal downloads a comprehensive .docx
- ✅ Pricing downloads an .xlsx workbook
- ✅ No "Demo mode" notes in results

**Demo Mode (Still):**
- ⚠️ Results show "Using demo data" note
- ⚠️ Recommendations mention missing configuration
- ⚠️ No file downloads available

---

## 🎯 Full Activation Checklist

- [ ] Copy fixed `competitive_intel.py`
- [ ] Neo4j running with `contactsgraphdb`
- [ ] Set `NEO4J_URI`, `NEO4J_PASSWORD`
- [ ] Set `ANTHROPIC_API_KEY`
- [ ] Create `company_profile.json`
- [ ] Test each agent
- [ ] Verify file downloads work

---

## 💡 Hybrid Mode

**The system is designed to work in hybrid mode:**
- If Neo4j unavailable → Shows demo incumbents
- If API key missing → Shows requirements message
- If everything configured → Uses real agents

**This means:**
- Platform works immediately (demo)
- Gradually activate features as you configure
- No "all or nothing" requirement
