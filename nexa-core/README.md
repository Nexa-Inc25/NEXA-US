# Nexa Core - Field Operations Platform

Complete workflow platform for utility field operations with AI-powered compliance analysis.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     NEXA CORE PLATFORM                        │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐      ┌──────────────┐                     │
│  │   Mobile App │      │ Web Dashboard│                     │
│  │  (Foreman)   │      │   (GF/QA)    │                     │
│  └──────┬───────┘      └──────┬───────┘                     │
│         │                     │                              │
│         │    ┌────────────────┴────────────┐                │
│         │    │                              │                │
│         └────►  API Gateway (Node.js)       │                │
│              │  /submit-as-built            │                │
│              │  /contest-audit              │                │
│              │  /jobs, /schedules           │                │
│              └────────┬─────────────────────┘                │
│                       │                                       │
│         ┌─────────────┼─────────────┐                       │
│         │             │             │                        │
│    ┌────▼────┐  ┌────▼────┐  ┌────▼─────┐                  │
│    │ Data    │  │ Analyzer│  │PostgreSQL│                  │
│    │ Lake    │  │ Service │  │  (RLS)   │                  │
│    │(S3/SQS) │  │(Multi-  │  │          │                  │
│    │         │  │ Spec)   │  │          │                  │
│    └─────────┘  └─────────┘  └──────────┘                  │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## Workflow

### 1. Pre-Field (General Foreman)
- **Platform:** Web Dashboard
- **Actions:**
  - Create job records
  - Assign crew foreman
  - Set schedules
  - Generate QR codes for mobile

### 2. Field Operations (Crew Foreman)
- **Platform:** Mobile App (Offline-First)
- **Actions:**
  - Scan QR to pull job
  - Complete as-built forms
  - Capture photos (equipment, installations)
  - Submit (queues offline, syncs when connected)

### 3. QA Review
- **Platform:** Web Dashboard
- **Actions:**
  - Review as-builts
  - Submit to PGE
  - Receive go-backs

### 4. Contest Go-Backs (QA)
- **Platform:** Web Dashboard + Analyzer
- **Actions:**
  - Upload PGE audit/go-back PDF
  - Analyzer cross-references 50-spec library
  - Returns: Repealable/confidence/reasons with spec citations
  - QA compiles evidence for PGE

## Directory Structure

```
nexa-core/
├── apps/
│   ├── mobile/          # React Native (Expo) - Foreman app
│   │   ├── src/
│   │   ├── package.json
│   │   └── app.json
│   └── web/             # React - GF/QA dashboard
│       ├── src/
│       ├── public/
│       └── package.json
├── services/
│   ├── api/             # Node.js/Express - Main API
│   │   ├── routes/
│   │   ├── middleware/
│   │   └── server.js
│   ├── analyzer/        # Python - Multi-Spec Document Analyzer
│   │   └── (linked to ../backend/pdf-service)
│   └── data-lake/       # S3/SQS handlers
├── db/
│   ├── schema.sql       # Postgres schema with RLS
│   ├── migrations/
│   └── seeds/
├── infra/
│   ├── docker-compose.yml
│   ├── render.yaml      # Render deployment config
│   └── terraform/       # (Future: IaC)
├── scripts/
│   └── setup-dev.sh
└── docs/
    ├── API.md
    ├── WORKFLOW.md
    └── DEPLOYMENT.md
```

## Tech Stack

### Frontend
- **Mobile:** React Native (Expo) + AsyncStorage (offline)
- **Web:** React + TailwindCSS + shadcn/ui
- **State:** Context API / Zustand

### Backend
- **API:** Node.js + Express
- **Analyzer:** Python + FastAPI (existing multi-spec service)
- **Auth:** JWT + API keys
- **RLS:** Postgres Row-Level Security

### Data & Storage
- **Database:** Render Postgres (free tier for dev)
- **Files:** AWS S3 (photos, PDFs)
- **Queue:** AWS SQS (audit notifications)
- **Cache:** Redis (optional, for sessions)

### Deployment
- **Free Tier:**
  - Render Web Service (API)
  - Render Static Site (Web Dashboard)
  - Render Postgres (Database)
  - Existing: nexa-doc-analyzer-oct2025 (Analyzer)

- **Paid Tier (Production):**
  - Render Starter ($7/month per service)
  - AWS S3 (~$1-5/month)
  - AWS SQS (free tier)

## Development Setup

### Prerequisites
- Node.js 18+
- Python 3.11
- Postgres 15
- Expo CLI (for mobile)

### Quick Start

```bash
# 1. Clone and install
cd nexa-core
npm install  # Root dependencies
cd apps/mobile && npm install
cd ../web && npm install
cd ../../services/api && npm install

# 2. Setup database
createdb nexa_core_dev
psql nexa_core_dev < db/schema.sql

# 3. Configure environment
cp .env.example .env
# Edit .env with your credentials

# 4. Start development
# Terminal 1: API
cd services/api && npm run dev

# Terminal 2: Web
cd apps/web && npm start

# Terminal 3: Mobile
cd apps/mobile && expo start

# 5. Analyzer (already deployed)
# https://nexa-doc-analyzer-oct2025.onrender.com
```

## Integration with Existing Analyzer

The **Multi-Spec Document Analyzer** (already deployed) integrates as a microservice:

```javascript
// In services/api/routes/audits.js
const analyzeGoBack = async (req, res) => {
  const { pdfFile } = req.files;
  
  // Call deployed analyzer
  const formData = new FormData();
  formData.append('file', pdfFile.buffer, pdfFile.originalname);
  
  const response = await fetch(
    'https://nexa-doc-analyzer-oct2025.onrender.com/analyze-audit',
    {
      method: 'POST',
      body: formData
    }
  );
  
  const analysis = await response.json();
  
  // Save to DB
  await db.audits.create({
    submission_id: req.body.submissionId,
    pge_go_back: pdfFile,
    repeal_analysis: analysis,
    status: analysis.some(i => i.status === 'REPEALABLE') ? 'contestable' : 'valid'
  });
  
  res.json(analysis);
};
```

## Roadmap

### Phase 1: MVP (Weeks 1-2)
- [x] Core directory structure
- [ ] Database schema with RLS
- [ ] Basic API (jobs, submissions)
- [ ] Web dashboard (GF schedule, QA review)
- [ ] Analyzer integration
- [ ] Deploy on Render free tier

### Phase 2: Mobile (Weeks 3-4)
- [ ] React Native app
- [ ] Offline submission queue
- [ ] Photo capture
- [ ] QR code scanning
- [ ] Sync mechanism

### Phase 3: Data Lake (Week 5)
- [ ] S3 integration for photos
- [ ] SQS for audit events
- [ ] Data ingestion pipeline
- [ ] Analytics dashboard

### Phase 4: Production (Week 6+)
- [ ] Upgrade to paid tiers
- [ ] Performance optimization
- [ ] Load testing
- [ ] Security audit
- [ ] Launch

## Environment Variables

```bash
# API
PORT=3000
NODE_ENV=development
DATABASE_URL=postgresql://localhost/nexa_core_dev
JWT_SECRET=your_secret_here

# Analyzer
ANALYZER_URL=https://nexa-doc-analyzer-oct2025.onrender.com
ANALYZER_API_KEY=optional_key_here

# AWS (for S3/SQS)
AWS_REGION=us-west-2
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
S3_BUCKET=nexa-field-photos

# Feature Flags
ENABLE_OFFLINE_AI=false
ENABLE_ANALYTICS=true
```

## License

Proprietary - Nexa Inc. 2025
