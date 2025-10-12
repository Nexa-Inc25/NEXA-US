# NEXA Codebase Guide
*Last Updated: October 11, 2025*

##  Overview
NEXA is a comprehensive document intelligence system for electrical contractors working with utilities (PG&E, SCE, SDG&E). It automates job package analysis, spec compliance checking, and as-built form filling, saving 3.5 hours per job.

##  System Architecture

### Production URLs
- **Main API**: https://nexa-api-xpu3.onrender.com
- **Dashboard**: https://nexa-dashboard.onrender.com (if deployed)
- **Infrastructure**: Render.com ($134/month total)

### Tech Stack
- **Backend**: FastAPI (Python 3.11)
- **ML Models**: 
  - Sentence-transformers (all-MiniLM-L6-v2) for semantic search
  - YOLOv8 for pole/crossarm detection
  - Fine-tuned NER for utility jargon extraction
- **Database**: PostgreSQL with pgvector extension
- **Cache**: Redis for sub-5ms lookups
- **Storage**: 100GB persistent disk at /data
- **Mobile**: Expo/React Native (SDK 54)

##  Project Structure (After Cleanup)

```
nexa-inc-mvp/
├── README.md                     # Main project readme
├── Dockerfile                    # Main Docker config
├── requirements.txt              # Main requirements
├── .env                         # Environment variables
│
├── archive/                     # Old/deprecated files
├── docs/                        # All documentation
├── deployment/                  # Deployment configs
├── scripts/                     # Utility scripts
├── tests/                       # Test files
│
├── backend/
│   ├── api/                     # (Currently empty)
│   └── pdf-service/             # Main backend service
│       ├── app_oct2025_enhanced.py  # MAIN PRODUCTION APP
│       ├── middleware.py            # Rate limiting, error handling
│       ├── utils.py                 # Utility functions
│       ├── requirements_oct2025.txt # Production requirements
│       ├── Dockerfile.oct2025       # Production Docker
│       │
│       ├── modules/                 # Core functionality
│       │   ├── enhanced_spec_analyzer.py      # PDF analysis engine
│       │   ├── pricing_integration.py         # Labor/equipment pricing
│       │   ├── pole_vision_detector.py        # YOLO pole detection
│       │   ├── job_workflow_api.py           # PM→GF→Foreman→QA flow
│       │   ├── field_management_api.py       # Field crew management
│       │   ├── as_built_filler.py            # Auto-fill PG&E forms
│       │   ├── mega_bundle_endpoints.py      # Batch processing
│       │   └── spec_learning_endpoints.py    # Spec book learning
│       │
│       ├── archive/             # Old app versions
│       ├── docs/                # Service documentation
│       ├── tests/               # Service tests
│       ├── data/                # Runtime data
│       └── fine_tuned_ner_deep/ # NER models
│
├── mobile/                      # Expo React Native app
│   ├── App.tsx
│   ├── package.json
│   └── src/
│       ├── screens/
│       └── services/
│
├── web/                         # React dashboard (empty)
├── dashboard/                   # Legacy dashboard (empty)
└── foreman-app/                # Foreman specific app

```

##  Critical Production Files

### Main Application
- **`app_oct2025_enhanced.py`** (59KB)
  - FastAPI application with 20+ integrated modules
  - Handles all API endpoints
  - Integrates ML models, database, caching

### Core Modules (in modules/ folder)
1. **`enhanced_spec_analyzer.py`** - PDF parsing and NER entity extraction
2. **`pricing_integration.py`** - IBEW labor rates, equipment pricing
3. **`pole_vision_detector.py`** - YOLOv8 computer vision for poles
4. **`job_workflow_api.py`** - Complete contractor workflow
5. **`as_built_filler.py`** - Auto-fills PG&E submission forms
6. **`mega_bundle_endpoints.py`** - Handles 3500+ job batches

