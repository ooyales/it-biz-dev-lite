# Dashboard Integration Guide

## 🎯 Integrating Agents with Team Dashboard

This guide shows you how to add the Opportunity Scout and Competitive Intelligence agents to your existing team dashboard.

## 🏗️ Architecture Overview

```
Team Dashboard (http://localhost:8080)
├─ Home (existing)
├─ Contacts (existing)
├─ Contact Detail (existing)
├─ BD Intelligence (NEW!) ← Agents integrated here
└─ API Endpoints (NEW!)
    ├─ /api/scout/opportunities
    ├─ /api/scout/summary
    ├─ /api/intel/incumbents
    ├─ /api/intel/teaming-partners
    └─ /api/dashboard/bd-intelligence
```

## 📦 Step-by-Step Integration

### Step 1: Add API Routes to Flask App

Edit your `team_dashboard_app.py`:

```python
# At the top, add imports
import sys
sys.path.append('knowledge_graph')

# Add this after your existing routes
# Copy the routes from agent_api_routes.py

# Or include the file:
exec(open('agent_api_routes.py').read())
```

**Full integration example:**

```python
#!/usr/bin/env python3
from flask import Flask, render_template, jsonify, request
import sqlite3
import os
import sys

# Add knowledge_graph to path
sys.path.append('knowledge_graph')

app = Flask(__name__)

# ... your existing routes ...

# ============================================================================
# ADD AGENT API ROUTES HERE
# ============================================================================

# Copy all routes from agent_api_routes.py
# OR load them:
with open('agent_api_routes.py') as f:
    code = f.read()
    # Remove the imports and app definition from the code
    code = '\n'.join([line for line in code.split('\n') 
                      if not line.startswith('from flask') 
                      and not line.startswith('app =')])
    exec(code)

# ============================================================================
# ADD NEW ROUTE FOR BD INTELLIGENCE PAGE
# ============================================================================

@app.route('/bd-intelligence')
def bd_intelligence():
    """BD Intelligence Hub page"""
    return render_template('bd-intelligence.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
```

### Step 2: Add Template File

Copy the BD Intelligence template:

```bash
cp /mnt/user-data/outputs/templates/bd-intelligence.html templates/
```

### Step 3: Update Navigation

Edit your main dashboard template to add a link:

```html
<!-- In your navigation menu -->
<li class="nav-item">
    <a class="nav-link" href="/bd-intelligence">
        <i class="fas fa-chart-line"></i> BD Intelligence
    </a>
</li>
```

### Step 4: Install Dependencies

```bash
# If not already installed
pip install flask-cors
```

### Step 5: Test the Integration

```bash
# Start the dashboard
cd ~/Downloads/ai-assistants-for-federal-contracting-operations
python team_dashboard_app.py

# Visit:
http://localhost:8080/bd-intelligence
```

## 🎨 What You Get

### BD Intelligence Dashboard Features

**Overview Cards:**
- Total opportunities analyzed
- High-priority opportunities
- Opportunities with contacts
- Total network contacts

**Opportunities Tab:**
- Live opportunity list with scoring
- Priority filters (HIGH/MEDIUM/LOW)
- Contact presence filter
- One-click to run scout
- Click opportunity for details

**Competitive Intel Tab:**
- Agency analysis
- Incumbent identification
- Teaming partner recommendations
- Market sizing data

**Recent Activity Tab:**
- Scout run history
- Intel report history
- Collection activity

## 🔌 API Endpoints Available

### Opportunity Scout

```javascript
// Get scored opportunities
GET /api/scout/opportunities?days=7&priority=HIGH

// Get summary stats
GET /api/scout/summary

// Trigger scout run
POST /api/scout/run
Body: {"days": 7}
```

### Competitive Intelligence

```javascript
// Get incumbents at agency
GET /api/intel/incumbents?agency=NASA&naics=541512

// Analyze agency spending
GET /api/intel/agency-spending?agency=NASA

// Find teaming partners
GET /api/intel/teaming-partners?agency=NASA

// Generate full report
POST /api/intel/report
Body: {"agency": "NASA", "naics": "541512"}
```

### Dashboard Integration

```javascript
// Complete BD intelligence summary
GET /api/dashboard/bd-intelligence

// Recent activity feed
GET /api/dashboard/recent-activity
```

## 💡 Usage Examples

### Example 1: Dashboard Homepage Widget

Add this to your main dashboard:

```html
<div class="card">
    <div class="card-header">
        <h5>BD Intelligence</h5>
    </div>
    <div class="card-body">
        <div id="bd-widget"></div>
    </div>
</div>

<script>
async function loadBDWidget() {
    const res = await fetch('/api/scout/summary');
    const data = await res.json();
    
    document.getElementById('bd-widget').innerHTML = `
        <p><strong>${data.high_priority}</strong> high-priority opportunities</p>
        <p><strong>${data.with_contacts}</strong> with existing contacts</p>
        <a href="/bd-intelligence" class="btn btn-primary">View All</a>
    `;
}

loadBDWidget();
</script>
```

