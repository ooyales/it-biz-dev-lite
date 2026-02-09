#!/usr/bin/env python3
"""
USAspending Intelligence Module
Provides market intelligence, teaming partner discovery, and spending analysis
"""

import requests
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import json


class USAspendingIntelligence:
    """Query USAspending.gov for market and teaming intelligence"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.base_url = "https://api.usaspending.gov/api/v2"
        self.logger = logging.getLogger(__name__)
    
    def get_contractor_profile(self, contractor_name: str) -> Dict[str, Any]:
        """
        Get comprehensive profile of a contractor (competitor or potential partner)
        
        Args:
            contractor_name: Name of contractor
            
        Returns:
            Dictionary with contractor intelligence
        """
        try:
            # Search for contractor
            url = f"{self.base_url}/search/spending_by_award/"
            
            payload = {
                "filters": {
                    "recipient_search_text": [contractor_name],
                    "award_type_codes": ["A", "B", "C", "D"],  # Contract types
                    "time_period": [
                        {
                            "start_date": (datetime.now() - timedelta(days=1095)).strftime('%Y-%m-%d'),
                            "end_date": datetime.now().strftime('%Y-%m-%d')
                        }
                    ]
                },
                "fields": ["Award ID", "Recipient Name", "Award Amount", "Award Type"],
                "limit": 100,
                "page": 1
            }
            
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            results = data.get('results', [])
            
            if not results:
                return {'contractor_name': contractor_name, 'message': 'No data found'}
            
            # Aggregate data
            total_value = sum(float(r.get('Award Amount', 0)) for r in results)
            award_count = len(results)
            
            # Get agency breakdown
            agencies = {}
            for result in results:
                agency = result.get('Awarding Agency', 'Unknown')
                agencies[agency] = agencies.get(agency, 0) + 1
            
            top_agencies = sorted(agencies.items(), key=lambda x: x[1], reverse=True)[:5]
            
            return {
                'contractor_name': contractor_name,
                'total_contract_value_3yr': total_value,
                'contract_count_3yr': award_count,
                'average_contract_value': total_value / award_count if award_count else 0,
                'top_agencies': [{'name': name, 'count': count} for name, count in top_agencies],
                'recent_awards': results[:5]
            }
            
        except Exception as e:
            self.logger.error(f"Error getting contractor profile: {e}")
            return {'error': str(e)}
    
    def find_teaming_partners(self,
                             naics_code: str,
                             capability_keywords: List[str] = None,
                             small_business_only: bool = False,
                             min_revenue: float = 1000000,
                             max_revenue: float = 50000000) -> List[Dict[str, Any]]:
        """
        Find potential teaming partners based on capabilities and size
        
        Args:
            naics_code: NAICS code for capability area
            capability_keywords: Specific capabilities to look for
            small_business_only: Filter to small businesses only
            min_revenue: Minimum 3-year government revenue
            max_revenue: Maximum 3-year government revenue
            
        Returns:
            List of potential partners with intelligence
        """
        try:
            url = f"{self.base_url}/search/spending_by_award/"
            
            payload = {
                "filters": {
                    "naics_codes": [naics_code],
                    "award_type_codes": ["A", "B", "C", "D"],
                    "time_period": [
                        {
                            "start_date": (datetime.now() - timedelta(days=1095)).strftime('%Y-%m-%d'),
                            "end_date": datetime.now().strftime('%Y-%m-%d')
                        }
                    ]
                },
                "fields": ["Recipient Name", "Award Amount", "Award Type"],
                "limit": 200,  # Get a good sample
                "page": 1
            }
            
            if small_business_only:
                payload["filters"]["recipient_type_names"] = ["small_business"]
            
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            results = data.get('results', [])
            
            # Aggregate by contractor
            contractors = {}
            for result in results:
                name = result.get('Recipient Name', 'Unknown')
                amount = float(result.get('Award Amount', 0))
                
                if name not in contractors:
                    contractors[name] = {
                        'name': name,
                        'total_value': 0,
                        'award_count': 0,
                        'awards': []
                    }
                
                contractors[name]['total_value'] += amount
                contractors[name]['award_count'] += 1
                contractors[name]['awards'].append(result)
            
            # Filter by revenue range and sort
            partners = []
            for contractor in contractors.values():
                if min_revenue <= contractor['total_value'] <= max_revenue:
                    contractor['average_award'] = contractor['total_value'] / contractor['award_count']
                    partners.append(contractor)
            
            partners.sort(key=lambda x: x['total_value'], reverse=True)
            
            return partners[:20]  # Top 20 candidates
            
        except Exception as e:
            self.logger.error(f"Error finding teaming partners: {e}")
            return []
    
    def get_prime_sub_relationships(self, prime_contractor: str) -> List[Dict[str, Any]]:
        """
        Find subcontractors that work with a prime contractor
        
        Args:
            prime_contractor: Name of prime contractor
            
        Returns:
            List of subcontractors and their relationship details
        """
        try:
            # USAspending API endpoint for subawards
            url = f"{self.base_url}/subawards/"
            
            payload = {
                "filters": {
                    "prime_award_recipient_search_text": [prime_contractor],
                    "time_period": [
                        {
                            "start_date": (datetime.now() - timedelta(days=1095)).strftime('%Y-%m-%d'),
                            "end_date": datetime.now().strftime('%Y-%m-%d')
                        }
                    ]
                },
                "limit": 100
            }
            
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            results = data.get('results', [])
            
            # Aggregate subcontractors
            subs = {}
            for result in results:
                sub_name = result.get('recipient_name', 'Unknown')
                sub_amount = float(result.get('amount', 0))
                
                if sub_name not in subs:
                    subs[sub_name] = {
                        'name': sub_name,
                        'total_subaward_value': 0,
                        'subaward_count': 0
                    }
                
                subs[sub_name]['total_subaward_value'] += sub_amount
                subs[sub_name]['subaward_count'] += 1
            
            sub_list = list(subs.values())
            sub_list.sort(key=lambda x: x['total_subaward_value'], reverse=True)
            
            return sub_list
            
        except Exception as e:
            self.logger.error(f"Error getting prime-sub relationships: {e}")
            return []
    
    def get_market_trends(self,
                         naics_code: str,
                         agency_name: str = None,
                         years: int = 3) -> Dict[str, Any]:
        """
        Analyze market trends for a NAICS code
        
        Args:
            naics_code: NAICS code to analyze
            agency_name: Optional agency filter
            years: Number of years to analyze
            
        Returns:
            Dictionary with trend analysis
        """
        try:
            url = f"{self.base_url}/search/spending_over_time/"
            
            filters = {
                "naics_codes": [naics_code],
                "award_type_codes": ["A", "B", "C", "D"]
            }
            
            if agency_name:
                filters["agencies"] = [{"type": "awarding", "tier": "toptier", "name": agency_name}]
            
            payload = {
                "filters": filters,
                "group": "fiscal_year",
                "order": "desc"
            }
            
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            results = data.get('results', [])
            
            if not results:
                return {'message': 'No trend data available'}
            
            # Calculate year-over-year trends
            years_data = {}
            for result in results:
                year = result.get('time_period', {}).get('fiscal_year')
                amount = float(result.get('aggregated_amount', 0))
                years_data[year] = amount
            
            # Calculate trend
            sorted_years = sorted(years_data.keys())
            if len(sorted_years) >= 2:
                oldest_year_amount = years_data[sorted_years[0]]
                newest_year_amount = years_data[sorted_years[-1]]
                
                if oldest_year_amount > 0:
                    growth_rate = ((newest_year_amount - oldest_year_amount) / oldest_year_amount) * 100
                else:
                    growth_rate = 0
                
                trend_direction = 'increasing' if growth_rate > 10 else 'decreasing' if growth_rate < -10 else 'stable'
            else:
                growth_rate = 0
                trend_direction = 'insufficient_data'
            
            return {
                'naics_code': naics_code,
                'agency': agency_name or 'All Agencies',
                'years_analyzed': len(sorted_years),
                'yearly_spending': years_data,
                'total_spending': sum(years_data.values()),
                'average_annual_spending': sum(years_data.values()) / len(years_data) if years_data else 0,
                'trend_direction': trend_direction,
                'growth_rate_percent': growth_rate
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing market trends: {e}")
            return {'error': str(e)}
    
    def find_similar_companies(self,
                              your_naics_codes: List[str],
                              your_size_range: tuple = (1000000, 50000000)) -> List[Dict[str, Any]]:
        """
        Find companies similar to yours (potential competitors or partners)
        
        Args:
            your_naics_codes: Your NAICS codes
            your_size_range: Your 3-year revenue range (min, max)
            
        Returns:
            List of similar companies
        """
        try:
            all_companies = []
            
            for naics in your_naics_codes:
                url = f"{self.base_url}/search/spending_by_award/"
                
                payload = {
                    "filters": {
                        "naics_codes": [naics],
                        "award_type_codes": ["A", "B", "C", "D"],
                        "time_period": [
                            {
                                "start_date": (datetime.now() - timedelta(days=1095)).strftime('%Y-%m-%d'),
                                "end_date": datetime.now().strftime('%Y-%m-%d')
                            }
                        ]
                    },
                    "limit": 200
                }
                
                response = requests.post(url, json=payload, timeout=30)
                response.raise_for_status()
                data = response.json()
                
                results = data.get('results', [])
                
                # Aggregate by company
                for result in results:
                    name = result.get('Recipient Name', 'Unknown')
                    amount = float(result.get('Award Amount', 0))
                    
                    # Find or create company entry
                    company = next((c for c in all_companies if c['name'] == name), None)
                    if not company:
                        company = {
                            'name': name,
                            'total_value': 0,
                            'naics_codes': set(),
                            'award_count': 0
                        }
                        all_companies.append(company)
                    
                    company['total_value'] += amount
                    company['naics_codes'].add(naics)
                    company['award_count'] += 1
            
            # Filter by size range
            min_size, max_size = your_size_range
            similar = [
                c for c in all_companies
                if min_size <= c['total_value'] <= max_size
            ]
            
            # Convert sets to lists for JSON serialization
            for company in similar:
                company['naics_codes'] = list(company['naics_codes'])
                company['naics_overlap'] = len(company['naics_codes'])
            
            # Sort by revenue
            similar.sort(key=lambda x: x['total_value'], reverse=True)
            
            return similar[:30]  # Top 30
            
        except Exception as e:
            self.logger.error(f"Error finding similar companies: {e}")
            return []


def format_contractor_profile(profile: Dict[str, Any]) -> str:
    """Format contractor profile into readable report"""
    
    if 'error' in profile or 'message' in profile:
        return f"Contractor Profile: {profile.get('message', profile.get('error'))}"
    
    report = f"""
