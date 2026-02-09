# SAM.gov API Rate Limit Guide

## Understanding the Rate Limit

SAM.gov has API rate limits to prevent abuse:

**Current Limits (as of 2025):**
- **1,000 requests per day** per API key
- **10 requests per 10 seconds** (burst limit)

**What triggers rate limits:**
- Running diagnostic tool multiple times
- Making many searches in quick succession
- Large pagination (multiple pages of results)
- Running the system repeatedly

## Immediate Solutions

### Solution 1: Use the Rate-Limited Version (Recommended)

Replace `sam_scout.py` with the rate-limited version that includes caching:

```bash
# Backup original
cp sam_scout.py sam_scout_original.py

# Use rate-limited version
cp sam_scout_rate_limited.py sam_scout.py
```

**What this does:**
- ✅ Adds 2-second delay between requests
- ✅ Caches results for 24 hours
- ✅ Automatically retries with exponential backoff
- ✅ Respects "Retry-After" headers
- ✅ Limits pagination to prevent excessive calls

### Solution 2: Wait It Out

**If you've hit the limit:**
- Wait 24 hours for quota to reset
- Quota resets at midnight UTC (7 PM EST / 4 PM PST)

**Check your usage:**
- SAM.gov doesn't provide a usage dashboard
- Track manually or use rate-limited version

### Solution 3: Use Cached Results

The rate-limited version caches results:

```bash
# Check cache directory
ls data/cache/

# Results are cached for 24 hours
# Re-running won't make new API calls if cache is fresh
```

### Solution 4: Optimize Your Searches

**Reduce API calls by:**

1. **Increase lookback days** (one search instead of multiple):
   ```yaml
   lookback_days: 30  # Instead of 7
   ```

2. **Run less frequently:**
   ```bash
   # Instead of multiple times per day, run once daily
   0 9 * * * python main_integrated.py
   ```

3. **Disable competitive intel temporarily:**
   ```bash
   python main_integrated.py --no-intel
   ```

4. **Use broader NAICS codes** (fewer searches):
   ```yaml
   naics_codes:
     - "541512"  # One broader code instead of many specific ones
   ```

## Understanding Rate-Limited Version Features

### 1. Smart Caching

```python
# First run - hits API
python main_integrated.py

# Second run within 24 hours - uses cache (no API calls)
python main_integrated.py
```

**Cache location:** `data/cache/*.json`

**Clear cache manually:**
```bash
# Clear all cache
rm -rf data/cache/*.json

# Or use Python
python -c "from sam_scout import SAMOpportunityScoutRateLimited; s=SAMOpportunityScoutRateLimited(); s.clear_cache()"
```

### 2. Automatic Retry

When rate limited, the system:
1. Detects 429 (Too Many Requests) response
2. Reads "Retry-After" header
3. Waits the specified time
4. Retries automatically (up to 3 times)

### 3. Request Throttling

- 2-second delay between requests
- Prevents burst limit violations
- Pages through results slowly but safely

## Best Practices to Avoid Rate Limits

### Daily Operations

