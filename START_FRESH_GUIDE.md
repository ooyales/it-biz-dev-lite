# 🚀 START FRESH - Complete Integrated System

## What You're Getting

A **production-ready federal contracting AI system** with competitive intelligence **built-in from day one**. No separate modules to integrate—everything works together seamlessly.

## Complete System Components

### Core Files (Use These)
| File | Purpose |
|------|---------|
| `main_integrated.py` | **Main script** - Run this to execute the system |
| `claude_agents_integrated.py` | AI agents with competitive intel built-in |
| `sam_scout.py` | SAM.gov opportunity monitoring |
| `fpds_intel.py` | FPDS incumbent & pricing intelligence |
| `usaspending_intel.py` | USAspending market & teaming intelligence |
| `competitive_intel_agent.py` | Competitive intelligence orchestrator |
| `config.yaml` | **Configuration** - Edit this with your info |
| `staff_database_template.json` | Template for your team data |
| `requirements.txt` | Python dependencies |

### Documentation
| File | Purpose |
|------|---------|
| `QUICKSTART.md` | **Start here** - 5-minute quick start |
| `SETUP_GUIDE.md` | Comprehensive setup instructions |
| `DATA_SOURCES_GUIDE.md` | Deep dive on all data sources |
| `INTEGRATION_GUIDE.md` | (Reference only - already integrated!) |
| `IMPLEMENTATION_CHECKLIST.md` | Track your setup progress |

### Helper Files
| File | Purpose |
|------|---------|
| `setup_wizard.py` | Interactive configuration assistant |
| `scheduler.py` | Automated scheduling script |
| `.gitignore` | Protects sensitive data |

## 🎯 What Makes This "Integrated"

**OLD WAY (separate modules):**
```
1. SAM.gov finds opportunities
2. Manually run competitive intel
3. Manually combine data
4. Send to AI for analysis
```

**NEW WAY (integrated):**
```
1. SAM.gov finds opportunities
   ↓ (automatic)
2. FPDS + USAspending gather intel
   ↓ (automatic)
3. AI analyzes with full context
   ↓ (automatic)
4. Complete report ready
```

**One command. Complete intelligence.**

## Quick Start (10 minutes)

### Step 1: Install Python Environment (2 min)
```bash
# Create virtual environment
python3 -m venv fed_contracting_env

# Activate
source fed_contracting_env/bin/activate  # Mac/Linux
# OR
fed_contracting_env\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Get API Keys (5 min)

**SAM.gov (FREE):**
1. Go to https://open.gsa.gov/api/entity-api/
2. Register with business email
3. Copy API key

**Anthropic Claude (~$100/month):**
1. Go to https://console.anthropic.com/
2. Create account and add payment
3. Generate API key (starts with "sk-ant-")

### Step 3: Configure System (2 min)

**Option A: Interactive Wizard (Easiest)**
```bash
python setup_wizard.py
```
Follow the prompts.

**Option B: Manual Edit**
1. Open `config.yaml`
2. Add your API keys
3. Set company info (name, UEI, CAGE, NAICS codes)
4. Configure search parameters

### Step 4: Add Staff Data (10-30 min)
```bash
# Copy template
cp staff_database_template.json data/staff_database.json

# Edit with your team info
nano data/staff_database.json  # or use any text editor
```

Fill in your 20 staff members' skills, clearances, certs.

### Step 5: Test It! (1 min)
```bash
# Test SAM.gov connection
python main_integrated.py --test

# Run full analysis with competitive intelligence
python main_integrated.py
```

### Step 6: Review Results
```
data/
├── opportunities/     ← Raw SAM.gov data
├── analysis/          ← AI analysis + competitive intel
└── reports/
    ├── action_report_*.txt              ← **READ THIS FIRST**
    └── competitive_intel_summary_*.txt  ← Intel overview
```

## What Happens When You Run It

```
═══════════════════════════════════════════════════════════════
FEDERAL CONTRACTING AI - INTEGRATED SYSTEM
═══════════════════════════════════════════════════════════════

[1/5] Searching SAM.gov...
  ✓ Found 23 opportunities

[2/5] Gathering competitive intelligence...
  ✓ Running intel 1/23: ABC123
  ✓ Running intel 2/23: DEF456
  ... (automatic for all opportunities)

[3/5] AI analysis with competitive context...
  ✓ Processing 1/23: Cloud Services
  ✓ Processing 2/23: Cybersecurity SOC
  ... (AI considers both opportunity + competitive intel)

