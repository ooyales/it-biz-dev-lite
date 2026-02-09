#!/usr/bin/env python3
"""
debug_descriptions.py
======================
Pulls one page of contract awards and dumps the raw descriptions
so we can see what the IT filter is actually working with.

Run from your project directory:
    python debug_descriptions.py
"""
import os, json, requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('SAM_API_KEY')
if not API_KEY:
    print("❌ SAM_API_KEY not in .env")
    exit(1)

BASE = "https://api.sam.gov/contract-awards/v1/search"

params = {
    'api_key': API_KEY,
    'limit': 10,
    'offset': 0,
    'awardOrIDV': 'Award',
    'dateSigned': '[07/01/2024,01/31/2026]',
    'naicsCode': '541512',
}

print("Fetching 10 records from NAICS 541512...")
resp = requests.get(BASE, params=params, timeout=30)

if resp.status_code != 200:
    print(f"❌ Status {resp.status_code}: {resp.text[:500]}")
    exit(1)

data = resp.json()
hits = data.get('awardSummary', [])
print(f"Got {len(hits)} records. Total available: {data.get('totalRecords')}\n")

for i, record in enumerate(hits):
    core = record.get('coreData', {})
    contract_id = record.get('contractId', {})
    details = record.get('awardDetails', {})

    piid = contract_id.get('piid', 'N/A')
    
    # Agency from coreData (this one was right)
    federal_org = core.get('federalOrganization', {})
    contracting_info = federal_org.get('contractingInformation', {})
    contracting_dept = contracting_info.get('contractingDepartment', {})
    agency = contracting_dept.get('name', 'N/A')
    
    # Vendor from awardDetails.awardeeData.awardeeHeader
    awardee_data = details.get('awardeeData', {})
    awardee_header = awardee_data.get('awardeeHeader', {})
    vendor = awardee_header.get('awardeeName', 'N/A')
    
    # NAICS from awardDetails.productOrServiceInformation.idvNAICS
    prod_svc_info = details.get('productOrServiceInformation', {})
    naics_obj = prod_svc_info.get('idvNAICS', {})
    naics = naics_obj.get('code', 'N/A') if isinstance(naics_obj, dict) else 'N/A'
    
    # PSC from coreData.productOrServiceInformation.productOrService.code
    core_prod_svc = core.get('productOrServiceInformation', {})
    psc_obj = core_prod_svc.get('productOrService', {})
    psc = psc_obj.get('code', 'N/A') if isinstance(psc_obj, dict) else 'N/A'
    
    # Description from awardDetails.productOrServiceInformation.descriptionOfContractRequirement
    description = prod_svc_info.get('descriptionOfContractRequirement', '')

    print(f"─── Record {i+1} ───")
    print(f"  PIID        : {piid}")
    print(f"  Vendor      : {vendor}")
    print(f"  Agency      : {agency}")
    print(f"  NAICS       : {naics}")
    print(f"  PSC         : {psc}")
    print(f"  Description : {repr(description[:200]) if description else '*** EMPTY ***'}")
    print()

# Also dump ALL keys in coreData for the first record so we don't miss
# a field that might have the real description
print("=" * 60)
print("ALL coreData keys in first record:")
print("=" * 60)
if hits:
    core = hits[0].get('coreData', {})
    for k, v in core.items():
        val_str = str(v)[:120] if v else '(empty/null)'
        print(f"  {k}: {val_str}")

print("\n" + "=" * 60)
print("ALL awardDetails keys in first record:")
print("=" * 60)
if hits:
    details = hits[0].get('awardDetails', {})
    if details:
        for k, v in details.items():
            val_str = str(v)[:120] if v else '(empty/null)'
            print(f"  {k}: {val_str}")
    else:
        print("  (awardDetails is empty or missing)")

print("\n" + "=" * 60)
print("Checking for awardee/vendor fields in multiple locations:")
print("=" * 60)
if hits:
    rec = hits[0]
    print(f"  coreData.awardee: {rec.get('coreData', {}).get('awardee', 'NOT FOUND')}")
    print(f"  coreData.awardeeName: {rec.get('coreData', {}).get('awardeeName', 'NOT FOUND')}")
    print(f"  awardDetails.awardee: {rec.get('awardDetails', {}).get('awardee', 'NOT FOUND')}")
    print(f"  awardee (top level): {rec.get('awardee', 'NOT FOUND')}")

print("\n" + "=" * 60)
print("coreData.productOrServiceInformation (full object):")
print("=" * 60)
if hits:
    prod_svc = hits[0].get('coreData', {}).get('productOrServiceInformation', {})
    if prod_svc:
        import json
        print(json.dumps(prod_svc, indent=2))
    else:
        print("  (productOrServiceInformation not found or empty)")

print("\n" + "=" * 60)
print("awardDetails.productOrServiceInformation (full object):")
print("=" * 60)
if hits:
    prod_svc = hits[0].get('awardDetails', {}).get('productOrServiceInformation', {})
    if prod_svc:
        import json
        print(json.dumps(prod_svc, indent=2))
    else:
        print("  (productOrServiceInformation not found or empty)")