**Do:**
- ✅ Run once or twice daily (morning and evening)
- ✅ Use caching (it's on by default in rate-limited version)
- ✅ Set appropriate lookback_days (7-30)
- ✅ Let the system run slowly - it's designed to avoid limits

**Don't:**
- ❌ Run the diagnostic tool repeatedly
- ❌ Test multiple times in succession
- ❌ Run main script multiple times per hour
- ❌ Use very short lookback periods repeatedly

### Configuration Tweaks

**Optimize in `config.yaml`:**

```yaml
sam_gov:
  search:
    lookback_days: 14  # Sweet spot - not too short, not too long
    
    # Be selective with opportunity types to reduce results
    opportunity_types:
      - "Solicitation"
      - "Presolicitation"
      # Remove "Sources Sought" and "Special Notice" if not needed
    
    # Narrow your search to reduce API load
    value_range:
      min: 100000  # Higher minimum reduces results
      max: 5000000  # Reasonable maximum
```

## Rate Limit Error Messages

### What You'll See

```
⚠️  Rate limit exceeded
Waiting 60 seconds before retry...
```

Or:

```
API error: 429
Response: {"error": "Rate limit exceeded"}
```

### What To Do

1. **Don't panic** - This is normal if testing extensively
2. **Wait** - Let the retry mechanism work
3. **Check cache** - You may already have recent data
4. **Adjust schedule** - Run less frequently

## Monitoring Your Usage

### Create a Usage Log

Add this to track your API calls:

```python
# In your script
import logging

logger = logging.getLogger(__name__)
logger.info(f"API call made at {datetime.now()}")
```

Check logs:
```bash
grep "API call" logs/fed_contracting_ai.log | wc -l
```

### Estimate Your Daily Usage

**Typical usage:**
- 1 search query: 1-10 API calls (depending on pagination)
- Competitive intel per opportunity: 2-3 calls (FPDS + USAspending)
- Full pipeline run: 10-50 calls total

**Daily limit: 1,000 calls**
- Running once daily: ~50 calls = ✅ Safe
- Running 3x daily: ~150 calls = ✅ Safe
- Running 10x daily: ~500 calls = ⚠️ Pushing it
- Testing/diagnostics: Can quickly hit limit

## Alternative: Get Additional API Keys

**If you need higher limits:**

1. **Request increased quota:**
   - Email: sam.gov API support
   - Explain your use case
   - They may grant higher limits

2. **Multiple API keys:**
   - Register with different emails
   - Rotate keys in your config
   - Not officially recommended but possible

3. **Partner with others:**
   - Share results with colleagues
   - One person runs, shares outputs
   - Coordinate to avoid duplicate searches

## Competitive Intelligence Rate Limits

**FPDS and USAspending:**
- Generally more lenient than SAM.gov
- FPDS: ~1,000 requests/day
- USAspending: No published hard limit

**To reduce competitive intel API calls:**

```yaml
competitive_intelligence:
  enabled: true
  triggers:
    min_value: 1000000  # Only run intel on $1M+ opportunities
```

## Emergency: Already Hit the Limit?

### Immediate Actions

1. **Use cached data:**
   ```bash
   # Check what's in cache
   ls -lh data/cache/
   
   # Use existing opportunities files
   ls -lh data/opportunities/
   ```

2. **Process existing data:**
   ```bash
   # If you have opportunities saved, process them
   python claude_agents.py data/opportunities/opportunities_latest.json
   ```

3. **Work offline:**
   - Review existing reports
   - Refine configuration
   - Update staff database
   - Plan next search

4. **Schedule for tomorrow:**
   ```bash
   # Set up cron for next morning after quota resets
   echo "0 7 * * * cd /path/to/system && python main_integrated.py" | crontab -
   ```

## Long-Term Strategy

### Sustainable Daily Operations

**Morning routine (7-9 AM):**
```bash
# One comprehensive search per day
python main_integrated.py
```

**Cache management:**
- Cache lasts 24 hours
- Automatically refreshes daily
- No manual intervention needed

**Monitoring:**
- Check logs weekly
- Review cache hit rate
- Adjust frequency as needed

### Optimize for Your Business

**High-volume pursuer (20+ opps/week):**
- Run twice daily (morning and evening)
- Use 14-day lookback
- Enable full competitive intel

**Selective pursuer (5-10 opps/week):**
- Run once daily
- Use 30-day lookback
- Enable competitive intel on $500K+ only

**Niche market (1-5 opps/week):**
- Run 2-3x per week
- Use 60-day lookback
- Full competitive intel on everything

## Summary

**Key Points:**
1. ✅ SAM.gov limits: 1,000 requests/day
2. ✅ Use rate-limited version with caching
3. ✅ Run once or twice daily, not constantly
4. ✅ Cache is your friend - use it!
5. ✅ Wait 24 hours if you hit the limit

**Quick Fix:**
```bash
# Use the rate-limited version
cp sam_scout_rate_limited.py sam_scout.py

# Run once daily
python main_integrated.py

# Results cached for 24 hours automatically
```

**The system is designed to work within limits - just run it once daily and let caching do its job!**
