# 🚀 Nexa Core - Getting Started Guide

## ✅ What's Been Created

Your Nexa Core platform foundation is ready! Here's what we've built:

### 📁 Directory Structure
```
nexa-core/
├── apps/
│   ├── mobile/          # React Native app (to be built)
│   └── web/             # React dashboard (to be built)
├── services/
│   ├── api/             # ✅ Node.js API (READY)
│   ├── analyzer/        # Links to existing multi-spec service
│   └── data-lake/       # S3/SQS handlers (to be built)
├── db/
│   └── schema.sql       # ✅ Complete database schema (READY)
├── infra/
│   └── docker-compose.yml  # ✅ Local development stack (READY)
└── docs/
```

### ✅ Core Components Ready

1. **Database Schema** (`db/schema.sql`)
   - Users & roles (GF, crew_foreman, QA, admin)
   - Jobs & scheduling
   - Submissions (as-builts from field)
   - Audits & go-backs
   - Spec library integration
   - Row-Level Security (RLS) for data isolation

2. **API Service** (`services/api/`)
   - Express.js server with authentication
   - JWT + API key support
   - Analyzer integration route (`/api/audits/contest`)
   - Health monitoring
   - Rate limiting
   - Error handling

3. **Analyzer Integration**
   - Already deployed: `nexa-doc-analyzer-oct2025.onrender.com`
   - Multi-spec v2.0 with 50-PDF library support
   - Source tracking for spec citations
   - API route ready to call analyzer

---

## 🎯 Quick Start (15 Minutes)

### Step 1: Setup Database (3 minutes)

```bash
# Option A: Local Postgres
createdb nexa_core_dev
psql nexa_core_dev < db/schema.sql

# Option B: Render Postgres (Production)
# 1. Go to https://dashboard.render.com
# 2. New → PostgreSQL
# 3. Name: nexa-core-db
# 4. Plan: Free (for dev)
# 5. Copy DATABASE_URL
# 6. Run migration:
psql "your_render_database_url" < db/schema.sql
```

### Step 2: Configure Environment (2 minutes)

```bash
# Copy environment template
cd nexa-core
copy .env.example .env

# Edit .env with your values:
# - DATABASE_URL (from step 1)
# - JWT_SECRET (generate: openssl rand -hex 32)
# - ANALYZER_URL (already set: nexa-doc-analyzer-oct2025.onrender.com)
```

### Step 3: Install Dependencies (5 minutes)

```bash
# Root dependencies
npm install

# API service
cd services/api
npm install
cd ../..
```

### Step 4: Start API Server (1 minute)

```bash
# Local development
cd services/api
npm run dev

# Should see:
# 🚀 Nexa Core API listening on port 3000
# 📊 Environment: development
# 🔗 Analyzer Service: https://nexa-doc-analyzer-oct2025.onrender.com
# 💾 Database: Connected
```

### Step 5: Test the API (2 minutes)

```bash
# Health check
curl http://localhost:3000/health

# Should return:
# {
#   "status": "ok",
#   "checks": {
#     "api": "ok",
#     "database": "ok",
#     "analyzer": {
#       "status": "ok",
#       "spec_learned": true
#     }
#   }
# }
```

---

## 🔑 Core Workflow Implementation

### 1. Contest a Go-Back (QA Use Case)

This is your KEY feature - QA analyzing PGE go-backs with the multi-spec analyzer:

