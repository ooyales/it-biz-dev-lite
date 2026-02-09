# Setting Up Environment Variables

## 🔒 Why Use .env Files?

**Security Benefits:**
- ✅ API keys never in code
- ✅ Never accidentally committed to git
- ✅ Easy to manage across environments
- ✅ One place to update credentials

## 📝 Quick Setup (2 Minutes)

### Step 1: Install python-dotenv

```bash
pip install python-dotenv
```

### Step 2: Create Your .env File

```bash
cd knowledge_graph

# Copy the template
cp .env.template .env

# Edit with your actual keys
nano .env
# or
code .env
# or
open -e .env
```

### Step 3: Fill In Your Keys

Your `.env` file should look like:

```env
# SAM.gov API Key
SAM_API_KEY=abc123xyz789yourrealkeyhere

# Neo4j Database
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_actual_neo4j_password
NEO4J_DATABASE=contactsgraphdb

# Anthropic API Key
ANTHROPIC_API_KEY=sk-ant-api03-yourrealkeyhere

# Collection Settings
NAICS_CODES=541512,541511,541519
DEFAULT_DAYS_BACK=30
DEFAULT_LIMIT=10
```

### Step 4: Run the Environment-Aware Collector

```bash
# Now just run it - no keys needed!
python collect_env.py --limit 50

# Or
python collect_env.py --limit 100 --days 60
```

## ✅ What's Protected

The `.gitignore` file ensures these are **never** committed:

```
# These files are protected
.env                           # Your credentials
config.yaml                    # Alternative config
processed_opportunities.json   # Your cache
collection_summary.json        # Run summaries
*.key                          # Any key files
*_api_key.txt                 # API key text files
```

## 🔍 Verify It's Working

```bash
cd knowledge_graph

# Check .env exists and has keys
cat .env | grep -v "^#" | grep -v "^$"

# Should show your actual keys (not "your_key_here")
```

## 🚀 Usage Examples

### Basic Run
```bash
# Uses defaults from .env
python collect_env.py
```

### Custom Parameters
```bash
# Override defaults
python collect_env.py --limit 100 --days 60
```

### Clear Cache
```bash
# Start fresh
python collect_env.py --clear-cache
```

## 🎯 Three Collector Versions

You now have **three versions** to choose from:

### 1. `collect_opportunities.py` - Original
```bash
# Requires keys as arguments
python collect_opportunities.py \
  --sam-key YOUR_KEY \
  --neo4j-password YOUR_PASSWORD \
  --anthropic-key YOUR_KEY \
  --limit 50
```

**Pros:** Explicit, no dependencies
**Cons:** Keys in command history, tedious

### 2. `collect_smart.py` - With Deduplication
```bash
# Still requires keys as arguments
python collect_smart.py \
  --sam-key YOUR_KEY \
  --neo4j-password YOUR_PASSWORD \
  --anthropic-key YOUR_KEY \
  --limit 50
```

**Pros:** Skips processed opportunities
**Cons:** Keys in command history

### 3. `collect_env.py` - Environment-Aware ⭐ **RECOMMENDED**
```bash
# Loads from .env automatically
python collect_env.py --limit 50
```

**Pros:** 
- ✅ Secure (no keys in command line)
- ✅ Deduplication (skips processed)
- ✅ Simple to use
- ✅ Easy to manage

**Cons:** Requires `pip install python-dotenv`

## 💡 Best Practices

### DO:
- ✅ Use `.env` files for all secrets
- ✅ Keep `.env` in `.gitignore`
- ✅ Use different `.env` files for dev/prod
- ✅ Document required variables in `.env.template`

### DON'T:
- ❌ Commit `.env` to git
- ❌ Put keys in command-line arguments
- ❌ Hardcode keys in Python files
- ❌ Share `.env` files (share `.env.template` instead)

## 🔧 Troubleshooting

### "Missing environment variables"

```bash
# Check .env exists
ls -la .env

# Check it has content
cat .env

# Make sure keys don't have quotes or extra spaces
# Good: SAM_API_KEY=abc123
# Bad:  SAM_API_KEY="abc123"
# Bad:  SAM_API_KEY = abc123
```

### ".env not found"

```bash
# Must be in knowledge_graph directory
cd knowledge_graph

# Then run
python collect_env.py --limit 10
```

### "python-dotenv not installed"

```bash
pip install python-dotenv
```

## 🎊 You're All Set!

Now you can:
1. ✅ Keep keys secure in `.env`
2. ✅ Run collectors without typing keys
3. ✅ Never worry about exposing credentials
4. ✅ Manage environments easily

**Just run:**
```bash
cd knowledge_graph
python collect_env.py --limit 50
```

Clean, secure, simple! 🔒
