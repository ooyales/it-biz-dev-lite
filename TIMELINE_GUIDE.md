# Enhanced Timeline Feature Guide

## Overview

The timeline visualization has been significantly enhanced with:
1. ✅ Spread opportunities across 2026-2027 (no more crowding!)
2. ✅ Configurable Y-axis (Fit Score, Win %, Contract Value)
3. ✅ Adjustable time range (12, 24, or 36 months)
4. ✅ Smart bubble positioning (no overlaps)
5. ✅ Y-axis labels for easy reading
6. ✅ Size-based on contract value
7. ✅ Color-coded by fit score

## Generating Spread-Out Demo Data

**The demo data generator now spreads opportunities across 2 years by default!**

### Quick Demo (Recommended)
```bash
# Access data admin panel
http://localhost:8080/data-admin

# Click "Quick Demo Setup"
# Generates 40 opportunities spread from now through 2027
```

### Custom Amount
```bash
# Run generator directly
python generate_demo_data.py

# When prompted:
Number of opportunities [30]: 50

# Creates 50 opportunities spread across 24 months
```

### What Changed
- **Before**: All opportunities within 15-90 days (crowded!)
- **After**: Opportunities spread 30 days to 2 years (perfect spacing!)

## Timeline Configuration

### Y-Axis Options

**1. Fit Score (Default)**
- Range: 0-10
- Best for: Seeing opportunity quality at a glance
- Interpretation: Higher = better fit for your company

**2. Win Probability %**
- Range: 0-100%
- Best for: Assessing likelihood of winning
- Interpretation: Higher = better chance of success

**3. Contract Value**
- Range: Logarithmic scale ($10K - $10M+)
- Best for: Seeing contract size distribution
- Interpretation: Higher = larger contract value

### Time Range Options

**1. Next 12 Months**
- Good for: Near-term planning
- Focus: Immediate opportunities
- Use when: You want tactical view

**2. Next 24 Months (Default)**
- Good for: Strategic planning
- Focus: Balance of near and long-term
- Use when: Building relationships 6-12 months out

**3. Next 36 Months**
- Good for: Long-term strategy
- Focus: Full contract lifecycle
- Use when: Enterprise planning, major programs

## Reading the Timeline

### Bubble Properties

**Position:**
- X-axis (horizontal): Days until deadline
- Y-axis (vertical): Selected metric value

**Size:**
- Small bubble (40px): <$100K contract
- Medium bubble (60px): $100K-$1M contract
- Large bubble (80px): >$1M contract

**Color:**
- Green: High fit score (≥7.0) - PURSUE
- Yellow/Orange: Medium fit (6.0-6.9) - WATCH
- Red: Low fit (<6.0) - PASS

### Interaction

**Hover over bubble:**
- Expands to show full information
- Displays title, deadline, and Y-axis value
- Changes from circle to rounded rectangle

**Click bubble:**
- Opens full opportunity details
- Shows competitive intelligence
- Make pursue/watch/pass decision

## Example Views

### View 1: Quality-Based Planning
```
Y-Axis: Fit Score
Time Range: 24 Months
Use Case: Identify high-quality opportunities to build relationships early
Strategy: Focus on green bubbles (≥7.0) 6+ months out
```

### View 2: Win Probability Analysis
```
Y-Axis: Win Probability %
Time Range: 12 Months
Use Case: Prioritize opportunities with best chance of winning
Strategy: Target high-percentage opportunities in next 6 months
```

### View 3: Revenue Opportunity Mapping
```
Y-Axis: Contract Value
Time Range: 36 Months
Use Case: Long-term revenue planning and capacity allocation
Strategy: See distribution of small, medium, large contracts
```

## Timeline Reading Strategy

### "Shift Left" Approach

**The timeline enables proactive relationship building:**

1. **12+ months out (Right side)**
   - Current contract likely still active
   - Incumbent identified via competitive intel
   - **Action**: Research agency, attend industry days
   - **Goal**: Get on their radar before RFP

2. **6-12 months out (Middle)**
   - Solicitation likely in planning
   - Time to build relationships
   - **Action**: Schedule meetings, demonstrate capabilities
   - **Goal**: Become preferred vendor

3. **0-6 months out (Left side)**
   - RFP may already be published
   - Less time to influence
   - **Action**: Prepare proposal, finalize team
   - **Goal**: Submit competitive bid

### Color Strategy

**Green bubbles (≥7.0 fit):**
- Always investigate
- Prioritize for early engagement
- Assign BD resources

**Yellow bubbles (6.0-6.9 fit):**
- Monitor for changes
- Consider if strategic fit
- May pursue if capacity allows

**Red bubbles (<6.0 fit):**
- Generally pass
- Only pursue if unique circumstances
- Don't waste resources

## Demo Workflow for Team

### Preparation (5 minutes before demo)

```bash
# 1. Generate demo data
http://localhost:8080/data-admin
Click "Quick Demo Setup"

# 2. Open dashboard
http://localhost:8080

# 3. Configure timeline
Y-Axis: Fit Score
Time Range: 24 Months
```

