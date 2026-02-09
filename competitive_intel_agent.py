#!/usr/bin/env python3
"""
Competitive Intelligence Agent - FIXED
Gathers competitive intelligence for federal contracting opportunities
"""

import logging
from datetime import datetime
from fpds_intel import FPDSIntel  # Fixed import

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CompetitiveIntelAgent:
    """Agent to gather competitive intelligence"""
    
    def __init__(self):
        self.fpds = FPDSIntel()
    
    def analyze_opportunity(self, opportunity_data):
        """
        Comprehensive competitive analysis for an opportunity
        
        Args:
            opportunity_data: Dict with opportunity details
        
        Returns:
            Dict with competitive intelligence
        """
        notice_id = opportunity_data.get('noticeId')
        naics_code = opportunity_data.get('naicsCode')
        agency = opportunity_data.get('fullParentPathName', '')
        
        logger.info(f"Analyzing opportunity {notice_id}")
        
        intel = {
            'notice_id': notice_id,
            'timestamp': datetime.now().isoformat(),
            'incumbent': None,
            'incumbent_profile': None,
            'pricing_intelligence': None,
            'market_trends': None,
            'competitive_assessment': None
        }
        
        # Get pricing intelligence
        if naics_code:
            try:
                logger.info(f"Getting pricing intelligence for NAICS {naics_code}")
                intel['pricing_intelligence'] = self.fpds.get_pricing_intelligence(
                    naics_code,
                    agency=agency
                )
            except Exception as e:
                logger.error(f"Error getting pricing intel: {e}")
        
        # Get market trends
        if naics_code:
            try:
                logger.info(f"Getting market trends for NAICS {naics_code}")
                intel['market_trends'] = self.fpds.get_market_trends(naics_code)
            except Exception as e:
                logger.error(f"Error getting market trends: {e}")
        
        # Competitive assessment
        intel['competitive_assessment'] = self._assess_competitive_position(
            opportunity_data,
            intel
        )
        
        return intel
    
    def _assess_competitive_position(self, opportunity_data, intel):
        """
        Assess competitive position and calculate win probability
        """
        import random
        
        # Base win probability on various factors
        base_probability = 50
        
        # Adjust based on contract size (sweet spot analysis)
        contract_value = self._get_contract_value(opportunity_data)
        if 250000 <= contract_value <= 5000000:
            base_probability += 10  # Sweet spot for small business
        elif contract_value > 10000000:
            base_probability -= 10  # Harder to compete on large contracts
        
        # Adjust based on set-aside
        set_aside = opportunity_data.get('typeOfSetAside')
        if set_aside in ['Small Business', '8(a)', 'SDVOSB', 'WOSB']:
            base_probability += 15  # Advantage if you qualify
        
        # Adjust based on incumbent strength
        incumbent_profile = intel.get('incumbent_profile')
        if incumbent_profile:
            strength = incumbent_profile.get('strength_rating', 'moderate')
            if strength == 'weak':
                base_probability += 10
            elif strength == 'strong':
                base_probability -= 15
        
        # Cap probability
        win_probability = max(20, min(85, base_probability))
        
        # Determine competitive position
        if win_probability >= 65:
            position = 'Strong'
        elif win_probability >= 45:
            position = 'Moderate'
        else:
            position = 'Weak'
        
        # Generate strategy recommendations
        strategies = self._generate_strategies(
            opportunity_data,
            intel,
            win_probability
        )
        
        return {
            'win_probability': win_probability,
            'competitive_position': position,
            'strategy_recommendations': strategies,
            'key_success_factors': [
                'Strong past performance',
                'Competitive pricing',
                'Technical approach',
                'Key personnel qualifications'
            ]
        }
    
    def _generate_strategies(self, opportunity_data, intel, win_probability):
        """Generate strategic recommendations"""
        
        strategies = []
        
        # Universal strategies
        strategies.append('Emphasize past performance in similar projects')
        strategies.append('Highlight cost-effective solution')
        
        # Based on set-aside
        set_aside = opportunity_data.get('typeOfSetAside')
        if set_aside:
            strategies.append(f'Leverage {set_aside} status')
        else:
            strategies.append('Consider teaming with small business')
        
        # Based on win probability
        if win_probability < 50:
            strategies.append('Focus on technical differentiation')
            strategies.append('Consider more aggressive pricing')
        
        # Based on incumbent
        incumbent_profile = intel.get('incumbent_profile')
        if incumbent_profile:
            strength = incumbent_profile.get('strength_rating')
            if strength == 'strong':
                strategies.append('Highlight innovation and new approaches')
            else:
                strategies.append('Emphasize stability and proven methods')
        
        # Relationship building
        strategies.append('Build relationships with key decision makers')
        strategies.append('Attend industry days and pre-solicitation events')
        
        return strategies[:5]  # Return top 5 strategies
    
    def _get_contract_value(self, opportunity_data):
        """Extract contract value from opportunity data"""
        try:
            award = opportunity_data.get('award', {})
            if isinstance(award, dict):
                amount = award.get('amount', '0')
            else:
                amount = '0'
            
            # Clean and convert
            amount_str = str(amount).replace('$', '').replace(',', '').strip()
            return float(amount_str) if amount_str else 0
        except:
            return 0


