# NEXA PDF Processing & AI Analysis Service

Complete document intelligence system with PyMuPDF processing and AI-powered infraction analysis.

## Features

### PDF Processing
- **Optimized for Large PDFs**: Handles 1000+ page spec books efficiently
- **Stream Processing**: Memory-efficient page-by-page processing
- **Smart Extraction**: Tables, instructions, GPS coordinates, permits
- **Fast Performance**: 2-5x faster than pdfplumber for large files

### AI Analysis (NEW)
- **Spec Learning**: Embeds and indexes specification documents
- **Infraction Detection**: Extracts go-backs, violations, and issues
- **Repealability Analysis**: Determines if infractions can be challenged
- **Confidence Scoring**: 0-100% confidence based on spec similarity
- **Reason Generation**: Provides spec citations for appeals

## API Endpoints

### `/parse-job-pdf/`
Extracts materials, instructions, and GPS coordinates from job PDFs.

**Response:**
```json
{
  "materials": {
    "headers": ["Item", "Quantity"],
    "rows": [["Bolts", "10"]]
  },
  "instructions": ["Step 1...", "Step 2..."],
  "gps_links": [{
    "coordinates": "37.7749,-122.4194",
    "googleMapsUrl": "...",
    "page": 1,
    "context": "..."
  }],
  "chunks": [...],
  "permits": ["PM12345678"]
}
```

### `/learn-spec/`
Processes large spec books for learning/indexing.

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run server
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

## Deploy to Render

### Option 1: As Separate Service

1. Create new repository or add to existing:
   ```bash
   git add pdf-service/
   git commit -m "Add Python PDF service"
   git push origin main
   ```

2. In Render Dashboard:
   - Create New > Web Service
   - Connect GitHub repo
   - Root Directory: `backend/pdf-service`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn app:app --host 0.0.0.0 --port $PORT`

3. Get service URL (e.g., `https://nexa-pdf-service.onrender.com`)

### Option 2: Using render.yaml

```bash
# Deploy with Render Blueprint
render create --file render.yaml
```

## Connect to Node.js Backend

1. Add environment variable to Node.js service on Render:
   ```
   PDF_SERVICE_URL=https://nexa-pdf-service.onrender.com
   ```

2. Node.js will automatically use Python service when available

## Performance Benchmarks

| File Size | Pages | pdfplumber | PyMuPDF | Improvement |
|-----------|-------|------------|---------|-------------|
| 10MB      | 100   | 8s         | 3s      | 2.6x        |
| 50MB      | 500   | 45s        | 15s     | 3x          |
| 100MB     | 1000  | 120s       | 35s     | 3.4x        |

## Memory Usage

- Stream processing keeps memory under 256MB even for 1000+ page PDFs
- Page batching (50 pages) prevents memory spikes
- Suitable for Render Starter plan ($7/month)

## Error Handling

- Corrupt PDF detection
- Page limit safety (MAX_PAGES=1500)
- Graceful degradation for missing sections
- Detailed error logging for debugging

## Testing

```bash
# Test with sample PDF
curl -X POST http://localhost:8000/parse-job-pdf/ \
  -F "job_file=@sample.pdf"

# Test large spec book
curl -X POST http://localhost:8000/learn-spec/ \
  -F "spec_file=@large_spec.pdf"
```
