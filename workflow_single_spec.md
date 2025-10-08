# Single-Spec Workflow for 50 PDFs

## Step 1: Merge Your 50 PDFs into One

### Option 1: Using Adobe Acrobat
1. Open Acrobat
2. Tools → Combine Files
3. Add all 50 PDFs
4. Arrange in order
5. Click "Combine"
6. Save as "PGE_Complete_Spec_Book.pdf"

### Option 2: Using pdftk (Command Line)
```bash
# Install pdftk first
# Windows: choco install pdftk
# Mac: brew install pdftk-java

# Combine all PDFs in a folder
pdftk *.pdf cat output PGE_Complete_Spec_Book.pdf

# Or specific order:
pdftk 001.pdf 002.pdf 003.pdf ... 050.pdf cat output PGE_Complete_Spec_Book.pdf
```

### Option 3: Using Python
```python
from PyPDF2 import PdfMerger
import glob

merger = PdfMerger()

# Get all PDFs in order
pdf_files = sorted(glob.glob("specs/*.pdf"))

for pdf in pdf_files:
    print(f"Adding {pdf}...")
    merger.append(pdf)

merger.write("PGE_Complete_Spec_Book.pdf")
merger.close()

print("✅ Merged into PGE_Complete_Spec_Book.pdf")
```

## Step 2: Upload Combined Spec Book

```bash
# Upload the merged PDF
curl -X POST https://nexa-doc-analyzer-oct2025.onrender.com/upload-spec-book \
  -F "file=@PGE_Complete_Spec_Book.pdf" \
  -o spec_response.json

# Check result
cat spec_response.json
# Expected: {"chunks_learned": 2000+, "message": "Spec book learned successfully"}
```

## Step 3: Analyze Audits

```bash
# Analyze your go-back audit
curl -X POST https://nexa-doc-analyzer-oct2025.onrender.com/analyze-audit \
  -F "file=@QA25-35601253-120424794-Alvah-GOBACK1.pdf" \
  -o audit_results.json

# View results with jq (prettier)
cat audit_results.json | jq .

# Or without jq
cat audit_results.json
```

## Step 4: Verify Learning

```bash
# Check if spec is loaded
curl https://nexa-doc-analyzer-oct2025.onrender.com/health | jq

# Should show:
# "spec_learned": true
# "endpoints": ["/health", "/upload-spec-book", "/analyze-audit"]
```

## Limitations of This Approach

1. **No Source Tracking**: Results won't tell you which of the 50 sections matched
2. **Overwrites on Update**: Must re-upload entire 3GB+ file to update one section
3. **Large File**: Combined PDF may be 500MB-2GB (slower uploads)
4. **Memory Usage**: Loading entire spec book at once

## When to Switch to Multi-Spec

Switch to multi-spec version (Option B) if you need:
- Source tracking (know which spec section matched)
- Incremental updates (add/remove individual sections)
- Faster uploads (batch 10 files at a time)
- Better organization (50 files separate)