[4/5] Generating reports...
  ✓ Action report generated
  ✓ Competitive intel summary generated

[5/5] Sending notifications...
  ✓ Email sent (3 high-priority opportunities)

═══════════════════════════════════════════════════════════════
Pipeline Complete!
  Opportunities Found: 23
  Analyzed: 23
  With Competitive Intel: 23
  High Priority (≥7): 3

Reports:
  data/reports/action_report_20260123_143022.txt
  data/reports/competitive_intel_summary_20260123_143022.txt
═══════════════════════════════════════════════════════════════
```

## Sample Output - Before vs. After

### BEFORE (Basic Analysis Only)
```
Title: DoD Cloud Migration Services
Fit Score: 7/10
Recommendation: PURSUE

Next Actions:
- Review requirements
- Assess team capability
- Prepare proposal
```

### AFTER (Integrated with Competitive Intel)
```
Title: DoD Cloud Migration Services
Fit Score: 8.5/10
Win Probability: 68%
Recommendation: STRONGLY PURSUE

═══════════════════════════════════════════════════════════════
COMPETITIVE INTELLIGENCE
═══════════════════════════════════════════════════════════════

INCUMBENT: TechCorp Solutions Inc.
  Contract: $2.4M (expires in 4 months)
  3-Year Revenue: $48M (large business)
  Assessment: VULNERABLE - approaching contract end

PRICING INTELLIGENCE (47 similar contracts):
  Market Average: $2.8M
  Your Target: $2.5M - $3.0M
  Trend: INCREASING (+12% annually)

MARKET ANALYSIS:
  Trend: GROWING (+18% per year)
  Agency Preference: Small business (70% of awards)
  Total Market: $450M annually

COMPETITIVE POSITION:
  Incumbent Strength: MODERATE
  Your Advantage: Small business vs. large incumbent
  Strategy: Prime with FedRAMP-certified subcontractor

═══════════════════════════════════════════════════════════════
RECOMMENDED STRATEGY
═══════════════════════════════════════════════════════════════

1. IMMEDIATE: Contact agency for technical briefing
2. THIS WEEK: Partner with SecureCloud Inc. for FedRAMP
3. WEEK 2: Submit capability statement
4. WEEK 3: Begin proposal development
5. Target price: $2.7M (competitive, profitable)

WIN FACTORS:
✓ Small business advantage
✓ Incumbent contract expiring soon
✓ Growing market with budget increase
✓ Your pricing is competitive
✓ Strong past performance match

RISKS:
⚠ Need FedRAMP partner (mitigation: teaming identified)
⚠ Incumbent has relationship (mitigation: SB preference)
```

## Command Reference

### Basic Execution
```bash
# Run with all features
python main_integrated.py

# Look back 14 days instead of config default
python main_integrated.py --days 14

# Disable competitive intel (faster, less insight)
python main_integrated.py --no-intel

# Test mode (SAM.gov search only)
python main_integrated.py --test
```

### Automated Scheduling

**Linux/Mac (cron):**
```bash
# Edit crontab
crontab -e

# Run daily at 9 AM
0 9 * * * cd /path/to/system && /path/to/venv/bin/python main_integrated.py

# Run twice daily (9 AM and 5 PM)
0 9,17 * * * cd /path/to/system && /path/to/venv/bin/python main_integrated.py
```

**Windows (Task Scheduler):**
1. Open Task Scheduler
2. Create Basic Task
3. Trigger: Daily at 9:00 AM
4. Action: Start program
   - Program: `C:\path\to\venv\Scripts\python.exe`
   - Arguments: `main_integrated.py`
   - Start in: `C:\path\to\system`

**Python Scheduler (any OS):**
```bash
# Edit scheduler.py to set times
python scheduler.py
```

## Configuration Options

### Competitive Intelligence Control

In `config.yaml`:

```yaml
competitive_intelligence:
  enabled: true
  
  triggers:
    min_value: 500000  # Only run intel for $500K+ opportunities
    # min_value: 0     # Run for all opportunities (default)
```

**When to use min_value:**
- Set to `0`: Run intel on everything (thorough, slower)
- Set to `500000`: Only $500K+ opportunities (faster, focused)
- Set to `1000000`: Only $1M+ opportunities (high-value focus)

### Intelligence Features

```yaml
competitive_intelligence:
  features:
    incumbent_identification: true   # Who has contract now
    pricing_analysis: true           # Historical pricing
    market_trends: true              # Market growth/decline
    teaming_partners: false          # Find partners (slower)
    competitor_profiling: true       # Incumbent details