CONTRACTOR PROFILE: {profile['contractor_name']}

3-Year Government Revenue: ${profile['total_contract_value_3yr']:,.2f}
Contract Count: {profile['contract_count_3yr']}
Average Contract Value: ${profile['average_contract_value']:,.2f}

Top Customer Agencies:
"""
    
    for agency in profile.get('top_agencies', [])[:5]:
        report += f"  • {agency['name']}: {agency['count']} contracts\n"
    
    return report


def format_teaming_recommendations(partners: List[Dict[str, Any]]) -> str:
    """Format teaming partner recommendations"""
    
    if not partners:
        return "No teaming partners found matching criteria"
    
    report = f"\nTEAMING PARTNER RECOMMENDATIONS ({len(partners)} candidates)\n\n"
    
    for i, partner in enumerate(partners[:10], 1):
        report += f"{i}. {partner['name']}\n"
        report += f"   3-Yr Gov Revenue: ${partner['total_value']:,.2f}\n"
        report += f"   Contract Count: {partner['award_count']}\n"
        report += f"   Avg Contract: ${partner['average_award']:,.2f}\n\n"
    
    return report


def format_market_trends(trends: Dict[str, Any]) -> str:
    """Format market trend analysis"""
    
    if 'error' in trends or 'message' in trends:
        return f"Market Trends: {trends.get('message', trends.get('error'))}"
    
    report = f"""
MARKET TREND ANALYSIS

NAICS: {trends['naics_code']}
Agency: {trends['agency']}
Years Analyzed: {trends['years_analyzed']}

Total Spending: ${trends['total_spending']:,.2f}
Average Annual: ${trends['average_annual_spending']:,.2f}

Trend: {trends['trend_direction'].upper()}
Growth Rate: {trends['growth_rate_percent']:+.1f}%

Yearly Breakdown:
"""
    
    for year, amount in sorted(trends.get('yearly_spending', {}).items()):
        report += f"  FY{year}: ${amount:,.2f}\n"
    
    return report


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    usa = USAspendingIntelligence()
    
    # Example: Get competitor profile
    profile = usa.get_contractor_profile("Booz Allen Hamilton")
    print(format_contractor_profile(profile))
    
    # Example: Find teaming partners
    partners = usa.find_teaming_partners(
        naics_code="541512",
        small_business_only=True,
        min_revenue=1000000,
        max_revenue=20000000
    )
    print(format_teaming_recommendations(partners))
    
    # Example: Market trends
    trends = usa.get_market_trends(
        naics_code="541512",
        agency_name="Department of Defense"
    )
    print(format_market_trends(trends))
