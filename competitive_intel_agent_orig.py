#!/usr/bin/env python3
"""
Enhanced Competitive Intelligence Agent
Integrates FPDS and USAspending data for comprehensive competitive analysis
"""

import logging
from typing import Dict, Any, List
from fpds_intel import FPDSIntelligence, format_incumbent_report, format_pricing_report
from usaspending_intel import (
    USAspendingIntelligence, 
    format_contractor_profile,
    format_market_trends,
    format_teaming_recommendations
)


class CompetitiveIntelligenceAgent:
    """
    Advanced competitive intelligence combining multiple data sources
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.fpds = FPDSIntelligence(config)
        self.usaspending = USAspendingIntelligence(config)
        self.logger = logging.getLogger(__name__)
    
    def analyze_opportunity_competitiveness(self,
                                           opportunity: Dict[str, Any],
                                           your_company_profile: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Complete competitive analysis for an opportunity
        
        Args:
            opportunity: Opportunity data from SAM.gov
            your_company_profile: Your company's stats for comparison
            
        Returns:
            Comprehensive competitive intelligence package
        """
        self.logger.info(f"Running competitive intelligence for: {opportunity.get('title')}")
        
        # Extract key data from opportunity
        agency_name = self._extract_agency_name(opportunity)
        naics_code = opportunity.get('naicsCode', '')
        keywords = self._extract_keywords(opportunity)
        
        analysis = {
            'opportunity_id': opportunity.get('noticeId'),
            'title': opportunity.get('title'),
            'analysis_timestamp': None
        }
        
        # Step 1: Find incumbent
        self.logger.info("Step 1: Identifying incumbent contractor...")
        incumbent = self.fpds.find_incumbent_contract(
            agency_name=agency_name,
            naics_code=naics_code,
            keywords=keywords
        )
        analysis['incumbent'] = incumbent
        
        # Step 2: Get pricing intelligence
        self.logger.info("Step 2: Gathering pricing intelligence...")
        pricing = self.fpds.get_pricing_intelligence(
            naics_code=naics_code,
            agency_name=agency_name
        )
        analysis['pricing_intelligence'] = pricing
        
        # Step 3: Analyze incumbent (if found)
        if incumbent and incumbent.get('contractor_name'):
            self.logger.info("Step 3: Profiling incumbent contractor...")
            incumbent_profile = self.usaspending.get_contractor_profile(
                incumbent['contractor_name']
            )
            analysis['incumbent_profile'] = incumbent_profile
            
            # Get incumbent's teaming partners
            subs = self.usaspending.get_prime_sub_relationships(
                incumbent['contractor_name']
            )
            analysis['incumbent_team'] = subs
        
        # Step 4: Market trends
        self.logger.info("Step 4: Analyzing market trends...")
        market_trends = self.usaspending.get_market_trends(
            naics_code=naics_code,
            agency_name=agency_name
        )
        analysis['market_trends'] = market_trends
        
        # Step 5: Agency spending patterns
        self.logger.info("Step 5: Analyzing agency spending patterns...")
        agency_patterns = self.fpds.get_agency_spending_patterns(
            agency_name=agency_name,
            naics_code=naics_code
        )
        analysis['agency_patterns'] = agency_patterns
        
        # Step 6: Competitive assessment
        self.logger.info("Step 6: Generating competitive assessment...")
        assessment = self._generate_competitive_assessment(
            analysis,
            your_company_profile
        )
        analysis['competitive_assessment'] = assessment
        
        return analysis
    
    def find_teaming_opportunities(self,
                                  opportunity: Dict[str, Any],
                                  capability_gaps: List[str],
                                  your_size: str = "small") -> Dict[str, Any]:
        """
        Find potential teaming partners for capability gaps
        
        Args:
            opportunity: Opportunity data
            capability_gaps: List of missing capabilities
            your_size: "small" or "large"
            
        Returns:
            Teaming partner recommendations
        """
        naics_code = opportunity.get('naicsCode', '')
        
        # Determine size constraints
        if your_size == "small":
            # Look for other small businesses or large businesses who need a small prime
            small_business_only = True
            min_revenue = 500000
            max_revenue = 50000000
        else:
            # Look for small businesses to subcontract to
            small_business_only = True
            min_revenue = 100000
            max_revenue = 20000000
        
        # Find partners with relevant experience
        partners = self.usaspending.find_teaming_partners(
            naics_code=naics_code,
            small_business_only=small_business_only,
            min_revenue=min_revenue,
            max_revenue=max_revenue
        )
        
        # Score and rank partners
        scored_partners = []
        for partner in partners:
            score = self._score_teaming_partner(partner, capability_gaps)
            partner['teaming_score'] = score
            scored_partners.append(partner)
        
        scored_partners.sort(key=lambda x: x['teaming_score'], reverse=True)
        
        return {
            'capability_gaps': capability_gaps,
            'partner_count': len(scored_partners),
            'top_recommendations': scored_partners[:10],
            'teaming_strategy': self._recommend_teaming_strategy(
                opportunity, 
                capability_gaps, 
                scored_partners
            )
        }
    
    def benchmark_against_competitors(self,
                                     your_naics_codes: List[str],
                                     your_3yr_revenue: float) -> Dict[str, Any]:
        """
        Benchmark your company against similar competitors
        
        Args:
            your_naics_codes: Your registered NAICS codes
            your_3yr_revenue: Your 3-year government contract revenue
            
        Returns:
            Competitive benchmark analysis
        """
        # Find similar companies
        competitors = self.usaspending.find_similar_companies(
            your_naics_codes=your_naics_codes,
            your_size_range=(your_3yr_revenue * 0.5, your_3yr_revenue * 2)
        )
        
        if not competitors:
            return {'message': 'No comparable competitors found'}
        
        # Calculate statistics
        revenues = [c['total_value'] for c in competitors]
        avg_revenue = sum(revenues) / len(revenues)
        median_revenue = sorted(revenues)[len(revenues) // 2]
        
        # Your percentile
        your_rank = sum(1 for r in revenues if r < your_3yr_revenue)
        your_percentile = (your_rank / len(revenues)) * 100
        
        return {
            'your_revenue': your_3yr_revenue,
            'competitor_count': len(competitors),
            'market_average': avg_revenue,
            'market_median': median_revenue,
            'your_percentile': your_percentile,
            'position': 'above average' if your_3yr_revenue > avg_revenue else 'below average',
            'top_competitors': competitors[:10],
            'competitive_insights': self._generate_benchmark_insights(
                your_3yr_revenue,
                avg_revenue,
                your_percentile,
                competitors
            )
        }
    
    def _extract_agency_name(self, opportunity: Dict[str, Any]) -> str:
        """Extract agency name from opportunity data"""
        # SAM.gov provides agency info in various fields
        office_address = opportunity.get('officeAddress', {})
        return office_address.get('agency', 'Unknown')
    
    def _extract_keywords(self, opportunity: Dict[str, Any]) -> List[str]:
        """Extract relevant keywords from opportunity"""
        title = opportunity.get('title', '').lower()
        description = opportunity.get('description', '').lower()
        
        # Simple keyword extraction (could be enhanced with NLP)
        common_terms = ['services', 'support', 'solutions', 'systems', 'management']
        
        keywords = []
        for term in [title, description]:
            words = term.split()
            keywords.extend([w for w in words if len(w) > 5 and w not in common_terms][:5])
        
        return keywords[:10]
    
    def _generate_competitive_assessment(self,
                                        analysis: Dict[str, Any],
                                        your_profile: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate competitive assessment based on all intelligence gathered"""
        
        assessment = {
            'incumbent_strength': 'unknown',
            'pricing_position': 'unknown',
            'market_position': 'unknown',
            'win_probability': 0,
            'key_factors': [],
            'recommended_strategy': ''
        }
        
        # Assess incumbent strength
        incumbent = analysis.get('incumbent')
        incumbent_profile = analysis.get('incumbent_profile', {})
        
        if incumbent and incumbent_profile.get('total_contract_value_3yr'):
            incumbent_revenue = incumbent_profile['total_contract_value_3yr']
            
            if incumbent_revenue > 100000000:
                assessment['incumbent_strength'] = 'very_strong'
                assessment['key_factors'].append("Incumbent is large, well-established contractor")
            elif incumbent_revenue > 50000000:
                assessment['incumbent_strength'] = 'strong'
                assessment['key_factors'].append("Incumbent has significant government presence")
            else:
                assessment['incumbent_strength'] = 'moderate'
                assessment['key_factors'].append("Incumbent is comparable size competitor")
        else:
            assessment['incumbent_strength'] = 'unknown'
            assessment['key_factors'].append("No clear incumbent identified (greenfield opportunity)")
        
        # Assess pricing position
        pricing = analysis.get('pricing_intelligence', {})
        if pricing.get('average'):
            avg_price = pricing['average']
            assessment['pricing_position'] = 'competitive'
            assessment['key_factors'].append(f"Market average: ${avg_price:,.0f}")
            
            if pricing.get('trend', {}).get('direction') == 'increasing':
                assessment['key_factors'].append("Market prices trending upward")
        
        # Assess market position
        trends = analysis.get('market_trends', {})
        if trends.get('trend_direction') == 'increasing':
            assessment['market_position'] = 'growing'
            assessment['key_factors'].append("Market is growing (favorable conditions)")
        elif trends.get('trend_direction') == 'stable':
            assessment['market_position'] = 'stable'
            assessment['key_factors'].append("Market is stable")
        else:
            assessment['market_position'] = 'declining'
            assessment['key_factors'].append("Market is declining (increased competition)")
        
        # Calculate win probability (simplified model)
        win_prob = 50  # Base probability
        
        if assessment['incumbent_strength'] == 'very_strong':
            win_prob -= 20
        elif assessment['incumbent_strength'] == 'unknown':
            win_prob += 10
        
        if assessment['market_position'] == 'growing':
            win_prob += 10
        elif assessment['market_position'] == 'declining':
            win_prob -= 10
        
        assessment['win_probability'] = max(0, min(100, win_prob))
        
        # Recommend strategy
        if assessment['incumbent_strength'] in ['very_strong', 'strong']:
            assessment['recommended_strategy'] = 'Consider teaming as subcontractor or focus on differentiation'
        elif assessment['incumbent_strength'] == 'moderate':
            assessment['recommended_strategy'] = 'Compete aggressively with competitive pricing and innovation'
        else:
            assessment['recommended_strategy'] = 'Prime opportunity - establish early relationships with agency'
        
        return assessment
    
    def _score_teaming_partner(self, partner: Dict[str, Any], capability_gaps: List[str]) -> float:
        """Score a potential teaming partner"""
        score = 0.0
        
        # Base score on revenue (size matters for capability)
        revenue = partner.get('total_value', 0)
        if 1000000 <= revenue <= 20000000:
            score += 30  # Ideal size for subcontractor
        elif revenue > 20000000:
            score += 20  # Larger, more capable
        else:
            score += 10  # Smaller, might lack resources
        
        # Award count (experience matters)
        award_count = partner.get('award_count', 0)
        if award_count >= 10:
            score += 30
        elif award_count >= 5:
            score += 20
        else:
            score += 10
        
        # Average award size (relevant experience)
        avg_award = partner.get('average_award', 0)
        if avg_award >= 500000:
            score += 20
        else:
            score += 10
        
        # Keyword matching (would be enhanced with actual capability matching)
        score += 20  # Placeholder - would match against capability_gaps
        
        return score
    
    def _recommend_teaming_strategy(self,
                                   opportunity: Dict[str, Any],
                                   capability_gaps: List[str],
                                   partners: List[Dict[str, Any]]) -> str:
        """Recommend teaming strategy"""
        
        if not capability_gaps:
            return "No teaming required - pursue as prime"
        
        if len(capability_gaps) == 1:
            return f"Single subcontractor needed for {capability_gaps[0]}"
        
        if len(partners) < 2:
            return "Limited teaming options - consider developing capability internally or delaying bid"
        
        return f"Multi-partner team recommended to cover {len(capability_gaps)} capability gaps"
    
    def _generate_benchmark_insights(self,
                                     your_revenue: float,
                                     market_avg: float,
                                     percentile: float,
                                     competitors: List[Dict]) -> List[str]:
        """Generate insights from benchmark analysis"""
        insights = []
        
        if percentile >= 75:
            insights.append("You are in the top quartile of competitors in this market")
        elif percentile >= 50:
            insights.append("You are above average among competitors")
        elif percentile >= 25:
            insights.append("You are below average - focus on growth strategies")
        else:
            insights.append("You are in the bottom quartile - consider focusing on niche markets")
        
        if your_revenue < market_avg * 0.5:
            insights.append("Significantly smaller than average competitor - teaming may be essential")
        elif your_revenue > market_avg * 2:
            insights.append("Significantly larger than average - can pursue larger opportunities")
        
        # NAICS diversity
        avg_naics_count = sum(len(c.get('naics_codes', [])) for c in competitors) / len(competitors)
        insights.append(f"Competitors average {avg_naics_count:.1f} NAICS codes - diversification opportunity")
        
        return insights


def generate_competitive_intelligence_report(analysis: Dict[str, Any]) -> str:
    """Generate formatted competitive intelligence report"""
    
    report = f"""
{'='*80}
COMPETITIVE INTELLIGENCE REPORT
{'='*80}

Opportunity: {analysis.get('title', 'Unknown')}
Notice ID: {analysis.get('opportunity_id', 'Unknown')}

"""
    
    # Incumbent section
    incumbent = analysis.get('incumbent')
    if incumbent:
        report += format_incumbent_report(incumbent)
    else:
        report += "INCUMBENT INTELLIGENCE\nNo incumbent contract identified (greenfield opportunity)\n"
    
    report += "\n"
    
    # Pricing section
    pricing = analysis.get('pricing_intelligence')
    if pricing:
        report += format_pricing_report(pricing)
    
    report += "\n"
    
    # Market trends section
    trends = analysis.get('market_trends')
    if trends:
        report += format_market_trends(trends)
    
    report += "\n"
    
    # Competitive assessment
    assessment = analysis.get('competitive_assessment', {})
    if assessment:
        report += f"""
{'='*80}
COMPETITIVE ASSESSMENT
{'='*80}

Incumbent Strength: {assessment.get('incumbent_strength', 'Unknown').upper()}
Market Position: {assessment.get('market_position', 'Unknown').upper()}
Win Probability: {assessment.get('win_probability', 0)}%

Key Factors:
"""
        for factor in assessment.get('key_factors', []):
            report += f"  • {factor}\n"
        
        report += f"\nRecommended Strategy:\n  {assessment.get('recommended_strategy', 'N/A')}\n"
    
    return report


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    agent = CompetitiveIntelligenceAgent()
    
    # Example opportunity
    sample_opportunity = {
        'noticeId': 'TEST123',
        'title': 'Cloud Infrastructure Services',
        'naicsCode': '541512',
        'officeAddress': {
            'agency': 'DEPARTMENT OF DEFENSE'
        },
        'description': 'Cloud migration and infrastructure services for DoD systems'
    }
    
    # Run competitive analysis
    analysis = agent.analyze_opportunity_competitiveness(sample_opportunity)
    
    # Generate report
    report = generate_competitive_intelligence_report(analysis)
    print(report)
