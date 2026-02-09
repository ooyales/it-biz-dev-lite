# Admin Panel User Guide

## Overview

The **Admin Panel** provides a beautiful, user-friendly interface to:
- ✅ Configure SAM.gov search parameters
- ✅ Manage company information
- ✅ Add/Edit/Delete staff members
- ✅ Configure competitive intelligence
- ✅ Set up email and Slack notifications
- ✅ Preview configuration changes in real-time

**No more editing YAML files manually!**

## Accessing the Admin Panel

Once your team dashboard is running:

```
Main Dashboard:  http://localhost:5000
Admin Panel:     http://localhost:5000/admin
```

Or click "Admin" from the dashboard header.

## Admin Panel Sections

### 1. SAM.gov Configuration

**What it controls:** How the system searches for opportunities

**Settings:**

- **API Key** - Your SAM.gov API key (required)
  - Get free at: https://open.gsa.gov/api/entity-api/

- **Lookback Days** - How far back to search (7-60 recommended)
  - 7 days = Daily fresh opportunities
  - 30 days = Broader search, less frequent
  - 60 days = Comprehensive but slower

- **Contract Value Range** - Min and max opportunity size
  - Example: $50,000 - $10,000,000
  - Set min high to filter out small contracts
  - Set max based on your capacity

- **Opportunity Types** - Which types to search for
  - ☑ Solicitation (RFPs you can bid on)
  - ☑ Presolicitation (advance notice)
  - ☐ Sources Sought (market research)
  - ☐ Special Notice (informational)

- **Keywords** - Search terms to filter opportunities
  - Type keyword, press Enter to add
  - Examples: "IT services", "cybersecurity", "cloud"
  - Click X to remove

**Tips:**
- Start with 14 days lookback
- Add 5-10 relevant keywords
- Include Solicitation + Presolicitation
- Adjust value range to your sweet spot

---

### 2. Company Information

**What it controls:** Your company profile for matching

**Settings:**

- **Company Name** (Optional) - Used in reports only

- **NAICS Codes** (Required) - Industries you compete in
  - Type 6-digit code, press Enter
  - Example: 541512 (Computer Systems Design)
  - Add all codes you're registered for
  - Remove codes you don't pursue

- **Set-Aside Categories** - Your eligibility
  - ☑ Small Business
  - ☐ 8(a)
  - ☐ HUBZone
  - ☐ WOSB (Women-Owned)
  - ☐ SDVOSB (Service-Disabled Veteran)
  - ☐ VOSB (Veteran-Owned)

- **Contract Vehicles** (Optional) - GWACs, IDIQs you hold
  - Type vehicle name, press Enter
  - Example: "GSA MAS", "SeaPort-e"

**Tips:**
- Be selective with NAICS codes (quality over quantity)
- Only check set-asides you actually qualify for
- Add vehicles to help identify on-contract opportunities

---

### 3. Staff Management

**What it controls:** Your team capabilities database

**Features:**

**View Staff:**
- See all team members at a glance
- Quick view of clearance, experience, rate, skills
- Organized cards with key info

**Add Staff Member:**
1. Click "➕ Add Staff Member"
2. Fill in form:
   - Name (required)
   - Title (e.g., "Senior Engineer")
   - Clearance level & expiry date
   - Labor category
   - Hourly rate
   - Years of experience
   - Education
   - **Technical Skills** - Type skill, press Enter
   - **Certifications** - Type cert, press Enter
   - Availability (Available, Partial, Unavailable)
3. Click "Save Changes"

**Edit Staff Member:**
1. Click "Edit" on staff card
2. Update any information
3. Add/remove skills and certifications
4. Click "Save Changes"

**Delete Staff Member:**
1. Click "Delete" on staff card
2. Confirm deletion
3. Staff removed from database

**Tips:**
- Keep skills updated for accurate matching
- Set availability to help team planning
- Include all relevant certifications
- Update clearance expiry dates

---

### 4. Competitive Intelligence

**What it controls:** Market intelligence gathering

**Settings:**

- **Enable Competitive Intelligence** - Turn on/off
  - On = Get incumbent, pricing, market data
  - Off = Faster but less insight

- **Min Value for Intel** - Only run intel on opportunities above this $
  - $0 = Run on all opportunities
  - $500,000 = Only $500K+ opportunities
  - Higher value = Faster, focused on large contracts

- **Lookback Years** - Historical data window (1-5 years)
  - 3 years = Good balance (recommended)
  - 5 years = More data, slower
  - 1 year = Recent only

- **Intelligence Features** - What to gather
  - ☑ Incumbent Identification (who has it now)
  - ☑ Pricing Analysis (historical pricing)
  - ☑ Market Trends (growth/decline)
  - ☑ Competitor Profiling (incumbent details)
  - ☐ Teaming Partner Discovery (slower, optional)

**Tips:**
- Keep enabled for best results
- Set min value to $100K+ to save time
- Use 3 years lookback
- Disable teaming partners if slow

---

### 5. Notifications

**What it controls:** Team alerts for new opportunities

#### Email Notifications

**Settings:**

- **Enable Email Notifications** - Turn on/off

- **SMTP Server** - Email server
  - Gmail: `smtp.gmail.com`
  - Outlook: `smtp.office365.com`
  - Custom: Your company's SMTP server

- **SMTP Port** - Usually 587 or 465

- **From Email** - Sender address

- **App Password** (Gmail users)
  - NOT your regular password
  - Generate at: https://myaccount.google.com/apppasswords
  - More secure than regular password

- **To Addresses** - Recipients
  - Type email, press Enter to add
  - Add multiple team members
  - Click X to remove

