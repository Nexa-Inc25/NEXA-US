# 🚀 PRODUCTION DEPLOYMENT: Multi-Spec v2.0

## ✅ COMPLETED: Code Updated for Multi-Spec

Your app has been upgraded to **Multi-Spec v2.0** with:
- ✅ Upload 50+ PDFs with batch processing
- ✅ Source tracking (know which spec matched)
- ✅ Persistent storage at `/data`
- ✅ Incremental learning (append/replace modes)
- ✅ Deduplication by file hash
- ✅ Library management endpoints

**Backup created:** `app_oct2025_enhanced_BACKUP.py` (rollback if needed)

---

## 🔥 DEPLOY NOW (Choose One Method)

### Method 1: Manual Deploy on Render (EASIEST)

1. Go to: https://dashboard.render.com
2. Find service: `nexa-doc-analyzer-oct2025`
3. Click: **"Manual Deploy"** button (top right)
4. Select: **"Deploy latest commit"**
5. Wait: 5-10 minutes for build

**Look for in logs:**
```
Multi-Spec v2.0 enabled - Supports batch upload
New endpoints: /upload-specs, /spec-library, /manage-specs
```

### Method 2: Auto-Deploy via Git Push

If auto-deploy is enabled:
```bash
# Already committed, just need to push
git push origin main

# If push fails, try:
git push https://github.com/Nexa-Inc25/NEXA-US.git main
```

Render will auto-detect and deploy.

---

## 🎯 NEW ENDPOINTS AVAILABLE

After deployment, you'll have:

### 1. Batch Upload Multiple Specs
```bash
POST /upload-specs
```

### 2. View Spec Library
```bash
GET /spec-library
```

### 3. Manage Library
```bash
POST /manage-specs
```

### Plus Existing:
- `GET /` - API info
- `GET /health` - Health check  
- `POST /upload-spec-book` - Single spec (still works)
- `POST /analyze-audit` - Analyze audits
- `GET /docs` - Swagger UI

---

## 📊 VERIFY DEPLOYMENT

### Quick Test Script:

```bash
# Test new endpoints
curl https://nexa-doc-analyzer-oct2025.onrender.com/ | jq

# Should now show:
# {
#   "name": "NEXA AI Document Analyzer",
#   "version": "2.0.0 (Multi-Spec)",
#   "endpoints": [
#     "/upload-specs",      # NEW!
#     "/spec-library",      # NEW!
#     "/manage-specs",      # NEW!
#     ...
#   ]
# }
```

---

## 🚀 SCALE PLAN FOR PRODUCTION

### Immediate (Free Tier - OK for Testing)
- ✅ Current setup works for 50 specs
- ⚠️ Cold starts (~30s)
- ⚠️ Limited concurrent requests

### Phase 1: Starter Plan ($7/month) - RECOMMENDED
**Upgrade when:**
- Multiple users analyzing simultaneously
- Need <5s response times
- Want 24/7 uptime

**Benefits:**
- No cold starts (always-on)
- 512MB → 1GB RAM
- Better CPU allocation
- Persistent disk included

**How to Upgrade:**
1. Dashboard → `nexa-doc-analyzer-oct2025`
2. Settings → Instance Type
3. Select: **Starter**
4. Confirm ($7/month)

### Phase 2: Standard Plan ($25/month)
**Upgrade when:**
- 10+ concurrent users
- Processing 100+ audits/day
- Need autoscaling

**Benefits:**
- 2GB RAM
- 2 vCPUs
- Autoscaling to 5 instances
- 99.95% uptime SLA

### Phase 3: Pro Plan ($85/month)
**Upgrade when:**
- 50+ concurrent users
- Enterprise deployment
- Need dedicated resources

**Benefits:**
- 4GB RAM
- 4 vCPUs
- Advanced monitoring
- Priority support

---

## 📈 SCALING CHECKLIST

### Before Going Live:

- [ ] Upgrade to Starter plan ($7/month minimum)
- [ ] Set PORT=8000 environment variable
- [ ] Upload all 50 spec PDFs
- [ ] Test with real audit documents
- [ ] Monitor response times (<3s target)
- [ ] Set up uptime monitoring (UptimeRobot)
- [ ] Document API for users
- [ ] Create backup/restore process

### Performance Targets by Tier:

| Metric | Free | Starter | Standard | Pro |
|--------|------|---------|----------|-----|
| Cold Start | 30s | 0s | 0s | 0s |
| Avg Response | 3-5s | 1-2s | 0.5-1s | 0.3-0.5s |
| Concurrent Users | 1-2 | 5-10 | 20-50 | 100+ |
| Uptime | 80% | 99% | 99.5% | 99.95% |
| Cost/Month | $0 | $7 | $25 | $85 |

---

## 🔧 ENVIRONMENT VARIABLES FOR PRODUCTION

Add these in Render Dashboard → Environment:

### Required:
```
PORT=8000
```

### Recommended:
```
# Performance
OMP_NUM_THREADS=4
MKL_NUM_THREADS=4
PYTORCH_ENABLE_MPS_FALLBACK=1

# Confidence thresholds
CONFIDENCE_THRESHOLD=0.65
MIN_MATCH_SCORE=0.70

# Rate limiting
MAX_REQUESTS_PER_MINUTE=100
MAX_FILE_SIZE_MB=100

# Storage
DATA_PATH=/data
```