### Example 2: Opportunity Alert Banner

```html
<script>
async function checkHighPriority() {
    const res = await fetch('/api/scout/opportunities?priority=HIGH');
    const data = await res.json();
    
    if (data.opportunities.length > 0) {
        // Show alert banner
        const banner = document.createElement('div');
        banner.className = 'alert alert-success';
        banner.innerHTML = `
            <strong>${data.opportunities.length} high-priority opportunities!</strong>
            <a href="/bd-intelligence">Review now</a>
        `;
        document.body.prepend(banner);
    }
}

checkHighPriority();
</script>
```

### Example 3: Contact Detail Enhancement

On your contact detail page, show related opportunities:

```javascript
async function showContactOpportunities(contactName, agency) {
    const res = await fetch('/api/scout/opportunities');
    const data = await res.json();
    
    // Filter opportunities at this contact's agency
    const relevant = data.opportunities.filter(opp => 
        opp.agency.includes(agency)
    );
    
    // Display them
    document.getElementById('related-opps').innerHTML = 
        relevant.map(opp => `
            <div class="mb-2">
                <strong>${opp.title}</strong><br>
                Win Probability: ${opp.win_probability}%
            </div>
        `).join('');
}
```

## 🔄 Workflow Integration

### Typical BD Workflow with Integrated Dashboard

**Morning Routine:**
1. Open dashboard → BD Intelligence page
2. Review high-priority opportunities
3. Check which ones have your contacts
4. Click opportunity → See incumbent analysis
5. Make pursue/pass decision
6. Contact decision makers

**Weekly Review:**
1. Dashboard → BD Intelligence
2. Run scout for last 7 days
3. Export competitive intel report
4. Team meeting to review priorities

**Pre-Proposal:**
1. Find opportunity in dashboard
2. Check competitive intel for that agency
3. View your contacts at agency
4. Identify teaming partners
5. Calculate win probability
6. Make bid/no-bid decision

## 🎯 Advanced: Auto-Refresh

Add this to run scout automatically:

```python
from apscheduler.schedulers.background import BackgroundScheduler

def run_daily_scout():
    """Run scout in background"""
    scout = OpportunityScout()
    scout.run_daily_scout(days_back=1)
    scout.close()

# Schedule daily at 8 AM
scheduler = BackgroundScheduler()
scheduler.add_job(run_daily_scout, 'cron', hour=8)
scheduler.start()
```

## 📊 Data Flow Diagram

```
SAM.gov API
    ↓
Opportunity Scout
    ↓
scout_data_*.json (cache)
    ↓
Flask API (/api/scout/opportunities)
    ↓
Dashboard UI (bd-intelligence.html)
    ↓
User makes decision

FPDS/USASpending API
    ↓
Competitive Intel Agent
    ↓
Neo4j Knowledge Graph
    ↓
Flask API (/api/intel/*)
    ↓
Dashboard UI (competitive tab)
    ↓
User analyzes competition
```

## 🎊 Result: Unified BD Platform

**Before Integration:**
```
Team Dashboard: Just contacts
Opportunity Scout: Command line
Competitive Intel: Command line
Knowledge Graph: Neo4j Browser

→ Siloed, disconnected
```

**After Integration:**
```
Unified Dashboard:
├─ All contacts (existing)
├─ Opportunity intelligence (NEW)
├─ Competitive analysis (NEW)
├─ Win probability calculator (NEW)
├─ Relationship mapping (NEW)
└─ One-click decisions

→ Integrated, powerful, actionable
```

## 🚀 Quick Start

```bash
# 1. Copy files
cp /mnt/user-data/outputs/agent_api_routes.py .
cp /mnt/user-data/outputs/templates/bd-intelligence.html templates/

# 2. Update team_dashboard_app.py (add routes)

# 3. Restart dashboard
python team_dashboard_app.py

# 4. Visit
open http://localhost:8080/bd-intelligence

# 5. Done!
```

## 💡 Pro Tips

1. **Start Simple:** Just add the BD Intelligence page first
2. **Test APIs:** Use `/api/scout/summary` to verify it works
3. **Add Gradually:** Add widgets to existing pages over time
4. **Mobile Friendly:** Bootstrap makes it responsive automatically
5. **Real-time Updates:** Use JavaScript `setInterval()` for auto-refresh

## 🎯 Next Level: Future Agent Integration

When you build Agents 3-6, they'll plug in the same way:

```python
# Agent 3: Capability Matching
@app.route('/api/capabilities/match')
def match_capabilities():
    # Return staff matching for opportunity
    pass

# Agent 4: RFI Response
@app.route('/api/rfi/generate')
def generate_rfi():
    # Return drafted RFI response
    pass

# Agent 5: Proposal Assistant
@app.route('/api/proposal/outline')
def proposal_outline():
    # Return proposal structure
    pass
```

All following the same pattern! 🎨

---

**You now have a complete BD intelligence platform in your dashboard!** 🚀
