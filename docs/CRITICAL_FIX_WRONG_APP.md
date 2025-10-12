# 🚨 CRITICAL: Wrong App Running on Render!

## Problem Identified
- **Expected**: FastAPI running with uvicorn on port 8000
- **Actual**: Streamlit running on port 10000
- **Cause**: Render is not using the correct Dockerfile

## Immediate Fix Options

### Option 1: Update render.yaml (RECOMMENDED)
Change the dockerfilePath to use absolute path:
```yaml
services:
  - type: web
    name: nexa-api
    runtime: docker
    dockerfilePath: ./Dockerfile.api  # Make sure this is correct
```

### Option 2: Rename Dockerfile
```bash
# Backup current Dockerfile
mv Dockerfile Dockerfile.backup

# Use the API dockerfile as main
cp Dockerfile.api Dockerfile

# Commit and push
git add -A
git commit -m "Fix: Use correct Dockerfile for API service"
git push origin main
```

### Option 3: Manual Fix in Render Dashboard
1. Go to https://dashboard.render.com
2. Find `nexa-api` service
3. Click Settings
4. Under "Build & Deploy":
   - Docker Build Context Directory: `.`
   - Dockerfile Path: `./Dockerfile.api`
5. Click "Save Changes"
6. Trigger manual deploy

## The Real Issue
Render is ignoring the `dockerfilePath: ./Dockerfile.api` setting and using the root `Dockerfile` instead.

## Check Current Service
Visit: https://nexa-api.onrender.com
- If you see Streamlit UI → Wrong app
- If you get JSON response → Correct app
