# Team Collaboration Dashboard - Setup Guide

## Overview

This system provides a **web-based team dashboard** for collaborative opportunity management with:

1. ✅ **Automated Morning Scout** - Runs at 7 AM daily
2. ✅ **Team Dashboard** - Web interface for your team
3. ✅ **Collaborative Decision Making** - Team can review and decide together
4. ✅ **Staff Database Management** - Update capabilities through UI
5. ✅ **Visual Timeline** - See contract expirations to "shift left"
6. ✅ **Market Intelligence Visualization** - Charts and trends

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Automated Scout (7 AM Daily)                           │
│  • Searches SAM.gov                                      │
│  • Runs competitive intelligence                        │
│  • Analyzes with AI                                      │
│  • Updates team database                                 │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│  Team Dashboard (localhost:5000)                        │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Timeline View                                   │    │
│  │  • Contract expirations on time axis            │    │
│  │  • Opportunity bubbles by deadline              │    │
│  │  • "Shift left" to build early relationships   │    │
│  └─────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Opportunities Grid                              │    │
│  │  • Fit scores and win probabilities            │    │
│  │  • Competitive intelligence                     │    │
│  │  • Team actions: Pursue / Watch / Pass         │    │
│  └─────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Staff Management (Coming Soon)                 │    │
│  │  • Update skills and certifications            │    │
│  │  • Track availability                           │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

## Installation

### Step 1: Install Additional Dependencies

```bash
# Activate your virtual environment
source fed_contracting_env/bin/activate

# Install Flask and dependencies
pip install flask flask-cors schedule

# Or update requirements
echo "flask>=3.0.0" >> requirements.txt
echo "flask-cors>=4.0.0" >> requirements.txt
echo "schedule>=1.2.0" >> requirements.txt
pip install -r requirements.txt
```

### Step 2: Create Directories

```bash
# Create template directory
mkdir -p templates

# Create static directory (for future CSS/JS)
mkdir -p static

# Ensure data directories exist
mkdir -p data/cache
```

### Step 3: Place Files

Place the following files in your project directory:

- `team_dashboard_app.py` - Flask backend
- `templates/dashboard.html` - Web interface
- `automated_daily_scout.py` - Automated scheduler

## Running the System

### Option 1: Start Everything Together (Recommended)

Create a start script `start_team_system.sh`:

```bash
#!/bin/bash

# Start the team dashboard (background)
echo "Starting team dashboard..."
python team_dashboard_app.py &
DASHBOARD_PID=$!

# Wait for dashboard to start
sleep 3

# Start the automated scout
echo "Starting automated scout..."
python automated_daily_scout.py &
SCOUT_PID=$!

echo ""
echo "="
echo "Team Collaboration System Started!"
echo "="
echo ""
echo "Dashboard: http://localhost:5000"
echo "Scout: Running in background"
echo ""
echo "To stop: kill $DASHBOARD_PID $SCOUT_PID"
echo ""

# Wait for user interrupt
wait
```

Make it executable:
```bash
chmod +x start_team_system.sh
./start_team_system.sh
```

### Option 2: Start Components Separately

**Terminal 1 - Team Dashboard:**
```bash
python team_dashboard_app.py
```

**Terminal 2 - Automated Scout:**
```bash
python automated_daily_scout.py
```

## Using the Team Dashboard

### Access the Dashboard

Open your web browser:
```
http://localhost:5000
```

Or from another computer on your network:
```
http://[YOUR_IP]:5000
```

### Dashboard Features

#### 1. **Stats Overview** (Top Cards)
- **Total Opportunities** - All opportunities found
- **High Priority** - Opportunities with fit score ≥ 7
- **Active Pursuits** - Opportunities your team is pursuing
- **Upcoming Deadlines** - Deadlines in next 7 days

#### 2. **Timeline View** (Contract Expirations)
- **X-axis**: Time from now to 1 year out
- **Bubbles**: Opportunities positioned by deadline
- **Bubble size/color**: Indicates fit score and priority
- **"Shift Left" Strategy**: See opportunities 6-12 months out to build agency relationships early

**How to use:**
- Click bubbles to see details
- Identify contracts expiring 6+ months out
- Start building relationships NOW before RFP

#### 3. **Opportunities Grid**
Each card shows:
- **Fit Score** - AI assessment (0-10)
- **Win Probability** - Based on competitive intel
- **Competitive Intel** - Incumbent, pricing, market trends
- **Actions**: Pursue / Watch / Pass

**Team Workflow:**
1. Review opportunities together
2. Click "Pursue" for go-decisions
3. Click "Watch" to monitor
4. Click "Pass" to decline
5. Decisions are tracked and logged

#### 4. **Tabs**
- **All Opportunities** - Everything found
- **High Priority** - Pre-filtered to score ≥ 7
- **Pursuing** - Opportunities you've marked
- **Watch List** - Opportunities you're monitoring

### Team Collaboration Workflow

**Morning Routine:**

1. **7:00 AM** - Scout runs automatically
   - Searches SAM.gov
   - Analyzes opportunities
   - Updates dashboard

2. **9:00 AM** - Team huddle
   - Open dashboard: http://localhost:5000
   - Click "Refresh" to see new opportunities
   - Review high-priority tab together

3. **Decision Making:**
   ```
   For each high-priority opportunity:
   
   → Review fit score and win probability
   → Check competitive intelligence
   → Discuss as team
   → Click action: Pursue / Watch / Pass
   → Assign to team member if pursuing
   ```

4. **Timeline Review:**
   - Look at timeline view
   - Identify contracts expiring 6-12 months out
   - Assign relationship-building tasks
   - Start agency engagement early

### Managing Your Staff Database

