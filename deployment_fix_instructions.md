# NEXA Deployment Fix Instructions

## Critical: Update Environment Variables

### On Render.com Dashboard or Vercel:

1. **Backend API Service** (nexa-core/services/api):
   - Find environment variable: `ANALYZER_URL`
   - Current value: `http://nexa-doc-analyzer-oct2025.onrender.com`
   - **CHANGE TO**: `https://nexa-doc-analyzer-oct2025.onrender.com`

2. **Frontend Dashboard** (if deployed separately):
   - Find environment variable: `REACT_APP_DOC_ANALYZER_URL`
   - Ensure it's set to: `https://nexa-doc-analyzer-oct2025.onrender.com`

### Local .env Files to Check:

```bash
# Backend API (.env)
ANALYZER_URL=https://nexa-doc-analyzer-oct2025.onrender.com

# Frontend (.env)
REACT_APP_DOC_ANALYZER_URL=https://nexa-doc-analyzer-oct2025.onrender.com
```

### After Updating:
1. Restart/redeploy the affected services
2. Clear browser cache
3. Test the analyze-audit endpoint

## Image-Only PDFs Issue

These 3 files need OCR processing:
- 015116 3-Wire Crossarm Construction 12, 17, and 21 KV.pdf
- 094674 - EFD SENSORS STANDARD_With added dimensions.pdf (P)_1.pdf  
- Vertical Primary Construction.pdf

### Solution Options:

1. **Use OCR Tool** (already created):
   ```bash
   python convert_image_pdfs.py
   ```

2. **Get Text Versions from PG&E**:
   - Request searchable PDF versions
   - These appear to be scanned documents

3. **Manual OCR Services**:
   - Adobe Acrobat Pro (OCR feature)
   - Google Drive (upload and open with Google Docs)
   - Online OCR services like smallpdf.com

## Verification Steps:

1. Check HTTPS is working:
   ```javascript
   // In browser console
   fetch('https://nexa-doc-analyzer-oct2025.onrender.com/status')
     .then(r => r.json())
     .then(console.log)
   ```

2. Test analyze endpoint:
   ```bash
   curl -X POST https://nexa-doc-analyzer-oct2025.onrender.com/analyze-audit \
     -F "file=@test.pdf"
   ```
