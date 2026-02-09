# Contact Sync Guide

## 🔗 Syncing Neo4j Contacts to Contact Management Page

Your system has two contact databases:
- **Neo4j Knowledge Graph** - 200+ contacts from SAM.gov collection
- **SQLite Database** - Used by the Contact Management page (currently empty)

The sync script bridges them!

## 🚀 Quick Start

```bash
# Copy the sync script
cp /mnt/user-data/outputs/sync_contacts.py .

# Preview what will be synced (dry run)
python sync_contacts.py --preview

# Sync all contacts
python sync_contacts.py

# Or clear SQLite and do a fresh sync
python sync_contacts.py --clear
```

## 📊 What You'll See

```
======================================================================
NEO4J TO SQLITE CONTACT SYNC
======================================================================

✓ Connected to Neo4j
✓ SQLite database ready
→ SQLite currently has 0 contacts
→ Fetching contacts from Neo4j...
✓ Found 200 contacts in Neo4j

→ Syncing 200 contacts...

======================================================================
SYNC COMPLETE
======================================================================

Created: 200 new contacts
Updated: 0 existing contacts
Skipped: 0 contacts

SQLite now has: 200 total contacts

✓ Contact sync complete!

View contacts at: http://localhost:8080/contacts
```

## 🎯 How It Works

### What Gets Synced

From Neo4j Person nodes:
- ✅ Name
- ✅ Email
- ✅ Phone
- ✅ Organization (from WORKS_AT relationship or property)
- ✅ Title/Role
- ✅ Notes (includes source, role type, influence level)
- ✅ Relationship Strength (mapped from influence level)

### Intelligent Merging

The script:
1. **Checks for existing contacts** by email or name
2. **Updates** if contact exists (won't create duplicates)
3. **Creates** if contact is new
4. **Preserves** SQLite data when updating (doesn't overwrite with blanks)

### Mapping Logic

**Relationship Strength:**
```
Neo4j Influence → SQLite Strength
─────────────────────────────────
Very High        → Strong
High             → Strong
Medium           → Warm
Low              → New
None             → New
```

**Organization:**
```
Priority:
1. Neo4j WORKS_AT relationship (most accurate)
2. Neo4j organization property
3. "Unknown" if neither exists
```

**Notes Field:**
```
Includes:
- Source (where we found them)
- Role Type (Decision Maker, Technical Lead, etc.)
- Influence Level
- Extraction timestamp
```

## 💡 Usage Scenarios

### Scenario 1: First Time Setup
```bash
# You have 200 contacts in Neo4j, 0 in SQLite
python sync_contacts.py

# Result: 200 contacts in SQLite now!
```

### Scenario 2: After Collecting More
```bash
# You collected 50 more opportunities
cd knowledge_graph
python collect_env.py --limit 50

# Now sync the new contacts
cd ..
python sync_contacts.py

# Result: New contacts added, existing ones updated
```

### Scenario 3: Fresh Start
```bash
# Clear everything and re-sync
python sync_contacts.py --clear

# Result: Clean slate with current Neo4j data
```

### Scenario 4: Check Before Syncing
```bash
# Preview mode - see what would happen
python sync_contacts.py --preview

# Shows you:
# - How many contacts would be created
# - How many would be updated
# - No actual changes made
```

## 🔄 Keeping Them In Sync

### Option 1: Manual Sync
Run the sync script whenever you collect new opportunities:
```bash
python collect_env.py --limit 25
python sync_contacts.py
```

### Option 2: Automated Sync (Add to Dashboard)
I can add a "Sync Contacts" button to the dashboard that runs this automatically!

### Option 3: Real-Time Sync
Or we could modify the contact management page to read directly from Neo4j (no sync needed!)

## 📈 Benefits

### Before Sync
```
Contact Management Page: Empty
Neo4j: 200+ contacts

Problem: Can't use the nice UI to manage contacts
```

### After Sync
```
Contact Management Page: 200+ contacts
Neo4j: 200+ contacts (still there)

Benefits:
✅ Use the UI to view/edit contacts
✅ Search and filter
✅ Add interactions and notes
✅ Track relationship strength
✅ Export to CSV
```

## ⚠️ Important Notes

### What Gets Updated
When syncing an existing contact:
- ✅ Phone (if new value exists)
- ✅ Organization (always updated)
- ✅ Role (always updated)
- ✅ Notes (always updated - overwrites!)
- ✅ Relationship Strength (always updated)

### What Doesn't Get Updated
- ❌ Name (kept as-is)
- ❌ Email (kept as-is)
- ❌ Custom notes you added in SQLite (will be overwritten!)

### Best Practice
If you add custom notes in the Contact Management UI, the sync will overwrite them. 

**Solution:** We can enhance the script to append instead of replace notes. Want that?

## 🎨 Future Enhancements

### 1. Bi-directional Sync
Sync changes FROM SQLite back TO Neo4j:
```bash
python sync_contacts.py --bidirectional
```

### 2. Selective Sync
Sync only specific organizations or roles:
```bash
python sync_contacts.py --org "Department of Defense"
python sync_contacts.py --role "Decision Maker"
```

### 3. Dashboard Integration
Add a "Sync Contacts" button in the UI:
```
Contact Management Page
├─ [+ Add Contact]
├─ [📥 Import CSV]
├─ [🔄 Sync from Neo4j]  ← NEW!
```

### 4. Auto-Sync
Run sync automatically when collecting opportunities:
```bash
python collect_env.py --limit 50 --auto-sync
```

### 5. Conflict Resolution
Show conflicts when SQLite has newer data:
```
Contact: John Smith
Neo4j Title: Program Manager
SQLite Title: Senior Program Manager (updated 2 days ago)

Which to keep? [N]eo4j, [S]QLite, [M]erge: 
```

## 🚀 Ready to Sync?

```bash
# Copy the script
cp /mnt/user-data/outputs/sync_contacts.py .

# Run it!
python sync_contacts.py

# Then visit
open http://localhost:8080/contacts
```

**Your 200+ Neo4j contacts will now appear in the Contact Management UI!** 🎉
