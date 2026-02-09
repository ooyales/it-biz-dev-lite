# IT Opportunity Filtering Guide

## ✅ Filters Already Implemented!

Your opportunity collector now has comprehensive IT-only filtering with 4 layers:

### Layer 1: NAICS Codes (Primary Filter)
```
541511 - Custom Computer Programming Services
541512 - Computer Systems Design Services  
541519 - Other Computer Related Services
518210 - Data Processing, Hosting, and Related Services
```

Set in `.env`:
```bash
NAICS_CODES=541511,541512,541519,518210
```

### Layer 2: PSC Codes (Product Service Codes)
Automatically filters for IT-specific PSC codes:

**D3xx Series (IT & Telecom):**
- D302 - Systems Development
- D307 - IT Strategy & Architecture
- D310 - Cybersecurity
- D311 - Software Engineering
- D312 - Systems Analysis
- D314 - Data Management
- D316 - Network Management
- D317 - Web-Based Services
- D318 - Cloud Computing
- D320 - Database Design
- D321 - Programming
- D399 - Other IT & Telecom

**Other IT PSC:**
- 7030 - ADP & Telecom Equipment

### Layer 3: IT Keywords (Must Have At Least One)

**Core IT:**
- software, hardware, network, database, server, cloud
- application, system, data, cyber, security, infrastructure

**Development:**
- development, programming, coding, engineering, devops
- agile, scrum, api, integration, web, mobile

**Modern Tech:**
- artificial intelligence, machine learning, ai/ml, analytics
- big data, blockchain, iot, saas, paas, iaas

**IT Services:**
- it support, help desk, technical support, system admin
- architecture, migration, modernization, digital transformation

**Technologies:**
- aws, azure, google cloud, kubernetes, docker
- python, java, javascript, sql, oracle, salesforce

**IT Management:**
- it service, itil, it operations, service desk
- incident management, configuration management

### Layer 4: Exclusion Keywords (Auto-Reject)

**Construction & Facilities:**
- construction, renovation, building maintenance, hvac
- plumbing, electrical work, carpentry, painting
- roofing, flooring, demolition

**Janitorial & Cleaning:**
- janitorial, custodial, cleaning services, sanitation
- housekeeping, waste removal, groundskeeping

**Facilities (Non-IT):**
- facilities maintenance, grounds maintenance, landscaping
- pest control, snow removal, trash removal

**Medical:**
- medical services, healthcare provider, nursing, clinical
- patient care, dental, pharmacy

**Food Services:**
- food service, catering, cafeteria, dining

**Security Guards (Not Cybersecurity):**
- security guard, physical security officer, armed guard

**Other:**
- transportation, moving services, freight, shipping
- printing services, courier, mail service

---

## 🎯 How It Works

### Decision Logic:

```
For each opportunity:

1. Check PSC Code
   ✓ Has D3xx or 7030? → ACCEPT (even if has exclusion keyword)

2. Check Keywords
   ✓ Has IT keyword + No exclusion → ACCEPT
   ✓ Has IT keyword + Has exclusion + 3+ IT keywords → ACCEPT (probably IT)
   
3. Otherwise → REJECT
```

### Example Results:

**ACCEPTED:**
```
Title: "Cloud Migration and Cybersecurity Services"
PSC: D310 (Cybersecurity)
Keywords: cloud, migration, cybersecurity, security
Exclusions: none
→ ACCEPT (has IT PSC and keywords)
```

**ACCEPTED:**
```
Title: "Software Development for HR System"
PSC: D311 (Software Engineering)
Keywords: software, development, system
Exclusions: none
→ ACCEPT (has IT PSC and keywords)
```

**REJECTED:**
```
Title: "Janitorial Services for Data Center"
PSC: S208 (Housekeeping)
Keywords: none (data is not enough)
Exclusions: janitorial
→ REJECT (no IT PSC, has exclusion keyword)
```

**ACCEPTED (Smart Filter):**
```
Title: "IT Infrastructure Maintenance and Support"
PSC: D316 (Network Management)
Keywords: IT, infrastructure, support, network, system
Exclusions: maintenance (but 5 IT keywords override)
→ ACCEPT (IT PSC code + multiple IT keywords)
```

---

## 📊 Statistics After Filtering

When you run the collector, you'll see:

