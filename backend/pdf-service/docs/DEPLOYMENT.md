# Deployment Guide - NEXA AI Document Analyzer

## 🚀 Quick Deploy to Render.com

### Prerequisites
- GitHub repository connected to Render
- Render account (Starter plan $7/month is sufficient)

### Step 1: Prepare for Deployment

1. **Test Locally First**
```bash
# Run full workflow test
cd backend/pdf-service
python test_full_workflow.py
```

2. **Verify All Files Present**
```
backend/pdf-service/
├── app.py                    # Main FastAPI application
├── requirements.txt          # Python dependencies
├── render.yaml              # Render configuration
├── Dockerfile               # Optional Docker config
├── test_full_workflow.py    # Integration tests
└── README.md                # Documentation
```

### Step 2: Deploy to Render

#### Option A: Using Render Dashboard (Recommended)

1. **Create New Web Service**
   - Go to [Render Dashboard](https://dashboard.render.com)
   - Click "New +" → "Web Service"
   - Connect your GitHub repository

2. **Configure Service**
   ```yaml
   Name: nexa-pdf-analyzer
   Region: Oregon (US West)
   Branch: main
   Root Directory: backend/pdf-service
   Runtime: Python 3
   Build Command: pip install -r requirements.txt
   Start Command: uvicorn app:app --host 0.0.0.0 --port $PORT
   ```

3. **Environment Variables**
   ```
   AUTH_ENABLED=true
   AUTH0_DOMAIN=dev-kbnx7pja3zpg0lud.us.auth0.com
   AUTH0_AUDIENCE=https://api.nexa.local
   ```

4. **Advanced Settings**
   - Instance Type: Starter ($7/month)
   - Auto-Deploy: Yes
   - Health Check Path: /health

#### Option B: Using render.yaml (Automated)

1. **Verify render.yaml**
```yaml
services:
  - type: web
    name: nexa-pdf-analyzer
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn app:app --host 0.0.0.0 --port $PORT
    healthCheckPath: /health
    envVars:
      - key: AUTH_ENABLED
        value: true
      - key: PYTHON_VERSION
        value: 3.11.0
```

2. **Deploy via Git Push**
```bash
git add backend/pdf-service/
git commit -m "Deploy AI document analyzer with optimized extraction"
git push origin main
```

### Step 3: Post-Deployment Testing

1. **Get Service URL**
   - Example: `https://nexa-pdf-analyzer.onrender.com`

2. **Test Health Endpoint**
```bash
curl https://nexa-pdf-analyzer.onrender.com/health
```

3. **Test Full Workflow**
```bash
# Upload spec to learn
curl -X POST https://nexa-pdf-analyzer.onrender.com/learn-spec/ \
  -F "spec_file=@spec.pdf"

# Analyze audit
curl -X POST https://nexa-pdf-analyzer.onrender.com/analyze-audit/ \
  -F "audit_file=@audit.pdf"
```

### Step 4: Connect to Node.js Backend

1. **Update Node.js Environment**
```bash
# In Render dashboard for Node.js service
PDF_SERVICE_URL=https://nexa-pdf-analyzer.onrender.com
```

2. **Test Integration**
   - Upload PDF in mobile app
   - Check Materials screen for extracted data

## 📊 Performance Metrics

### Expected Performance on Render Starter ($7/month)

| Operation | File Size | Pages | Time | Memory |
|-----------|-----------|-------|------|--------|
| Parse PDF | 5MB | 50 | 3s | 128MB |
| Learn Spec | 50MB | 500 | 45s | 256MB |
| Analyze Audit | 10MB | 100 | 8s | 200MB |
| FAISS Search | - | - | <1s | 150MB |

### Optimization Tips

1. **Memory Management**
   - Pages processed in batches of 50
   - Stream processing prevents OOM
   - Automatic garbage collection

2. **Caching**
   - FAISS index persisted to disk
   - Chunks cached after learning
   - No need to re-learn specs

3. **Rate Limiting**
   - Implement rate limits for API endpoints
   - Use queue for large file processing

## 🔍 Monitoring & Debugging

### Render Logs
```bash
# View live logs in Render dashboard
# Or use Render CLI
render logs --service nexa-pdf-analyzer --tail
```

### Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| OOM on large PDFs | Reduce PAGE_BATCH_SIZE to 25 |
| Slow extraction | Ensure PyMuPDF installed (not pdfplumber) |
| Index not persisting | Check /data directory permissions |
| Auth failures | Verify AUTH0_DOMAIN and AUDIENCE |

### Health Monitoring
- Endpoint: `/health`
- Expected response:
```json
{
  "status": "healthy",
  "service": "pdf-processor",
  "auth_enabled": true,
  "index_loaded": true
}
```

## 🎯 Testing Checklist

Before marking deployment complete:

- [ ] Health check returns 200
- [ ] PDF parsing extracts required_docs dynamically
- [ ] Materials table extraction working
- [ ] Multi-line instructions captured properly
- [ ] Spec learning creates FAISS index
- [ ] Audit analysis returns confidence scores
- [ ] Repealability determination accurate
- [ ] Index persists between restarts
- [ ] Node.js backend can connect

## 📈 Scaling Considerations

### When to Upgrade from Starter Plan

- Processing >100 PDFs/day → Upgrade to Standard
- Files >100MB regularly → Add more memory
- Need faster processing → Use GPU instances for embeddings

### Cost Optimization

- Current: $7/month handles ~1000 PDFs/month
- With caching: Minimal compute after initial learning
- Storage: 1GB included, sufficient for indexes

## 🔐 Security Best Practices

1. **Enable Authentication in Production**
```python
AUTH_ENABLED=true  # Set in environment
```

2. **Validate File Uploads**
   - Max file size: 50MB
   - Only accept PDF files
   - Scan for malicious content

3. **Rate Limiting**
   - Already implemented in endpoints
   - Adjust based on usage patterns

## 📝 API Documentation

### Complete API Endpoints

#### 1. Parse Job PDF
```http
POST /parse-job-pdf/
Content-Type: multipart/form-data

Returns:
{
  "required_docs": [...],  // Dynamically extracted
  "materials": {...},      // Table structure
  "instructions": [...],    // Multi-line support
  "gps_links": [...],      // With context
  "permits": [...]
}
```

#### 2. Learn Specification
```http
POST /learn-spec/
Content-Type: multipart/form-data

Returns:
{
  "index_size": 245,
  "embedding_dim": 384,
  "total_chunks": 245
}
```

#### 3. Analyze Audit
```http
POST /analyze-audit/
Content-Type: multipart/form-data

Returns:
{
  "summary": {...},
  "analysis": [
    {
      "infraction": "...",
      "repealable": true,
      "confidence": 85.0,
      "reasons": [...]
    }
  ]
}
```

## ✅ Final Deployment Steps

1. **Push to GitHub**
```bash
git add -A
git commit -m "Production-ready AI document analyzer"
git push origin main
```

2. **Monitor Deployment**
   - Watch Render dashboard for build progress
   - Check logs for any errors
   - Verify health endpoint

3. **Update Mobile App**
   - Set PDF_SERVICE_URL in Node.js backend
   - Test PDF upload flow
   - Verify data in Materials screen

## 🎉 Success Criteria

Your deployment is successful when:
- ✅ Service health check passes
- ✅ Dynamic extraction working
- ✅ Spec learning completes
- ✅ Audit analysis provides confidence scores
- ✅ Mobile app shows extracted data

## Support & Troubleshooting

For issues:
1. Check Render logs
2. Run test_full_workflow.py locally
3. Verify environment variables
4. Check memory usage in Render metrics

---

**Deployment Time**: ~10 minutes
**Monthly Cost**: $7 (Render Starter)
**Capacity**: 1000+ PDFs/month
