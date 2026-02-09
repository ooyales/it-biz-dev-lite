# Implementation Checklist

Use this checklist to track your setup progress.

## Phase 1: Initial Setup (Day 1)

- [ ] Install Python 3.8+ on your computer
- [ ] Create virtual environment: `python3 -m venv fed_contracting_env`
- [ ] Activate virtual environment
- [ ] Install dependencies: `pip install -r requirements.txt`
- [ ] Create required directories (or run `setup_wizard.py`)

## Phase 2: Get API Keys (Day 1)

### SAM.gov API Key (Free)
- [ ] Go to https://open.gsa.gov/api/entity-api/
- [ ] Register for API key
- [ ] Verify email and activate key
- [ ] Test key works

### Anthropic API Key (Paid)
- [ ] Create account at https://console.anthropic.com/
- [ ] Add payment method
- [ ] Generate API key
- [ ] Note: Expect ~$100/month for typical usage

## Phase 3: Configuration (Day 1-2)

### Option A: Use Setup Wizard (Recommended)
- [ ] Run: `python setup_wizard.py`
- [ ] Follow prompts to configure system

### Option B: Manual Configuration
- [ ] Copy and edit `config.yaml`
- [ ] Add SAM.gov API key
- [ ] Add Anthropic API key
- [ ] Set company name, UEI, CAGE code
- [ ] Add NAICS codes (minimum 2-3)
- [ ] Set set-aside categories
- [ ] Configure search parameters:
  - [ ] Contract value range
  - [ ] Keywords (5-10 recommended)
  - [ ] Lookback days (7-14 recommended)

## Phase 4: Staff Database (Day 2)

- [ ] Copy `staff_database_template.json` to `data/staff_database.json`
- [ ] For each of your 20 staff members, add:
  - [ ] Basic info (name, title, ID)
  - [ ] Clearance level and expiry
  - [ ] Technical skills
  - [ ] Certifications
  - [ ] Domain expertise
  - [ ] Years of experience
  - [ ] Education
  - [ ] Past performance highlights
  - [ ] NAICS experience
- [ ] Remove the TEMPLATE entry
- [ ] Validate JSON format

## Phase 5: Testing (Day 2)

- [ ] Test SAM.gov connection: `python main.py --test`
- [ ] Verify opportunities are found
- [ ] Check logs in `logs/fed_contracting_ai.log`
- [ ] Review output files in `data/opportunities/`
- [ ] Run first full analysis: `python main.py`
- [ ] Review analysis results in `data/analysis/`
- [ ] Review action report in `data/reports/`
- [ ] Verify fit scores make sense

## Phase 6: Optimization (Week 1)

- [ ] Review first week of results
- [ ] Adjust keywords if too many/few results
- [ ] Tune value range if needed
- [ ] Adjust scoring weights in config.yaml:
  - [ ] NAICS match weight
  - [ ] Set-aside weight
  - [ ] Value appropriateness weight
  - [ ] Keyword match weight
- [ ] Set appropriate thresholds:
  - [ ] Capability match threshold
  - [ ] RFI auto-draft threshold
- [ ] Review AI analysis quality
- [ ] Refine staff database with more details if needed

## Phase 7: Automation (Week 2)

### Choose Your Automation Method:

#### Option A: Cron (Linux/Mac)
- [ ] Edit crontab: `crontab -e`
- [ ] Add schedule (e.g., daily at 9 AM):
  ```
  0 9 * * * cd /path/to/fed-contracting-ai && /path/to/venv/bin/python main.py
  ```
- [ ] Test cron job runs correctly
- [ ] Monitor logs to ensure it works

#### Option B: Windows Task Scheduler
- [ ] Open Task Scheduler
- [ ] Create new basic task
- [ ] Set trigger (daily, time)
- [ ] Set action: run python script
- [ ] Test task runs correctly

#### Option C: Python Scheduler
- [ ] Edit `scheduler.py` with desired schedule
- [ ] Run in background: `nohup python scheduler.py &`
- [ ] Or run as a service
- [ ] Monitor scheduler logs

## Phase 8: Notifications (Week 2)

### Email Notifications (Optional)
- [ ] Get SMTP credentials (Gmail app password recommended)
- [ ] Configure in config.yaml
- [ ] Test email notifications
- [ ] Verify high-priority alerts work

### Slack Notifications (Optional)
- [ ] Create Slack app
- [ ] Get webhook URL
- [ ] Configure in config.yaml
- [ ] Test Slack notifications
- [ ] Set up dedicated channel

## Phase 9: Workflow Integration (Week 3-4)

- [ ] Train team on reading reports
- [ ] Establish review process for high-priority opportunities
- [ ] Create workflow for:
  - [ ] Reviewing AI recommendations
  - [ ] Approving RFI responses
  - [ ] Deciding bid/no-bid
  - [ ] Assigning proposal responsibilities
- [ ] Integrate with existing tools:
  - [ ] CRM
  - [ ] Proposal management software
  - [ ] Project management tools

## Phase 10: Ongoing Maintenance

### Weekly
- [ ] Review action reports
- [ ] Act on high-priority opportunities
- [ ] Check logs for errors
- [ ] Monitor API costs

### Monthly
- [ ] Update staff database (new certs, skills)
- [ ] Review and adjust keywords
- [ ] Analyze win/loss data
- [ ] Refine search parameters
- [ ] Review AI analysis accuracy

### Quarterly
- [ ] Major configuration review
- [ ] Update NAICS codes if focus changes
- [ ] Add new contract vehicles
- [ ] Review and update past performance database
- [ ] Assess ROI and adjust budget

## Advanced Features (Future)

- [ ] Add competitive intelligence agent
- [ ] Build full proposal writer
- [ ] Create web dashboard
- [ ] Integrate with pricing tools
- [ ] Add teaming partner finder
- [ ] Build past performance library
- [ ] Create custom reporting

## Success Metrics

Track these to measure ROI:

- [ ] Opportunities identified per week
- [ ] Time saved on research (hours/week)
- [ ] High-quality opportunities (score ≥ 7)
- [ ] RFI response rate
- [ ] Proposal submission rate
- [ ] Win rate
- [ ] Revenue from opportunities found by system
- [ ] Cost per opportunity analyzed
- [ ] Team satisfaction with tool

## Troubleshooting Completed

If you encounter issues, check these off as you resolve them:

- [ ] SAM.gov API connection issues
- [ ] Claude API connection issues
- [ ] No opportunities found
- [ ] Too many irrelevant opportunities
- [ ] AI scores seem inaccurate
- [ ] RFI drafts need improvement
- [ ] Notification issues
- [ ] Scheduling problems
- [ ] Performance/speed issues

## Support Resources Used

- [ ] Read README.md
- [ ] Read SETUP_GUIDE.md
- [ ] Reviewed example outputs
- [ ] Consulted SAM.gov API docs
- [ ] Consulted Claude API docs
- [ ] Joined federal contracting forums
- [ ] Connected with other small contractors

---

## Notes and Customizations

Use this space to track your specific configuration choices and customizations:

```
Date started: _________________

Company specifics:
- NAICS codes: _______________________________________
- Set-asides: ________________________________________
- Target contract size: $_____________ to $___________
- Primary keywords: __________________________________

Customizations made:
1. ________________________________________________
2. ________________________________________________
3. ________________________________________________

Issues encountered and solutions:
1. ________________________________________________
2. ________________________________________________
3. ________________________________________________

```
