# NEXA AI Document Analyzer - October 2025 Enhanced Deployment Guide

## 🚀 Deployment to Render.com

### Version: 1.0.0 (October 2025 Enhanced)
**Last Updated:** October 06, 2025

### ✨ New Features in This Release
- **FuseSaver Support**: Enhanced parsing for Siemens FuseSaver specifications
- **TripSaver Support**: Complete TripSaver II device requirements
- **Recloser Analysis**: Line recloser ratings and coordination
- **SCADA-Mate SD**: SCADA antenna installation requirements
- **Enhanced OCR**: Better cleaning of garbled audit text
- **Increased Limits**: Support for 1100MB files (up from 300MB)
- **Improved Chunking**: 1100 character chunks for detailed specifications

---

## 📋 Prerequisites

1. **GitHub Account** with repository containing:
   - `app_oct2025_enhanced.py`
   - `requirements_oct2025.txt`
   - `Dockerfile.oct2025`

2. **Render.com Account** (free or paid)
   - Free tier: Limited resources, no persistent disk
   - Starter ($7/month): Persistent disk for embeddings

3. **PG&E Specification PDFs** including:
   - Document 092813: FuseSaver Installation
   - Document 094669: OH Switches - Line Reclosers  
   - Document 094672: TripSaver II Requirements
   - Additional specs as available

---

## 🛠️ Deployment Steps

### Step 1: Prepare Repository

```bash
# Clone or update your repository
git clone https://github.com/yourusername/nexa-doc-analyzer.git
cd nexa-doc-analyzer

# Copy enhanced files
cp backend/pdf-service/app_oct2025_enhanced.py .
cp backend/pdf-service/requirements_oct2025.txt .
cp backend/pdf-service/Dockerfile.oct2025 Dockerfile

# Commit and push
git add .
git commit -m "Deploy October 2025 enhanced version with FuseSaver/Recloser support"
git push origin main
```

### Step 2: Create Render Service

1. **Log in to Render.com**
2. **Click "New +" → "Web Service"**
3. **Connect GitHub repository**
4. **Configure service:**

```yaml
Name: nexa-doc-analyzer-oct2025
Environment: Docker
Region: Oregon (US West)
Branch: main
```

### Step 3: Environment Variables

Add these in Render dashboard:

```bash
# Optional - for monitoring
LOG_LEVEL=INFO

# If using external storage (optional)
EMBEDDINGS_PATH=/data/spec_embeddings.pkl
```

### Step 4: Configure Resources

#### Free Tier (Testing)
- **Instance Type:** Free
- **No persistent disk**
- **Note:** Embeddings lost on restart

#### Starter Tier (Recommended for Production)
- **Instance Type:** Starter ($7/month)
- **Add Disk:**
  - Name: `nexa-embeddings`
  - Mount Path: `/data`
  - Size: 1GB (sufficient for embeddings)

### Step 5: Deploy

1. **Click "Create Web Service"**
2. **Wait for build** (~5-10 minutes first time)
3. **Check logs** for successful startup:
   ```
   🔧 Using device: cpu
   💾 Embeddings will be stored at: /data/spec_embeddings.pkl
   INFO:     Uvicorn running on http://0.0.0.0:8000
   ```

---

## 🧪 Testing Deployment

### 1. Health Check
```bash
curl https://your-app.onrender.com/health

# Expected response:
{
  "status": "healthy",
  "device": "cpu",
  "spec_learned": false,
  "ocr_available": true,
  "max_file_size_mb": 1100
}
```

### 2. Check Features
```bash
curl https://your-app.onrender.com/

# Should show:
{
  "name": "NEXA AI Document Analyzer",
  "version": "1.0.0 (Oct 2025 Enhanced)",
  "features": [
    "FuseSaver support",
    "TripSaver support",
    "SCADA-Mate SD support",
    "Line reclosers analysis",
    "Enhanced OCR cleaning",
    "1100MB file support"
  ]
}
```

### 3. Upload Spec Book
```bash
# Using curl
curl -X POST https://your-app.onrender.com/upload-spec-book \
  -F "file=@path/to/pge_specs.pdf"

# Or using the test script
python test_oct2025_enhanced.py
```

### 4. Analyze Audit
```bash
curl -X POST https://your-app.onrender.com/analyze-audit \
  -F "file=@path/to/audit.pdf"
```

---

## 📊 Example Analysis Results

### FuseSaver Infraction
**Input:** "Go-back: Incorrect FuseSaver phasing per audit"
**Output:**
```json
{
  "infraction": "Go-back: Incorrect FuseSaver phasing per audit",
  "status": "REPEALABLE",
  "confidence": 85.2,
  "match_count": 3,
  "reasons": [
    "From Document 092813: FuseSavers must be installed on single phase taps only (similarity 85%)",
    "Spec match (similarity 82%): Maximum rating 100A for single-phase..."
  ]
}
```

### Recloser Issue
**Input:** "Line recloser rating does not match spec requirements"
**Output:**
```json
{
  "status": "REPEALABLE",
  "confidence": 78.5,
  "reasons": [
    "From Document 094669: Recloser ratings must match spec requirements (similarity 79%)"
  ]
}
```

---

## 🔧 Troubleshooting

### Issue: OCR not working
**Solution:** Dockerfile includes Tesseract. Check logs for OCR initialization.

### Issue: Large files timeout
**Solution:** 
- Increase timeout in Render settings
- Consider chunking large uploads client-side
- Use Starter tier for better performance

### Issue: Embeddings not persisting
**Solution:** 
- Upgrade to Starter tier with disk
- Or implement external storage (S3, etc.)

### Issue: Garbled text in results
**Solution:** Enhanced cleaning is automatic. Check if OCR is enabled:
```python
# OCR should be enabled by default
use_ocr=True
```

---

## 📈 Performance Tips

1. **Pre-process PDFs:** Remove unnecessary images to reduce size
2. **Batch uploads:** Upload all spec books at once
3. **Monitor memory:** Use `/health` endpoint to check status
4. **Cache results:** Store analysis results to avoid re-processing

---

## 🔐 Security Considerations

1. **File validation:** Only PDF files accepted
2. **Size limits:** 1100MB max to prevent DoS
3. **Rate limiting:** Implement if needed via Render
4. **HTTPS only:** Render provides SSL by default

---

## 📝 Update Checklist

When updating to this version:

- [x] Update `requirements_oct2025.txt` with latest versions
- [x] Deploy `app_oct2025_enhanced.py` 
- [x] Update `Dockerfile.oct2025`
- [x] Test FuseSaver parsing
- [x] Test TripSaver parsing  
- [x] Test SCADA requirements
- [x] Test recloser analysis
- [x] Verify OCR cleaning
- [x] Check 1100MB file support

---

## 🆘 Support

For issues or questions:
1. Check Render logs: Dashboard → Logs
2. Test locally first: `uvicorn app_oct2025_enhanced:app --reload`
3. Use test script: `python test_oct2025_enhanced.py`
4. Review this guide for common issues

---

## 📊 Metrics & Monitoring

Track these metrics for optimal performance:
- **Chunks learned:** Should be 500-2000 for typical spec books
- **Analysis confidence:** >60% indicates good matches
- **Processing time:** <30s for most audits
- **Memory usage:** Monitor via Render dashboard

---

**Deployment successful?** Your NEXA Document Analyzer is now ready to process PG&E audits with enhanced FuseSaver, TripSaver, and recloser support! 🎉
