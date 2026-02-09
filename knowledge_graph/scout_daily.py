#!/usr/bin/env python3
"""
Daily Opportunity Scout Scheduler
Runs the scout daily and emails/saves reports

Setup as cron job:
    0 8 * * * cd /path/to/knowledge_graph && python scout_daily.py
    (Runs every day at 8 AM)
"""

import sys
sys.path.append('..')

from opportunity_scout import OpportunityScout
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def send_email_report(report: str, recipient: str):
    """Send report via email (optional)"""
    
    sender = os.getenv('SMTP_FROM_EMAIL')
    smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    smtp_port = int(os.getenv('SMTP_PORT', '587'))
    smtp_password = os.getenv('SMTP_PASSWORD')
    
    if not sender or not smtp_password:
        print("⚠️  Email credentials not configured, skipping email")
        return False
    
    try:
        msg = MIMEMultipart()
        msg['From'] = sender
        msg['To'] = recipient
        msg['Subject'] = f"Daily Opportunity Scout Report - {datetime.now().strftime('%Y-%m-%d')}"
        
        msg.attach(MIMEText(report, 'plain'))
        
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender, smtp_password)
        server.send_message(msg)
        server.quit()
        
        print(f"✓ Report emailed to {recipient}")
        return True
        
    except Exception as e:
        print(f"✗ Email failed: {e}")
        return False


def run_daily_scout():
    """Run the daily scout operation"""
    
    print("\n" + "="*70)
    print(f"DAILY OPPORTUNITY SCOUT - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("="*70 + "\n")
    
    try:
        # Run scout
        scout = OpportunityScout()
        report = scout.run_daily_scout(days_back=1)  # Just today's opportunities
        scout.close()
        
        # Optional: Send email
        recipient = os.getenv('REPORT_EMAIL')
        if recipient and report:
            send_email_report(report, recipient)
        
        print("\n✓ Daily scout completed successfully")
        print(f"  Report saved in current directory")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Daily scout failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_daily_scout()
    sys.exit(0 if success else 1)