def format_intel_report(intel_data):
    """Format intelligence data as readable report"""
    
    report = []
    report.append("\n" + "="*70)
    report.append("COMPETITIVE INTELLIGENCE REPORT")
    report.append("="*70)
    
    # Pricing Intelligence
    pricing = intel_data.get('pricing_intelligence')
    if pricing:
        report.append("\n📊 PRICING INTELLIGENCE")
        report.append("-" * 70)
        report.append(f"Similar Contracts:     {pricing['similar_contracts_found']}")
        report.append(f"Average Award Value:   ${pricing['average_award_value']:,}")
        report.append(f"Price Range:           ${pricing['price_range']['min']:,} - ${pricing['price_range']['max']:,}")
        report.append(f"Trend:                 {pricing['trend'].upper()}")
    
    # Market Trends
    trends = intel_data.get('market_trends')
    if trends:
        report.append("\n📈 MARKET TRENDS")
        report.append("-" * 70)
        report.append(f"NAICS Code:            {trends['naics_code']}")
        report.append(f"Direction:             {trends['trend_direction'].upper()}")
        report.append(f"Growth Rate:           {trends['growth_rate_percent']:+.1f}%")
        report.append(f"Total Spending (3yr):  ${trends['total_spending_3yr']:,}")
    
    # Incumbent
    incumbent = intel_data.get('incumbent_profile')
    if incumbent:
        report.append("\n🏢 INCUMBENT PROFILE")
        report.append("-" * 70)
        report.append(f"Company:               {incumbent['contractor_name']}")
        report.append(f"3-Year Revenue:        ${incumbent['total_contract_value_3yr']:,}")
        report.append(f"Contract Count:        {incumbent['contract_count_3yr']}")
        report.append(f"Strength Rating:       {incumbent['strength_rating'].upper()}")
    
    # Competitive Assessment
    assessment = intel_data.get('competitive_assessment')
    if assessment:
        report.append("\n⚔️  COMPETITIVE ASSESSMENT")
        report.append("-" * 70)
        report.append(f"Win Probability:       {assessment['win_probability']}%")
        report.append(f"Competitive Position:  {assessment['competitive_position'].upper()}")
        report.append("\nStrategy Recommendations:")
        for i, strategy in enumerate(assessment['strategy_recommendations'], 1):
            report.append(f"  {i}. {strategy}")
    
    report.append("\n" + "="*70 + "\n")
    
    return "\n".join(report)


def test_competitive_intel():
    """Test competitive intelligence agent"""
    
    print("\n" + "="*70)
    print("COMPETITIVE INTELLIGENCE AGENT - TEST")
    print("="*70 + "\n")
    
    # Sample opportunity
    opportunity = {
        'noticeId': 'TEST-2026-001',
        'title': 'Cloud Infrastructure Services',
        'naicsCode': '541512',
        'fullParentPathName': 'Department of Defense',
        'typeOfSetAside': 'Small Business',
        'award': {
            'amount': '2500000'
        }
    }
    
    # Analyze
    agent = CompetitiveIntelAgent()
    print("Analyzing opportunity...")
    intel = agent.analyze_opportunity(opportunity)
    
    # Display report
    report = format_intel_report(intel)
    print(report)
    
    print("✅ Test Complete\n")

CompetitiveIntelligenceAgent = CompetitiveIntelAgent
generate_competitive_intelligence_report = format_intel_report
if __name__ == "__main__":
    test_competitive_intel()
