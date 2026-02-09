# Troubleshooting Guide - Team Dashboard

## Common Errors and Solutions

### Error: "ImportError: cannot import name 'escape' from 'jinja2'"

**Cause:** Flask/Jinja2 version incompatibility

**Solution 1: Quick Fix Script (Recommended)**

```bash
# Make sure virtual environment is activated
source fed_contracting_env/bin/activate

# Run the fix script
chmod +x fix_jinja2_error.sh
./fix_jinja2_error.sh

# Then start the system
./start_team_system.sh
```

**Solution 2: Manual Fix**

```bash
# Activate virtual environment
source fed_contracting_env/bin/activate  # Mac/Linux
# OR
fed_contracting_env\Scripts\activate  # Windows

# Uninstall old versions
pip uninstall -y flask jinja2 werkzeug markupsafe flask-cors

# Install correct versions
pip install flask==3.0.0
pip install jinja2==3.1.2
pip install markupsafe==2.1.3
pip install werkzeug==3.0.1
pip install flask-cors==4.0.0

# Verify installation
python -c "import flask; print(f'Flask: {flask.__version__}')"
python -c "import jinja2; print(f'Jinja2: {jinja2.__version__}')"

# Should show:
# Flask: 3.0.0
# Jinja2: 3.1.2
```

**Solution 3: Fresh Install**

```bash
# Remove virtual environment
rm -rf fed_contracting_env

# Create new one
python3 -m venv fed_contracting_env
source fed_contracting_env/bin/activate

# Install from updated requirements
pip install -r requirements.txt
```

---

### Error: "ModuleNotFoundError: No module named 'flask'"

**Cause:** Flask not installed

**Solution:**

```bash
# Activate virtual environment
source fed_contracting_env/bin/activate

# Install Flask
pip install flask flask-cors

# Or install all requirements
pip install -r requirements.txt
```

---

### Error: "Address already in use" or "Port 8080 is already allocated"

**Cause:** Port 8080 is being used by another application

**Solution 1: Kill Process on Port 8080**

```bash
# Find what's using port 8080
lsof -i :8080

# Kill the process
kill -9 $(lsof -t -i:8080)

# Or on Windows
netstat -ano | findstr :8080
taskkill /PID <PID> /F
```

**Solution 2: Use Different Port**

Edit `team_dashboard_app.py`, change last line:

```python
# From:
app.run(debug=True, host='0.0.0.0', port=8080)

# To:
app.run(debug=True, host='0.0.0.0', port=8081)
```

Then access at: `http://localhost:8081`

---

### Error: "Template not found: dashboard.html"

**Cause:** Templates directory missing or in wrong location

**Solution:**

```bash
# Check directory structure
ls -la templates/

# Should contain:
# - dashboard.html
# - admin.html

# If missing, create directory
mkdir -p templates

# Make sure HTML files are in templates/
mv dashboard.html templates/ 2>/dev/null
mv admin.html templates/ 2>/dev/null
```

---

### Error: "FileNotFoundError: [Errno 2] No such file or directory: 'config.yaml'"

**Cause:** Running from wrong directory

**Solution:**

```bash
# Make sure you're in the project directory
cd /path/to/fed-contracting-ai

# Verify config.yaml exists
ls -la config.yaml

# If missing, run setup wizard
python setup_wizard.py

# Then start system
./start_team_system.sh
```

---

### Error: "sqlite3.OperationalError: unable to open database file"

**Cause:** Data directory missing or no write permissions

**Solution:**

```bash
# Create data directory
mkdir -p data

# Check permissions
ls -la data/

# If permission denied, fix it
chmod 755 data/

# Restart dashboard
pkill -f team_dashboard_app.py
python team_dashboard_app.py
```

---

### Error: "Connection refused" when accessing dashboard

**Cause:** Dashboard not running or firewall blocking

**Solution:**

```bash
# Check if dashboard is running
ps aux | grep team_dashboard_app.py

# If not running, start it
python team_dashboard_app.py

# Check if listening on port
netstat -an | grep 8080

# Should show: 0.0.0.0:8080

# If firewall issue (Mac)
# System Preferences → Security → Firewall → Add Python

# If firewall issue (Linux)
sudo ufw allow 8080/tcp
```

---

### Dashboard loads but shows "No opportunities found"

**Cause:** Scout hasn't run yet or no opportunities match filters

**Solution:**

```bash
# Run scout manually
python main_integrated.py

# Check for errors in output
# Look for opportunities found

# If no opportunities:
# 1. Check SAM.gov API key in config.yaml
# 2. Broaden search filters (more NAICS codes, longer lookback)
# 3. Remove keywords temporarily
# 4. Check SAM.gov quota hasn't been exceeded
```

---

### Admin panel shows blank page or errors

**Cause:** JavaScript not loading or API errors

**Solution:**

