#!/usr/bin/env python3
"""
Automated Scheduler for Federal Contracting AI Assistant

This script runs the main pipeline on a schedule.
Alternative to using cron or Windows Task Scheduler.
"""

import schedule
import time
import logging
from datetime import datetime
from main import FedContractingAI


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def run_pipeline():
    """Execute the full pipeline"""
    logger.info("="*80)
    logger.info(f"Starting scheduled pipeline run at {datetime.now()}")
    logger.info("="*80)
    
    try:
        system = FedContractingAI()
        summary = system.run_full_pipeline()
        
        logger.info(f"Pipeline completed successfully")
        logger.info(f"  Opportunities found: {summary['opportunities_found']}")
        logger.info(f"  High priority: {summary['high_priority']}")
        
    except Exception as e:
        logger.error(f"Pipeline failed with error: {e}", exc_info=True)


def main():
    """Set up schedule and run continuously"""
    
    # Configuration - modify these to match your needs
    
    # Option 1: Run twice daily (9 AM and 5 PM)
    schedule.every().day.at("09:00").do(run_pipeline)
    schedule.every().day.at("17:00").do(run_pipeline)
    
    # Option 2: Run once daily (comment out option 1, uncomment this)
    # schedule.every().day.at("06:00").do(run_pipeline)
    
    # Option 3: Run every N hours (comment out option 1, uncomment this)
    # schedule.every(12).hours.do(run_pipeline)
    
    # Option 4: Run on specific days
    # schedule.every().monday.at("09:00").do(run_pipeline)
    # schedule.every().wednesday.at("09:00").do(run_pipeline)
    # schedule.every().friday.at("09:00").do(run_pipeline)
    
    logger.info("Scheduler started. Configured schedule:")
    for job in schedule.jobs:
        logger.info(f"  {job}")
    
    # Optional: Run immediately on startup
    # logger.info("Running initial pipeline on startup...")
    # run_pipeline()
    
    # Run the scheduler
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute


if __name__ == "__main__":
    main()
