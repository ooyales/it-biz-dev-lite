#!/usr/bin/env python3
"""
FPDS Intelligence Module
Provides incumbent contractor and pricing intelligence from Federal Procurement Data System
"""

import requests
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import xml.etree.ElementTree as ET
from urllib.parse import urlencode


class FPDSIntelligence:
    """Query FPDS for competitive and pricing intelligence"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.base_url = "https://www.fpds.gov/ezsearch/FEEDS/ATOM"
        self.logger = logging.getLogger(__name__)
        
    def find_incumbent_contract(self, 
                               agency_name: str,
                               naics_code: str,
                               keywords: List[str] = None,
                               lookback_years: int = 3) -> Optional[Dict[str, Any]]:
        """
        Find the most recent contract for similar work (likely the incumbent)
        
        Args:
            agency_name: Agency name from SAM.gov opportunity
            naics_code: NAICS code
            keywords: Keywords from opportunity description
            lookback_years: How many years back to search
            
        Returns:
            Dictionary with incumbent contract details or None
        """
        try:
            # Build FPDS query
            start_date = (datetime.now() - timedelta(days=365*lookback_years)).strftime('%Y/%m/%d')
            end_date = datetime.now().strftime('%Y/%m/%d')
            
            # FPDS query parameters
            params = {
                'AGENCY_NAME': agency_name,
                'NAICS_CODE': naics_code,
                'LAST_MOD_DATE': f"[{start_date},{end_date}]",
                'sortBy': '-SIGNED_DATE',  # Most recent first
                'max': '10'  # Get top 10 to analyze
            }
            
            # Add keyword search if provided
            if keywords:
                # FPDS uses PRODUCT_OR_SERVICE_CODE_DESCRIPTION for text search
                params['DESCRIPTION'] = ' '.join(keywords[:3])  # First 3 keywords
            
            query_string = urlencode(params)
            url = f"{self.base_url}?{query_string}"
            
            self.logger.info(f"Querying FPDS for incumbent: {agency_name}, NAICS {naics_code}")
            
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            # Parse ATOM feed
            root = ET.fromstring(response.content)
            namespace = {'atom': 'http://www.w3.org/2005/Atom'}
            
            entries = root.findall('atom:entry', namespace)
            
            if not entries:
                self.logger.info("No incumbent contracts found")
                return None
            
            # Parse the most recent entry (most likely incumbent)
            incumbent = self._parse_fpds_entry(entries[0], namespace)
            
            self.logger.info(f"Found incumbent: {incumbent.get('contractor_name')}")
            return incumbent
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error querying FPDS: {e}")
            return None
        except ET.ParseError as e:
            self.logger.error(f"Error parsing FPDS response: {e}")
            return None
    
    def get_pricing_intelligence(self,
                                naics_code: str,
                                agency_name: str = None,
                                lookback_years: int = 3) -> Dict[str, Any]:
        """
        Get pricing intelligence for similar contracts
        
        Args:
            naics_code: NAICS code
            agency_name: Optional agency filter
            lookback_years: Years of history to analyze
            
        Returns:
            Dictionary with pricing statistics
        """
        try:
            start_date = (datetime.now() - timedelta(days=365*lookback_years)).strftime('%Y/%m/%d')
            end_date = datetime.now().strftime('%Y/%m/%d')
            
            params = {
                'NAICS_CODE': naics_code,
                'LAST_MOD_DATE': f"[{start_date},{end_date}]",
                'max': '100'  # Get more for statistical analysis
            }
            
            if agency_name:
                params['AGENCY_NAME'] = agency_name
            
            query_string = urlencode(params)
            url = f"{self.base_url}?{query_string}"
            
            self.logger.info(f"Querying FPDS for pricing data: NAICS {naics_code}")
            
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            root = ET.fromstring(response.content)
            namespace = {'atom': 'http://www.w3.org/2005/Atom'}
            
            entries = root.findall('atom:entry', namespace)
            
            if not entries:
                return {
                    'sample_size': 0,
                    'message': 'No historical contracts found'
                }
            
            # Extract award amounts
            awards = []
            for entry in entries:
                contract = self._parse_fpds_entry(entry, namespace)
                if contract.get('award_amount'):
                    try:
                        amount = float(contract['award_amount'])
                        if amount > 0:  # Skip $0 contracts
                            awards.append({
                                'amount': amount,
                                'contractor': contract.get('contractor_name'),
                                'date': contract.get('signed_date'),
                                'description': contract.get('description', '')[:100]
                            })
                    except (ValueError, TypeError):
                        continue
            
            if not awards:
                return {
                    'sample_size': len(entries),
                    'message': 'No valid pricing data available'
                }
            
            # Calculate statistics
            amounts = [a['amount'] for a in awards]
            amounts.sort()
            
            stats = {
                'sample_size': len(awards),
                'average': sum(amounts) / len(amounts),
                'median': amounts[len(amounts)//2],
                'min': amounts[0],
                'max': amounts[-1],
                'recent_awards': awards[:5],  # 5 most recent
                'percentile_25': amounts[len(amounts)//4],
                'percentile_75': amounts[3*len(amounts)//4]
            }
            
            # Calculate trend (comparing first half to second half chronologically)
            if len(awards) >= 10:
                mid_point = len(awards) // 2
                early_avg = sum(a['amount'] for a in awards[mid_point:]) / mid_point
                recent_avg = sum(a['amount'] for a in awards[:mid_point]) / mid_point
                
                if early_avg > 0:
                    trend_pct = ((recent_avg - early_avg) / early_avg) * 100
                    stats['trend'] = {
                        'direction': 'increasing' if trend_pct > 5 else 'decreasing' if trend_pct < -5 else 'stable',
                        'percent_change': trend_pct
                    }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting pricing intelligence: {e}")
            return {'error': str(e)}
    
    def get_agency_spending_patterns(self,
                                    agency_name: str,
                                    naics_code: str,
                                    lookback_years: int = 3) -> Dict[str, Any]:
        """
        Analyze agency's spending patterns in a NAICS code
        
        Returns:
            Dictionary with spending pattern analysis
        """
        try:
            start_date = (datetime.now() - timedelta(days=365*lookback_years)).strftime('%Y/%m/%d')
            end_date = datetime.now().strftime('%Y/%m/%d')
            
            params = {
                'AGENCY_NAME': agency_name,
                'NAICS_CODE': naics_code,
                'LAST_MOD_DATE': f"[{start_date},{end_date}]",
                'max': '100'
            }
            
            query_string = urlencode(params)
            url = f"{self.base_url}?{query_string}"
            
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            root = ET.fromstring(response.content)
            namespace = {'atom': 'http://www.w3.org/2005/Atom'}
            entries = root.findall('atom:entry', namespace)
            
            if not entries:
                return {'message': 'No agency spending data found'}
            
            # Analyze patterns
            contractors = {}
            set_asides = {}
            total_value = 0
            
            for entry in entries:
                contract = self._parse_fpds_entry(entry, namespace)
                
                # Count by contractor
                contractor = contract.get('contractor_name', 'Unknown')
                contractors[contractor] = contractors.get(contractor, 0) + 1
                
                # Count by set-aside type
                set_aside = contract.get('set_aside_type', 'None')
                set_asides[set_aside] = set_asides.get(set_aside, 0) + 1
                
                # Sum total value
                try:
                    amount = float(contract.get('award_amount', 0))
                    total_value += amount
                except (ValueError, TypeError):
                    pass
            
            # Find top contractors
            top_contractors = sorted(
                contractors.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]
            
            return {
                'total_contracts': len(entries),
                'total_value': total_value,
                'top_contractors': [
                    {'name': name, 'contract_count': count}
                    for name, count in top_contractors
                ],
                'set_aside_breakdown': set_asides,
                'average_contract_value': total_value / len(entries) if entries else 0
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing agency spending: {e}")
            return {'error': str(e)}
    
    def _parse_fpds_entry(self, entry: ET.Element, namespace: Dict) -> Dict[str, Any]:
        """Parse an FPDS ATOM entry into a dictionary"""
        
        def get_text(element, tag, ns=namespace):
            """Safely get text from XML element"""
            elem = element.find(f"atom:{tag}", ns)
            return elem.text if elem is not None else None
        
        # FPDS ATOM feeds contain contract data in the content section
        # This is a simplified parser - actual FPDS data is more complex
        content = entry.find('atom:content', namespace)
        
        contract = {
            'title': get_text(entry, 'title'),
            'updated': get_text(entry, 'updated'),
        }
        
        # If content exists, try to parse contract details
        if content is not None:
            # Note: Actual FPDS content is in a nested structure
            # This is a simplified version - you may need to adjust based on actual responses
            contract.update({
                'contractor_name': 'See FPDS link',  # Would be extracted from content
                'award_amount': None,  # Would be extracted from content
                'signed_date': None,  # Would be extracted from content
                'description': get_text(entry, 'summary'),
                'link': entry.find('atom:link', namespace).get('href') if entry.find('atom:link', namespace) is not None else None
            })
        
        return contract
    
    def get_contract_expirations(self,
                                naics_code: str,
                                agency_name: str = None,
                                months_ahead: int = 12) -> List[Dict[str, Any]]:
        """
        Find contracts expiring soon (recompete opportunities)
        
        Args:
            naics_code: NAICS code to search
            agency_name: Optional agency filter
            months_ahead: Look ahead window
            
        Returns:
            List of contracts expiring in the window
        """
        # This would require querying for contracts and checking their end dates
        # FPDS provides CURRENT_COMPLETION_DATE field
        
        self.logger.info("Contract expiration tracking requires FPDS-NG Data Warehouse access")
        self.logger.info("Recommend manual tracking or GovWin subscription for this feature")
        
        return []


def format_pricing_report(pricing_data: Dict[str, Any]) -> str:
    """Format pricing intelligence into readable report"""
    
    if 'error' in pricing_data or pricing_data.get('sample_size', 0) == 0:
        return "No pricing intelligence available"
    
    report = f"""
