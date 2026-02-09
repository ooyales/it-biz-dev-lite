#!/usr/bin/env python3
"""
SAM.gov API Diagnostic Tool
Tests your SAM.gov API connection and helps troubleshoot why no opportunities are found
"""

import requests
import json
import yaml
from datetime import datetime, timedelta
from urllib.parse import urlencode


class SAMDiagnostic:
    """Diagnostic tool for SAM.gov API"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config = self._load_config(config_path)
        self.base_url = "https://api.sam.gov/opportunities/v2/search"
        self.api_key = self.config['sam_gov']['api_key']
    
    def _load_config(self, config_path: str):
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def test_api_connection(self):
        """Test basic API connectivity"""
        print("\n" + "="*80)
        print("TEST 1: Basic API Connection")
        print("="*80)
        
        try:
            # Simple test query - get any recent opportunities
            params = {
                'api_key': self.api_key,
                'limit': 1,
                'postedFrom': (datetime.now() - timedelta(days=7)).strftime('%m/%d/%Y'),
                'postedTo': datetime.now().strftime('%m/%d/%Y')
            }
            
            print(f"Testing connection to: {self.base_url}")
            print(f"API Key: {self.api_key[:10]}...{self.api_key[-5:]}")
            
            response = requests.get(self.base_url, params=params, timeout=30)
            
            print(f"\nResponse Status: {response.status_code}")
            
            if response.status_code == 200:
                print("✓ SUCCESS: API connection is working!")
                data = response.json()
                total = data.get('totalRecords', 0)
                print(f"✓ Total opportunities in SAM.gov (last 7 days): {total:,}")
                return True
            elif response.status_code == 401:
                print("✗ FAILED: Invalid API key")
                print("  → Check your API key in config.yaml")
                print("  → Get a new key at: https://open.gsa.gov/api/entity-api/")
                return False
            elif response.status_code == 403:
                print("✗ FAILED: Access forbidden")
                print("  → Your API key may not be activated yet")
                print("  → Check your email for activation link")
                return False
            else:
                print(f"✗ FAILED: Unexpected status code {response.status_code}")
                print(f"Response: {response.text[:500]}")
                return False
                
        except requests.exceptions.Timeout:
            print("✗ FAILED: Request timed out")
            print("  → SAM.gov may be slow or down")
            print("  → Try again in a few minutes")
            return False
        except requests.exceptions.ConnectionError:
            print("✗ FAILED: Cannot connect to SAM.gov")
            print("  → Check your internet connection")
            print("  → SAM.gov may be down")
            return False
        except Exception as e:
            print(f"✗ FAILED: {e}")
            return False
    
    def test_with_your_filters(self):
        """Test with your configured filters"""
        print("\n" + "="*80)
        print("TEST 2: Search with Your Configuration")
        print("="*80)
        
        config_search = self.config['sam_gov']['search']
        
        print("\nYour configuration:")
        print(f"  NAICS Codes: {self.config['company']['naics_codes']}")
        print(f"  Set-Asides: {self.config['company']['set_asides']}")
        print(f"  Value Range: ${config_search['value_range']['min']:,} - ${config_search['value_range']['max']:,}")
        print(f"  Lookback Days: {config_search['lookback_days']}")
        print(f"  Keywords: {config_search.get('keywords', [])}")
        
        # Test with your exact filters
        end_date = datetime.now()
        start_date = end_date - timedelta(days=config_search['lookback_days'])
        
        params = {
            'api_key': self.api_key,
            'postedFrom': start_date.strftime('%m/%d/%Y'),
            'postedTo': end_date.strftime('%m/%d/%Y'),
            'limit': 100
        }
        
        # Add NAICS codes
        naics_codes = self.config['company']['naics_codes']
        if naics_codes:
            params['ncode'] = ','.join(naics_codes)
        
        # Add set-asides
        set_asides = self.config['company']['set_asides']
        if set_asides:
            # Map our names to SAM.gov values
            sam_set_asides = []
            for sa in set_asides:
                if sa == 'small_business':
                    sam_set_asides.append('SBA')
                elif sa == '8a':
                    sam_set_asides.append('8A')
                elif sa == 'hubzone':
                    sam_set_asides.append('HZS')
                elif sa == 'wosb':
                    sam_set_asides.append('WOSB')
                elif sa == 'sdvosb':
                    sam_set_asides.append('SDVOSBC')
                else:
                    sam_set_asides.append(sa.upper())
            
            if sam_set_asides:
                params['typeOfSetAside'] = ','.join(sam_set_asides)
        
        print(f"\nSearching from {start_date.date()} to {end_date.date()}...")
        
        try:
            response = requests.get(self.base_url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('opportunitiesData', [])
                total = len(results)
                
                print(f"\n✓ Query successful!")
                print(f"✓ Found {total} opportunities with your filters")
                
                if total == 0:
                    print("\n⚠ WARNING: No opportunities found with your current filters")
                    print("\nTroubleshooting suggestions:")
                    print("  1. Try broadening your search (see TEST 3)")
                    print("  2. Check if your NAICS codes are correct")
                    print("  3. Try increasing lookback_days in config.yaml")
                    print("  4. Try removing set-aside filters temporarily")
                else:
                    print(f"\nSample opportunities found:")
                    for i, opp in enumerate(results[:3], 1):
                        print(f"\n  {i}. {opp.get('title', 'No title')[:60]}")
                        print(f"     Type: {opp.get('type')}")
                        print(f"     NAICS: {opp.get('naicsCode')}")
                        print(f"     Posted: {opp.get('postedDate')}")
                
                return total > 0
            else:
                print(f"✗ FAILED: Status {response.status_code}")
                print(f"Response: {response.text[:500]}")
                return False
                
        except Exception as e:
            print(f"✗ FAILED: {e}")
            return False
    
    def test_broadened_search(self):
        """Test with very broad filters to confirm opportunities exist"""
        print("\n" + "="*80)
        print("TEST 3: Broadened Search (No Filters)")
        print("="*80)
        
        print("Testing with minimal filters to confirm opportunities exist...")
        
        params = {
            'api_key': self.api_key,
            'postedFrom': (datetime.now() - timedelta(days=30)).strftime('%m/%d/%Y'),
            'postedTo': datetime.now().strftime('%m/%d/%Y'),
            'limit': 10
        }
        
        try:
            response = requests.get(self.base_url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                total_records = data.get('totalRecords', 0)
                results = data.get('opportunitiesData', [])
                
                print(f"\n✓ Total opportunities in SAM.gov (last 30 days): {total_records:,}")
                print(f"✓ Retrieved {len(results)} sample opportunities")
                
                if results:
                    print("\nSample opportunities (any NAICS, any set-aside):")
                    for i, opp in enumerate(results[:5], 1):
                        print(f"\n  {i}. {opp.get('title', 'No title')[:70]}")
                        print(f"     Type: {opp.get('type')}")
                        print(f"     NAICS: {opp.get('naicsCode')}")
                        print(f"     Set-Aside: {opp.get('typeOfSetAside', 'None')}")
                        print(f"     Posted: {opp.get('postedDate')}")
                
                return True
            else:
                print(f"✗ FAILED: Status {response.status_code}")
                return False
                
        except Exception as e:
            print(f"✗ FAILED: {e}")
            return False
    
    def test_specific_naics(self):
        """Test each NAICS code individually"""
        print("\n" + "="*80)
        print("TEST 4: Individual NAICS Code Testing")
        print("="*80)
        
        naics_codes = self.config['company']['naics_codes']
        
        print(f"Testing each of your {len(naics_codes)} NAICS codes individually...")
        
        results = {}
        
        for naics in naics_codes:
            params = {
                'api_key': self.api_key,
                'ncode': naics,
                'postedFrom': (datetime.now() - timedelta(days=30)).strftime('%m/%d/%Y'),
                'postedTo': datetime.now().strftime('%m/%d/%Y'),
                'limit': 5
            }
            
            try:
                response = requests.get(self.base_url, params=params, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    count = len(data.get('opportunitiesData', []))
                    results[naics] = count
                    
                    status = "✓" if count > 0 else "✗"
                    print(f"\n{status} NAICS {naics}: {count} opportunities")
                    
                    if count > 0:
                        sample = data['opportunitiesData'][0]
                        print(f"   Sample: {sample.get('title', 'No title')[:60]}")
                else:
                    print(f"✗ NAICS {naics}: Error {response.status_code}")
                    results[naics] = 0
                    
            except Exception as e:
                print(f"✗ NAICS {naics}: {e}")
                results[naics] = 0
        
        print("\n" + "-"*80)
        print("NAICS Code Summary:")
        total_found = sum(results.values())
        print(f"Total opportunities across all NAICS codes: {total_found}")
        
        if total_found == 0:
            print("\n⚠ WARNING: None of your NAICS codes returned opportunities")
            print("\nRecommendations:")
            print("  1. Verify your NAICS codes are correct")
            print("  2. Try more common NAICS codes like:")
            print("     - 541330 (Engineering Services)")
            print("     - 541512 (Computer Systems Design)")
            print("     - 541519 (Other Computer Related Services)")
            print("  3. Increase lookback_days to 30 or 60")
        
        return total_found > 0
    
    def test_opportunity_types(self):
        """Test what types of opportunities exist"""
        print("\n" + "="*80)
        print("TEST 5: Opportunity Types Available")
        print("="*80)
        
        params = {
            'api_key': self.api_key,
            'postedFrom': (datetime.now() - timedelta(days=30)).strftime('%m/%d/%Y'),
            'postedTo': datetime.now().strftime('%m/%d/%Y'),
            'limit': 100
        }
        
        try:
            response = requests.get(self.base_url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('opportunitiesData', [])
                
                # Count by type
                type_counts = {}
                for opp in results:
                    opp_type = opp.get('type', 'Unknown')
                    type_counts[opp_type] = type_counts.get(opp_type, 0) + 1
                
                print("\nOpportunity types in SAM.gov (last 30 days):")
                for opp_type, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
                    print(f"  {opp_type}: {count}")
                
                config_types = self.config['sam_gov']['search']['opportunity_types']
                print(f"\nYour configured types: {config_types}")
                
                # Check if any configured types have opportunities
                matching = sum(type_counts.get(t, 0) for t in config_types)
                print(f"Opportunities matching your types: {matching}")
                
                return True
            else:
                print(f"✗ FAILED: Status {response.status_code}")
                return False
                
        except Exception as e:
            print(f"✗ FAILED: {e}")
            return False
    
    def generate_recommendations(self):
        """Generate recommendations based on test results"""
        print("\n" + "="*80)
        print("RECOMMENDATIONS")
        print("="*80)
        
        print("\nBased on the diagnostic tests, here are some recommendations:")
        print("\n1. BROADEN YOUR SEARCH:")
        print("   - Increase lookback_days from 7 to 30 or 60")
        print("   - Add more NAICS codes")
        print("   - Remove or relax value_range filters")
        
        print("\n2. CHECK YOUR NAICS CODES:")
        print("   - Verify codes are 6 digits")
        print("   - Make sure they're relevant to federal contracting")
        print("   - Common codes that usually have opportunities:")
        print("     • 541330 - Engineering Services")
        print("     • 541512 - Computer Systems Design")
        print("     • 541519 - Other Computer Related Services")
        print("     • 541611 - Administrative Management")
        print("     • 541990 - All Other Professional Services")
        
        print("\n3. ADJUST FILTERS:")
        print("   - Try removing set-aside filters temporarily")
        print("   - Remove keyword filters to start broad")
        print("   - Adjust opportunity types (include more types)")
        
        print("\n4. TIMING:")
        print("   - Federal opportunities fluctuate by season")
        print("   - Try checking at different times")
        print("   - Some NAICS codes may have few active opportunities")
        
        print("\n5. VERIFY API KEY:")
        print("   - Make sure it's fully activated (check email)")
        print("   - Key should start with 'YOUR_API_KEY'")
        print("   - Get a new key if needed at: https://open.gsa.gov/api/entity-api/")
    
    def run_all_diagnostics(self):
        """Run all diagnostic tests"""
        print("\n" + "="*80)
        print("SAM.GOV API DIAGNOSTIC TOOL")
        print("="*80)
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        results = {
            'connection': self.test_api_connection(),
            'configured_search': self.test_with_your_filters(),
            'broadened_search': self.test_broadened_search(),
            'naics_individual': self.test_specific_naics(),
            'opportunity_types': self.test_opportunity_types()
        }
        
        self.generate_recommendations()
        
        print("\n" + "="*80)
        print("DIAGNOSTIC SUMMARY")
        print("="*80)
        
        print("\nTest Results:")
        for test, passed in results.items():
            status = "✓ PASS" if passed else "✗ FAIL"
            print(f"  {test}: {status}")
        
        if all(results.values()):
            print("\n✓ All tests passed! Your SAM.gov API is working correctly.")
            print("  If you're still not getting opportunities, try broadening your filters.")
        elif results['connection']:
            print("\n⚠ API connection works, but no opportunities found with your filters.")
            print("  Review the recommendations above to adjust your search criteria.")
        else:
            print("\n✗ API connection failed. Check your API key and internet connection.")
        
        print("\n" + "="*80)


def main():
    """Run diagnostics"""
    diagnostic = SAMDiagnostic()
    diagnostic.run_all_diagnostics()


if __name__ == "__main__":
    main()
