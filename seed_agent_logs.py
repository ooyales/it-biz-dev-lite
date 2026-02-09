#!/usr/bin/env python3
"""
Seed Agent Logs

Creates sample log entries for all 6 agents so the View Logs buttons
show realistic activity when clicked.
"""

from agent_logger import AgentLogger
from datetime import datetime, timedelta
import random

def seed_logs():
    """Create sample log entries for all agents"""
    logger = AgentLogger()
    
    print("Creating seed log data for agent dashboard...")
    
    # Get timestamps for the last 7 days
    now = datetime.now()
    
    # Agent 1: Opportunity Scout
    for i in range(15):
        days_ago = random.randint(0, 7)
        timestamp = now - timedelta(days=days_ago, hours=random.randint(0, 23))
        
        logger.log_agent_activity(
            agent_id=1,
            agent_name='Opportunity Scout',
            action='Score opportunities from SAM.gov',
            status='success' if random.random() > 0.1 else 'error',
            duration_seconds=round(random.uniform(1.5, 8.0), 2),
            input_data={
                'search_naics': '541512',
                'days_back': 30,
                'opportunity_count': random.randint(5, 25)
            },
            output_data={
                'scored': random.randint(5, 25),
                'high_priority': random.randint(0, 5),
                'medium_priority': random.randint(2, 10)
            }
        )
    print("✓ Agent 1: Opportunity Scout (15 logs)")
    
    # Agent 2: Competitive Intelligence
    for i in range(12):
        days_ago = random.randint(0, 7)
        
        logger.log_agent_activity(
            agent_id=2,
            agent_name='Competitive Intelligence',
            action='Analyze incumbent contractor',
            status='success',
            duration_seconds=round(random.uniform(3.0, 12.0), 2),
            input_data={
                'opportunity_id': f'OPP-{random.randint(1000, 9999)}',
                'incumbent_search': True
            },
            output_data={
                'incumbent_found': random.random() > 0.3,
                'incumbent_name': random.choice([
                    'Leidos Inc.',
                    'SAIC',
                    'Booz Allen Hamilton',
                    'General Dynamics IT',
                    'None Found'
                ]),
                'teaming_partners': random.randint(0, 4)
            }
        )
    print("✓ Agent 2: Competitive Intelligence (12 logs)")
    
    # Agent 3: Capability Matching
    for i in range(8):
        days_ago = random.randint(0, 7)
        
        logger.log_agent_activity(
            agent_id=3,
            agent_name='Capability Matching',
            action='Match staff to opportunity requirements',
            status='success' if random.random() > 0.05 else 'error',
            duration_seconds=round(random.uniform(1.0, 4.0), 2),
            input_data={
                'opportunity_id': f'OPP-{random.randint(1000, 9999)}',
                'requirements_count': random.randint(15, 35)
            },
            output_data={
                'team_score': random.randint(65, 98),
                'matched_requirements': random.randint(18, 32),
                'total_requirements': random.randint(20, 35),
                'recommended_staff': random.randint(4, 8)
            }
        )
    print("✓ Agent 3: Capability Matching (8 logs)")
    
    # Agent 4: RFI Generator
    for i in range(3):
        days_ago = random.randint(0, 7)
        
        logger.log_agent_activity(
            agent_id=4,
            agent_name='RFI Generator',
            action='Generate RFI response',
            status='success',
            duration_seconds=round(random.uniform(8.0, 25.0), 2),
            input_data={
                'opportunity_id': f'OPP-{random.randint(1000, 9999)}',
                'rfi_questions_count': random.randint(5, 15)
            },
            output_data={
                'rfi_generated': True,
                'word_count': random.randint(800, 2500),
                'sections': random.randint(4, 8)
            }
        )
    print("✓ Agent 4: RFI Generator (3 logs)")
    
    # Agent 5: Proposal Writer
    for i in range(2):
        days_ago = random.randint(0, 7)
        
        logger.log_agent_activity(
            agent_id=5,
            agent_name='Proposal Writer',
            action='Draft proposal sections',
            status='success',
            duration_seconds=round(random.uniform(15.0, 45.0), 2),
            input_data={
                'opportunity_id': f'OPP-{random.randint(1000, 9999)}',
                'sections_requested': ['Executive Summary', 'Technical Approach', 'Management Plan']
            },
            output_data={
                'proposal_generated': True,
                'total_pages': random.randint(15, 35),
                'word_count': random.randint(5000, 12000)
            }
        )
    print("✓ Agent 5: Proposal Writer (2 logs)")
    
    # Agent 6: Pricing Generator
    for i in range(4):
        days_ago = random.randint(0, 7)
        
        logger.log_agent_activity(
            agent_id=6,
            agent_name='Pricing Generator',
            action='Generate IGCE pricing model',
            status='success' if random.random() > 0.1 else 'error',
            duration_seconds=round(random.uniform(5.0, 15.0), 2),
            input_data={
                'opportunity_id': f'OPP-{random.randint(1000, 9999)}',
                'labor_categories': random.randint(6, 12),
                'contract_years': random.randint(1, 5)
            },
            output_data={
                'igce_generated': True,
                'total_price': random.randint(500000, 5000000),
                'labor_rate_avg': random.randint(85, 165)
            }
        )
    print("✓ Agent 6: Pricing Generator (4 logs)")
    
    print()
    print("=" * 70)
    print("SEED DATA CREATED")
    print("=" * 70)
    print("  Total logs: 44")
    print()
    print("View Logs buttons are now functional!")
    print("Restart your Flask server and click any 'View Logs' button")
    print("on the Agent Dashboard to see the activity.")
    print()


if __name__ == '__main__':
    seed_logs()
