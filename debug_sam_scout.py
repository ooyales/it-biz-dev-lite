#!/usr/bin/env python3
"""
Detailed Error Checker for sam_scout.py
This will show you the EXACT error in sam_scout.py
"""

import sys
import traceback

print("\n" + "="*70)
print("SAM_SCOUT.PY ERROR CHECKER")
print("="*70 + "\n")

print("Testing sam_scout.py import...\n")

try:
    import sam_scout
    print("✓ Module imported successfully")
    
    # Check if class exists
    if hasattr(sam_scout, 'SAMOpportunityScout'):
        print("✓ SAMOpportunityScout class found")
        
        # Try to instantiate (this might fail if config is missing)
        try:
            scout = sam_scout.SAMOpportunityScout()
            print("✓ Class instantiated successfully")
        except Exception as e:
            print(f"⚠️  Class exists but can't instantiate: {e}")
            print("   (This is OK if config.yaml is missing/incomplete)")
    else:
        print("✗ SAMOpportunityScout class NOT found in sam_scout module")
        print("   Available attributes:", dir(sam_scout))
    
except SyntaxError as e:
    print("✗ SYNTAX ERROR in sam_scout.py:")
    print("-" * 70)
    print(f"Line {e.lineno}: {e.msg}")
    print(f"Text: {e.text}")
    print("-" * 70)
    print("\nFIX: Check line", e.lineno, "in sam_scout.py for syntax errors")
    
except ImportError as e:
    print("✗ IMPORT ERROR:")
    print("-" * 70)
    print(str(e))
    print("-" * 70)
    print("\nPossible causes:")
    print("  1. Missing dependency (install with: pip install <package>)")
    print("  2. Another Python file has errors")
    print("  3. sam_scout.py imports a module that doesn't exist")
    
except Exception as e:
    print("✗ UNEXPECTED ERROR:")
    print("-" * 70)
    traceback.print_exc()
    print("-" * 70)

print("\n" + "="*70)
print("CHECKING DEPENDENCIES")
print("="*70 + "\n")

# Check required packages
required_packages = {
    'yaml': 'pyyaml',
    'requests': 'requests',
}

for module_name, package_name in required_packages.items():
    try:
        __import__(module_name)
        print(f"✓ {module_name:<20} INSTALLED")
    except ImportError:
        print(f"✗ {module_name:<20} MISSING - install with: pip install {package_name}")

print("\n" + "="*70)
print("QUICK FIX OPTIONS")
print("="*70 + "\n")

print("Option 1: Use the working version from outputs")
print("-" * 70)
print("cp /mnt/user-data/outputs/sam_scout.py .")
print("python check_imports.py")
print()

print("Option 2: Check for syntax errors")
print("-" * 70)
print("python -m py_compile sam_scout.py")
print()

print("Option 3: Install missing dependencies")
print("-" * 70)
print("pip install pyyaml requests")
print()

print("Option 4: Use the dashboard instead (recommended for demo)")
print("-" * 70)
print("./start_team_system.sh")
print("Open: http://localhost:8080")
print()
