#!/bin/bash
"""
Setup Daily Bulk Fetch
Configures cron job to run bulk fetch every morning at 9 AM
"""

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PYTHON_PATH=$(which python3)

echo "Setting up daily bulk fetch cron job..."
echo ""
echo "Script directory: $SCRIPT_DIR"
echo "Python path: $PYTHON_PATH"
echo ""

# Create cron job
CRON_JOB="0 9 * * * cd $SCRIPT_DIR && $PYTHON_PATH bulk_fetch_and_filter.py >> logs/bulk_fetch.log 2>&1"

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "bulk_fetch_and_filter.py"; then
    echo "⚠️  Cron job already exists!"
    echo ""
    echo "Current cron jobs:"
    crontab -l | grep bulk_fetch
    echo ""
    read -p "Do you want to replace it? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Cancelled."
        exit 0
    fi
    
    # Remove old job
    crontab -l | grep -v "bulk_fetch_and_filter.py" | crontab -
fi

# Add new job
(crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -

echo "✓ Cron job added successfully!"
echo ""
echo "Schedule: Every day at 7:00 AM"
echo "Command: $CRON_JOB"
echo ""
echo "Verify with: crontab -l"
echo "View logs: tail -f logs/bulk_fetch.log"
echo ""
echo "To run manually now: python bulk_fetch_and_filter.py"
echo ""
