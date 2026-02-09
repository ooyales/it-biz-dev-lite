#!/usr/bin/env python3
"""
Diagnostic Script - Check Module Imports
Run this to diagnose import issues
"""

import sys
import os

print("\n" + "="*70)
print("MODULE IMPORT DIAGNOSTIC")
print("="*70 + "\n")

print(f"Python version: {sys.version}")
print(f"Current directory: {os.getcwd()}")
print(f"Python path: {sys.path[0]}\n")

# Check if files exist
files_to_check = [
    'sam_scout.py',
    'competitive_intel_agent.py',
    'fpds_intel.py',
    'config.yaml',
    'main.py'
]

print("Checking for required files:")
print("-" * 70)
for filename in files_to_check:
    exists = os.path.exists(filename)
    status = "✓" if exists else "✗"
    print(f"{status} {filename:<35} {'FOUND' if exists else 'NOT FOUND'}")

print()

# Try importing modules
print("Attempting imports:")
print("-" * 70)

# SAM Scout
try:
    from sam_scout import SAMOpportunityScout
    print("✓ sam_scout.SAMOpportunityScout     SUCCESS")
except ImportError as e:
    print(f"✗ sam_scout.SAMOpportunityScout     FAILED: {e}")
except Exception as e:
    print(f"✗ sam_scout.SAMOpportunityScout     ERROR: {e}")

# Competitive Intel
try:
    from competitive_intel_agent import CompetitiveIntelAgent
    print("✓ competitive_intel_agent            SUCCESS")
except ImportError as e:
    print(f"✗ competitive_intel_agent            FAILED: {e}")
except Exception as e:
    print(f"✗ competitive_intel_agent            ERROR: {e}")

# FPDS Intel
try:
    from fpds_intel import FPDSIntel
    print("✓ fpds_intel.FPDSIntel              SUCCESS")
except ImportError as e:
    print(f"✗ fpds_intel.FPDSIntel              FAILED: {e}")
except Exception as e:
    print(f"✗ fpds_intel.FPDSIntel              ERROR: {e}")

print("\n" + "="*70)
print("RECOMMENDATIONS")
print("="*70 + "\n")

if not os.path.exists('sam_scout.py'):
    print("⚠️  sam_scout.py not found in current directory")
    print("   Copy sam_scout.py to:", os.getcwd())

if not os.path.exists('config.yaml'):
    print("⚠️  config.yaml not found")
    print("   This is required for SAM.gov API key")

print("\n✓ If all imports show SUCCESS, your setup is correct!")
print("✓ Run your script from this directory:", os.getcwd())
print("\nTo run main.py with competitive intel:")
print("  python main.py --competitive-intel --days 14\n")
