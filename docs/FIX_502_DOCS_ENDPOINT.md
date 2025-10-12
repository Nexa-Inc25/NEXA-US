# 🔧 Fix 502 Bad Gateway on /docs Endpoint

## Current Status
- ✅ Root endpoint working: `https://nexa-doc-analyzer-oct2025.onrender.com/`
- ✅ API is functional (returns JSON with app info)
- ❌ `/docs` throwing 502 Bad Gateway

## Root Cause
**Free Tier Limitations:**
- Cold start timeout (~30s limit)
- Swagger UI generation is heavy (OpenAPI JSON + model loading)
- Proxy connection timeout during docs rendering
- Your app loads model in ~5s, but /docs adds overhead

## Immediate Fixes (Priority Order)

### Fix 1: Set PORT Environment Variable (CRITICAL)
**Why:** Stops restart loops from "New primary port detected"

**Steps:**
1. Go to Render Dashboard: https://dashboard.render.com
2. Select: `nexa-doc-analyzer-oct2025`
3. Click: **Environment** tab
4. Click: **Add Environment Variable**
5. Add:
   - Key: `PORT`
   - Value: `8000`
6. Click: **Save Changes**
7. Click: **Manual Deploy**

**Expected Result:** Logs should stop showing port detection restarts.

---

### Fix 2: Upgrade to Starter Plan ($7/month) (RECOMMENDED)
**Why:** Eliminates cold starts, more resources for model + Swagger

**Benefits:**
- No cold starts (always-on)
- More RAM (512MB → 1GB+)
- Better CPU allocation
- Stable /docs endpoint
- Better for production use with your 50 spec PDFs

**Steps:**
1. Dashboard → Billing → Upgrade Service
2. Select: **Starter** ($7/month)
3. Confirm upgrade
4. Service auto-redeploys

**Cost-Benefit:**
- $7/month vs hours debugging free tier issues
- Required for production reliability
- Persistent disk included (your /data storage)

---

### Fix 3: Test OpenAPI Generation
**Diagnose if issue is docs-specific or JSON generation:**

```bash
# Test raw OpenAPI schema
curl https://nexa-doc-analyzer-oct2025.onrender.com/openapi.json

# If this works but /docs fails → Browser/UI issue
# If this 502s → OpenAPI generation timeout
```

---

### Fix 4: Disable Swagger UI (Temporary Workaround)
**Only if you don't need the web UI for testing**

Edit `app_oct2025_enhanced.py`:

```python
# BEFORE:
app = FastAPI(
    title="NEXA AI Document Analyzer",
    version="1.0.0 (Oct 2025 Enhanced)"
)

# AFTER (disables /docs and /redoc):
app = FastAPI(
    title="NEXA AI Document Analyzer",
    version="1.0.0 (Oct 2025 Enhanced)",
    docs_url=None,  # Disables /docs
    redoc_url=None  # Disables /redoc
)
```

**When to use:**
- You don't need Swagger UI
- You're using Python scripts or Postman instead
- Temporary until you upgrade to paid tier

**Re-enable later:**
Just remove `docs_url=None` and `redoc_url=None`

---

### Fix 5: Warm-Up Strategy (Free Tier Only)
**Keep service "warm" to avoid cold starts:**

```bash
# Create a cron job or schedule to ping every 10 minutes
curl https://nexa-doc-analyzer-oct2025.onrender.com/health
```

**Options:**
- UptimeRobot (free monitoring service)
- GitHub Actions with scheduled workflow
- Render Cron Job (requires paid plan)

---

## Testing After Fixes

### 1. Verify Endpoints Work
```bash
# Health check
curl https://nexa-doc-analyzer-oct2025.onrender.com/health

# Root info
curl https://nexa-doc-analyzer-oct2025.onrender.com/

# OpenAPI schema
curl https://nexa-doc-analyzer-oct2025.onrender.com/openapi.json
```

### 2. Check Swagger UI
Open in browser:
```
https://nexa-doc-analyzer-oct2025.onrender.com/docs
```

Should see interactive FastAPI documentation.

### 3. Monitor Logs
Dashboard → Logs → Look for:
- ✅ No "New primary port detected" messages
- ✅ "Uvicorn running on http://0.0.0.0:8000"
- ✅ No 502 errors on /docs requests
- ✅ Model loads successfully

---

## Understanding the 502

### Why Root Works But /docs Fails

| Endpoint | Load Time | Complexity | Free Tier Result |
|----------|-----------|------------|------------------|
| `/` | <1s | Simple JSON | ✅ Works |
| `/health` | <1s | Status check | ✅ Works |
| `/openapi.json` | 2-5s | Generate schema | ⚠️ Might timeout |
| `/docs` | 5-10s | Schema + Swagger UI | ❌ 502 on cold start |

### Cold Start Timeline (Free Tier)
```
0s:  Request arrives → Wake container
2s:  Python starts
5s:  Model loading (sentence-transformers)
7s:  App initialization
10s: /docs tries to render
15s: Swagger UI loading
20s: 502 timeout from proxy
```

### Starter Tier Timeline
```
0s:  Request arrives (already running!)
0.1s: /docs renders (cached model)
0.5s: Swagger UI displays
```

---

## Recommended Solution Path

**For Development/Testing:**
1. Set PORT env var (fixes restarts)
2. Disable /docs temporarily
3. Use Python scripts or Postman for API testing

**For Production:**
1. Upgrade to Starter ($7/month)
2. Set PORT env var
3. Keep /docs enabled for team access
4. Add persistent disk for your 50 spec PDFs

---

## Alternative: Use ReDoc Instead
ReDoc is lighter than Swagger UI:

```python
app = FastAPI(
    title="NEXA AI Document Analyzer",
    version="1.0.0 (Oct 2025 Enhanced)",
    docs_url=None,  # Disable heavy Swagger
    redoc_url="/docs"  # Use ReDoc at /docs instead
)
```

Access at: `https://nexa-doc-analyzer-oct2025.onrender.com/docs`

---

## When to Worry vs When It's Normal

### ❌ Concerning Signs:
- 502 on `/` or `/health` (core app broken)
- 502 persists after upgrade to Starter
- OOM (Out of Memory) errors in logs
- Constant restarts

### ✅ Expected Behavior (Free Tier):
- 502 on /docs during cold start
- First request slow (10-30s)
- Service sleeps after 15min inactivity
- Port detection messages

---

## Next Steps

1. **Immediate:** Add PORT=8000 env var → Manual deploy
2. **Short-term:** Test if /docs works after warm-up
3. **Long-term:** Upgrade to Starter for production use

Your API is **working correctly** - this is purely a Render free tier limitation, not a code issue!