**Update staff through the dashboard** (coming in next version):

For now, edit manually:
```bash
nano data/staff_database.json
```

After editing, restart dashboard:
```bash
# Kill dashboard process
pkill -f team_dashboard_app.py

# Restart
python team_dashboard_app.py
```

### Running Scout Manually

From dashboard:
- Click "Run Scout" button in header
- Confirms before running
- Runs in background
- Dashboard auto-refreshes when complete

Or via command line:
```bash
python main_integrated.py
```

## Automated Schedule

The `automated_daily_scout.py` script runs:

| Time | Task | Purpose |
|------|------|---------|
| **7:00 AM** | Morning scout | Fresh opportunities daily |
| **Every 6 hours** | Health check | System monitoring |
| **Midnight** | Cache cleanup | Remove old cache files |

### Customize Schedule

Edit `automated_daily_scout.py`:

```python
# Morning scout - change time
schedule.every().day.at("07:00").do(run_morning_scout)

# Add evening update
schedule.every().day.at("17:00").do(run_evening_update)

# Weekend only
schedule.every().saturday.at("09:00").do(run_weekend_scout)
```

## Multi-User Access

### On Same Network

1. **Find your IP address:**
   ```bash
   # Linux/Mac
   ifconfig | grep "inet "
   
   # Windows
   ipconfig
   ```

2. **Access from other computers:**
   ```
   http://192.168.1.XXX:5000
   ```

3. **Team members can:**
   - View same dashboard
   - Make decisions simultaneously
   - See real-time updates (with refresh)

### Security Considerations

**For internal team use:**
- ✅ Run on your network only
- ✅ Use VPN for remote access
- ✅ Don't expose to internet without authentication

**For production deployment:**
- Add user authentication
- Use HTTPS
- Deploy on secure server
- Implement role-based access

## Production Deployment (Optional)

### Deploy to a Server

**Using a cloud instance (AWS, DigitalOcean, etc.):**

```bash
# 1. Install system dependencies
sudo apt update
sudo apt install python3-pip nginx

# 2. Clone/copy your system files

# 3. Install Python packages
pip3 install -r requirements.txt

# 4. Run with gunicorn (production WSGI server)
pip3 install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 team_dashboard_app:app

# 5. Configure nginx as reverse proxy
# See nginx configuration below
```

**Nginx config** (`/etc/nginx/sites-available/fedcon`):
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Run as System Service

Create `/etc/systemd/system/fedcon-dashboard.service`:

```ini
[Unit]
Description=Federal Contracting Team Dashboard
After=network.target

[Service]
User=yourusername
WorkingDirectory=/path/to/fed-contracting-ai
ExecStart=/path/to/fed_contracting_env/bin/python team_dashboard_app.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable fedcon-dashboard
sudo systemctl start fedcon-dashboard
```

## Troubleshooting

### Dashboard won't start

```bash
# Check if port 5000 is already in use
lsof -i :5000

# Kill process on port 5000
kill -9 $(lsof -t -i:5000)

# Try different port
# Edit team_dashboard_app.py, change:
app.run(debug=True, host='0.0.0.0', port=5001)
```

### Scout fails to run

```bash
# Check logs
tail -f logs/automated_scout.log

# Test manually
python main_integrated.py --test
```

### Database errors

```bash
# Reset database
rm data/team_dashboard.db

# Restart dashboard (will recreate)
python team_dashboard_app.py
```

### Can't access from other computers

```bash
# Check firewall
sudo ufw allow 5000/tcp

# On Mac
# System Preferences → Security → Firewall → Add Flask

# Verify dashboard is listening on all interfaces
netstat -an | grep 5000
# Should show 0.0.0.0:5000 not 127.0.0.1:5000
```

## Advanced Features

### Email Notifications

Edit `automated_daily_scout.py`:

```python
def send_team_notification(message: str, error: bool = False):
    # Add email integration
    import smtplib
    from email.mime.text import MIMEText
    
    msg = MIMEText(message)
    msg['Subject'] = 'FedCon Scout Update'
    msg['From'] = 'scout@yourcompany.com'
    msg['To'] = 'team@yourcompany.com'
    
    # Send email...
```

### Slack Integration

```python
def send_team_notification(message: str, error: bool = False):
    import requests
    
    webhook_url = 'YOUR_SLACK_WEBHOOK'
    requests.post(webhook_url, json={'text': message})
```

### Custom Reports

Add to dashboard API:

```python
@app.route('/api/reports/weekly')
def generate_weekly_report():
    # Custom report logic
    pass
```

## Tips for Team Adoption

### Week 1: Training
- Show team the dashboard
- Walk through workflow
- Practice making decisions
- Explain timeline "shift left" strategy

### Week 2: Daily Use
- Team reviews dashboard daily
- Makes pursue/watch/pass decisions
- Tracks results

### Week 3: Refinement
- Adjust filters based on team feedback
- Refine scoring weights
- Customize views

### Month 2: Advanced
- Track win rates
- Analyze which opportunities convert
- Refine competitive strategy
- Build agency relationships early

## Summary

**What you've built:**
- ✅ Automated daily scout (runs at 7 AM)
- ✅ Beautiful team dashboard
- ✅ Contract expiration timeline
- ✅ Collaborative decision-making
- ✅ Market intelligence visualization

**Daily workflow:**
1. Scout runs automatically at 7 AM
2. Team reviews dashboard at 9 AM
3. Make pursue/watch/pass decisions together
4. Track opportunities through pipeline
5. Use timeline to "shift left" on relationships

**Access:**
```
http://localhost:5000
```

**Start system:**
```bash
./start_team_system.sh
```

Your team now has a professional opportunity management system! 🎯
