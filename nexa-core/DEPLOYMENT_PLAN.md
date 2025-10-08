# 🚀 Nexa Core - Production Deployment Plan

## Current State

### ✅ PRODUCTION-READY Components

1. **Multi-Spec Analyzer** (Already Live)
   - URL: `https://nexa-doc-analyzer-oct2025.onrender.com`
   - Status: ✅ Deployed and tested
   - Specs: Ready to load 50 PDFs
   - Features: Source tracking, OCR, CPU-optimized
   - Performance: 1-3s analysis time

2. **Database Schema** (Ready to Deploy)
   - File: `db/schema.sql`
   - Status: ✅ Complete with RLS
   - Tables: Users, Jobs, Submissions, Audits, Spec Library
   - Security: Row-level security for data isolation

3. **API Service** (Ready to Deploy)
   - Framework: Node.js + Express
   - Status: ✅ Core routes implemented
   - Key Feature: `/api/audits/contest` (analyzer integration)
   - Auth: JWT + API keys

---

## 🎯 Immediate Deployment (TODAY)

### Step 1: Deploy Database (5 minutes)

**On Render.com:**

1. Go to https://dashboard.render.com
2. Click **New +** → **PostgreSQL**
3. Configure:
   ```
   Name: nexa-core-db
   Database: nexa_core
   User: nexa_admin
   Region: Oregon (same as analyzer)
   Plan: Free (for dev) or Starter ($7/month for prod)
   ```
4. Click **Create Database**
5. Wait for "Available" status
6. Copy **Internal Database URL**

**Run Migration:**
```bash
# Copy the Internal Database URL from Render
psql "postgresql://nexa_admin:password@dpg-xxx.oregon-postgres.render.com/nexa_core" < db/schema.sql

# Verify
psql "your_db_url" -c "SELECT COUNT(*) FROM users"
# Should return: 4 (from seed data)
```

### Step 2: Deploy API Service (10 minutes)

**On Render.com:**

1. Click **New +** → **Web Service**
2. Connect your GitHub repo: `Nexa-Inc25/NEXA-US`
3. Configure:
   ```
   Name: nexa-core-api
   Root Directory: nexa-core/services/api
   Runtime: Node
   Build Command: npm install
   Start Command: npm start
   Plan: Free (or Starter $7/month for production)
   ```

4. **Environment Variables:**
   ```
   NODE_ENV=production
   PORT=3000
   DATABASE_URL=[From Step 1 - Internal Database URL]
   JWT_SECRET=[Generate with: openssl rand -hex 32]
   ANALYZER_URL=https://nexa-doc-analyzer-oct2025.onrender.com
   MAX_UPLOAD_SIZE_MB=100
   RATE_LIMIT_MAX_REQUESTS=100
   ENABLE_SWAGGER_DOCS=true
   LOG_LEVEL=info
   ```

5. Click **Create Web Service**
6. Wait for deployment (~5-7 minutes)

**Verify Deployment:**
```bash
# Health check
curl https://nexa-core-api.onrender.com/health

# Expected response:
{
  "status": "ok",
  "checks": {
    "api": "ok",
    "database": "ok",
    "analyzer": {
      "status": "ok",
      "spec_learned": true
    }
  }
}
```

### Step 3: Upload 50 Specs to Analyzer (5 minutes)

Your analyzer is deployed but needs the 50 spec PDFs:

```bash
# Run the multi-spec deployment script
cd c:\Users\mikev\CascadeProjects\nexa-inc-mvp

# Upload your 50 PGE spec PDFs
python backend/pdf-service/batch_upload_50_specs.py C:\path\to\50\specs\ --mode replace --batch-size 10

# Verify
curl https://nexa-doc-analyzer-oct2025.onrender.com/spec-library | jq
# Should show: "total_files": 50
```

---

## 🧪 Test End-to-End Workflow (10 minutes)

### Test 1: Get QA API Key

```bash
# Connect to your Render database
psql "your_render_db_url"

# Get QA user API key
SELECT api_key FROM users WHERE role='qa' LIMIT 1;
# Copy the key (e.g., 'qa_test_key_789')
```

### Test 2: Contest a Go-Back

```bash
# Upload a real PGE go-back PDF
curl -X POST https://nexa-core-api.onrender.com/api/audits/contest \
  -H "X-API-Key: qa_test_key_789" \
  -F "submission_id=1" \
  -F "pge_reference_number=TEST-GOBACK-001" \
  -F "pge_inspector=Test Inspector" \
  -F "audit_pdf=@C:\path\to\QA25-35601253-120424794-Alvah-GOBACK1.pdf"

# Expected response:
{
  "success": true,
  "audit": {
    "id": 1,
    "uuid": "...",
    "contestable": true
  },
  "analysis": [
    {
      "infraction": "Go-back: Incorrect secondary aerial cable spacing",
      "status": "REPEALABLE",
      "confidence": 87.5,
      "match_count": 3,
      "reasons": [
        "[Source: 057875_Secondary_Aerial_Cable.pdf] Minimum separation...",
        "[Source: 015225_Cutouts_Fuses.pdf] For secondary in rack...",
        "[Source: 092813_FuseSaver.pdf] Exception for single-phase..."
      ]
    }
  ],
  "summary": {
    "total_infractions": 1,
    "repealable_count": 1,
    "high_confidence_count": 1,
    "recommendation": "CONTEST_RECOMMENDED"
  }
}
```

### Test 3: View Contestable Audits

```bash
curl https://nexa-core-api.onrender.com/api/audits/contestable \
  -H "X-API-Key: qa_test_key_789" | jq

# Should show the audit you just created
```

