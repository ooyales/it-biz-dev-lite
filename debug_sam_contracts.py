#!/usr/bin/env python3
"""
debug_sam_contracts.py
=======================
One-shot debug: hits SAM.gov Contract Awards API and dumps the raw
response so we can see exactly what structure it returns and why
the collector is getting zero results.

Run this from your project directory (where .env lives):
    python debug_sam_contracts.py
"""
import os, json, requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('SAM_API_KEY')
if not API_KEY:
    print("❌ SAM_API_KEY not in .env")
    exit(1)

BASE = "https://api.sam.gov/contract-awards/v1/search"

def dump_response(label, resp):
    print(f"\n{'─' * 60}")
    print(f"  {label}")
    print(f"{'─' * 60}")
    print(f"  Status : {resp.status_code}")
    print(f"  Content-Type: {resp.headers.get('content-type', 'N/A')}")

    try:
        data = resp.json()
        print(f"  Top-level keys: {list(data.keys())}")
        for k, v in data.items():
            if isinstance(v, list):
                print(f"    {k}: list of {len(v)} items")
                if v and isinstance(v[0], dict):
                    print(f"      first item keys: {list(v[0].keys())[:20]}")
                    # Show first item values (truncated)
                    print(f"      first item sample:")
                    for fk, fv in list(v[0].items())[:10]:
                        print(f"        {fk}: {str(fv)[:80]}")
            elif isinstance(v, dict):
                print(f"    {k}: dict with keys {list(v.keys())[:10]}")
            else:
                print(f"    {k}: {type(v).__name__} = {str(v)[:120]}")
    except Exception as e:
        print(f"  ❌ Not valid JSON: {e}")
        print(f"  Raw (first 2000 chars):\n{resp.text[:2000]}")


# ---------------------------------------------------------------
# TEST 1: Exactly what quick_fpds_setup sends (should match the
#          zero-result run)
# ---------------------------------------------------------------
print("\n" + "=" * 60)
print(" TEST 1: Original params (what returned 0 results)")
print("=" * 60)

params1 = {
    'api_key': API_KEY,
    'limit': 5,
    'offset': 0,
    'awardOrIDV': 'Award',
    'dateSigned': '[07/01/2025,12/31/2025]',
    'naicsCode': '541512',
}
print(f"  Params: {json.dumps({k:v for k,v in params1.items() if k != 'api_key'}, indent=4)}")
dump_response("Test 1 result", requests.get(BASE, params=params1, timeout=30))


# ---------------------------------------------------------------
# TEST 2: Drop dateSigned entirely — see if NAICS alone returns data
# ---------------------------------------------------------------
print("\n" + "=" * 60)
print(" TEST 2: No dateSigned filter (NAICS only)")
print("=" * 60)

params2 = {
    'api_key': API_KEY,
    'limit': 5,
    'offset': 0,
    'awardOrIDV': 'Award',
    'naicsCode': '541512',
}
print(f"  Params: {json.dumps({k:v for k,v in params2.items() if k != 'api_key'}, indent=4)}")
dump_response("Test 2 result", requests.get(BASE, params=params2, timeout=30))


# ---------------------------------------------------------------
# TEST 3: No filters at all — just get ANY awards back
# ---------------------------------------------------------------
print("\n" + "=" * 60)
print(" TEST 3: Bare minimum (no filters, just limit=2)")
print("=" * 60)

params3 = {
    'api_key': API_KEY,
    'limit': 2,
    'offset': 0,
}
print(f"  Params: {json.dumps({k:v for k,v in params3.items() if k != 'api_key'}, indent=4)}")
dump_response("Test 3 result", requests.get(BASE, params=params3, timeout=30))


# ---------------------------------------------------------------
# TEST 4: Try alternate date format (YYYY-MM-DD)
# ---------------------------------------------------------------
print("\n" + "=" * 60)
print(" TEST 4: dateSigned with YYYY-MM-DD format")
print("=" * 60)

params4 = {
    'api_key': API_KEY,
    'limit': 5,
    'offset': 0,
    'awardOrIDV': 'Award',
    'dateSigned': '[2024-01-01,2025-01-31]',
    'naicsCode': '541512',
}
print(f"  Params: {json.dumps({k:v for k,v in params4.items() if k != 'api_key'}, indent=4)}")
dump_response("Test 4 result", requests.get(BASE, params=params4, timeout=30))


# ---------------------------------------------------------------
# TEST 5: Confirm API key works on opportunities endpoint
# ---------------------------------------------------------------
print("\n" + "=" * 60)
print(" TEST 5: Opportunities endpoint (key validation)")
print("=" * 60)

resp5 = requests.get(
    "https://api.sam.gov/opportunities/v2/search",
    params={'api_key': API_KEY, 'limit': 1},
    timeout=30
)
print(f"  Status: {resp5.status_code}")
try:
    d = resp5.json()
    print(f"  Keys: {list(d.keys())}")
    total = d.get('totalCount', d.get('total', 'N/A'))
    print(f"  Total opportunities: {total}")
except:
    print(f"  Raw: {resp5.text[:500]}")

print("\n" + "=" * 60)
print(" DONE — review the output above to diagnose the issue")
print("=" * 60)