```bash
# Get QA API key from database
psql $DATABASE_URL -c "SELECT api_key FROM users WHERE role='qa' LIMIT 1"
# Copy the api_key (e.g., 'qa_test_key_789')

# Upload PGE go-back PDF for analysis
curl -X POST http://localhost:3000/api/audits/contest \
  -H "X-API-Key: qa_test_key_789" \
  -F "submission_id=1" \
  -F "pge_reference_number=PGE-GOBACK-2025-001" \
  -F "pge_inspector=John Inspector" \
  -F "audit_pdf=@path/to/pge_go_back.pdf"

# Response:
{
  "success": true,
  "audit": {
    "id": 1,
    "uuid": "abc-123-def",
    "contestable": true
  },
  "analysis": [
    {
      "infraction": "Go-back: Incorrect secondary aerial cable spacing",
      "status": "REPEALABLE",
      "confidence": 87.5,
      "match_count": 3,
      "reasons": [
        "[Source: 057875_Secondary_Aerial_Cable.pdf] Minimum separation from cutouts...",
        "[Source: 015225_Cutouts_Fuses.pdf] For secondary in rack construction...",
        "[Source: 092813_FuseSaver.pdf] Exception for single-phase taps..."
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

### 2. View Contestable Audits

```bash
# Get all go-backs that should be contested
curl http://localhost:3000/api/audits/contestable \
  -H "X-API-Key: qa_test_key_789"

# Response:
{
  "count": 5,
  "audits": [
    {
      "id": 1,
      "submission_uuid": "...",
      "job_number": "JOB-2025-001",
      "location": {"address": "123 Main St"},
      "foreman_name": "Mike Johnson",
      "contestable": true,
      "repeal_analysis": [...],
      "created_at": "2025-10-07T..."
    }
  ]
}
```

### 3. File Contest with PGE

```bash
# Mark audit as contest filed
curl -X POST http://localhost:3000/api/audits/1/file-contest \
  -H "X-API-Key: qa_test_key_789" \
  -H "Content-Type: application/json" \
  -d '{
    "contest_notes": "Contesting based on spec 057875 section 3.2 which allows 4ft spacing for rack construction. Attached analyzer report shows 87.5% confidence with 3 supporting spec citations."
  }'
```

---

## 📊 What's Working NOW

### ✅ Backend (API + Database)
- [x] Database schema with RLS
- [x] User authentication (JWT + API keys)
- [x] Audit contest endpoint
- [x] Analyzer integration
- [x] Health monitoring
- [x] Error handling
- [x] Rate limiting

### ✅ Analyzer Service (Already Deployed)
- [x] Multi-spec document analyzer
- [x] 50-PDF library support
- [x] Source tracking
- [x] Persistent storage
- [x] OCR support
- [x] CPU optimization

---

## 🚧 Next Steps to Complete

### Phase 1: Finish API Routes (1-2 days)

Create these routes in `services/api/src/routes/`:

1. **`jobs.js`** - Job management
   ```javascript
   POST /api/jobs - Create job (GF)
   GET /api/jobs - List jobs
   GET /api/jobs/:id - Get job details
   PUT /api/jobs/:id - Update job
   GET /api/jobs/:id/qr - Generate QR code for mobile
   ```

2. **`submissions.js`** - As-built submissions
   ```javascript
   POST /api/submissions - Submit as-built (foreman)
   GET /api/submissions - List submissions (QA review)
   GET /api/submissions/:id - Get submission
   PUT /api/submissions/:id/review - QA review
   ```

3. **`users.js`** - User management
   ```javascript
   POST /api/users/login - JWT login
   GET /api/users/me - Current user info
   ```

### Phase 2: Build Web Dashboard (3-5 days)

```bash
cd apps/web
npx create-react-app . --template typescript

# Key pages:
# - GF Dashboard (create jobs, schedules)
# - QA Dashboard (review submissions, contest go-backs)
# - Contest Analyzer View (upload PDF, show results)
```

### Phase 3: Build Mobile App (5-7 days)

```bash
cd apps/mobile
npx create-expo-app@latest .

# Key features:
# - Scan QR to pull job
# - Fill as-built form
# - Capture photos
# - Submit (offline queue)
```

### Phase 4: Deploy to Render (1 day)

```yaml
# infra/render.yaml
services:
  - type: web
    name: nexa-api
    runtime: node
    buildCommand: cd services/api && npm install
    startCommand: cd services/api && npm start
    envVars:
      - key: DATABASE_URL
        fromDatabase:
          name: nexa-core-db
          property: connectionString
      - key: ANALYZER_URL
        value: https://nexa-doc-analyzer-oct2025.onrender.com