PRICING INTELLIGENCE (based on {pricing_data['sample_size']} similar contracts)

Award Amount Statistics:
  Average:    ${pricing_data['average']:,.2f}
  Median:     ${pricing_data['median']:,.2f}
  Range:      ${pricing_data['min']:,.2f} - ${pricing_data['max']:,.2f}
  25th %ile:  ${pricing_data.get('percentile_25', 0):,.2f}
  75th %ile:  ${pricing_data.get('percentile_75', 0):,.2f}
"""
    
    if 'trend' in pricing_data:
        trend = pricing_data['trend']
        report += f"\nTrend: {trend['direction'].upper()} ({trend['percent_change']:+.1f}%)\n"
    
    if 'recent_awards' in pricing_data:
        report += "\nRecent Similar Awards:\n"
        for award in pricing_data['recent_awards'][:3]:
            report += f"  • ${award['amount']:,.2f} - {award['contractor']} ({award['date']})\n"
    
    return report


def format_incumbent_report(incumbent: Dict[str, Any]) -> str:
    """Format incumbent intelligence into readable report"""
    
    if not incumbent:
        return "No incumbent contract found"
    
    report = f"""
INCUMBENT INTELLIGENCE

Current Contractor: {incumbent.get('contractor_name', 'Unknown')}
Contract Award: {incumbent.get('signed_date', 'Unknown')}
Award Amount: ${incumbent.get('award_amount', 'Unknown')}
Description: {incumbent.get('description', 'N/A')[:200]}

FPDS Link: {incumbent.get('link', 'N/A')}
"""
    
    return report


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    fpds = FPDSIntelligence()
    
    # Example: Find incumbent for a DoD IT Services contract
    incumbent = fpds.find_incumbent_contract(
        agency_name="DEPARTMENT OF DEFENSE",
        naics_code="541512",
        keywords=["cloud", "infrastructure"]
    )
    
    print(format_incumbent_report(incumbent))
    
    # Example: Get pricing intelligence
    pricing = fpds.get_pricing_intelligence(
        naics_code="541512",
        agency_name="DEPARTMENT OF DEFENSE"
    )
    
    print(format_pricing_report(pricing))
