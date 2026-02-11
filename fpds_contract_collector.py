#!/usr/bin/env python3
"""
Contract Data Collector — SAM.gov Contract Awards API
======================================================
FPDS ezsearch/ATOM was retired in July 2025. Contract award data
now lives at: https://api.sam.gov/contract-awards/v1/search

Requires your SAM_API_KEY (already in your .env).
"""

import requests
import os
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()


# =============================================================================
# 4-Layer IT Filter — same logic used for opportunities, adapted for contracts.
# Contracts have: description (from coreData), naics, psc already parsed.
# =============================================================================

IT_KEYWORDS = {
    'software', 'cloud', 'cybersecurity', 'cyber security', 'network', 'database',
    'application', 'development', 'programming', 'devops', 'agile', 'scrum',
    'data analytics', 'data science', 'machine learning', 'artificial intelligence',
    'it infrastructure', 'systems integration', 'help desk', 'technical support',
    'server', 'virtualization', 'container', 'kubernetes', 'docker',
    'web development', 'mobile app', 'api', 'microservices', 'saas',
    'information technology', 'computer systems', 'it services',
    'system administration', 'it security', 'information security',
    'software engineering', 'full stack', 'frontend', 'backend',
    'cloud computing', 'aws', 'azure', 'google cloud', 'gcp',
    'automation', 'ci/cd', 'continuous integration', 'deployment',
    'monitoring', 'logging', 'observability',
    'digital transformation', 'modernization', 'migration',
    'enterprise architecture', 'solution architecture',
    'business intelligence', 'analytics platform',
    'etl', 'data pipeline', 'data warehouse', 'data lake',
    'zero trust', 'devsecops', 'soc', 'incident response',
    'identity management', 'iam', 'siem', 'endpoint',
}

EXCLUSION_KEYWORDS = {
    'janitorial', 'custodial', 'cleaning service', 'sanitation', 'housekeeping',
    'waste removal', 'trash', 'garbage', 'recycling service',
    'construction', 'renovation', 'building maintenance', 'hvac', 'plumbing',
    'electrical work', 'carpentry', 'painting', 'roofing', 'flooring',
    'demolition', 'facilities maintenance', 'grounds maintenance',
    'landscaping', 'lawn care', 'pest control', 'snow removal',
    'security guard', 'physical security officer', 'armed guard',
    'unarmed guard', 'security patrol',
    'food service', 'cafeteria', 'transportation', 'moving service',
    'shipping', 'delivery', 'courier',
    'bottled', 'juice', 'beverage', 'fuel', 'diesel', 'gasoline',
    'oil tank', 'propane', 'chlorine', 'chemical',
    'door maintenance', 'automatic door', 'gate', 'fence',
    'parking', 'vehicle', 'automobile', 'truck',
    'medical equipment', 'hospital', 'clinic',
    'textiles', 'uniforms', 'laundry',
    'office supplies', 'furniture', 'fixtures',
}

IT_NAICS_CODES = {'541511', '541512', '541519', '518210'}
IT_PSC_PREFIXES = ['D3', 'D4', 'DF', '7030', 'R4']  # D-series = IT/ADP equipment and services


