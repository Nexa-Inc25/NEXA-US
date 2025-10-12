# NEXA 50-Section Spec Book Upload Guide

## Quick Start

Your spec book with **50 separate PDF sections** can be uploaded efficiently using our batch upload system.

## Method 1: Command Line Batch Upload (Recommended)

### Step 1: Organize Your PDFs
Place all 50 PDFs in a single folder:
```
specs/
  ├── 015077_Crossarm_hardware.pdf
  ├── 015225_Cutouts_Fuses.pdf
  ├── 092813_FuseSaver.pdf
  ├── 094672_TripSaver.pdf
  ├── ... (46 more PDFs)
  └── 099999_Final_section.pdf
```

### Step 2: Run Batch Upload
```bash
# Upload all 50 PDFs (appends to existing library)
python batch_upload_50_specs.py specs/

# Or replace entire library
python batch_upload_50_specs.py specs/ --mode replace

# Adjust batch size if needed (default is 10 files per batch)
python batch_upload_50_specs.py specs/ --batch-size 5
```

### What Happens:
- **Automatic Batching**: Uploads 10 files at a time (5 batches total)
- **Progress Tracking**: Shows upload progress for each batch
- **Error Recovery**: If a batch fails, continues with next batch
- **Deduplication**: Skips files already in library (by hash)
- **Time Estimate**: ~2-5 minutes for all 50 files

## Method 2: Web Interface Upload

### For smaller batches (5-10 files at a time):

1. Open `upload_example.html` in browser
2. Drag and drop 10 PDFs at a time
3. Click "Upload Spec Files"
4. Repeat 5 times for all 50 files

## Method 3: Python Script Upload

```python
import os
import requests
from pathlib import Path

def upload_50_specs(spec_folder):
    """Upload all 50 spec PDFs"""
    
    # Get all PDFs
    pdf_files = list(Path(spec_folder).glob("*.pdf"))
    print(f"Found {len(pdf_files)} PDFs")
    
    # Upload in batches of 10
    batch_size = 10
    url = "https://nexa-doc-analyzer-oct2025.onrender.com/upload-specs"
    
    for i in range(0, len(pdf_files), batch_size):
        batch = pdf_files[i:i+batch_size]
        
        # Prepare files for upload
        files = []
        for pdf_path in batch:
            with open(pdf_path, 'rb') as f:
                files.append(('files', (pdf_path.name, f.read(), 'application/pdf')))
        
        # Upload batch
        print(f"Uploading batch {i//batch_size + 1}/{(len(pdf_files) + batch_size - 1)//batch_size}")
        response = requests.post(url, files=files, data={"mode": "append"})
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Uploaded {data['files_processed']} files")
        else:
            print(f"❌ Batch failed: {response.status_code}")
        
        time.sleep(2)  # Brief pause between batches

# Usage
upload_50_specs("path/to/your/50/specs/")
```

## Understanding the Process

### Storage Structure After Upload:
```
/data/ (Persistent Storage)
  ├── spec_embeddings.pkl (50-100MB)
  │   └── Contains embeddings for all 50 sections
  └── spec_metadata.json
      └── Metadata for all 50 PDFs
```

### Expected Metrics:
- **50 PDF files** → ~2,000-5,000 chunks total
- **Storage size**: 50-100MB
- **Upload time**: 2-5 minutes total
- **Analysis speed**: Same (uses indexed embeddings)

## Benefits of 50 Separate PDFs

✅ **Better Organization**: Each section clearly defined
✅ **Source Tracking**: Know exactly which section matched
✅ **Selective Updates**: Update individual sections without re-uploading all
✅ **Parallel Processing**: Batches can upload simultaneously
✅ **Error Isolation**: If one PDF fails, others still upload

## Monitoring Upload Progress

### Check Status During Upload:
```python
# In another terminal/script
import requests

response = requests.get("https://nexa-doc-analyzer-oct2025.onrender.com/spec-library")
data = response.json()

print(f"Files uploaded so far: {data['total_files']}/50")
print(f"Total chunks: {data['total_chunks']}")
```

## After Upload: Verify Success

### Check Final Library:
```bash
python test_multi_spec.py status
```

Expected output:
```
📚 Total files in library: 50
📊 Total chunks: 3,847
✅ Storage path: /data
```

## Troubleshooting

### If Upload Fails:
1. **Timeout errors**: Reduce batch size to 5 files
2. **Memory errors**: Upload in smaller groups
3. **Network issues**: Script automatically retries failed batches

### Check Individual File Status:
```python
# List all uploaded files
import requests

response = requests.get("https://nexa-doc-analyzer-oct2025.onrender.com/spec-library")
data = response.json()

for file in data['files']:
    print(f"{file['filename']}: {file['chunk_count']} chunks, {file['file_hash']}")
```

## Best Practices for 50-Section Spec Books

1. **Naming Convention**: Use consistent naming (e.g., `001_Section1.pdf`, `002_Section2.pdf`)
2. **File Size**: Keep individual PDFs under 20MB for faster processing
3. **Initial Upload**: Use `mode="replace"` for first upload
4. **Updates**: Use `mode="append"` when adding new sections
5. **Backup**: Keep local copies of all 50 PDFs

## Performance Expectations

With 50 spec PDFs loaded:
- **Library size**: ~50-100MB in memory
- **Analysis speed**: 1-3 seconds per audit
- **Accuracy**: Higher with comprehensive coverage
- **Match quality**: Source tracking shows which spec section matched

## Command Summary

```bash
# Full upload of 50 specs
python batch_upload_50_specs.py /path/to/specs/

# Check upload progress
python test_multi_spec.py status

# Clear and restart if needed
python test_multi_spec.py clear

# Analyze audit against all 50 specs
python test_multi_spec.py analyze audit.pdf
```

## Support

If you encounter issues with the 50-file upload:
1. Try smaller batch sizes (5 files)
2. Upload during off-peak hours
3. Use the batch script's error recovery
4. Check Render logs for server-side errors

Your 50-section spec book will be **permanently stored** and **instantly available** for all future audits!