```

---

## 🎯 MVP Roadmap (2 Weeks)

### Week 1: Backend + Database
- [x] Database schema ✅ DONE
- [x] API foundation ✅ DONE
- [x] Analyzer integration ✅ DONE
- [ ] Complete all API routes
- [ ] Test with Postman
- [ ] Deploy API to Render

### Week 2: Frontend
- [ ] Web dashboard (GF + QA views)
- [ ] Contest analyzer interface
- [ ] Mobile app basics
- [ ] End-to-end test
- [ ] Production deployment

---

## 💡 Architecture Highlights

### Data Flow: Go-Back Contest

```
PGE Inspector
    ↓ (sends go-back PDF)
QA Dashboard
    ↓ (uploads via /api/audits/contest)
Nexa API
    ↓ (forwards PDF)
Multi-Spec Analyzer
    ↓ (analyzes against 50 specs)
    ↓ (returns repeal analysis)
Nexa API
    ↓ (saves to DB, marks contestable)
QA Dashboard
    ↓ (shows results, recommendations)
QA Files Contest
```

### Authentication Flow

```
Crew Foreman (Mobile)
    ↓ Uses API Key
    X-API-Key: foreman_test_key_456
    ↓
API validates against users table
    ↓
Returns user permissions (role: crew_foreman)

GF/QA (Web Dashboard)
    ↓ Login with email/password
    ↓ Returns JWT token
    Authorization: Bearer <jwt>
    ↓
API validates JWT
    ↓
Returns user permissions (role: qa/general_foreman)
```

### Database Security (RLS)

```sql
-- Foremen can only see their own submissions
CREATE POLICY foreman_own_submissions ON submissions
    USING (foreman_id = current_user_id());

-- QA can see all submissions
CREATE POLICY qa_all_submissions ON submissions
    USING (current_user_role() = 'qa');
```

---

## 🔧 Development Tips

### Run with Docker (Local Stack)

```bash
cd infra
docker-compose up -d

# Services available:
# - Postgres: localhost:5432
# - Redis: localhost:6379
# - API: localhost:3000
# - LocalStack (S3/SQS): localhost:4566
```

### Debug API

```bash
# Enable detailed logging
LOG_LEVEL=debug npm run dev

# Test specific route
curl -v http://localhost:3000/api/audits/contestable \
  -H "X-API-Key: qa_test_key_789"
```

### Database Migrations

```bash
# Reset database
npm run db:reset

# Check data
psql $DATABASE_URL -c "SELECT * FROM users"
psql $DATABASE_URL -c "SELECT * FROM jobs"
```

---

## 📚 Key Files Reference

| File | Purpose |
|------|---------|
| `db/schema.sql` | Complete database structure |
| `services/api/src/server.js` | Main API entry point |
| `services/api/src/routes/audits.js` | **Contest go-backs (KEY FEATURE)** |
| `services/api/src/middleware/auth.js` | Authentication logic |
| `.env` | Environment configuration |
| `infra/docker-compose.yml` | Local development stack |

---

## 🚀 Your Current Status

### ✅ READY NOW:
- Backend API infrastructure
- Database with complete schema
- Analyzer integration working
- Contest endpoint functional

### 🔨 BUILD NEXT:
1. Remaining API routes (jobs, submissions)
2. Web dashboard for QA
3. Mobile app for foreman

### 💰 Costs (Free for Development):
- Render Postgres: Free
- Render Web Service (API): Free (or $7/month Starter)
- Analyzer: Already deployed
- **Total: $0-7/month for full development stack**

---

## 🎉 You're Ready to Build!

The foundation is set. Your multi-spec analyzer is working. Database is designed. API framework is ready.

**Start with:**
1. Test the contest endpoint with a real PGE go-back PDF
2. Build the QA dashboard to show contest results
3. Add job/submission routes for full workflow

Questions or need help with next steps? Check the other docs or ask!