```

**Recommended Settings:**
- **Small teams:** Set `teaming_partners: false` (faster)
- **Large pursuits:** Set `teaming_partners: true` (more intel)

## Cost Breakdown

| Component | Cost | Notes |
|-----------|------|-------|
| SAM.gov API | FREE | Unlimited with rate limits |
| FPDS API | FREE | Unlimited |
| USAspending API | FREE | Unlimited |
| Claude AI | $100-150/mo | ~50 opportunities/day |
| **TOTAL** | **$100-150/mo** | All-in cost |

**ROI Calculation:**
- Win one $100K contract = 10+ years of system cost
- Time saved: 15-20 hours/week = $30K-50K/year
- Better decisions: +20% win rate = $$$$

## Troubleshooting

### No opportunities found
```bash
# Check your NAICS codes in config.yaml
# Broaden search criteria
# Verify SAM.gov API key
```

### Competitive intel errors
```bash
# Check logs: logs/fed_contracting_ai.log
# FPDS/USAspending are free but can be slow
# Try reducing lookback_years in config
```

### Slow performance
```bash
# Set min_value to only analyze high-value opps
# Disable teaming_partners feature
# Reduce lookback_years from 3 to 2
```

### Python errors
```bash
# Make sure virtual environment is activated
source fed_contracting_env/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

## Files You Can Ignore

These are reference/legacy files (already integrated):
- `main.py` - Old version without integrated intel
- `claude_agents.py` - Old version without integrated intel
- `INTEGRATION_GUIDE.md` - For adding intel to old system

**Use the `_integrated` versions instead!**

## Next Steps After Setup

### Week 1: Learning
- [ ] Run daily and review outputs
- [ ] Compare opportunities with/without intel
- [ ] Understand the competitive intelligence reports
- [ ] Refine keywords and filters in config

### Week 2: Optimization
- [ ] Adjust scoring weights based on results
- [ ] Set up automated scheduling
- [ ] Configure notifications (email/Slack)
- [ ] Train team on using reports

### Week 3: Integration
- [ ] Establish bid/no-bid workflow
- [ ] Create proposal kickoff process
- [ ] Track which opps you pursue
- [ ] Measure win rate improvement

### Month 2: Advanced
- [ ] Build historical win/loss database
- [ ] Customize competitive intel thresholds
- [ ] Add agency-specific keywords
- [ ] Develop teaming partner relationships

## What Success Looks Like

**Week 1:**
- System running daily automatically
- Team reading action reports
- 3-5 high-priority opportunities identified

**Month 1:**
- First proposal submitted using system intel
- 10-15 opportunities pursued
- Time savings: 15+ hours/week

**Month 3:**
- First contract win using system intelligence
- Established workflow and processes
- System becomes core BD tool

**Month 6:**
- Multiple wins attributable to system
- ROI: 10x-50x cost of system
- Can't imagine working without it

## Support Resources

- **Quick Start:** This file
- **Detailed Setup:** SETUP_GUIDE.md
- **Data Sources:** DATA_SOURCES_GUIDE.md
- **Troubleshooting:** Check logs in `logs/fed_contracting_ai.log`
- **Configuration:** Review `config.yaml` comments

## Important Reminders

✅ **You're running the integrated version** - competitive intelligence is automatic  
✅ **All data sources are FREE** - only Claude AI costs money  
✅ **Files are created automatically** - check `data/reports/` for outputs  
✅ **Logs tell you everything** - check `logs/` if something seems wrong  
✅ **Start small** - test with one day of data first  

## Final Checklist

Before you begin:
- [ ] Python 3.8+ installed
- [ ] SAM.gov API key obtained (FREE)
- [ ] Anthropic API key obtained (~$100/mo)
- [ ] Company info ready (UEI, CAGE, NAICS)
- [ ] 30 minutes for initial setup
- [ ] Staff data prepared (or use template for now)

Ready? Let's go! 🚀

```bash
python setup_wizard.py
```

---

**Questions?** Everything is documented. Check the guides or review example outputs in the documentation.

**Problems?** Check `logs/fed_contracting_ai.log` for detailed error messages.

**Success?** You should see your first action report with competitive intelligence in minutes!
