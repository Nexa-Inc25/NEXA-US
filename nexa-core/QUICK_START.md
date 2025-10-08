# ⚡ Nexa Core - Quick Start Guide

## 🎯 Get Your Platform Running in 30 Minutes

### Prerequisites
- ✅ Multi-Spec Analyzer already deployed at `nexa-doc-analyzer-oct2025.onrender.com`
- ✅ GitHub repo: `Nexa-Inc25/NEXA-US`
- ✅ Render account
- ✅ 50 PGE spec PDFs ready

---

## 🚀 Deploy Production Backend (15 minutes)

### Step 1: Deploy Database (5 min)

1. Go to https://dashboard.render.com
2. Click **New +** → **PostgreSQL**
3. Configure:
   ```
   Name: nexa-core-db
   Database: nexa_core
   User: nexa_admin
   Region: Oregon
   Plan: Free (dev) or Starter ($7/month for prod)
   ```
4. Click **Create Database**
5. Wait for "Available" status (~2 min)
6. Copy **Internal Database URL**

7. **Run Migration:**
   ```bash
   # In PowerShell
   cd c:\Users\mikev\CascadeProjects\nexa-inc-mvp\nexa-core
   
   # Replace with your actual DB URL from Render
   $DB_URL = "postgresql://nexa_admin:xxx@dpg-xxx.oregon-postgres.render.com/nexa_core"
   
   psql $DB_URL -f db\schema.sql
   
   # Verify
   psql $DB_URL -c "SELECT COUNT(*) FROM users"
   # Should return: 4
   ```

### Step 2: Deploy API (10 min)

1. **In Render Dashboard:**
   - Click **New +** → **Web Service**
   - Connect your GitHub: `Nexa-Inc25/NEXA-US`

2. **Configure Service:**
   ```
   Name: nexa-core-api
   Root Directory: nexa-core/services/api
   Runtime: Node
   Build Command: npm install
   Start Command: npm start
   Plan: Free (or Starter $7/month)
   ```

3. **Add Environment Variables:**
   ```
   NODE_ENV=production
   PORT=3000
   DATABASE_URL=[Paste Internal DB URL from Step 1]
   JWT_SECRET=[Generate: openssl rand -hex 32 or use any 64-char string]
   ANALYZER_URL=https://nexa-doc-analyzer-oct2025.onrender.com
   MAX_UPLOAD_SIZE_MB=100
   RATE_LIMIT_MAX_REQUESTS=100
   LOG_LEVEL=info
   ```

4. Click **Create Web Service**
5. Wait for deployment (~5-7 min)

6. **Verify:**
   ```bash
   curl https://nexa-core-api.onrender.com/health
   
   # Should return:
   # {
   #   "status": "ok",
   #   "checks": {
   #     "api": "ok",
   #     "database": "ok",
   #     "analyzer": {
   #       "status": "ok",
   #       "spec_learned": true/false
   #     }
   #   }
   # }
   ```

---

## 📚 Upload 50 Spec PDFs (5 min)

### If Multi-Spec Not Deployed Yet:

```bash
# 1. Deploy multi-spec version
cd c:\Users\mikev\CascadeProjects\nexa-inc-mvp

# Go to Render Dashboard
# Find: nexa-doc-analyzer-oct2025
# Click: Manual Deploy
# Wait: 5-7 minutes
```

### Upload Your 50 Specs:

```bash
# Navigate to your spec PDFs folder
cd C:\path\to\your\50\PGE\specs\

# Run batch upload
python c:\Users\mikev\CascadeProjects\nexa-inc-mvp\backend\pdf-service\batch_upload_50_specs.py . --mode replace --batch-size 10

# Expected output:
# 📦 Starting upload of 50 files in 5 batches
# ✅ Batch 1 complete: 10 files, 234 chunks
# ✅ Batch 2 complete: 10 files, 456 chunks total
# ...
# ✅ All 50 files uploaded! Total: 3,247 chunks
```

### Verify Library:

```bash
curl https://nexa-doc-analyzer-oct2025.onrender.com/spec-library | jq

# Should show:
# {
#   "total_files": 50,
#   "total_chunks": 3000+,
#   "files": [...]
# }
```

---

## 🧪 Test Your Platform (5 min)

### Test 1: Get QA API Key

