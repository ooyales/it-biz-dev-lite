# 🚀 Quick Reference - Port 8080

## Access URLs

```
Main Dashboard:     http://localhost:8080
Admin Panel:        http://localhost:8080/admin

Team Access:        http://YOUR_IP:8080
                    http://192.168.1.XXX:8080
```

## Start & Stop

**Start Everything:**
```bash
./start_team_system.sh
```

**Stop Everything:**
```bash
pkill -f team_dashboard_app.py
pkill -f automated_daily_scout.py
```

**Start Dashboard Only:**
```bash
python team_dashboard_app.py
```

**Start Scout Only:**
```bash
python automated_daily_scout.py
```

## Check Status

**Is dashboard running?**
```bash
netstat -an | grep 8080
# Should show: 0.0.0.0:8080
```

**Test API:**
```bash
curl http://localhost:8080/api/dashboard/stats
```

**View logs:**
```bash
tail -f logs/fed_contracting_ai.log
```

## Common Commands

**Fix Jinja2 error:**
```bash
./fix_jinja2_error.sh
```

**Run scout manually:**
```bash
python main_integrated.py
```

**Update configuration:**
```
1. Go to http://localhost:8080/admin
2. Make changes
3. Click "Save All Changes"
```

**Add staff member:**
```
1. Go to http://localhost:8080/admin
2. Click "Staff Management" tab
3. Click "+ Add Staff Member"
4. Fill in details
5. Click "Save Changes"
```

## Port Already in Use?

**Kill process on port 8080:**
```bash
lsof -i :8080
kill -9 $(lsof -t -i:8080)
```

**Use different port:**

Edit `team_dashboard_app.py`, change:
```python
app.run(debug=True, host='0.0.0.0', port=8081)
```

Then access at: `http://localhost:8081`

## Team Access

**Find your IP:**
```bash
# Mac/Linux
ifconfig | grep "inet "

# Windows
ipconfig
```

**Share with team:**
```
http://192.168.1.XXX:8080
```

Replace XXX with your actual IP address.

## Troubleshooting

**Dashboard won't start:**
```bash
# Check virtual environment
source fed_contracting_env/bin/activate

# Check dependencies
pip install -r requirements.txt

# Check port
lsof -i :8080
```

**Can't access from other computers:**
```bash
# Check firewall
sudo ufw allow 8080/tcp  # Linux
# Or: System Preferences → Firewall  # Mac
```

**Configuration not saving:**
```bash
# Check file permissions
ls -la config.yaml data/staff_database.json

# Verify admin panel access
curl http://localhost:8080/api/config
```

## Daily Workflow

**Morning (7 AM - Automated):**
- Scout runs automatically
- Searches SAM.gov
- Updates dashboard

**Team Review (9 AM):**
1. Open http://localhost:8080
2. Click "Refresh"
3. Review opportunities
4. Make pursue/watch/pass decisions

**Admin Tasks (As needed):**
1. Open http://localhost:8080/admin
2. Update staff availability
3. Refine search parameters
4. Add new keywords

## Quick Stats

**Current Configuration:**
- Port: **8080** (changed from 5000)
- Dashboard: Flask 3.0
- Database: SQLite
- API: RESTful
- Multi-user: Yes

**System Requirements:**
- Python 3.9+
- Flask 3.0+
- SAM.gov API key (free)
- Anthropic API key (~$100/month)

## Emergency Commands

**Complete restart:**
```bash
pkill -f team_dashboard_app.py
pkill -f automated_daily_scout.py
./start_team_system.sh
```

**Reset database:**
```bash
rm data/team_dashboard.db
python team_dashboard_app.py
```

**Fresh start:**
```bash
rm -rf fed_contracting_env
python3 -m venv fed_contracting_env
source fed_contracting_env/bin/activate
pip install -r requirements.txt
./fix_jinja2_error.sh
./start_team_system.sh
```

---

## Need Help?

See **TROUBLESHOOTING.md** for detailed solutions.

**Most common issues:**
1. Virtual environment not activated
2. Wrong port (should be 8080)
3. Jinja2 version error (run fix script)
4. Firewall blocking port 8080

**Quick health check:**
```bash
source fed_contracting_env/bin/activate
python -c "import flask, jinja2; print('✓ OK')"
netstat -an | grep 8080
curl http://localhost:8080/api/dashboard/stats
```

All good? Access dashboard at: **http://localhost:8080** 🎯
