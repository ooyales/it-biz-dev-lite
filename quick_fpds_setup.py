#!/usr/bin/env python3
"""
Quick Contract Data Setup
==========================
Pulls real IT contract awards from SAM.gov and loads them into Neo4j
so the Competitive Intelligence agent has real data.

Usage:
    python quick_fpds_setup.py              # default: 1,000 contracts
    python quick_fpds_setup.py --count 500  # lighter pull
    python quick_fpds_setup.py --count 5000 # deep pull for richer market data

The --count is a target, not a hard cap. Each NAICS code gets an equal
share to start (count ÷ 4), but if one code comes up short (e.g. fewer
records available), the remaining codes pick up the slack so you still
hit close to your target.

Requires SAM_API_KEY in your .env (free, from sam.gov).
"""

import argparse
from fpds_contract_collector import FPDSCollector


IT_NAICS = {
    '541512': 'Computer Systems Design Services',
    '541511': 'Custom Computer Programming',
    '541519': 'Other Computer Related Services',
    '518210': 'Computer Processing & Data Prep',
}


def quick_setup(target_count: int):
    print("=" * 70)
    print(" QUICK CONTRACT DATA SETUP — SAM.gov Contract Awards API")
    print("=" * 70)
    print()
    print(f"  Target   : {target_count:,} contracts")
    print(f"  NAICS    : {len(IT_NAICS)} codes ({', '.join(IT_NAICS.keys())})")
    print(f"  Per code : ~{target_count // len(IT_NAICS):,} (gaps filled by other codes)")
    print(f"  Date range: 07/01/2024 – 01/31/2026")
    print()

    response = input("Continue? (y/n): ")
    if response.lower() != 'y':
        print("Cancelled.")
        return

    collector = FPDSCollector()

    try:
        all_contracts = []
        remaining_codes = list(IT_NAICS.keys())

        # --- Round-robin with gap-filling ---
        # Each code starts with an equal share. After each code runs,
        # if it came up short we redistribute the shortfall evenly
        # across the codes that haven't run yet.
        per_code = target_count // len(IT_NAICS)
        codes_remaining = len(IT_NAICS)

        for naics_code in list(IT_NAICS.keys()):
            still_need = target_count - len(all_contracts)
            if still_need <= 0:
                break

            # This code's share: either its original slice, or a larger
            # slice if earlier codes came up short
            this_code_target = min(per_code, still_need)
            # But if we're running low on codes, give this one more room
            if codes_remaining > 0:
                this_code_target = min(still_need, max(per_code, still_need // codes_remaining))

            naics_name = IT_NAICS[naics_code]
            print(f"\n   → NAICS {naics_code} ({naics_name})")
            print(f"     Target for this code: {this_code_target:,}")

            batch = collector.fetch_contracts(
                naics=naics_code,
                start_date='07/01/2024',
                end_date='01/31/2026',
                max_records=this_code_target,
            )
            all_contracts.extend(batch)
            codes_remaining -= 1

            shortfall = this_code_target - len(batch)
            if shortfall > 0:
                print(f"     ↳ Came up {shortfall:,} short — remaining codes will compensate")

        # Trim to exact target (in case we slightly overshot)
        contracts = all_contracts[:target_count]

        if not contracts:
            print("\n⚠️  No contracts returned.")
            print("   Possible causes:")
            print("   1. SAM_API_KEY is invalid — check sam.gov → Profile → Public API Key")
            print("   2. Rate limit hit — check sam.gov account status")
            print("   3. Date range has no data — try broadening it")
            return

        print(f"\n   ✓ Collected {len(contracts):,} contracts total")

        # Import to Neo4j
        imported = collector.import_to_neo4j(contracts)

        # Summary
        print("\n" + "=" * 70)
        stats = collector.get_statistics()
        print(f"  ✓ DONE — {imported:,} contracts imported to Neo4j")
        print(f"  Total contracts in Neo4j : {stats['total_contracts']:,}")
        print(f"  Total value              : ${stats['total_value']:,.0f}")
        print()

        # Per-NAICS breakdown
        print("  By NAICS code:")
        naics_counts = {}
        for c in contracts:
            n = c.get('naics', 'Unknown')
            naics_counts[n] = naics_counts.get(n, 0) + 1
        for n, count in sorted(naics_counts.items(), key=lambda x: -x[1]):
            label = IT_NAICS.get(n, n)
            print(f"    • {n} ({label}): {count:,}")
        print()

        # Top contractors
        print("  Top contractors:")
        for c in stats['top_contractors'][:8]:
            print(f"    • {c['contractor']}: {c['contracts']} awards, ${c['total_value']:,.0f}")
        print()

        # Top agencies
        print("  Top agencies:")
        for a in stats.get('top_agencies', [])[:5]:
            print(f"    • {a['agency']}: {a['count']} contracts")
        print()

        print("  Restart your dashboard and test Competitive Intel!")
        print("=" * 70)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        collector.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Pull IT contract awards from SAM.gov into Neo4j"
    )
    parser.add_argument(
        '--count',
        type=int,
        default=1000,
        help='Target number of contracts to pull (default: 1000). Example: --count 5000'
    )
    args = parser.parse_args()

    if args.count < 10:
        print("⚠️  Minimum 10 contracts. Setting to 10.")
        args.count = 10

    quick_setup(args.count)