def is_it_contract(contract: Dict, api_naics: str = None) -> tuple:
    """
    4-layer IT relevance check on a parsed contract record.
    Returns (bool, reason_string) so the caller can log why it passed or not.

    api_naics: the NAICS code we used to query SAM.gov. If the parser couldn't
               extract naics from the record itself, we fall back to this —
               because SAM already filtered by it server-side.

    Layer 1: IT NAICS code (strong signal, but still check exclusions)
    Layer 2: IT PSC code (strong signal)
    Layer 3: IT keyword count in description
    Layer 4: Exclusion keyword check (overrides layers 1-3 if strong enough)
    """
    description = (contract.get('description') or '').lower()
    naics = str(contract.get('naics') or '')
    psc = str(contract.get('psc') or '')

    # If the parser couldn't pull NAICS from the nested record, trust the
    # API-level filter — SAM already returned this record under that NAICS.
    if not naics and api_naics:
        naics = api_naics

    it_keyword_count = sum(1 for word in IT_KEYWORDS if word in description)
    exclusion_count = sum(1 for word in EXCLUSION_KEYWORDS if word in description)

    # Layer 1: IT NAICS
    if naics in IT_NAICS_CODES:
        # NAICS 541512 = Computer Systems Design — SAM.gov already filtered by this
        # Only reject if strong exclusion signal (2+ keywords)
        if exclusion_count >= 2:
            return False, f"IT NAICS but {exclusion_count} exclusion keywords"
        
        # 1 exclusion: need at least 2 IT keywords to override (lowered from 3)
        if exclusion_count == 1:
            if it_keyword_count >= 2:
                return True, f"IT NAICS + {it_keyword_count} IT keywords override 1 exclusion"
            return False, "IT NAICS but exclusion keyword present, insufficient IT keywords"
        
        # No exclusions → trust the NAICS (even if description is sparse)
        return True, "IT NAICS, no exclusions"

    # Layer 2: IT PSC code
    if any(psc.upper().startswith(prefix) for prefix in IT_PSC_PREFIXES):
        if exclusion_count == 0:
            return True, "IT PSC code, no exclusions"

    # Layer 3 & 4: keyword analysis (no NAICS/PSC signal to lean on)
    if exclusion_count >= 2:
        return False, f"{exclusion_count} exclusion keywords"
    if exclusion_count == 1 and it_keyword_count >= 2:
        return True, f"{it_keyword_count} IT keywords override 1 exclusion"
    if exclusion_count >= 1:
        return False, "Exclusion keyword present"
    # Lowered threshold to 1 since descriptions are often truncated at 150 chars
    if it_keyword_count >= 1:
        return True, f"{it_keyword_count} IT keyword(s)"

    # Not enough signal either way
    return False, f"Only {it_keyword_count} IT keywords, no IT NAICS/PSC"


