# Capability Matching Agent Guide

## 🎯 What It Does

The Capability Matching Agent analyzes whether your company can perform the work required by an opportunity by:

1. **Extracting Requirements** from opportunity descriptions
2. **Matching Your Staff** to those requirements
3. **Identifying Capability Gaps** 
4. **Calculating Technical Win Probability**
5. **Recommending Bid Strategy** (bid alone, team, pass)

## 🚀 Quick Start

```bash
# Copy the agent
cp /mnt/user-data/outputs/knowledge_graph/capability_matcher.py knowledge_graph/

# Test it
cd knowledge_graph
python capability_matcher.py
```

## 📊 Sample Output

```
======================================================================
CAPABILITY MATCH ANALYSIS
======================================================================

Opportunity: Cloud Migration and Cybersecurity Services
Agency: Department of Defense

Capability Score: 85/100
Technical Win Probability: High (75-90%)

Recommendation: STRONG MATCH - You have the capabilities to perform this work

REQUIREMENTS ANALYSIS
----------------------------------------------------------------------
Total Requirements: 8
Matched: 7
Unmatched: 1

DETAILED REQUIREMENTS:

✓ [MANDATORY] Secret clearance required
   Matched by: John Smith, Sarah Johnson, Mike Williams, Emily Davis

✓ [OPTIONAL] CISSP certification
   Matched by: John Smith, Mike Williams

✓ [OPTIONAL] Python experience
   Matched by: John Smith, Sarah Johnson

✓ [OPTIONAL] AWS experience
   Matched by: John Smith, Robert Chen

✓ [OPTIONAL] Kubernetes experience
   Matched by: John Smith

✓ [OPTIONAL] Cybersecurity experience
   Matched by: Mike Williams

✓ [OPTIONAL] DevOps experience
   Matched by: John Smith

✗ [OPTIONAL] 5+ years of experience required

STAFF ASSIGNMENTS:
----------------------------------------------------------------------

John Smith:
  • Secret clearance required
  • CISSP certification
  • Python experience
  • AWS experience
  • Kubernetes experience
  • DevOps experience

Mike Williams:
  • Secret clearance required
  • CISSP certification
  • Cybersecurity experience

Sarah Johnson:
  • Secret clearance required
  • Python experience

Emily Davis:
  • Secret clearance required

Robert Chen:
  • AWS experience

CAPABILITY GAPS:
----------------------------------------------------------------------

[Medium] 5+ years of experience required
  → Nice to have, consider hiring or teaming
```

## 🎨 How It Works

### 1. Staff Database

Currently uses sample data. In production, you'd maintain a staff database:

```python
StaffMember(
    name="John Smith",
    title="Senior Software Engineer",
    clearance="Secret",
    certifications=["CISSP", "AWS Certified"],
    skills=["Python", "Java", "Cloud Architecture"],
    experience_years=10,
    past_projects=["DOD Cloud Migration"],
    availability="Available"
)
```

### 2. Requirement Extraction

Automatically extracts from opportunity text:
- **Clearance requirements** (Secret, Top Secret)
- **Certifications** (CISSP, Security+, PMP, AWS)
- **Technical skills** (Python, Cloud, AI/ML)
- **Experience levels** (5+ years, 10+ years)

### 3. Matching Algorithm

For each requirement:
1. Checks all staff members
2. Matches based on clearance, certs, skills
3. Assigns staff to requirements
4. Flags unmatched requirements as gaps

### 4. Scoring

```
Capability Score = (Mandatory Match % × 70) + (Optional Match % × 30)

85+ = Strong Match (bid alone)
60-84 = Good Match (minor gaps okay)
40-59 = Partial Match (team recommended)
<40 = Weak Match (reconsider)
```

### 5. Technical Win Probability

Maps capability score to technical win odds:
- **85-100**: High (75-90% technical win)
- **60-84**: Medium (50-75%)
- **40-59**: Low (25-50%)
- **<40**: Very Low (<25%)

## 🔗 Integration with Opportunity Scout

The capability score enhances the opportunity scout's win probability:

```
Final Win Probability = 
    (Relationship Score × 40%) +
    (Capability Score × 40%) +
    (Strategic Fit × 20%)
```

## 💡 Usage Scenarios

### Scenario 1: Pre-Bid Analysis