### Optional (Advanced):
```
# Logging
LOG_LEVEL=INFO
ENABLE_PERFORMANCE_LOGGING=true

# Monitoring
SENTRY_DSN=your_sentry_dsn_here
DATADOG_API_KEY=your_datadog_key
```

---

## 🎉 AFTER DEPLOYMENT: Upload Your 50 PDFs

### Option A: Batch Upload Script (Recommended)

```bash
# Navigate to your specs folder
cd C:\path\to\your\50\specs\

# Run batch uploader
python c:\Users\mikev\CascadeProjects\nexa-inc-mvp\backend\pdf-service\batch_upload_50_specs.py . --mode replace --batch-size 10
```

**Expected output:**
```
📦 Starting upload of 50 files in 5 batches
✅ Batch 1 complete in 12.3s
✅ Batch 2 complete in 10.8s
...
📊 UPLOAD SUMMARY
✅ Successful batches: 5/5
📁 Files uploaded: 50/50
⏱️ Total time: 65.2 seconds
✅ Final library contains:
   • Total files: 50
   • Total chunks: 3,247
```

### Option B: Web Interface

```bash
# Open the upload interface
start c:\Users\mikev\CascadeProjects\nexa-inc-mvp\backend\pdf-service\upload_example.html
```

Then:
1. Drag and drop 10 PDFs at a time
2. Select "Append" mode (after first batch)
3. Click "Upload Spec Files"
4. Repeat 5 times for all 50 files

### Option C: Python API

```python
import requests
from pathlib import Path

API_URL = "https://nexa-doc-analyzer-oct2025.onrender.com"
spec_folder = Path("C:/path/to/your/50/specs/")

# Get all PDFs
pdf_files = sorted(spec_folder.glob("*.pdf"))

# Upload in batches of 10
batch_size = 10
for i in range(0, len(pdf_files), batch_size):
    batch = pdf_files[i:i+batch_size]
    
    files = [
        ('files', (pdf.name, open(pdf, 'rb'), 'application/pdf'))
        for pdf in batch
    ]
    
    mode = "replace" if i == 0 else "append"
    
    response = requests.post(
        f"{API_URL}/upload-specs",
        files=files,
        data={"mode": mode}
    )
    
    print(f"Batch {i//batch_size + 1}: {response.status_code}")
```

---

## 🔍 VERIFY YOUR 50-SPEC LIBRARY

```bash
# Check library status
curl https://nexa-doc-analyzer-oct2025.onrender.com/spec-library | jq

# Expected output:
{
  "total_files": 50,
  "total_chunks": 3000,
  "storage_path": "/data",
  "last_updated": "2025-10-07T21:56:00Z",
  "files": [
    {
      "filename": "015077_Crossarm_hardware.pdf",
      "chunk_count": 45,
      "file_hash": "a1b2c3...",
      "uploaded_at": "2025-10-07T21:50:00Z"
    },
    ...
  ]
}
```

---

## 🎯 TEST WITH AUDIT ANALYSIS

```bash
# Analyze your go-back audit with source tracking
curl -X POST https://nexa-doc-analyzer-oct2025.onrender.com/analyze-audit \
  -F "file=@QA25-35601253-120424794-Alvah-GOBACK1.pdf" \
  | jq

# Expected output with SOURCE TRACKING:
[
  {
    "infraction": "Go-back: Incorrect secondary aerial cable spacing",
    "status": "REPEALABLE",
    "confidence": 85.0,
    "match_count": 2,
    "reasons": [
      "[Source: 057875_Secondary_Aerial_Cable.pdf] Minimum separation...",
      "[Source: 015225_Cutouts_Fuses.pdf] For secondary in rack..."
    ]
  }
]
```

Notice **[Source: filename.pdf]** showing which spec matched!

---

## 🚨 ROLLBACK PLAN (If Issues)

If something breaks:

```bash
cd backend/pdf-service

# Restore backup
copy app_oct2025_enhanced_BACKUP.py app_oct2025_enhanced.py

# Commit rollback
git add app_oct2025_enhanced.py
git commit -m "ROLLBACK: Restore single-spec version"
git push origin main

# Manual deploy on Render
```

Your single-spec version will be restored.

---

## 📞 MONITORING & ALERTS

### Set Up Uptime Monitoring (Free):

1. Sign up: https://uptimerobot.com (free)
2. Add monitor:
   - Type: HTTP(s)
   - URL: `https://nexa-doc-analyzer-oct2025.onrender.com/health`
   - Interval: 5 minutes
   - Alert: Email/SMS when down

### Response Time Monitoring:

```bash
# Create simple monitor script
# Check every 5 minutes, alert if >5s response
while true; do
  start=$(date +%s)
  curl -s https://nexa-doc-analyzer-oct2025.onrender.com/health > /dev/null
  end=$(date +%s)
  elapsed=$((end-start))
  
  if [ $elapsed -gt 5 ]; then
    echo "ALERT: Slow response ${elapsed}s at $(date)"
  fi
  
  sleep 300
done
```

---

## 🎊 DEPLOYMENT COMPLETE!

Once deployed and verified:

✅ **Your production-ready features:**
- 50-spec library with source tracking
- Batch upload capability
- Persistent storage
- Library management
- CPU-optimized for scale

✅ **Next steps:**
1. Verify deployment (check logs)
2. Upload your 50 spec PDFs
3. Test with real audits
4. Upgrade to Starter plan
5. Monitor performance

✅ **You're ready to scale!**

Need help with anything? Check the logs or run test scripts!
