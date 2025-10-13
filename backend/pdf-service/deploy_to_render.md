# NEXA Complete Deployment Guide for Render.com

## Production Deployment: AI Document Analyzer + Field Crew Backend

### Prerequisites
- GitHub repository connected to Render
- Render account with payment method (for persistent storage)
- Docker support enabled

---

## 1. Project Structure

```
nexa-inc-mvp/
├── backend/
│   ├── pdf-service/
│   │   ├── app_oct2025_enhanced.py          # Main FastAPI app
│   │   ├── field_crew_workflow.py           # Field crew backend
│   │   ├── infraction_analyzer.py           # AI analyzer
│   │   ├── asbuilt_validator.py            # PGE compliance validator
│   │   ├── modules/
│   │   │   ├── auth_system.py
│   │   │   ├── universal_standards.py
│   │   │   └── spec_analyzer.py
│   │   ├── requirements_oct2025.txt
│   │   ├── Dockerfile.render
│   │   └── render.yaml
│   ├── data/
│   │   ├── spec_books/                     # PGE spec storage
│   │   ├── audits/                         # Audit documents
│   │   ├── as_builts/                      # Generated as-builts
│   │   └── learned_patterns.json           # AI learning data
├── mobile/
│   └── FieldCrewApp.js                     # React Native app
└── docs/
    └── deployment.md
```

---

## 2. Dockerfile for Production

```dockerfile
# Dockerfile.render
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wkhtmltopdf \
    poppler-utils \
    tesseract-ocr \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for better caching
COPY backend/pdf-service/requirements_oct2025.txt .
RUN pip install --no-cache-dir -r requirements_oct2025.txt

# Copy application code
COPY backend/pdf-service/ .
COPY backend/data/ /data/

# Create necessary directories
RUN mkdir -p /data/spec_books /data/audits /data/as_builts /data/uploads

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Run the application
CMD ["uvicorn", "app_oct2025_enhanced:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 3. render.yaml Configuration

```yaml
# render.yaml
services:
  - type: web
    name: nexa-document-analyzer
    runtime: docker
    dockerfilePath: ./backend/pdf-service/Dockerfile.render
    dockerContext: .
    repo: https://github.com/YOUR_USERNAME/nexa-inc-mvp
    branch: main
    envVars:
      - key: ENVIRONMENT
        value: production
      - key: JWT_SECRET
        generateValue: true
      - key: OPENAI_API_KEY
        sync: false  # Add manually in Render dashboard
      - key: STORAGE_PATH
        value: /data
    disk:
      name: nexa-storage
      mountPath: /data
      sizeGB: 10
    healthCheckPath: /health
    plan: starter  # $7/month

  - type: background
    name: nexa-ai-worker
    runtime: docker
    dockerfilePath: ./backend/pdf-service/Dockerfile.worker
    repo: https://github.com/YOUR_USERNAME/nexa-inc-mvp
    envVars:
      - key: REDIS_URL
        fromService:
          type: redis
          name: nexa-redis
          property: connectionString
    plan: starter  # $7/month

databases:
  - name: nexa-postgres
    plan: starter  # $7/month
    databaseName: nexa_production
    user: nexa_admin
    postgresMajorVersion: 15

redis:
  - name: nexa-redis
    plan: starter  # $7/month
    maxmemoryPolicy: allkeys-lru
```

---

## 4. Updated requirements_oct2025.txt

```txt
# Core Framework
fastapi==0.115.2
uvicorn==0.32.0
python-multipart==0.0.12

# PDF Processing
pypdf==5.0.1
pdfkit==1.0.0
reportlab==4.2.5
PyPDF2==3.0.1

# AI & ML
langchain==0.3.1
langchain-community==0.3.1
sentence-transformers==3.1.1
transformers==4.44.2
faiss-cpu==1.8.0
torch==2.4.0
openai==1.51.0

# Computer Vision
ultralytics==8.0.200
opencv-python-headless==4.8.0.74
pillow==11.0.0

# Database
sqlalchemy==2.0.35
psycopg2-binary==2.9.9
redis==5.0.8

# Authentication
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
bcrypt==4.2.1

# Utilities
python-dotenv==1.0.1
pydantic==2.9.2
httpx==0.27.2
aiofiles==24.1.0
```

---

## 5. Environment Variables Setup

Create `.env.production`:

```env
# API Configuration
ENVIRONMENT=production
API_VERSION=1.0.0
BASE_URL=https://nexa-document-analyzer.onrender.com

# Database
DATABASE_URL=postgresql://user:password@host:5432/nexa_production

# Redis Cache
REDIS_URL=redis://redis-host:6379

# Storage
STORAGE_PATH=/data
MAX_FILE_SIZE_MB=50

# AI Configuration
OPENAI_API_KEY=sk-...
MODEL_NAME=gpt-4-turbo
EMBEDDING_MODEL=text-embedding-3-small
CONFIDENCE_THRESHOLD=0.85