### Configuration
- **`middleware.py`** - Rate limiting (100 req/min), error handling
- **`utils.py`** - PDF processing, embeddings, helpers
- **`Dockerfile.oct2025`** - Production Docker configuration
- **`requirements_oct2025.txt`** - All Python dependencies

##  Key Features & Endpoints

### Document Analysis
- `POST /upload-specs` - Upload PG&E spec books
- `POST /analyze-audit` - Analyze job packages for infractions
- `GET /spec-library` - View loaded specifications

### Workflow Management  
- `POST /upload-job-package` - PM uploads job
- `POST /assign-job` - PM assigns to GF
- `POST /prefield-job` - GF schedules work
- `POST /complete-job` - Foreman uploads photos
- `POST /qa-review` - QA approves package

### Vision AI
- `POST /detect-pole` - Detect poles in images
- `POST /classify-pole` - Classify pole types
- `POST /train-on-specs` - Train on new data

### Pricing & Estimation
- `POST /estimate-hours` - Estimate job hours
- `GET /pricing/labor` - Get labor rates
- `GET /pricing/equipment` - Get equipment costs

### Batch Processing
- `POST /mega-bundle/upload` - Process 3500+ jobs
- `GET /mega-bundle/status` - Check processing status

##  Machine Learning Models

### 1. Semantic Search (Sentence Transformers)
- Model: `all-MiniLM-L6-v2`
- Used for: Matching audit text to spec requirements
- Performance: 0.7-2.1s per analysis

### 2. Named Entity Recognition (NER)
- Model: Fine-tuned BERT
- Entities: MATERIAL, EQUIPMENT, STANDARD, LOCATION, etc.
- F1 Score: >0.90 on utility jargon

### 3. Computer Vision (YOLOv8)
- Model: `yolo_pole_trained.pt`
- Classes: Pole, Crossarm
- mAP50: 0.85+
- Inference: <2 seconds/image

##  Business Metrics
- **Time Saved**: 3.5 hours per job package
- **Rejection Reduction**: 30% → <5%
- **ROI**: 2,900% (30X return)
- **Capacity**: 70+ concurrent users, 500+ PDFs/hour

##  Development Workflow

### Running Locally
```bash
cd backend/pdf-service
pip install -r requirements_oct2025.txt
uvicorn app_oct2025_enhanced:app --reload --port 8000
```

### Running Tests
```bash
cd backend/pdf-service
pytest tests/
```

### Deployment
```bash
# Push to GitHub (triggers auto-deploy on Render)
git add .
git commit -m "Deploy updates"
git push origin main
```

##  Important Notes

1. **File Cleanup**: We just organized 400+ files that were scattered. Use the cleanup scripts if needed.

2. **Import Updates**: After moving modules, run `UPDATE_IMPORTS_AFTER_CLEANUP.ps1` to fix imports.

3. **Environment Variables Required**:
   - `DATABASE_URL` - PostgreSQL connection
   - `REDIS_URL` - Redis cache connection  
   - `RENDER_DISK_PATH=/data` - Persistent storage

4. **Model Training**: 
   - Job packages need training via `/train-job-package`
   - As-builts need examples via `/train-as-built`

5. **Current Issues**:
   - Crossarm detection recall is low (needs more training data)
   - Mobile app needs API integration
   - Dashboard needs deployment

##  Scaling Roadmap
- **Current**: 1-10 users
- **Week 1**: 30 users (optimize caching)
- **Week 2**: 70 users (async processing)
- **Month 1**: 200 users (distributed workers)
- **Month 3**: 1000+ users (Kubernetes)

##  Related Documentation
- See `/docs` folder for detailed guides
- `DEPLOYMENT_GUIDE.md` - Full deployment instructions
- `WORKFLOW_INTEGRATION_GUIDE.md` - API workflow details
- `SCALING_ROADMAP.md` - Scaling strategy

##  Support
For questions about the codebase, architecture, or deployment, refer to the memories in your AI assistant or the documentation in the `/docs` folder.