```bash
# Connect to database
$DB_URL = "your_db_url_here"
psql $DB_URL

# Get QA API key
nexa_core=> SELECT name, email, api_key FROM users WHERE role='qa';

# Output:
#     name     |    email     |      api_key       
# -------------+--------------+--------------------
# Sarah Davis  | qa@nexa.com  | qa_test_key_789

# Copy the api_key
\q
```

### Test 2: Contest a Go-Back

```bash
# Replace with your actual go-back PDF path
$PDF_PATH = "C:\path\to\QA25-35601253-120424794-Alvah-GOBACK1.pdf"

# Upload and analyze
curl -X POST https://nexa-core-api.onrender.com/api/audits/contest `
  -H "X-API-Key: qa_test_key_789" `
  -F "submission_id=1" `
  -F "pge_reference_number=TEST-GOBACK-001" `
  -F "pge_inspector=Test Inspector" `
  -F "audit_pdf=@$PDF_PATH"

# Expected response:
# {
#   "success": true,
#   "audit": {
#     "id": 1,
#     "uuid": "...",
#     "contestable": true
#   },
#   "analysis": [
#     {
#       "infraction": "Go-back: Incorrect cable spacing",
#       "status": "REPEALABLE",
#       "confidence": 87.5,
#       "match_count": 3,
#       "reasons": [
#         "[Source: 057875_Secondary_Aerial_Cable.pdf] Minimum separation 6ft...",
#         "[Source: 015225_Cutouts_Fuses.pdf] Exception for rack construction...",
#         "[Source: 092813_FuseSaver.pdf] Single-phase tap allowance..."
#       ]
#     }
#   ],
#   "summary": {
#     "total_infractions": 1,
#     "repealable_count": 1,
#     "high_confidence_count": 1,
#     "recommendation": "CONTEST_RECOMMENDED"
#   }
# }
```

### Test 3: View Contestable Audits

```bash
curl https://nexa-core-api.onrender.com/api/audits/contestable `
  -H "X-API-Key: qa_test_key_789" | jq

# Should show the audit you just created
```

---

## ✅ Success Checklist

After completing the above steps, you should have:

- [x] Database deployed with schema
- [x] API deployed and healthy
- [x] Analyzer loaded with 50 specs
- [x] End-to-end test successful
- [x] Contestable audits working

---

## 🎯 What You Have Now

### Working Features:

1. **Contest Engine** (Core Feature)
   - Upload PGE go-back PDF
   - Analyzer returns repeal analysis
   - Source tracking shows which specs matched
   - Auto-flagged as contestable if confidence >70%

2. **API Endpoints** (All Functional)
   - `/api/audits/contest` - Analyze go-backs
   - `/api/audits/contestable` - List contestable
   - `/api/jobs` - Job management
   - `/api/submissions` - As-built submissions
   - `/api/users` - User management
   - `/health` - System health

3. **Database** (Production Ready)
   - User roles (GF, foreman, QA, admin)
   - Job tracking
   - Submission management
   - Audit records
   - Row-level security

4. **Multi-Spec Analyzer** (Deployed)
   - 50 spec PDFs loaded
   - Source tracking enabled
   - 1-3s analysis time
   - OCR support

---

## 📅 Next Steps (Week by Week)

### This Week: Core Backend ✅
- [x] Deploy database
- [x] Deploy API
- [x] Upload specs
- [x] Test end-to-end
- [x] **YOU ARE HERE** 👈

### Next Week: QA Dashboard
Build React web app:
```bash
cd apps/web
npx create-react-app . --template typescript
npm install axios @tanstack/react-query tailwindcss

# Key pages:
# 1. Login page
# 2. Contest upload interface
# 3. Results display with spec citations
# 4. Contest management
```

**Deploy:**
- Render Static Site
- Connect to API

### Week 3-4: Mobile App
Build React Native app:
```bash
cd apps/mobile
npx create-expo-app@latest .

# Key features:
# 1. QR code scanning
# 2. As-built forms
# 3. Photo capture
# 4. Offline queue
```

**Test:**
- Expo Go on Android/iOS
- Build APK/IPA

### Week 5: Launch
- Upgrade to Starter tier ($21/month)
- Load testing
- User training
- Go live!

---

## 💡 Development Workflow

### Local Development

```bash
# Terminal 1: API
cd nexa-core/services/api
npm run dev
# API: http://localhost:3000

