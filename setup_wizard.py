#!/usr/bin/env python3
"""
Quick Start Wizard for Federal Contracting AI Assistant

This interactive script helps you set up the system for the first time.
"""

import os
import json
import yaml
from pathlib import Path


def print_banner():
    print("""
╔═══════════════════════════════════════════════════════════════╗
║     Federal Contracting AI Assistant - Setup Wizard           ║
║                                                                ║
║     This wizard will help you configure your system           ║
╚═══════════════════════════════════════════════════════════════╝
    """)


def get_input(prompt, default=None, required=True):
    """Get user input with optional default"""
    if default:
        prompt = f"{prompt} [{default}]: "
    else:
        prompt = f"{prompt}: "
    
    while True:
        value = input(prompt).strip()
        if value:
            return value
        elif default:
            return default
        elif not required:
            return None
        else:
            print("This field is required. Please enter a value.")


def get_yes_no(prompt, default=True):
    """Get yes/no input"""
    default_str = "Y/n" if default else "y/N"
    while True:
        response = input(f"{prompt} [{default_str}]: ").strip().lower()
        if response in ['y', 'yes']:
            return True
        elif response in ['n', 'no']:
            return False
        elif response == '':
            return default
        else:
            print("Please enter 'y' or 'n'")


def setup_config():
    """Interactive configuration setup"""
    print("\n" + "="*70)
    print("STEP 1: Basic Configuration")
    print("="*70)
    
    config = {}
    
    # Company information
    print("\n📋 Company Information (Optional fields can be skipped)")
    config['company'] = {
        'name': get_input("Company name (optional, for reports)", "My Company", required=False) or "My Company",
        'naics_codes': [],
        'set_asides': [],
        'contract_vehicles': []
    }
    
    # NAICS codes
    print("\n📊 NAICS Codes (enter one at a time, blank to finish)")
    while True:
        naics = get_input("NAICS code", required=False)
        if not naics:
            break
        config['company']['naics_codes'].append(naics)
    
    if not config['company']['naics_codes']:
        print("⚠️  No NAICS codes entered. You'll need to add these later in config.yaml")
    
    # Set-asides
    print("\n🎯 Set-Aside Categories")
    set_asides = {
        '1': 'small_business',
        '2': '8a',
        '3': 'hubzone',
        '4': 'wosb',
        '5': 'sdvosb'
    }
    
    print("Select applicable set-asides (comma-separated numbers):")
    for key, value in set_asides.items():
        print(f"  {key}. {value}")
    
    selections = get_input("Selections", required=False)
    if selections:
        for sel in selections.split(','):
            sel = sel.strip()
            if sel in set_asides:
                config['company']['set_asides'].append(set_asides[sel])
    
    # API Keys
    print("\n" + "="*70)
    print("STEP 2: API Configuration")
    print("="*70)
    
    print("\n🔑 SAM.gov API Key")
    print("Get your free API key at: https://open.gsa.gov/api/entity-api/")
    config['sam_gov'] = {
        'api_key': get_input("SAM.gov API key"),
        'search': {
            'opportunity_types': [
                'Presolicitation',
                'Solicitation',
                'Sources Sought',
                'Special Notice'
            ],
            'value_range': {
                'min': int(get_input("Minimum contract value ($)", "50000")),
                'max': int(get_input("Maximum contract value ($)", "10000000"))
            },
            'lookback_days': int(get_input("Days to look back", "7")),
            'keywords': []
        }
    }
    
    print("\n🔑 Anthropic API Key")
    print("Get your API key at: https://console.anthropic.com/")
    print("Note: This requires a paid account (~$100/month for typical usage)")
    config['claude'] = {
        'api_key': get_input("Anthropic API key"),
        'model': 'claude-sonnet-4-20250514',
        'max_tokens': 4000
    }
    
    # Keywords
    print("\n🔍 Search Keywords (enter one at a time, blank to finish)")
    print("Examples: 'IT services', 'cybersecurity', 'cloud computing'")
    while True:
        keyword = get_input("Keyword", required=False)
        if not keyword:
            break
        config['sam_gov']['search']['keywords'].append(keyword)
    
    # Staff database
    print("\n" + "="*70)
    print("STEP 3: Staff Database")
    print("="*70)
    
    config['staff'] = {
        'database_path': 'data/staff_database.json'
    }
    
    print("""
You'll need to create a staff database with your team's information.
A template is provided in 'staff_database_template.json'.

Copy this to 'data/staff_database.json' and fill in your staff details.
    """)
    
    # Notifications
    print("\n" + "="*70)
    print("STEP 4: Notifications (Optional)")
    print("="*70)
    
    config['notifications'] = {
        'email': {'enabled': False},
        'slack': {'enabled': False}
    }
    
    if get_yes_no("Configure email notifications?", default=False):
        print("\nNote: For Gmail, you'll need an App Password (not your regular password)")
        print("Generate at: https://myaccount.google.com/apppasswords")
        config['notifications']['email'] = {
            'enabled': True,
            'smtp_server': get_input("SMTP server", "smtp.gmail.com"),
            'smtp_port': int(get_input("SMTP port", "587")),
            'from_address': get_input("From email address"),
            'to_addresses': [get_input("To email address")],
            'password': get_input("Email App Password (not your regular password)")
        }
    
    if get_yes_no("Configure Slack notifications?", default=False):
        print("Get webhook URL at: https://api.slack.com/apps")
        config['notifications']['slack'] = {
            'enabled': True,
            'webhook_url': get_input("Slack webhook URL")
        }
    
    # Storage paths
    config['storage'] = {
        'base_path': 'data',
        'opportunities_path': 'data/opportunities',
        'analysis_path': 'data/analysis',
        'proposals_path': 'data/proposals',
        'reports_path': 'data/reports'
    }
    
    # Schedule
    config['schedule'] = {
        'sam_check_frequency': 12,
        'daily_digest_time': '09:00'
    }
    
    # Agents
    config['agents'] = {
        'opportunity_scout': {
            'enabled': True,
            'scoring_weights': {
                'naics_match': 10,
                'set_aside_match': 8,
                'value_appropriate': 7,
                'keyword_match': 6,
                'incumbent_intel': 5
            }
        },
        'capability_matcher': {
            'enabled': True,
            'min_match_threshold': 70
        },
        'competitive_intel': {
            'enabled': True,
            'sources': ['usaspending.gov', 'fpds.gov', 'sam.gov']
        },
        'rfi_responder': {
            'enabled': True,
            'auto_draft_threshold': 7
        },
        'proposal_writer': {
            'enabled': True,
            'auto_draft_threshold': 8
        }
    }
    
    # Logging
    config['logging'] = {
        'level': 'INFO',
        'file_path': 'logs/fed_contracting_ai.log'
    }
    
    return config


