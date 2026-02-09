# 🚀 Quick Start - Simplified Setup

## What's Changed - Easier Setup!

✅ **No company name required** - Optional for reports only  
✅ **No UEI number required** - Not needed for the system  
✅ **No CAGE code required** - Not needed for the system  
✅ **No email/password required** - Notifications are completely optional  

**What YOU NEED:**
1. **SAM.gov API key** (FREE)
2. **Anthropic API key** (~$100/month)
3. **Your NAICS codes** (the codes you compete under)
4. **Your set-aside status** (small business, 8(a), etc.)

That's it!

## 5-Minute Setup

### Step 1: Install Python Dependencies (2 min)
```bash
# Create virtual environment
python3 -m venv fed_contracting_env

# Activate it
source fed_contracting_env/bin/activate  # Mac/Linux
# OR
fed_contracting_env\Scripts\activate  # Windows

# Install packages
pip install -r requirements.txt
```

### Step 2: Get API Keys (3 min)

**SAM.gov (FREE):**
- Go to https://open.gsa.gov/api/entity-api/
- Register with any email
- Copy API key

**Anthropic Claude (~$100/month):**
- Go to https://console.anthropic.com/
- Create account, add payment
- Generate API key (starts with "sk-ant-")

### Step 3: Configure (Interactive - 2 min)
```bash
python setup_wizard.py
```

You'll be asked for:
1. ✅ **SAM.gov API key** (paste it in)
2. ✅ **Anthropic API key** (paste it in)
3. ✅ **NAICS codes** (your codes, one at a time)
4. ✅ **Set-asides** (select from menu)
5. ✅ **Search keywords** (your domain keywords)
6. ❌ Company name (OPTIONAL - just press Enter to skip)
7. ❌ Email notifications (OPTIONAL - select "no")
8. ❌ Slack notifications (OPTIONAL - select "no")

**Pro tip:** You can skip company name and notifications. They're completely optional!

### Step 4: Add Staff Data (Later)
```bash
# Copy template
cp staff_database_template.json data/staff_database.json

# You can edit this later - system will work without it initially
```

**Note:** Staff database is used for capability matching. You can run the system without it to see opportunities, then add staff data later for better analysis.

### Step 5: Run It! (30 seconds)
```bash
# Test SAM.gov connection
python main_integrated.py --test

# Full analysis with competitive intelligence
python main_integrated.py
```

## What You'll Get

After running, check these files:

```
data/reports/action_report_TIMESTAMP.txt
└── Your prioritized opportunities with competitive intelligence

data/reports/competitive_intel_summary_TIMESTAMP.txt
└── Summary of competitive intelligence gathered

data/analysis/*.json
└── Detailed analysis for each opportunity
```

## Manual Configuration (Alternative)

If you prefer to edit `config.yaml` manually instead of using the wizard:

### Minimum Required Configuration

```yaml
# SAM.gov API (REQUIRED)
sam_gov:
  api_key: "YOUR_SAM_GOV_API_KEY_HERE"
  search:
    opportunity_types:
      - "Solicitation"
      - "Presolicitation"
    value_range:
      min: 50000
      max: 10000000
    lookback_days: 7
    keywords:
      - "IT services"
      - "cybersecurity"
      # Add your keywords

# Anthropic API (REQUIRED)
claude:
  api_key: "YOUR_ANTHROPIC_API_KEY_HERE"
  model: "claude-sonnet-4-20250514"
  max_tokens: 4000

# Company Info (REQUIRED: NAICS and set-asides only)
company:
  name: "My Company"  # Optional - used in reports only
  naics_codes:
    - "541512"  # Add your NAICS codes
    - "541519"
  set_asides:
    - "small_business"  # Your status

# Staff Database (OPTIONAL initially)
staff:
  database_path: "data/staff_database.json"

# Notifications (OPTIONAL - can leave disabled)
notifications:
  email:
    enabled: false  # Leave false to skip
  slack:
    enabled: false  # Leave false to skip
```

## What's Optional vs Required

### ✅ REQUIRED
- SAM.gov API key
- Anthropic API key
- At least one NAICS code
- At least one set-aside category

### ❌ OPTIONAL
- Company name (just for reports)
- UEI number (not needed)
- CAGE code (not needed)
- Email notifications
- Slack notifications
- Staff database (can add later)
- Contract vehicles

## After First Run

1. **Review the action report:**
   ```
   data/reports/action_report_*.txt
   ```
   This shows your prioritized opportunities.

2. **Check competitive intelligence:**
   ```
   data/reports/competitive_intel_summary_*.txt
   ```
   This shows market intelligence gathered.

3. **Add staff data** (if you haven't):
   - Copy `staff_database_template.json` to `data/staff_database.json`
   - Fill in your team's skills and experience
   - Re-run for better capability matching

4. **Refine configuration:**
   - Adjust keywords in `config.yaml`
   - Tune value ranges
   - Add more NAICS codes if needed

## Troubleshooting

### "No opportunities found"
- Check your NAICS codes are correct
- Broaden your keywords
- Increase lookback_days in config
- Verify SAM.gov API key is valid

### "API Error" from SAM.gov
- Check your API key in config.yaml
- Verify internet connection
- Wait 10 minutes and try again (rate limits)

### "API Error" from Claude
- Check your Anthropic API key
- Verify you have credits/payment method
- Check model name: "claude-sonnet-4-20250514"

### Python errors
```bash
# Make sure virtual environment is activated
source fed_contracting_env/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

## Common Questions

**Q: Do I need a company name?**  
A: No! It's only used in reports for reference. You can use "My Company" or anything.

**Q: Do I need UEI or CAGE code?**  
A: No! These are not used by the system.

**Q: Do I need email configured?**  
A: No! Email notifications are completely optional. The system saves reports to files regardless.

**Q: Can I run without staff database?**  
A: Yes! The system will still find and analyze opportunities. Staff database is only for capability matching.

**Q: How much does this cost?**  
A: 
- SAM.gov API: FREE
- FPDS API: FREE  
- USAspending API: FREE
- Claude API: ~$100-150/month
- **Total: $100-150/month**

**Q: What if I want notifications later?**  
A: Just edit `config.yaml` and set `notifications.email.enabled: true`, then add your email settings.

## Next Steps

1. ✅ Run system daily for a week
2. ✅ Review outputs and refine keywords
3. ✅ Add staff database for better matching
4. ✅ Set up automation (scheduler or cron)
5. ✅ Configure notifications (if desired)

## Getting Help

- **Setup issues:** Check this guide
- **Configuration:** See config.yaml comments
- **Errors:** Check `logs/fed_contracting_ai.log`
- **Questions:** Review START_FRESH_GUIDE.md

---

**Ready to start?**

```bash
python setup_wizard.py
```

Then:

```bash
python main_integrated.py
```

**That's it!** No company registration details needed. No email setup required. Just API keys and your NAICS codes, and you're running! 🚀