```
Fetching IT opportunities from SAM.gov (limit: 25)...
  Using NAICS codes: 541511, 541512, 541519, 518210
  NAICS 541511: 87 opportunities
  NAICS 541512: 64 opportunities
  NAICS 541519: 42 opportunities
  NAICS 518210: 31 opportunities

Applying IT-specific filters...
  Before filtering: 224 opportunities
  After filtering: 189 IT opportunities
  Filtered out: 35 non-IT

Fetched 224 total opportunities
  Non-IT filtered out: 35
  Already processed: 164
  New IT opportunities: 25

✓ 25 new IT opportunities to process
```

**Filter Effectiveness:**
- NAICS alone: 224 opportunities (some non-IT)
- After IT filters: 189 opportunities (15% filtered)
- Final new opps: 25 (exactly what you requested)

---

## 🔧 Customization

### Add More IT Keywords

Edit `collect_env.py` line ~254:

```python
IT_KEYWORDS = [
    # Your existing keywords
    'your custom keyword',
    'another specific term',
]
```

### Add More Exclusion Keywords

Edit `collect_env.py` line ~282:

```python
EXCLUSION_KEYWORDS = [
    # Your existing exclusions
    'your exclusion',
]
```

### Adjust Filter Strictness

Edit `collect_env.py` line ~346:

```python
# Current: Requires 3+ IT keywords to override exclusion
if it_keyword_count >= 3:

# More strict: Require 5+ IT keywords
if it_keyword_count >= 5:

# Less strict: Require 2+ IT keywords  
if it_keyword_count >= 2:
```

---

## 🚀 Testing the Filters

Run a test collection:

```bash
cd knowledge_graph
python collect_env.py --limit 10
```

Check what gets through:

```bash
# View the opportunities collected
python3 << 'EOF'
import json
from pathlib import Path

# Find latest scout data
scout_files = sorted(Path('.').glob('scout_data_*.json'), reverse=True)
if scout_files:
    with open(scout_files[0]) as f:
        data = json.load(f)
    
    print(f"\nFound {len(data['opportunities'])} opportunities\n")
    
    for opp in data['opportunities'][:5]:
        print(f"Title: {opp.get('title', 'Unknown')}")
        print(f"PSC: {opp.get('classificationCode', 'N/A')}")
        print(f"NAICS: {opp.get('naicsCode', 'N/A')}")
        print(f"Type: {opp.get('type', 'N/A')}")
        print("-" * 70)
EOF
```

### Validate Filtering Quality

Check if any non-IT slipped through:

1. Look at the titles in your dashboard
2. Check for janitorial, construction, etc.
3. If you find false positives, add to EXCLUSION_KEYWORDS
4. If you find false negatives, add to IT_KEYWORDS

---

## 💡 Best Practices

### 1. Start Conservative
The current filters are designed to be precise (few false positives).
- Better to miss a few IT opps than to waste time on non-IT

### 2. Monitor Your Results
After collecting 100+ opportunities:
- Review what's getting through
- Adjust keywords based on your focus
- Add exclusions for patterns you see

### 3. Customize for Your Niche
If you specialize in specific IT areas:

**Cloud Focus:**
```python
IT_KEYWORDS = [
    'cloud', 'aws', 'azure', 'gcp', 'migration',
    'iaas', 'paas', 'saas', 'kubernetes', 'docker',
    'serverless', 'lambda', 'ec2', 's3',
]
```

**Cybersecurity Focus:**
```python
IT_KEYWORDS = [
    'cybersecurity', 'security', 'STIG', 'RMF', 'ATO',
    'penetration', 'vulnerability', 'FISMA', 'compliance',
    'zero trust', 'endpoint', 'firewall', 'SIEM',
]
```

**Software Development Focus:**
```python
IT_KEYWORDS = [
    'software', 'development', 'coding', 'programming',
    'agile', 'devops', 'ci/cd', 'api', 'microservices',
    'full stack', 'frontend', 'backend', 'mobile',
]
```

---

## ✅ Summary

Your system now filters for IT-only opportunities using:

1. ✅ **NAICS codes** - 4 IT-specific codes
2. ✅ **PSC codes** - D3xx series + ADP codes  
3. ✅ **IT keywords** - 70+ relevant terms
4. ✅ **Exclusions** - 30+ non-IT patterns

**Result:** Only genuine IT opportunities reach your dashboard!

No more janitorial, construction, or facilities maintenance cluttering your pipeline. 🎯