---

## 📊 Deployment Summary

### Free Tier (Development)
- **Database**: Render Postgres Free
- **API**: Render Web Service Free
- **Analyzer**: Already deployed (Free or paid?)
- **Total Cost**: $0/month

### Starter Tier (Production)
- **Database**: Render Postgres Starter ($7/month)
- **API**: Render Web Service Starter ($7/month)
- **Analyzer**: Render Web Service Starter ($7/month)
- **Total Cost**: $21/month

### Recommended for Launch
- **Database**: Starter (persistence + backups)
- **API**: Starter (no cold starts)
- **Analyzer**: Starter (already recommended)
- **Total**: $21/month for stable production

---

## 🎯 Phase 2: Frontend Development (Next Week)

### Web Dashboard (React)

**Deploy as Render Static Site:**

```bash
cd apps/web
npx create-react-app . --template typescript
npm install @tanstack/react-query axios zustand tailwindcss

# Key pages:
# 1. QA Dashboard
#    - List contestable audits
#    - Upload go-back PDF
#    - View analyzer results
#    - File contest with PGE

# 2. GF Dashboard
#    - Create jobs
#    - Assign foremen
#    - Generate QR codes

# Deploy:
# Render Dashboard → New → Static Site
# Build Command: npm run build
# Publish Directory: build
```

### Mobile App (React Native + Expo)

**Build & Test:**

```bash
cd apps/mobile
npx create-expo-app@latest .
npm install @react-navigation/native expo-camera expo-file-system

# Key features:
# 1. Scan QR to load job
# 2. Fill as-built form
# 3. Capture photos
# 4. Submit (queue offline)

# Deploy:
# expo build:android
# expo build:ios
```

---

## 🔐 Security Checklist

### Before Production Launch

- [ ] Change all default API keys in database
- [ ] Generate strong JWT_SECRET (32+ chars)
- [ ] Enable HTTPS only (Render does this automatically)
- [ ] Set up proper CORS origins (not '*')
- [ ] Add rate limiting per user (currently per IP)
- [ ] Enable database backups
- [ ] Set up monitoring (Sentry, DataDog)
- [ ] Add logging aggregation
- [ ] Configure proper RLS policies
- [ ] Audit user permissions

---

## 📈 Scaling Plan

### Phase 1: MVP (Weeks 1-2)
- **Users**: 5-10 QA staff
- **Load**: 50-100 audits/month
- **Cost**: $0-21/month
- **Tier**: Free or Starter

### Phase 2: Production (Months 1-3)
- **Users**: 20-50 field staff
- **Load**: 500-1000 audits/month
- **Cost**: $40-60/month
- **Tier**: Starter with auto-scaling

### Phase 3: Scale (Months 3-6)
- **Users**: 100+ field staff
- **Load**: 2000+ audits/month
- **Cost**: $100-200/month
- **Tier**: Standard with dedicated resources

---

## 🎯 Success Metrics

### Week 1 (MVP)
- [ ] API deployed and healthy
- [ ] Database migrated with seed data
- [ ] Analyzer loaded with 50 specs
- [ ] End-to-end test successful
- [ ] 1 real go-back analyzed

### Month 1 (Beta)
- [ ] Web dashboard deployed
- [ ] 5 QA users onboarded
- [ ] 10 go-backs contested
- [ ] >80% analyzer confidence on average
- [ ] <3s average analysis time

### Month 3 (Production)
- [ ] Mobile app deployed
- [ ] 20+ field staff using system
- [ ] 100+ audits processed
- [ ] >70% of go-backs overturned
- [ ] 99% uptime

---

## 🚨 Rollback Plan

### If Deployment Fails

**Database Rollback:**
```bash
# Restore from backup
pg_restore -d nexa_core < backup.dump

# Or redeploy schema
psql $DATABASE_URL < db/schema.sql
```

**API Rollback:**
```bash
# In Render Dashboard:
# 1. Go to nexa-core-api
# 2. Click "Rollback to previous deploy"
```

**Analyzer Rollback:**
```bash
# Already have backup: app_oct2025_enhanced_BACKUP.py
# See previous deployment docs
```

---

## 📞 Post-Deployment Checklist

### Immediate (After Deploy)
- [ ] Test /health endpoint
- [ ] Verify database connection
- [ ] Check analyzer integration
- [ ] Upload 50 spec PDFs
- [ ] Run end-to-end test
- [ ] Monitor logs for errors

### Within 24 Hours
- [ ] Set up UptimeRobot monitoring
- [ ] Configure alert emails
- [ ] Test from different networks
- [ ] Load test with 10 simultaneous requests
- [ ] Document API endpoints
- [ ] Share API docs with team

### Within 1 Week
- [ ] Deploy web dashboard
- [ ] Onboard first QA users
- [ ] Process real go-backs
- [ ] Gather feedback
- [ ] Iterate on UX
- [ ] Plan mobile app development

---

## 🎉 You're Ready to Deploy!

**Timeline:**
- ⏱️ Database: 5 minutes
- ⏱️ API: 10 minutes
- ⏱️ Specs Upload: 5 minutes
- ⏱️ Testing: 10 minutes
- **Total: 30 minutes to production!**

**Next Action:**
1. Go to https://dashboard.render.com
2. Create PostgreSQL database
3. Run migration
4. Deploy API service
5. Upload 50 specs
6. Test with real go-back

Your multi-spec analyzer is already working. Database schema is complete. API is ready. **Just deploy and test!** 🚀