**Gmail Setup:**
1. Go to https://myaccount.google.com/apppasswords
2. Sign in
3. Create app password (select "Other")
4. Copy 16-character password
5. Paste into "App Password" field

#### Slack Notifications

**Settings:**

- **Enable Slack Notifications** - Turn on/off

- **Webhook URL** - Slack integration URL
  - Get from: https://api.slack.com/apps
  - Create Incoming Webhook
  - Select channel
  - Copy webhook URL

**Slack Setup:**
1. Go to https://api.slack.com/apps
2. Create New App
3. Add Incoming Webhooks
4. Add to your workspace
5. Select channel (e.g., #opportunities)
6. Copy webhook URL
7. Paste into admin panel

**Tips:**
- Start with email (easier to set up)
- Add Slack for instant notifications
- Test before enabling
- Adjust notification preferences based on team feedback

---

## Configuration Preview

**Bottom of every page** shows real-time YAML preview:

```yaml
sam_gov:
  api_key: "YOUR_KEY"
  search:
    lookback_days: 14
    ...
```

**What it does:**
- Shows exactly what will be saved
- Updates as you type
- Helps verify changes before saving
- Learn YAML format if needed

---

## Saving Changes

**"Save All Changes" button** (top right):

1. Click "Save All Changes"
2. Configuration written to `config.yaml`
3. Success message appears
4. Changes take effect on next scout run

**What gets saved:**
- All configuration changes
- Staff additions/edits
- Notification settings
- Everything in the admin panel

**What doesn't get saved automatically:**
- Individual field changes (must click "Save All Changes")
- Draft edits (must click Save)

---

## Best Practices

### Initial Setup

1. **Start with SAM.gov Config**
   - Add API key
   - Set lookback to 14 days
   - Add your keywords
   - Set value range

2. **Configure Company Info**
   - Add your NAICS codes
   - Select set-asides
   - Add contract vehicles (if any)

3. **Add Your Team**
   - Add all 20 staff members
   - Include skills, clearances, rates
   - Set availability

4. **Enable Competitive Intel**
   - Keep default settings initially
   - Adjust based on performance

5. **Skip Notifications Initially**
   - Get system working first
   - Add notifications later

6. **Save and Test**
   - Click "Save All Changes"
   - Run scout manually
   - Review results
   - Refine settings

### Ongoing Maintenance

**Weekly:**
- Update staff availability
- Add new skills/certifications
- Review keywords (add/remove based on results)

**Monthly:**
- Review NAICS codes (add/remove based on pursuits)
- Adjust value range if needed
- Check competitive intel settings

**Quarterly:**
- Full staff database review
- Update clearance expiry dates
- Refine search parameters based on win rate

---

## Troubleshooting

### "Changes not taking effect"
- Did you click "Save All Changes"?
- Check success message appeared
- Restart dashboard if needed

### "Can't access admin panel"
```
Error: 404 Not Found
```
**Solution:**
- Make sure `templates/admin.html` exists
- Restart dashboard: `python team_dashboard_app.py`

### "Staff changes not saving"
```
Error saving staff member
```
**Solution:**
- Check `data/staff_database.json` exists
- Verify file permissions
- Check logs: `logs/fed_contracting_ai.log`

### "Config preview not updating"
**Solution:**
- Refresh page
- Check browser console for JavaScript errors
- Clear cache: Ctrl+Shift+R (Chrome)

### "Can't add tags (keywords, NAICS, etc.)"
**Solution:**
- Must press **Enter** to add tag
- Type in input field, then Enter
- Click X on tag to remove

---

## Keyboard Shortcuts

- **Enter** - Add tag (keywords, NAICS, skills, etc.)
- **Ctrl+S** - Save all changes (if browser allows)
- **Esc** - Close modal

---

## Security Notes

**Sensitive Data:**
- API keys visible in admin panel
- Email passwords visible (masked on page load)
- Staff hourly rates visible

**Recommendations:**
- Only give admin access to authorized users
- Use app passwords (not regular passwords) for email
- Don't expose admin panel to internet
- Keep dashboard internal network only

**For production:**
- Add authentication
- Use HTTPS
- Implement role-based access
- Encrypt sensitive fields

---

## Quick Reference

| What You Want | Where to Go |
|---------------|-------------|
| Change search keywords | SAM.gov Config → Keywords |
| Add NAICS code | Company Info → NAICS Codes |
| Add team member | Staff Management → Add Staff |
| Update clearance | Staff Management → Edit staff → Clearance |
| Enable email alerts | Notifications → Email → Enable |
| Change lookback days | SAM.gov Config → Lookback Days |
| Disable competitive intel | Competitive Intel → Uncheck Enable |
| Add skill to staff | Staff Management → Edit → Technical Skills |

---

## Tips for Team Adoption

**Week 1: Admin Only**
- Admin sets up configuration
- Adds all staff members
- Tests and refines
- Doesn't give team access yet

**Week 2: Show Team**
- Show main dashboard only
- Explain how opportunities appear
- Get feedback on filtering

**Week 3: Refine Config**
- Admin adjusts based on feedback
- Update keywords
- Refine value range
- Tune competitive intel

**Month 2: Stable**
- Minimal config changes needed
- Staff database kept current
- System runs smoothly

---

## Summary

**Admin Panel Benefits:**
- ✅ No YAML editing required
- ✅ Visual, intuitive interface
- ✅ Real-time preview of changes
- ✅ Easy staff management
- ✅ One-click save

**Access:**
```
http://localhost:5000/admin
```

**Key Actions:**
1. Configure SAM.gov search
2. Add your team (20 staff)
3. Set competitive intel preferences
4. Enable notifications (optional)
5. Save all changes
6. Run scout and review

Your team collaboration system just got even easier to manage! 🎯