```bash
# Analyze a specific opportunity
cd knowledge_graph
python3 << 'EOF'
from capability_matcher import CapabilityMatcher

# Your opportunity from SAM.gov
opportunity = {
    'title': 'Cybersecurity Assessment Services',
    'agency': 'NASA',
    'description': 'Secret clearance and CISSP required...'
}

matcher = CapabilityMatcher()
analysis = matcher.analyze_opportunity(opportunity)
report = matcher.generate_report(analysis)
print(report)
EOF
```

### Scenario 2: Batch Analysis

Analyze all high-priority opportunities:

```python
from opportunity_scout import OpportunityScout
from capability_matcher import CapabilityMatcher

scout = OpportunityScout()
matcher = CapabilityMatcher()

# Get high-priority opportunities
opps = scout.fetch_opportunities(days_back=7)
for opp in opps:
    score = scout.score_opportunity(opp)
    if score['priority'] == 'HIGH':
        # Analyze capabilities
        cap_analysis = matcher.analyze_opportunity(opp)
        if cap_analysis['capability_score'] >= 70:
            print(f"PURSUE: {opp['title']}")
            print(f"  Win Prob: {score['win_probability']}%")
            print(f"  Capability: {cap_analysis['capability_score']}/100")
```

### Scenario 3: Staff Allocation Planning

```python
# Which staff are overallocated?
from capability_matcher import CapabilityMatcher

matcher = CapabilityMatcher()

# Analyze multiple opportunities
assignments = {}
for opp in opportunities:
    analysis = matcher.analyze_opportunity(opp)
    for staff, reqs in analysis['staff_assignments'].items():
        if staff not in assignments:
            assignments[staff] = []
        assignments[staff].append(opp['title'])

# Find busy staff
for staff, opps in assignments.items():
    if len(opps) > 3:
        print(f"⚠️  {staff} assigned to {len(opps)} opportunities")
```

## 🎯 Dashboard Integration

Add capability analysis to the opportunity modal:

```javascript
// In bd-intelligence.html modal
fetch(`/api/capability/analyze/${noticeId}`)
    .then(r => r.json())
    .then(data => {
        document.getElementById('capability-section').innerHTML = `
            <h6>Capability Match</h6>
            <div class="progress">
                <div class="progress-bar" style="width: ${data.capability_score}%">
                    ${data.capability_score}/100
                </div>
            </div>
            <p class="mt-2">${data.recommendation}</p>
            
            <h6 class="mt-3">Staff Assignments</h6>
            ${Object.entries(data.staff_assignments).map(([staff, reqs]) => `
                <div><strong>${staff}</strong>: ${reqs.length} requirements</div>
            `).join('')}
        `;
    });
```

## 📈 Customization

### Add Your Staff

Edit the `load_staff_database()` method:

```python
def load_staff_database(self):
    self.staff = [
        StaffMember(
            name="Your Name",
            title="Your Title",
            clearance="Secret/TS/None",
            certifications=["CISSP", "PMP"],
            skills=["Python", "AWS", "etc"],
            experience_years=10
        ),
        # Add more staff...
    ]
```

### Or Load from Database

```python
def load_staff_database(self):
    # Load from Neo4j or SQL
    with kg.driver.session() as session:
        result = session.run("MATCH (s:StaffMember) RETURN s")
        self.staff = [self.staff_from_node(r['s']) for r in result]
```

### Add Custom Skills

```python
skill_keywords = [
    'Python', 'Java', 'JavaScript', 'C++',
    'AWS', 'Azure', 'GCP',
    'Docker', 'Kubernetes',
    'Machine Learning', 'AI', 'NLP',
    # Add your company's specific skills
    'Your Custom Skill'
]
```

## 🎊 Combined Intelligence

When you use Capability Matcher + Opportunity Scout together:

```
Opportunity: NASA Cloud Migration
├─ Relationship Score: 75/100 (you have 2 contacts)
├─ Capability Score: 85/100 (strong technical match)
├─ Combined Win Probability: 80%
└─ Recommendation: STRONGLY PURSUE
    • You have the right people (relationships)
    • You can do the work (capabilities)
    • High chance of winning
```

**This is the complete picture for bid/no-bid decisions!** 🎯

---

## 🚀 Next Steps

Want me to:
1. **Integrate this into the dashboard** with a capability tab?
2. **Build a staff database manager** UI?
3. **Add Claude AI for smarter requirement extraction**?
4. **Move on to Agent 4** (RFI Response Generator)?

You now have 3 of 6 agents working! 💪
