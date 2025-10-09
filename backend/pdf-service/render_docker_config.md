# Render Docker Configuration Fix

## Problem
Render is using the wrong Dockerfile, causing it to look for the wrong Python file.

## Solution in Render Dashboard

### Option 1: Update Dockerfile Path
In your Render service settings, look for one of these fields:
- **Dockerfile Path**: `backend/pdf-service/Dockerfile.oct2025`
- **Docker Command**: `docker build -f backend/pdf-service/Dockerfile.oct2025 .`
- **Build Filter/Path**: `backend/pdf-service/Dockerfile.oct2025`

### Option 2: Update Build Command
If there's a "Build Command" field, set it to:
```bash
docker build -f Dockerfile.oct2025 -t nexa-doc-analyzer .
```

### Option 3: Rename Dockerfile (Last Resort)
If Render insists on using `Dockerfile`, rename the files:

```bash
# Backup current Dockerfile
mv Dockerfile Dockerfile.backup

# Use October 2025 version as default
cp Dockerfile.oct2025 Dockerfile
```

## Verification
After deployment, check logs for:
- Should see: `Loading app_oct2025_enhanced.py`
- Should NOT see: `ModuleNotFoundError: No module named 'psycopg2'`

## Available Dockerfiles

| File | Purpose | Start Command |
|------|---------|---------------|
| `Dockerfile` | Basic version | `app:app` |
| `Dockerfile.oct2025` | **October 2025 (USE THIS)** | `app_oct2025_enhanced:app` |
| `Dockerfile.api` | PostgreSQL version | `api:app` |
| `Dockerfile.render` | Render optimized | Check file for command |

## Environment Variables to Set

```bash
# No DATABASE_URL needed for October 2025 version
PYTHON_VERSION=3.10
PORT=8000
```

## Test After Deploy

```bash
curl https://nexa-doc-analyzer-oct2025.onrender.com/status
```

Should return spec library status without database errors.