# Terminal 2: Web (future)
cd nexa-core/apps/web
npm start
# Web: http://localhost:3001

# Terminal 3: Database (Docker)
docker run -p 5432:5432 -e POSTGRES_PASSWORD=password postgres:15
```

### Test with Postman

1. **Import endpoints:**
   - Base URL: `http://localhost:3000` or `https://nexa-core-api.onrender.com`
   - Auth: Header `X-API-Key: qa_test_key_789`

2. **Test sequence:**
   ```
   1. GET /health (no auth)
   2. GET /api/users/me (with API key)
   3. POST /api/audits/contest (upload PDF)
   4. GET /api/audits/contestable
   ```

---

## 🐛 Troubleshooting

### Database Connection Failed
```bash
# Check database status in Render dashboard
# Verify DATABASE_URL in API service environment

# Test connection manually:
psql $DATABASE_URL -c "SELECT 1"
```

### API Not Responding
```bash
# Check logs in Render dashboard
# Verify all environment variables set
# Check health endpoint:
curl https://nexa-core-api.onrender.com/health
```

### Analyzer Not Found
```bash
# Verify analyzer is deployed:
curl https://nexa-doc-analyzer-oct2025.onrender.com/health

# Check ANALYZER_URL in API environment variables
```

### 401 Unauthorized
```bash
# Verify API key from database:
psql $DB_URL -c "SELECT api_key FROM users WHERE role='qa'"

# Use exact key in header:
-H "X-API-Key: qa_test_key_789"
```

---

## 📊 Monitoring

### Health Checks

```bash
# API health
curl https://nexa-core-api.onrender.com/health

# Analyzer health
curl https://nexa-doc-analyzer-oct2025.onrender.com/health

# Database connection count
psql $DB_URL -c "SELECT count(*) FROM pg_stat_activity"
```

### Set Up Monitoring

1. **UptimeRobot** (Free)
   - Sign up: https://uptimerobot.com
   - Add monitor: `https://nexa-core-api.onrender.com/health`
   - Interval: 5 minutes
   - Alert: Email when down

2. **Render Dashboard**
   - Metrics tab shows CPU/memory/requests
   - Logs show real-time activity
   - Events show deployments/restarts

---

## 💰 Current Costs

### Free Tier (What You Have Now)
- Database: $0
- API: $0
- Analyzer: $0 or $7
- **Total: $0-7/month**

**Good for:** MVP, testing, light usage

### Recommended for Production
- Database: $7/month (Starter)
- API: $7/month (Starter)
- Analyzer: $7/month (Starter)
- **Total: $21/month**

**Benefits:**
- No cold starts
- Better performance
- Persistent disk
- More RAM/CPU

---

## 🎉 Congratulations!

You now have:
- ✅ **Production-ready API**
- ✅ **Multi-spec analyzer with 50 PDFs**
- ✅ **Complete workflow implementation**
- ✅ **Database with security**
- ✅ **Contest engine working**

**Your platform is LIVE and ready to contest go-backs!**

---

## 📞 Quick Reference

### URLs
- **API:** `https://nexa-core-api.onrender.com`
- **Analyzer:** `https://nexa-doc-analyzer-oct2025.onrender.com`
- **Render:** `https://dashboard.render.com`

### Test Credentials
```
QA User:
  Email: qa@nexa.com
  API Key: qa_test_key_789

General Foreman:
  Email: gf@nexa.com
  API Key: gf_test_key_123

Crew Foreman:
  Email: foreman@nexa.com
  API Key: foreman_test_key_456
```

### Key Endpoints
```
Contest:      POST /api/audits/contest
Contestable:  GET  /api/audits/contestable
Health:       GET  /health
Spec Library: GET  https://nexa-doc-analyzer-oct2025.onrender.com/spec-library
```

### Documentation
- `README.md` - Architecture overview
- `GETTING_STARTED.md` - Detailed setup
- `DEPLOYMENT_PLAN.md` - Production deployment
- `IMPLEMENTATION_SUMMARY.md` - Complete feature list

---

## 🚀 Start Building!

Your backend is live. Your analyzer is working. Your database is ready.

**Next:** Build the QA dashboard to visualize these results!

```bash
cd apps/web
npx create-react-app . --template typescript
# Start building the UI!
```

Good luck! 🎊