```bash
# Check browser console (F12)
# Look for JavaScript errors

# Verify static/admin.js exists
ls -la static/admin.js

# If missing static directory
mkdir -p static

# Make sure admin.js is in static/
mv admin.js static/ 2>/dev/null

# Restart dashboard
pkill -f team_dashboard_app.py
python team_dashboard_app.py

# Hard refresh browser: Ctrl+Shift+R
```

---

### Error: "Failed to load configuration"

**Cause:** config.yaml is malformed or has syntax errors

**Solution:**

```bash
# Validate YAML syntax
python -c "import yaml; yaml.safe_load(open('config.yaml'))"

# If errors shown, fix YAML manually or:

# Backup broken config
cp config.yaml config.yaml.backup

# Run setup wizard to create fresh config
python setup_wizard.py

# Or use admin panel after dashboard starts
```

---

### Staff changes not saving

**Cause:** staff_database.json file issue

**Solution:**

```bash
# Check if file exists
ls -la data/staff_database.json

# If missing, copy template
cp staff_database_template.json data/staff_database.json

# Check file permissions
chmod 644 data/staff_database.json

# Validate JSON
python -c "import json; json.load(open('data/staff_database.json'))"

# If errors, fix JSON or recreate from template
```

---

### Virtual environment issues

**Symptoms:** Packages not found, import errors, wrong Python version

**Solution:**

```bash
# Deactivate current environment
deactivate

# Remove old environment
rm -rf fed_contracting_env

# Create fresh environment with correct Python version
python3.9 -m venv fed_contracting_env  # Use Python 3.9+
# OR
python3.10 -m venv fed_contracting_env

# Activate
source fed_contracting_env/bin/activate

# Verify Python version
python --version  # Should be 3.9 or higher

# Install all dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Verify installations
pip list | grep -E "flask|jinja2|anthropic"
```

---

## Diagnostic Commands

**Check if dashboard is running:**
```bash
ps aux | grep team_dashboard_app.py
netstat -an | grep 8080
```

**Check logs:**
```bash
tail -f logs/fed_contracting_ai.log
tail -f logs/automated_scout.log
```

**Test Python imports:**
```bash
python -c "import flask; import jinja2; import anthropic; print('All imports OK')"
```

**Test API connectivity:**
```bash
curl http://localhost:8080/api/dashboard/stats
```

**Check file structure:**
```bash
tree -L 2
# Should show:
# ├── config.yaml
# ├── data/
# ├── logs/
# ├── templates/
# │   ├── admin.html
# │   └── dashboard.html
# ├── static/
# │   └── admin.js
# └── team_dashboard_app.py
```

---

## Getting More Help

**Check logs:**
```bash
# Main system log
cat logs/fed_contracting_ai.log

# Scout log
cat logs/automated_scout.log

# Look for ERROR or WARNING lines
grep ERROR logs/*.log
```

**Enable debug mode:**

In `team_dashboard_app.py`, last line should be:
```python
app.run(debug=True, host='0.0.0.0', port=5000)
```

Debug mode shows detailed errors in browser.

**Browser developer tools:**
- Press F12
- Check Console tab for JavaScript errors
- Check Network tab for API call failures

---

## Prevention Tips

**Always activate virtual environment:**
```bash
# Before running ANY Python commands
source fed_contracting_env/bin/activate
```

**Keep packages updated:**
```bash
pip install --upgrade pip
pip install -r requirements.txt --upgrade
```

**Regular backups:**
```bash
# Backup important files
cp config.yaml config.yaml.backup
cp data/staff_database.json data/staff_database.json.backup
```

**Use version control:**
```bash
git init
git add config.yaml data/staff_database.json
git commit -m "Backup configuration"
```

---

## Quick Checklist

Before reporting issues, verify:

- [ ] Virtual environment activated
- [ ] All dependencies installed (`pip install -r requirements.txt`)
- [ ] In correct directory (`ls config.yaml` works)
- [ ] Directories exist (`data/`, `logs/`, `templates/`, `static/`)
- [ ] Config file valid (`python -c "import yaml; yaml.safe_load(open('config.yaml'))"`)
- [ ] Port 8080 available (`lsof -i :8080` shows nothing)
- [ ] Python 3.9+ (`python --version`)
- [ ] Flask 3.0+ (`python -c "import flask; print(flask.__version__)"`)

---

## Still Having Issues?

1. **Run the fix script:**
   ```bash
   ./fix_jinja2_error.sh
   ```

2. **Check this troubleshooting guide**

3. **Review logs:**
   ```bash
   tail -100 logs/fed_contracting_ai.log
   ```

4. **Try fresh install:**
   - Remove virtual environment
   - Recreate from scratch
   - Install dependencies
   - Run setup wizard

Most issues are related to virtual environment or package versions. The fix script should resolve 90% of problems! 🔧