class FPDSCollector:
    """Collect contract award data via SAM.gov Contract Awards API"""

    BASE_URL = "https://api.sam.gov/contract-awards/v1/search"

    def __init__(self):
        self.api_key = os.getenv('SAM_API_KEY')
        if not self.api_key:
            raise ValueError(
                "SAM_API_KEY not set in .env\n"
                "Get one free at: https://sam.gov  sign in  Profile  Public API Key"
            )

        self.neo4j_uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
        self.neo4j_user = os.getenv('NEO4J_USER', 'neo4j')
        self.neo4j_password = os.getenv('NEO4J_PASSWORD')
        if not self.neo4j_password:
            raise ValueError("NEO4J_PASSWORD not set in .env")

        self.driver = GraphDatabase.driver(
            self.neo4j_uri, auth=(self.neo4j_user, self.neo4j_password)
        )
        print("✓ Connected to Neo4j")
        print(f"✓ SAM API key loaded ({self.api_key[:8]}...)")

    # ------------------------------------------------------------------
    # Fetch
    # ------------------------------------------------------------------
    def fetch_contracts(
        self,
        agency: str = None,
        naics: str = None,
        start_date: str = None,   # MM/DD/YYYY
        end_date: str = None,     # MM/DD/YYYY
        max_records: int = 100
    ) -> List[Dict]:
        """
        Fetch contract awards from SAM.gov.

        Parameters match the SAM.gov Contract Awards API exactly:
          - contractingDepartmentName  (partial match, e.g. 'DEFENSE')
          - naicsCode                  (exact NAICS, e.g. '541512')
          - dateSigned                 ([MM/DD/YYYY,MM/DD/YYYY])
        """
        if not start_date:
            start_date = (datetime.now() - timedelta(days=180)).strftime('%m/%d/%Y')
        if not end_date:
            end_date = (datetime.now() - timedelta(days=1)).strftime('%m/%d/%Y')

        params = {
            'api_key': self.api_key,
            'limit': 100,          # max per page
            'offset': 0,
            'awardOrIDV': 'Award', # only awards, not IDVs
            'dateSigned': f'[{start_date},{end_date}]',
        }

        if agency:
            params['contractingDepartmentName'] = agency
        if naics:
            params['naicsCode'] = naics

        contracts = []
        raw_offset = 0          # tracks position in SAM.gov's result set
        total_available = None  # filled from first response's totalRecords
        print(f"🔍 Fetching contracts from SAM.gov Contract Awards API...")
        print(f"   Agency filter : {agency or 'All'}")
        print(f"   NAICS filter  : {naics or 'All'}")
        print(f"   Date range    : {start_date} to {end_date}")
        print(f"   IT filter     : enabled (keywords + exclusions)")

        while len(contracts) < max_records:
            params['offset'] = raw_offset
            print(f"   Fetching offset {raw_offset}... (IT-filtered: {len(contracts):,} so far)")

            try:
                resp = requests.get(self.BASE_URL, params=params, timeout=60)

                if resp.status_code == 401:
                    print("❌ 401 Unauthorized — your SAM_API_KEY is invalid or expired.")
                    print("   Get a new one: https://sam.gov  sign in  Profile  Public API Key")
                    break

                if resp.status_code == 429:
                    print("❌ Rate limited (429) — this is a DAILY limit, not per-minute.")
                    print("   Your account is on the 10 req/day tier.")
                    print()
                    print("   Quick fix (free, permanent):")
                    print("     1. sam.gov → sign in → Workspace")
                    print("     2. Request any Role (read-only is fine)")
                    print("     3. Once approved → 1,000 req/day automatically")
                    print()
                    print("   Or just run this script again tomorrow.")
                    break

                resp.raise_for_status()
                data = resp.json()

                # SAM.gov Contract Awards returns results under 'awardSummary'
                hits = data.get('awardSummary', [])
                if not hits:
                    print(f"   No more results.")
                    break

                # Grab totalRecords on first response so we know the ceiling
                if total_available is None:
                    total_available = int(data.get('totalRecords', 0))
                    print(f"   Total available in SAM.gov: {total_available:,}")

                before_filter = len(contracts)
                first_page = (raw_offset == 0)  # log detail on first page only
                if first_page:
                    print(f"   --- First page diagnostic ---")
                for record in hits:
                    parsed = self._parse_award(record)
                    if not parsed:
                        if first_page:
                            print(f"     [skip] _parse_award returned None (no vendor name?)")
                        continue
                    # 4-layer IT filter — pass api_naics as fallback in case
                    # the parser couldn't extract it from the nested record
                    is_it, reason = is_it_contract(parsed, api_naics=naics)
                    if first_page:
                        print(f"     [{('PASS' if is_it else 'FAIL')}] naics={parsed.get('naics') or '(empty)'} "
                              f"psc={parsed.get('psc') or '(empty)'} "
                              f"desc={repr((parsed.get('description') or '')[:60])} "
                              f"→ {reason}")
                    if not is_it:
                        continue
                    contracts.append(parsed)
                after_filter = len(contracts)
                if first_page:
                    print(f"   --- End diagnostic ---")

                print(f"   Got {len(hits)} raw, {after_filter - before_filter} passed IT filter "
                      f"(total IT so far: {len(contracts):,})")

                # Advance raw offset by the page size we actually fetched
                raw_offset += len(hits)

                # Stop if we've exhausted SAM.gov's full result set
                if raw_offset >= total_available:
                    print(f"   Exhausted all {total_available:,} records for this NAICS.")
                    break

                # Safety valve: if a full page returned zero IT contracts,
                # results are unlikely to get better further in — stop early
                if (after_filter - before_filter) == 0 and len(hits) >= 100:
                    print(f"   Full page with 0 IT matches — stopping early.")
                    break

                time.sleep(1)  # be polite

            except requests.exceptions.RequestException as e:
                print(f"⚠️  Request error: {e}")
                break

        contracts = contracts[:max_records]
        print(f"✓ Collected {len(contracts)} contracts")
        return contracts

    # ------------------------------------------------------------------
    # Parse a single award record from SAM.gov JSON
    # ------------------------------------------------------------------
    def _parse_award(self, record: Dict) -> Optional[Dict]:
        """
        SAM.gov Contract Awards API returns deeply nested objects per award.
        
        Actual paths confirmed from debug output:
        - Agency: coreData.federalOrganization.contractingInformation.contractingDepartment.name
        - Vendor: awardDetails.awardeeData.awardeeHeader.awardeeName
        - NAICS: awardDetails.productOrServiceInformation.idvNAICS.code
        - PSC: coreData.productOrServiceInformation.productOrServiceCode.code
        - Description: awardDetails.productOrServiceInformation.descriptionOfContractRequirement
        - Dollar value: awardDetails.dollars.baseDollarsObligated or totalContractDollars
        """
        try:
            contract_id_obj = record.get('contractId', {})
            core = record.get('coreData', {})
            details = record.get('awardDetails', {})
            
            # PIID from contractId
            piid = contract_id_obj.get('piid', '')
            if not piid:
                return None

            # Agency — coreData.federalOrganization...
            federal_org = core.get('federalOrganization', {})
            contracting_info = federal_org.get('contractingInformation', {})
            contracting_dept = contracting_info.get('contractingDepartment', {})
            agency = contracting_dept.get('name', '')
            
            # Fallback to subtier if main path fails
            if not agency:
                agency = contract_id_obj.get('subtier', {}).get('name', '')

            # Vendor — awardDetails.awardeeData.awardeeHeader.awardeeName
            awardee_data = details.get('awardeeData', {})
            awardee_header = awardee_data.get('awardeeHeader', {})
            vendor_name = awardee_header.get('awardeeName', '') or awardee_header.get('awardeeNameFromContract', '')
            
            # UEI from same location
            awardee_uei_obj = awardee_data.get('awardeeUEI', {})
            vendor_uei = awardee_uei_obj.get('ueiSAM', '') if isinstance(awardee_uei_obj, dict) else str(awardee_uei_obj or '')

            # NAICS — awardDetails.productOrServiceInformation.idvNAICS.code
            details_prod_svc = details.get('productOrServiceInformation', {})
            naics_obj = details_prod_svc.get('idvNAICS', {})
            naics = naics_obj.get('code', '') if isinstance(naics_obj, dict) else str(naics_obj or '')
            
            # PSC — coreData.productOrServiceInformation.productOrService.code
            core_prod_svc = core.get('productOrServiceInformation', {})
            psc_obj = core_prod_svc.get('productOrService', {})
            psc = psc_obj.get('code', '') if isinstance(psc_obj, dict) else str(psc_obj or '')

            # Description — awardDetails.productOrServiceInformation.descriptionOfContractRequirement
            description = details_prod_svc.get('descriptionOfContractRequirement', '').strip()

            # Dollar value — awardDetails.dollars.baseDollarsObligated
            value = 0.0
            dollars = details.get('dollars', {})
            for key in ('baseDollarsObligated', 'actionObligation', 'baseAndAllOptionsValue'):
                raw = dollars.get(key)
                if raw:
                    try:
                        value = float(str(raw).replace(',', ''))
                        break
                    except (ValueError, TypeError):
                        continue
            
            # Fallback to totalContractDollars if dollars object was empty
            if value == 0.0:
                total_dollars = details.get('totalContractDollars', {})
                for key in ('totalBaseAndExercisedOptionsValue', 'totalBaseAndAllOptionsValue', 'totalActionObligation'):
                    raw = total_dollars.get(key)
                    if raw:
                        try:
                            value = float(str(raw).replace(',', ''))
                            break
                        except (ValueError, TypeError):
                            continue

            # Date signed — awardDetails.dates.dateSigned
            dates = details.get('dates', {})
            date_signed = dates.get('dateSigned', '')
            if date_signed and ('T' in date_signed or ' ' in date_signed):
                date_signed = date_signed.split('T')[0].split(' ')[0]

            # Place of performance — coreData.principalPlaceOfPerformance
            pop = core.get('principalPlaceOfPerformance', {})
            city = pop.get('city', {})
            state = pop.get('state', {})
            city_name = city.get('name', '') if isinstance(city, dict) else str(city)
            state_code = state.get('code', '') if isinstance(state, dict) else str(state)
            place = f"{city_name}, {state_code}".strip(', ')

            # Contract type — coreData.awardOrIDVType.name
            type_obj = core.get('awardOrIDVType', {})
            contract_type = type_obj.get('name', '') if isinstance(type_obj, dict) else str(type_obj or '')

            # Must have at least vendor or agency to be useful
            if not vendor_name and not agency:
                return None

            # Return with keys that match what the filter and Neo4j expect
            return {
                'contract_id': piid,
                'agency': agency,
                'vendor_name': vendor_name.strip() if vendor_name else '',
                'vendor_uei': vendor_uei,
                'naics': naics,
                'psc': psc,
                'value': value,
                'date_signed': date_signed,
                'description': description[:500] if description else '',
                'place_of_performance': place,
                'contract_type': contract_type,
            }
        except Exception as e:
            print(f"   ⚠️  Parse error on one record: {e}")
            import traceback
            traceback.print_exc()
            return None

    # ------------------------------------------------------------------
    # Import to Neo4j
    # ------------------------------------------------------------------
    def import_to_neo4j(self, contracts: List[Dict]) -> int:
        if not contracts:
            print("⚠️  No contracts to import")
            return 0

        print(f"\n📥 Importing {len(contracts)} contracts to Neo4j...")

        with self.driver.session(database="neo4j") as session:
            for idx in [
                "CREATE INDEX contract_id IF NOT EXISTS FOR (c:Contract) ON (c.contract_id)",
                "CREATE INDEX contract_agency IF NOT EXISTS FOR (c:Contract) ON (c.agency)",
                "CREATE INDEX contract_naics IF NOT EXISTS FOR (c:Contract) ON (c.naics)",
            ]:
                session.run(idx)

            batch_size = 50
            imported = 0

            for i in range(0, len(contracts), batch_size):
                batch = contracts[i:i + batch_size]

                result = session.run("""
                    UNWIND $contracts AS c

                    MERGE (org:Organization {name: c.vendor_name})
                    ON CREATE SET org.uei = c.vendor_uei,
                                  org.created_at = datetime()

                    MERGE (contract:Contract {contract_id: c.contract_id})
                    SET contract.agency            = c.agency,
                        contract.agency_code       = c.agency_code,
                        contract.naics             = c.naics,
                        contract.psc               = c.psc,
                        contract.value             = c.value,
                        contract.date_signed       = c.date_signed,
                        contract.description       = c.description,
                        contract.place_of_performance = c.place_of_performance,
                        contract.contract_type     = c.contract_type,
                        contract.imported_at       = datetime()

                    MERGE (contract)-[:AWARDED_TO]->(org)

                    RETURN count(contract) as cnt
                """, contracts=batch)

                row = result.single()
                batch_imported = row['cnt'] if row else 0
                imported += batch_imported
                print(f"   Batch {i // batch_size + 1}: {batch_imported} contracts")

        print(f"✓ Imported {imported} contracts to Neo4j")
        return imported

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------
    def get_statistics(self) -> Dict:
        with self.driver.session(database="neo4j") as session:
            stats = {}

            row = session.run("MATCH (c:Contract) RETURN count(c) as total").single()
            stats['total_contracts'] = row['total'] if row else 0

            row = session.run("MATCH (c:Contract) RETURN sum(c.value) as tv").single()
            stats['total_value'] = row['tv'] or 0.0

            stats['top_agencies'] = [
                dict(r) for r in session.run("""
                    MATCH (c:Contract)
                    RETURN c.agency as agency, count(c) as count
                    ORDER BY count DESC LIMIT 10
                """)
            ]

            stats['top_contractors'] = [
                dict(r) for r in session.run("""
                    MATCH (c:Contract)-[:AWARDED_TO]->(o:Organization)
                    RETURN o.name as contractor, count(c) as contracts, sum(c.value) as total_value
                    ORDER BY total_value DESC LIMIT 10
                """)
            ]

        return stats

    def close(self):
        self.driver.close()
