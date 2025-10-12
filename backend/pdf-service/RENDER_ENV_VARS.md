# Render.com Environment Variables

Copy and paste these into Render Dashboard → Environment:

```bash
# ============ SECURITY (Generated - Do NOT commit!) ============
ENCRYPTION_KEY=w5AipvyG5p8mKmIZRVzjej7DN-PFPYBfjefmnu1zBE0=
JWT_SECRET=aaba1b5be097b87b509f6b2b888b2902435f73ac7d71a313f562bf06a1d6639e
JWT_ALGORITHM=HS256
AUTH_ENABLED=true

# ============ ML CONFIGURATION ============
FORCE_CPU=true
CUDA_DEVICE_ID=0
CUDA_MEMORY_FRACTION=0.8
GRADIENT_ACCUMULATION_STEPS=4
ENABLE_MIXED_PRECISION=false
USE_DEEPSPEED=false
SEED=42
DISABLE_COMPILE=false
EMBEDDING_MODEL=all-MiniLM-L6-v2

# ============ SERVICE CONFIGURATION ============
MAX_PAGES=1500
CHUNK_SIZE=400
PAGE_BATCH_SIZE=50
MAX_UPLOAD_SIZE_MB=200
RATE_LIMIT_PER_MINUTE=100
CACHE_TTL_SECONDS=1800

# ============ STORAGE PATHS ============
DATA_DIR=/data
RENDER_DISK_PATH=/data
SECURE_STORAGE_PATH=/data/secure_uploads
QUARANTINE_PATH=/data/quarantine
AUDIT_LOG_PATH=/data/audit_logs

# ============ LOGGING ============
LOG_LEVEL=INFO
LOG_FILE=/data/logs/nexa.log
ENABLE_METRICS=true

# ============ API CONFIGURATION ============
API_HOST=0.0.0.0
API_WORKERS=1
API_RELOAD=false
ENVIRONMENT=production
DEBUG=false
TESTING=false

# ============ CORS (Update with your domains) ============
CORS_ORIGINS=https://nexa-dashboard.onrender.com,https://your-frontend.com

# ============ FEATURE FLAGS ============
ENABLE_OCR=true
ENABLE_NER=true
ENABLE_YOLO=true
ENABLE_ENCRYPTION=true
ENABLE_AUDIT_LOGGING=true

# ============ MONITORING ============
PROMETHEUS_PORT=9090
ENABLE_PROFILING=false
MEMORY_PROFILING=false

# ============ CPU OPTIMIZATION ============
OMP_NUM_THREADS=4
KMP_AFFINITY=granularity=fine,compact,1,0
KMP_BLOCKTIME=0
DNNL_VERBOSE=0
MKL_DYNAMIC=FALSE
PYTORCH_ENABLE_MPS_FALLBACK=1

# ============ OPTIONAL SERVICES ============
# These will be auto-populated if you add Redis/Database through Render
# REDIS_URL=(auto-attached if added)
# DATABASE_URL=(auto-attached if added)
# CELERY_BROKER_URL=(same as REDIS_URL)
# CELERY_RESULT_BACKEND=(redis://.../:1)

# ============ EXTERNAL APIs (if needed) ============
# OPENAI_API_KEY=sk-...
# ANTHROPIC_API_KEY=sk-ant-...
# HUGGINGFACE_TOKEN=hf_...
# ROBOFLOW_API_KEY=rf_...
```

## Important Notes:

1. **Security Keys**: The `ENCRYPTION_KEY` and `JWT_SECRET` are generated and should be kept secret
2. **Database/Redis**: If you add PostgreSQL or Redis through Render, they auto-populate DATABASE_URL and REDIS_URL
3. **PORT**: Render automatically provides the PORT environment variable - no need to set it
4. **CORS**: Update CORS_ORIGINS with your actual frontend domains
5. **Performance**: For Starter plan ($7/mo), keep FORCE_CPU=true and workers=1
6. **Storage**: The /data path matches the persistent disk mount point
