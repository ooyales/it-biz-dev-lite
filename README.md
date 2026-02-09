# Federal Contracting AI Assistant

An intelligent automation system for small businesses pursuing federal contracts. This system monitors SAM.gov, analyzes opportunities, matches staff capabilities, and generates RFI responses using Claude AI.

## 🎯 What It Does

- **Automated SAM.gov Monitoring**: Searches for relevant opportunities based on your NAICS codes, set-asides, and keywords
- **AI-Powered Analysis**: Scores each opportunity (0-10) for fit with your business
- **Capability Matching**: Maps your staff's skills against opportunity requirements
- **Gap Analysis**: Identifies missing capabilities and suggests mitigation strategies
- **RFI Generation**: Auto-drafts professional RFI responses for high-priority opportunities
- **Prioritized Reports**: Generates actionable reports sorted by priority
- **Notifications**: Sends email/Slack alerts for high-value opportunities

## 💡 Perfect For

Small federal contracting businesses that:
- Have 10-50 employees
- Lack dedicated BD/capture staff
- Compete in multiple NAICS codes
- Need to respond to 10+ opportunities per month
- Want to scale without adding headcount

## 🚀 Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure the system
# Edit config.yaml with your API keys and company info
# Fill out data/staff_database.json with your team

# 3. Run first search
python main.py --test

# 4. Run full analysis
python main.py
```

See [SETUP_GUIDE.md](SETUP_GUIDE.md) for detailed installation instructions.

## 📊 System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     SAM.gov Monitor                          │
│  • Searches daily/twice-daily                                │
│  • Filters by NAICS, set-asides, keywords, value            │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│              Opportunity Analyzer (Claude AI)                │
│  • Scores fit (0-10)                                         │
│  • Identifies strengths and concerns                         │
│  • Recommends: PURSUE / MONITOR / PASS                       │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│             Capability Matcher (Claude AI)                   │
│  • Maps staff skills to requirements                         │
│  • Calculates coverage percentage                            │
│  • Suggests team composition                                 │
│  • Identifies gaps and mitigation                            │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│               RFI Responder (Claude AI)                      │
│  • Drafts professional RFI responses                         │
│  • Includes relevant past performance                        │
│  • Positions for future solicitation                         │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│                  Prioritized Reports                         │
│  • Action report with next steps                             │
│  • Email/Slack notifications                                 │
│  • Detailed analysis files                                   │
└─────────────────────────────────────────────────────────────┘
```

## 📁 Project Structure

```
fed-contracting-ai/
├── config.yaml                      # Main configuration
├── staff_database_template.json    # Template for staff data
├── requirements.txt                 # Python dependencies
├── SETUP_GUIDE.md                  # Detailed setup instructions
├── README.md                        # This file
│
├── main.py                          # Main orchestration script
├── sam_scout.py                     # SAM.gov monitoring
├── claude_agents.py                 # AI agent definitions
│
├── data/
│   ├── staff_database.json         # Your staff capabilities
│   ├── opportunities/              # Raw SAM.gov data
│   ├── analysis/                   # AI analysis results
│   ├── proposals/                  # Proposal drafts (future)
│   └── reports/                    # Action reports
│
└── logs/
    └── fed_contracting_ai.log      # System logs
```

## 🔑 Key Features

### Intelligent Filtering
- NAICS code matching
- Set-aside category filtering
- Contract value range filtering
- Keyword-based relevance filtering

### Multi-Agent AI System
- **Opportunity Scout**: Monitors and pre-filters opportunities
- **Opportunity Analyzer**: Deep analysis with scoring and recommendations
- **Capability Matcher**: Maps staff to requirements, identifies gaps
- **RFI Responder**: Generates professional responses

### Automated Workflow
- Scheduled searches (cron/Task Scheduler)
- Parallel opportunity processing
- Automatic report generation
- Email and Slack notifications

### Business Intelligence
- Incumbent tracking (planned)
- Competitive analysis (planned)
- Win probability scoring
- Past performance matching

## 💰 Cost Estimate

### One-Time Setup
- Free (just your time)

### Monthly Operating Costs
- **SAM.gov API**: Free
- **Claude API**: $90-150/month (analyzing 50 opps/day)
- **Total**: ~$100-150/month

**ROI**: If this system helps you win even one $100K contract, it pays for itself for years.

## 🛠️ Configuration

### Minimum Required
1. SAM.gov API key (free from https://open.gsa.gov)
2. Anthropic API key (from https://console.anthropic.com)
3. Your company NAICS codes
4. Staff database with skills and clearances

### Optional but Recommended
- Email/Slack notifications
- Automated scheduling
- Custom keywords for your domain
- Scoring weight adjustments

## 📈 Typical Results

After initial setup, you can expect:

- **50-100 opportunities/week** discovered
- **5-10 high-priority opportunities/week** (score ≥ 7)
- **2-3 RFI drafts/week** auto-generated
- **Time saved**: 15-20 hours/week on opportunity research and qualification

## 🔒 Security & Privacy

- All data stored locally
- API keys protected in config files
- Staff data never sent to SAM.gov
- Claude AI processes anonymized opportunity data
- No data retention by Anthropic (per API policy)

## 🎓 Use Cases

### Scenario 1: Daily Monitoring
Run the system every morning to get a prioritized list of new opportunities:
```bash
0 6 * * * python main.py
```

### Scenario 2: Twice-Daily Check
Monitor high-activity periods:
```bash
0 9,17 * * * python main.py
```

### Scenario 3: Weekly Deep Dive
Run comprehensive analysis weekly:
```bash
python main.py --days 14
```

## 🚧 Roadmap

- [x] SAM.gov integration
- [x] Multi-agent AI analysis
- [x] Capability matching
- [x] RFI generation
- [ ] Full proposal generation
- [ ] Competitive intelligence module
- [ ] Web dashboard
- [ ] CRM integration
- [ ] Past performance database
- [ ] Teaming partner recommendations
- [ ] Price-to-win analysis
- [ ] Automated bid/no-bid decisions

## 🤝 Contributing

This is a starting point for your custom federal contracting solution. Feel free to:
- Customize the AI prompts for your business
- Add new agent types
- Integrate with your existing tools
- Build additional features

## 📚 Resources

- [Detailed Setup Guide](SETUP_GUIDE.md)
- [SAM.gov API Docs](https://open.gsa.gov/api/)
- [Claude API Docs](https://docs.anthropic.com/)
- [Federal Contracting Guide](https://www.sba.gov/federal-contracting/)

## ⚖️ License

This project is provided as-is for commercial use by federal contractors.

## ⚠️ Disclaimer

This system assists with opportunity identification and analysis but does not replace human judgment. All opportunities should be reviewed by qualified personnel before pursuing. Past performance and capability claims should be verified before inclusion in proposals or RFI responses.

---

**Ready to get started?** See [SETUP_GUIDE.md](SETUP_GUIDE.md) for step-by-step installation instructions.

**Questions?** Check the troubleshooting section in the setup guide or review the logs in `logs/fed_contracting_ai.log`.