# Security
JWT_SECRET=your-secret-key-here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# PGE Standards
PGE_SPEC_VERSION=2025
COMPLIANCE_THRESHOLD=95
```

---

## 6. Deployment Steps

### Step 1: Prepare Repository
```bash
# Clone and setup
git clone https://github.com/YOUR_USERNAME/nexa-inc-mvp.git
cd nexa-inc-mvp

# Ensure all files are committed
git add .
git commit -m "Production deployment configuration"
git push origin main
```

### Step 2: Deploy on Render
1. Log in to [Render Dashboard](https://dashboard.render.com)
2. Click "New +" → "Blueprint"
3. Connect your GitHub repository
4. Select branch: `main`
5. Use the `render.yaml` file
6. Review services and click "Apply"

### Step 3: Configure Storage
```bash
# After deployment, SSH into service (if needed)
# Create persistent directories
mkdir -p /data/spec_books
mkdir -p /data/audits
mkdir -p /data/as_builts
mkdir -p /data/models

# Upload initial spec book
curl -X POST https://nexa-document-analyzer.onrender.com/api/utilities/PGE/ingest \
  -F "file=@PGE_Greenbook_2025.pdf"
```

### Step 4: Initialize AI Models
```bash
# Train on uploaded specs
curl -X POST https://nexa-document-analyzer.onrender.com/api/ai/train \
  -H "Content-Type: application/json" \
  -d '{"spec_book": "PGE_Greenbook_2025.pdf"}'

# Verify model status
curl https://nexa-document-analyzer.onrender.com/api/ai/status
```

### Step 5: Test Endpoints
```bash
# Health check
curl https://nexa-document-analyzer.onrender.com/health

# Submit test job (field crew)
curl -X POST https://nexa-document-analyzer.onrender.com/api/field/submit-job \
  -H "Content-Type: application/json" \
  -d @test_job.json

# Analyze audit document
curl -X POST https://nexa-document-analyzer.onrender.com/api/analyze-audit \
  -F "file=@QA_AUDIT_45568648.pdf"
```

---

## 7. Mobile App Configuration

Update `FieldCrewApp.js` with production URL:

```javascript
// mobile/FieldCrewApp.js
const API_CONFIG = {
  production: 'https://nexa-document-analyzer.onrender.com',
  development: 'http://localhost:8000'
};

const API_URL = __DEV__ ? API_CONFIG.development : API_CONFIG.production;
```

Build and deploy mobile app:

```bash
# Using Expo
cd mobile
npm install
npx expo build:ios
npx expo build:android

# Submit to app stores or distribute via TestFlight/Firebase
```

---

## 8. Monitoring & Maintenance

### Render Dashboard Monitoring
- **Metrics**: CPU, Memory, Disk usage
- **Logs**: Real-time application logs
- **Alerts**: Set up for >80% resource usage

### Health Check Endpoint
```python
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "database": check_database_connection(),
            "redis": check_redis_connection(),
            "ai_model": check_model_loaded(),
            "storage": check_storage_available()
        },
        "metrics": {
            "total_jobs": await get_job_count(),
            "compliance_rate": await get_compliance_rate(),
            "ai_accuracy": await get_ai_accuracy()
        }
    }
```

### Backup Strategy
```yaml
# render-backup.yaml
- type: cron
  name: nexa-backup
  runtime: docker
  schedule: "0 2 * * *"  # Daily at 2 AM
  dockerCommand: python backup.py
  envVars:
    - key: BACKUP_BUCKET
      value: s3://nexa-backups
```

---

## 9. Cost Breakdown

| Service | Plan | Monthly Cost |
|---------|------|--------------|
| Web Service | Starter | $7 |
| Background Worker | Starter | $7 |
| PostgreSQL | Starter | $7 |
| Redis | Starter | $7 |
| Persistent Disk | 10GB | $1 |
| **Total** | | **$29/month** |

---

## 10. Production Checklist

- [ ] GitHub repository setup with proper .gitignore
- [ ] Docker builds successfully locally
- [ ] Environment variables configured in Render
- [ ] Database migrations run
- [ ] Initial spec book uploaded
- [ ] AI model trained on specs
- [ ] Health check endpoint responding
- [ ] Mobile app pointing to production URL
- [ ] SSL certificate active (automatic on Render)
- [ ] Monitoring alerts configured
- [ ] Backup strategy implemented
- [ ] Team access granted in Render dashboard

---

## Support & Troubleshooting

### Common Issues

**1. Memory Issues with AI Model**
```yaml
# Increase plan to Standard ($25/month) for 2GB RAM
plan: standard
```

**2. Storage Full**
```yaml
# Increase disk size
disk:
  sizeGB: 25  # $2.50/month
```

**3. Slow AI Analysis**
```python
# Enable caching
from functools import lru_cache

@lru_cache(maxsize=100)
def analyze_infraction(infraction_text: str):
    # AI analysis with caching
```

---

## Next Steps

1. **Set up staging environment** for testing before production
2. **Implement CI/CD pipeline** with GitHub Actions
3. **Add performance monitoring** with DataDog or New Relic
4. **Create admin dashboard** for QA team
5. **Enable auto-scaling** for high load periods

This deployment will give you a production-ready NEXA system for <$30/month!
