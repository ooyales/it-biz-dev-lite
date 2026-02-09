#!/usr/bin/env python3
"""
Automated Daily Scout - Team Collaboration Version
Runs scout daily and updates team dashboard automatically
"""

import schedule
import time
import subprocess
import logging
from datetime import datetime
from pathlib import Path
import requests


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/automated_scout.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def run_morning_scout():
    """Run the morning opportunity scout"""
    logger.info("="*80)
    logger.info("MORNING SCOUT STARTED")
    logger.info("="*80)
    
    try:
        # Run the main integrated script
        logger.info("Executing main_integrated.py...")
        result = subprocess.run(
            ['python', 'main_integrated.py'],
            capture_output=True,
            text=True,
            timeout=1800  # 30 minute timeout
        )
        
        if result.returncode == 0:
            logger.info("✓ Scout completed successfully!")
            logger.info(f"Output: {result.stdout[-500:]}")  # Last 500 chars
            
            # Notify team dashboard
            notify_dashboard_update()
            
            # Optional: Send team notification
            send_team_notification("Morning scout completed. New opportunities available!")
            
        else:
            logger.error(f"✗ Scout failed with return code {result.returncode}")
            logger.error(f"Error: {result.stderr}")
            
            send_team_notification("⚠️ Morning scout encountered errors. Check logs.", error=True)
    
    except subprocess.TimeoutExpired:
        logger.error("✗ Scout timed out after 30 minutes")
        send_team_notification("⚠️ Morning scout timed out.", error=True)
    
    except Exception as e:
        logger.error(f"✗ Unexpected error: {e}", exc_info=True)
        send_team_notification(f"⚠️ Morning scout error: {str(e)}", error=True)
    
    logger.info("Morning scout finished")


def notify_dashboard_update():
    """Notify the team dashboard of new data"""
    try:
        # Dashboard webhook (if running)
        response = requests.post(
            'http://localhost:5000/api/system/refresh',
            timeout=5
        )
        logger.info("Dashboard notified of update")
    except requests.exceptions.ConnectionError:
        logger.debug("Dashboard not running - skipping notification")
    except Exception as e:
        logger.warning(f"Could not notify dashboard: {e}")


def send_team_notification(message: str, error: bool = False):
    """Send notification to team via configured channels"""
    # This would integrate with your notification system
    # For now, just log it
    if error:
        logger.warning(f"TEAM NOTIFICATION: {message}")
    else:
        logger.info(f"TEAM NOTIFICATION: {message}")
    
    # TODO: Integrate with Slack/Email from config
    # Example:
    # if config['notifications']['slack']['enabled']:
    #     send_slack_message(message)


def health_check():
    """Periodic health check"""
    logger.info("Running health check...")
    
    checks = {
        'config_exists': Path('config.yaml').exists(),
        'staff_db_exists': Path('data/staff_database.json').exists(),
        'logs_writable': Path('logs').exists(),
        'data_dirs_exist': all([
            Path('data/opportunities').exists(),
            Path('data/analysis').exists(),
            Path('data/reports').exists()
        ])
    }
    
    all_healthy = all(checks.values())
    
    if all_healthy:
        logger.info("✓ System healthy")
    else:
        logger.warning(f"⚠️ Health check issues: {checks}")
    
    return all_healthy


def cleanup_old_cache():
    """Clean up old cache files"""
    logger.info("Running cache cleanup...")
    
    try:
        from sam_scout import SAMOpportunityScoutRateLimited
        
        scout = SAMOpportunityScoutRateLimited()
        scout.clear_cache(older_than_hours=48)  # Clear cache older than 2 days
        
        logger.info("✓ Cache cleanup completed")
    except Exception as e:
        logger.warning(f"Cache cleanup failed: {e}")


def main():
    """Main scheduler loop"""
    logger.info("="*80)
    logger.info("AUTOMATED DAILY SCOUT - TEAM COLLABORATION")
    logger.info("="*80)
    
    # Schedule jobs
    
    # Morning scout (7 AM daily)
    schedule.every().day.at("07:00").do(run_morning_scout)
    logger.info("✓ Scheduled: Morning scout at 7:00 AM daily")
    
    # Optional: Evening update (5 PM daily)
    # schedule.every().day.at("17:00").do(run_evening_update)
    # logger.info("✓ Scheduled: Evening update at 5:00 PM daily")
    
    # Health check (every 6 hours)
    schedule.every(6).hours.do(health_check)
    logger.info("✓ Scheduled: Health check every 6 hours")
    
    # Cache cleanup (daily at midnight)
    schedule.every().day.at("00:00").do(cleanup_old_cache)
    logger.info("✓ Scheduled: Cache cleanup at midnight")
    
    logger.info("\nScheduler is running. Press Ctrl+C to stop.")
    logger.info("Next run: " + str(schedule.next_run()))
    
    # Optional: Run immediately on startup
    if input("\nRun scout immediately on startup? (y/n): ").lower() == 'y':
        run_morning_scout()
    
    # Main loop
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    
    except KeyboardInterrupt:
        logger.info("\n\nScheduler stopped by user")
    
    except Exception as e:
        logger.error(f"Scheduler crashed: {e}", exc_info=True)


if __name__ == "__main__":
    main()
