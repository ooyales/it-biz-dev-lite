#!/bin/bash
# Quick Fix for Jinja2 Import Error

echo "=========================================="
echo "Fixing Jinja2 Import Error"
echo "=========================================="
echo ""

# Check if virtual environment is activated
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "⚠️  Virtual environment not activated!"
    echo ""
    echo "Please activate your virtual environment first:"
    echo "  source fed_contracting_env/bin/activate"
    echo ""
    exit 1
fi

echo "Upgrading Flask and Jinja2 to compatible versions..."
echo ""

# Uninstall problematic versions
pip uninstall -y flask jinja2 werkzeug markupsafe flask-cors

# Install correct versions
pip install flask==3.0.0
pip install jinja2==3.1.2
pip install markupsafe==2.1.3
pip install werkzeug==3.0.1
pip install flask-cors==4.0.0

echo ""
echo "=========================================="
echo "✓ Fix complete!"
echo "=========================================="
echo ""
echo "Now you can run:"
echo "  ./start_team_system.sh"
echo ""