def create_directories():
    """Create necessary directories"""
    print("\n" + "="*70)
    print("Creating directories...")
    print("="*70)
    
    directories = [
        'data',
        'data/opportunities',
        'data/analysis',
        'data/proposals',
        'data/reports',
        'logs'
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✓ Created {directory}")


def save_config(config):
    """Save configuration to file"""
    print("\n" + "="*70)
    print("Saving configuration...")
    print("="*70)
    
    with open('config.yaml', 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
    
    print("✓ Configuration saved to config.yaml")


def setup_staff_database():
    """Copy staff database template"""
    print("\n" + "="*70)
    print("Setting up staff database...")
    print("="*70)
    
    if os.path.exists('data/staff_database.json'):
        if not get_yes_no("data/staff_database.json already exists. Overwrite?", default=False):
            print("Keeping existing staff database")
            return
    
    # Copy template
    import shutil
    shutil.copy('staff_database_template.json', 'data/staff_database.json')
    print("✓ Copied staff_database_template.json to data/staff_database.json")
    print("\n⚠️  IMPORTANT: Edit data/staff_database.json and fill in your staff information")


def test_connection():
    """Test SAM.gov connection"""
    print("\n" + "="*70)
    print("Testing SAM.gov connection...")
    print("="*70)
    
    if get_yes_no("Test SAM.gov connection now?", default=True):
        print("\nRunning test search...")
        os.system("python main.py --test")
    else:
        print("Skipped. You can test later with: python main.py --test")


def main():
    """Main setup wizard"""
    print_banner()
    
    # Check if config already exists
    if os.path.exists('config.yaml'):
        if not get_yes_no("config.yaml already exists. Overwrite?", default=False):
            print("\nSetup cancelled. Your existing configuration is preserved.")
            return
    
    # Run setup steps
    config = setup_config()
    create_directories()
    save_config(config)
    setup_staff_database()
    test_connection()
    
    # Final instructions
    print("\n" + "="*70)
    print("✅ Setup Complete!")
    print("="*70)
    print("""
Next steps:

1. Edit data/staff_database.json with your staff information
   (Remove the TEMPLATE entry when done)

2. Review and adjust config.yaml if needed

3. Test the system:
   python main.py --test

4. Run full analysis:
   python main.py

5. Set up automated scheduling (optional):
   - Linux/Mac: Use cron (see SETUP_GUIDE.md)
   - Windows: Use Task Scheduler (see SETUP_GUIDE.md)
   - Alternative: Run scheduler.py

For detailed documentation, see:
- README.md - Overview and quick start
- SETUP_GUIDE.md - Detailed setup and configuration
- Logs will be in: logs/fed_contracting_ai.log

Questions? Check the troubleshooting section in SETUP_GUIDE.md
    """)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user.")
    except Exception as e:
        print(f"\n❌ Error during setup: {e}")
        print("Please check the error and try again, or manually edit config.yaml")
