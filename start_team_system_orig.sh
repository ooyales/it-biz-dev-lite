#!/bin/bash
# Start Federal Contracting Team Collaboration System

echo "=========================================="
echo "Federal Contracting Team System"
echo "=========================================="
echo ""

# Check if Flask is installed
if ! python -c "import flask" 2>/dev/null; then
    echo "⚠️  Flask not installed!"
    echo "Installing required packages..."
    pip install flask flask-cors schedule
    echo ""
fi

# Create necessary directories
mkdir -p templates static data logs

echo "Starting Team Dashboard..."
python team_dashboard_app.py &
DASHBOARD_PID=$!

echo "Waiting for dashboard to start..."
sleep 5

echo ""
echo "✓ Team Dashboard started!"
echo "  URL: http://localhost:5000"
echo "  PID: $DASHBOARD_PID"
echo ""

# Ask if user wants to start automated scout
read -p "Start automated daily scout? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Starting Automated Scout..."
    python automated_daily_scout.py &
    SCOUT_PID=$!
    echo "✓ Automated Scout started!"
    echo "  PID: $SCOUT_PID"
fi

echo ""
echo "=========================================="
echo "System is running!"
echo "=========================================="
echo ""
echo "Dashboard: http://localhost:5000"
echo ""
echo "To stop the system:"
echo "  kill $DASHBOARD_PID"
if [ ! -z "$SCOUT_PID" ]; then
    echo "  kill $SCOUT_PID"
fi
echo ""
echo "Or press Ctrl+C and run:"
echo "  pkill -f team_dashboard_app.py"
echo "  pkill -f automated_daily_scout.py"
echo ""

# Keep script running
echo "Press Ctrl+C to stop..."
wait
