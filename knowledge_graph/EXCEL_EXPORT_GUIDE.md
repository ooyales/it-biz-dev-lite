# Excel Export Guide

## 📊 Browse Your BD Intelligence Data in Excel

The Excel exporter creates a professional multi-tab workbook from your Neo4j knowledge graph, giving you the familiar Excel interface for browsing, filtering, and analyzing your BD intelligence data.

## 🎯 Why Excel + Neo4j?

**Best of Both Worlds:**
- 🚀 **Neo4j**: Fast queries, relationship mapping, agent processing
- 📊 **Excel**: Familiar interface, easy browsing, portable, formulas

## 🚀 Quick Start

```bash
# Install openpyxl if needed
pip install openpyxl

# Copy the exporter
cp /mnt/user-data/outputs/knowledge_graph/excel_exporter.py knowledge_graph/

# Run it!
cd knowledge_graph
python excel_exporter.py
```

You'll get a file like: `bd_intelligence_20260130_143022.xlsx`

## 📊 Workbook Structure

### Tab 1: Dashboard
- Key Performance Indicators with formulas
- Total Opportunities, High Priority, Contacts, etc.
- Instructions for using the workbook

### Tab 2: Opportunities (200 rows)
- All opportunities with scoring
- Win probability, priority, contacts
- Clickable SAM.gov links
- Sortable/filterable table

### Tab 3: Contacts (200+ rows)
- Your entire network from Neo4j
- Name, title, organization, email
- Role type, influence level

### Tab 4: Organizations
- All organizations
- Contact counts, contract counts
- Type and activity level

### Tab 5: Contracts
- FPDS contract data
- Agency, contractor, value
- Award dates, descriptions

## 💡 Common Use Cases

**Find High-Priority Opportunities:**
1. Go to Opportunities tab
2. Filter Priority = "HIGH"
3. Sort by Win Probability

**Export Contacts for Outreach:**
1. Go to Contacts tab
2. Filter by Organization
3. Copy to new sheet or export

**Identify Top Incumbents:**
1. Go to Contracts tab
2. Create pivot table by Contractor
3. Sum values

## 🔄 Keeping It Updated

Re-export weekly or after collecting new opportunities:

```bash
cd knowledge_graph
python excel_exporter.py
```

The file is a snapshot - Neo4j remains your source of truth!

## 📈 Excel vs Neo4j

**Use Excel For:**
- Quick browsing
- Team sharing
- Offline access
- Pivot tables
- Reports

**Use Neo4j For:**
- Agent processing
- Complex queries
- Real-time updates
- Relationship mapping

**Use Both:**
- Neo4j = Source of truth
- Excel = Weekly snapshots
- Agents run on Neo4j
- Teams browse in Excel

---

**Your BD intelligence is now in both formats!** 🎉