### Demo Script (10 minutes)

**1. Show Stats (1 min)**
```
"We have 40 opportunities in our pipeline.
15 are high priority, 8 we're actively pursuing."
```

**2. Show Timeline (3 min)**
```
"This timeline shows all opportunities by deadline.
Y-axis shows fit score - higher is better for us.

See these green bubbles 6-12 months out?
Those are our 'shift left' targets.
We can build relationships NOW before RFP drops."

[Click green bubble]
"Here's the competitive intel:
- Current incumbent: TechCorp Solutions
- Contract value: $2.5M
- Our fit score: 8.2/10
- Win probability: 75%"
```

**3. Change Y-Axis (2 min)**
```
[Change to Win Probability]
"Now looking at win probability.
These high bubbles are our best bets."

[Change to Contract Value]
"And here's revenue potential.
Higher bubbles = bigger contracts."
```

**4. Show Opportunities Grid (2 min)**
```
[Scroll to opportunities]
"All opportunities shown here with full details.
We can make pursue/watch/pass decisions.
Everything tracked in the system."
```

**5. Make Sample Decision (2 min)**
```
[Click pursue on high-priority opp]
"When we decide to pursue, it updates status.
Dashboard tracks our active pursuits.
Team knows what we're going after."
```

### Team Questions to Expect

**Q: "Is this real data?"**
A: "This is demo data for today. Tomorrow we'll run scout for real SAM.gov data. Same interface, real opportunities."

**Q: "How do we know which to pursue?"**
A: "Green bubbles (≥7.0) are strong fits. Competitive intel shows win probability. We focus on high-score opportunities 6+ months out to build relationships."

**Q: "Can we filter by agency or contract size?"**
A: "Yes, click opportunities to see details. We can add filters in the Config Admin panel - NAICS codes, set-asides, value ranges."

**Q: "How often does this update?"**
A: "Automated scout runs daily at 7 AM. Checks SAM.gov for new opportunities. Dashboard updates automatically."

## Post-Demo: Transition to Real Data

### After Team Demo

**1. Clear demo data**
```bash
http://localhost:8080/data-admin
Click "Clear Demo Data Only"
```

**2. Configure real search**
```bash
http://localhost:8080/admin
- Set your NAICS codes
- Add keywords
- Set value range
- Save changes
```

**3. Run first real scout**
```bash
python main_integrated.py
# Or wait for 7 AM automated run
```

**4. View real opportunities**
```bash
http://localhost:8080
Timeline now shows actual SAM.gov opportunities
```

## Technical Details

### Demo Data Generation

**File**: `generate_demo_data.py`

**Deadline spread algorithm:**
```python
# Spreads across 2 years (730 days)
days_from_now = random.randint(30, 730)
deadline = datetime.now() + timedelta(days=days_from_now)
```

**Creates:**
- Database entries (SQLite)
- Analysis JSON files
- Complete competitive intelligence
- Summary reports

### Timeline Rendering

**File**: `templates/dashboard.html`

**Smart positioning:**
1. Groups opportunities by 30-day buckets
2. Calculates Y position based on selected metric
3. Applies slight horizontal offset to avoid overlap
4. Sizes bubbles based on contract value
5. Colors based on fit score

**Performance:**
- Handles 100+ opportunities smoothly
- Efficient bucket-based collision detection
- Smooth animations and hover effects

## Tips and Best Practices

### For Demo
- Use 40-50 opportunities (good variety)
- Set Y-axis to "Fit Score" initially
- Use 24-month view for balance
- Have 2-3 high-priority opportunities ready to click

### For Production
- Run scout daily
- Review timeline weekly with team
- Focus on 6-12 month opportunities
- Track relationships in CRM
- Update staff capabilities as team changes

### For Team Training
- Start with demo data
- Let team explore interface
- Practice making decisions
- Explain "shift left" strategy
- Transition to real data after 1 week

## Troubleshooting

### Timeline looks empty
- Check time range setting (increase to 24 or 36 months)
- Verify opportunities have deadlines
- Generate more demo data

### Bubbles overlapping
- Increase time range (spreads X-axis)
- Generate fewer opportunities
- Check bucket collision logic is working

### Y-axis doesn't make sense
- Verify data has the selected metric
- Check value ranges (fit: 0-10, win: 0-100%, value: logarithmic)
- Try different Y-axis option

### Demo data too crowded
- Regenerate with spread timeline
- Use data admin to clear and regenerate
- Increase time range to 36 months

## Summary

**Enhanced Timeline Features:**
✅ Opportunities spread across 2 years
✅ Three Y-axis options (fit, win%, value)
✅ Three time ranges (12, 24, 36 months)
✅ Smart positioning (no overlaps)
✅ Size based on contract value
✅ Color coded by fit score
✅ Hover for details, click for full info

**Perfect for showing team:**
- Visual, intuitive interface
- Strategic planning capability
- "Shift left" relationship building
- Data-driven decision making

Your timeline is now ready for a professional team demo! 🎯
