# Deploy Multi-Spec Version for 50 PDFs

## Why Upgrade to Multi-Spec?

Your current single-spec version works great for ONE PDF. But with 50 separate spec sections, multi-spec provides:

1. **Source Tracking**: Know which spec file triggered each match
2. **Incremental Learning**: Add/remove specs without re-uploading everything
3. **Batch Upload**: Upload 10-20 PDFs at once
4. **Deduplication**: Auto-skip duplicate files by hash
5. **Library Management**: View, clear, or remove individual specs

## Step 1: Update Your Deployment

### Option A: Replace Main App File (Easiest)

```bash
cd c:\Users\mikev\CascadeProjects\nexa-inc-mvp\backend\pdf-service

# Backup current version
copy app_oct2025_enhanced.py app_oct2025_enhanced_BACKUP.py

# Deploy multi-spec version
copy app_multi_spec.py app_oct2025_enhanced.py

# Commit and push
git add app_oct2025_enhanced.py
git commit -m "Upgrade to multi-spec support for 50 PDFs"
git push origin main
```

### Option B: Update Dockerfile to Use Multi-Spec

Edit `Dockerfile` line 52:
```dockerfile
# BEFORE:
CMD ["sh", "-c", "if [ -f app_oct2025_enhanced.py ]; then uvicorn app_oct2025_enhanced:app...

# AFTER:
CMD ["sh", "-c", "if [ -f app_multi_spec.py ]; then uvicorn app_multi_spec:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1; elif [ -f app_oct2025_enhanced.py ]; then uvicorn app_oct2025_enhanced:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1; else echo 'No app file found!' && exit 1; fi"]
```

Then:
```bash
git add Dockerfile
git commit -m "Update to use multi-spec app"
git push origin main
```

## Step 2: Trigger Render Deploy

1. Go to https://dashboard.render.com
2. Find: `nexa-doc-analyzer-oct2025`
3. Click: **Manual Deploy**
4. Wait: ~5-10 minutes for build

## Step 3: Verify New Endpoints

```bash
# Check API info (should show new endpoints)
curl https://nexa-doc-analyzer-oct2025.onrender.com/ | jq

# Expected new endpoints:
# - /upload-specs (multi-file upload)
# - /spec-library (view all specs)
# - /manage-specs (clear/remove specs)
```

## Step 4: Upload Your 50 Spec PDFs

### Using Batch Upload Script:

```bash
# Navigate to your specs folder
cd C:\path\to\your\50\specs\

# Run batch uploader
python c:\Users\mikev\CascadeProjects\nexa-inc-mvp\backend\pdf-service\batch_upload_50_specs.py . --mode replace --batch-size 10
```

### Manual Upload (Python):

```python
import requests
import glob
from pathlib import Path

API_URL = "https://nexa-doc-analyzer-oct2025.onrender.com"
spec_folder = "C:/path/to/your/50/specs/"

# Get all PDFs
pdf_files = sorted(Path(spec_folder).glob("*.pdf"))
print(f"Found {len(pdf_files)} PDFs")

# Upload in batches of 10
batch_size = 10
for i in range(0, len(pdf_files), batch_size):
    batch = pdf_files[i:i+batch_size]
    
    print(f"\nUploading batch {i//batch_size + 1}...")
    
    # Prepare files
    files = []
    for pdf_path in batch:
        with open(pdf_path, 'rb') as f:
            files.append(('files', (pdf_path.name, f.read(), 'application/pdf')))
    
    # Upload batch
    response = requests.post(
        f"{API_URL}/upload-specs",
        files=files,
        data={"mode": "append" if i > 0 else "replace"}
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Uploaded {result['files_processed']} files")
        print(f"   New chunks: {result['new_chunks_added']}")
        print(f"   Total chunks: {result['total_chunks']}")
    else:
        print(f"❌ Batch failed: {response.status_code}")
        print(response.text)
```

### Using Web Interface:

1. Open: `c:\Users\mikev\CascadeProjects\nexa-inc-mvp\backend\pdf-service\upload_example.html`
2. Drag and drop 10 PDFs at a time
3. Click "Upload Spec Files"
4. Repeat until all 50 uploaded

## Step 5: Check Your Library

```bash
# View all uploaded specs
curl https://nexa-doc-analyzer-oct2025.onrender.com/spec-library | jq

# Expected output:
{
  "total_files": 50,
  "total_chunks": 3000,
  "last_updated": "2025-10-07T16:20:00",
  "files": [
    {
      "filename": "015077_Crossarm_hardware.pdf",
      "chunk_count": 45,
      "file_hash": "abc123...",
      "uploaded_at": "2025-10-07T16:15:00"
    },
    ...
  ]
}
```

## Step 6: Analyze Audits with Source Tracking

```bash
# Analyze your go-back audit
curl -X POST https://nexa-doc-analyzer-oct2025.onrender.com/analyze-audit \
  -F "file=@QA25-35601253-120424794-Alvah-GOBACK1.pdf" \
  | jq

# Expected output with source tracking:
[
  {
    "infraction": "Go-back: Incorrect secondary aerial cable spacing",
    "status": "REPEALABLE",
    "confidence": 85.0,
    "match_count": 2,
    "reasons": [
      "[Source: 057875_Secondary_Aerial_Cable.pdf] Minimum separation from cutouts...",
      "[Source: 015225_Cutouts_Fuses.pdf] For secondary in rack construction..."
    ]
  }
]
```

Notice the **[Source: filename.pdf]** prefix showing which spec matched!

## New Endpoints Available

### 1. Upload Multiple Specs
```bash
curl -X POST https://nexa-doc-analyzer-oct2025.onrender.com/upload-specs \
  -F "files=@spec1.pdf" \
  -F "files=@spec2.pdf" \
  -F "files=@spec3.pdf" \
  -F "mode=append"
```

### 2. View Library
```bash
curl https://nexa-doc-analyzer-oct2025.onrender.com/spec-library
```

### 3. Manage Specs
```bash
# Clear entire library
curl -X POST https://nexa-doc-analyzer-oct2025.onrender.com/manage-specs \
  -H "Content-Type: application/json" \
  -d '{"operation": "clear"}'

# Remove specific file
curl -X POST https://nexa-doc-analyzer-oct2025.onrender.com/manage-specs \
  -H "Content-Type: application/json" \
  -d '{"operation": "remove", "filename": "old_spec.pdf"}'
```

## Benefits You'll See

1. **Faster Updates**: Update one spec without re-uploading all 50
2. **Better Debugging**: Know exactly which spec triggered a match
3. **Organized Library**: View all 50 specs with metadata
4. **Efficient Storage**: Deduplication prevents duplicate processing
5. **Scalable**: Easily add spec #51, #52, etc.

## Rollback Plan (If Issues)

```bash
# Restore backup
cd backend/pdf-service
copy app_oct2025_enhanced_BACKUP.py app_oct2025_enhanced.py

# Redeploy
git add app_oct2025_enhanced.py
git commit -m "Rollback to single-spec version"
git push origin main

# Manual deploy on Render
```

## Performance Expectations

With 50 spec PDFs (~3000-5000 chunks):
- **Upload time**: 2-5 minutes total (5 batches of 10 files)
- **Analysis speed**: Same as before (1-3 seconds per audit)
- **Memory usage**: ~200-300MB (efficient chunking)
- **Storage**: ~50-100MB in /data

## Ready to Deploy?

Choose your path:
- **Option A**: Copy app_multi_spec.py → app_oct2025_enhanced.py
- **Option B**: Update Dockerfile CMD to use app_multi_spec.py

Then: Push → Manual Deploy → Upload 50 PDFs → Analyze Audits!
