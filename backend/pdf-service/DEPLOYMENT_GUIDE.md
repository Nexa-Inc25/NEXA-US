# NEXA API Deployment Guide for Render.com

## Quick Fix for Current Error

The deployment is failing because the `DATABASE_URL` environment variable contains invalid text (likely placeholder text like `[Will`). 

### Immediate Steps to Fix:

1. **Log into Render.com Dashboard**
2. **Navigate to your `nexa-api` service**
3. **Go to Environment Variables**
4. **Fix the DATABASE_URL:**
   - If you have a Render PostgreSQL database, click "Connect Database" and select your database
   - Or manually set it to a valid PostgreSQL URL format:
     ```
     postgresql://username:password@host:port/database
     ```
   - **Remove any placeholder text** like `[Will` or brackets

## Deployment Options

### Option 1: Docker Deployment (Recommended)

1. **Use the new Docker configuration:**
   ```bash
   # From the root of your project
   render-cli deploy --file backend/pdf-service/render-docker.yaml
   ```
   
2. **Or manually in Render Dashboard:**
   - Create new Web Service
   - Connect your GitHub repo
   - Set Root Directory: `backend/pdf-service`
   - Set Dockerfile Path: `./Dockerfile.render`
   - Environment: Docker

### Option 2: Fix Existing Python Deployment

1. **Update Environment Variables in Render:**
   ```
   DATABASE_URL=postgresql://[your-db-connection-string]
   LOG_LEVEL=INFO
   VECTOR_INDEX_TYPE=hnsw
   ```

2. **If no database yet, the app will use in-memory storage**

## Database Setup

### Create PostgreSQL Database on Render:

1. **In Render Dashboard:**
   - New > PostgreSQL
   - Name: `nexa-postgres`
   - Plan: Pro (for pgvector support)
   - Version: 15

2. **Enable pgvector extension:**
   ```sql
   -- Connect to your database using Render's psql shell
   CREATE EXTENSION IF NOT EXISTS vector;
   ```

3. **Link Database to Service:**
   - Go to your web service
   - Environment > Add Environment Variable
   - Add from Database > Select your PostgreSQL instance

## Testing Deployment

### 1. Check Health Endpoint:
```bash
curl https://your-service.onrender.com/health
```

### 2. Test with Sample Files:
```bash
# Upload spec book
curl -X POST -F "file=@spec_book.pdf" \
  https://your-service.onrender.com/learn-spec/

# Analyze audit
curl -X POST -F "file=@audit.pdf" \
  https://your-service.onrender.com/analyze-audit/
```

## Environment Variables Reference

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| DATABASE_URL | PostgreSQL connection string | None (uses memory) | postgresql://user:pass@host/db |
| PORT | Server port (set by Render) | 8000 | 10000 |
| LOG_LEVEL | Logging verbosity | INFO | DEBUG, INFO, WARNING, ERROR |
| VECTOR_INDEX_TYPE | Index type for similarity search | hnsw | hnsw, ivfflat |
| HNSW_M | HNSW index parameter | 16 | 4-64 |
| HNSW_EF_SEARCH | HNSW search parameter | 60 | 40-200 |
| CHUNK_SIZE | Text chunk size for processing | 500 | 200-1000 |
| MAX_PAGES | Maximum PDF pages to process | 1500 | 100-5000 |

## Troubleshooting

### "Invalid DSN" Error:
- Check DATABASE_URL format
- Remove any brackets, placeholders, or special characters
- Ensure it starts with `postgresql://` or `postgres://`

### "No spec book loaded" Error:
- Upload a spec PDF first using `/learn-spec/` endpoint
- Check database connection is working

### Memory Issues:
- Reduce MAX_PAGES if processing large PDFs
- Use smaller CHUNK_SIZE
- Upgrade to larger Render instance

### Slow Performance:
- Adjust vector index parameters
- Use `ivfflat` instead of `hnsw` for faster indexing
- Enable database connection pooling

## Monitoring

### View Metrics:
```bash
curl https://your-service.onrender.com/metrics
```

### Check Database Performance:
```bash
curl https://your-service.onrender.com/db/pgstat
```

### Run Benchmark:
```bash
curl "https://your-service.onrender.com/bench/knn?queries=10"
```

## Support

For issues specific to the NEXA API, check the logs in Render Dashboard.
The application now has robust error handling and will fall back to in-memory storage if the database connection fails.
