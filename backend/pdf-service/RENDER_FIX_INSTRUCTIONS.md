# 🚨 URGENT: Fix Render Dockerfile Configuration

## Problem
Render is using `Dockerfile.api` (which requires PostgreSQL) instead of `Dockerfile` (October 2025 version with local storage).

## Root Cause
The Dockerfile path is configured in Render's dashboard, not in your code.

## ✅ SOLUTION: Update in Render Dashboard

### Step 1: Login to Render
Go to: https://dashboard.render.com

### Step 2: Find Your Service
Look for: `nexa-doc-analyzer-oct2025`

### Step 3: Go to Settings
Click on the service → Click "Settings" tab

### Step 4: Update Dockerfile Path
Find the field that says one of these:
- **"Dockerfile Path"**
- **"Docker Command"**  
- **"Build Command"**

Current value is probably one of:
- `./Dockerfile.api`
- `backend/pdf-service/Dockerfile.api`
- Empty (defaulting to wrong file)

**Change it to**:
```
backend/pdf-service/Dockerfile
```

### Step 5: Clear Build Cache (Important!)
1. Still in Settings, find "Build & Deploy" section
2. Look for "Clear build cache" button
3. Click it to force a fresh build

### Step 6: Manual Deploy
1. Go back to the service main page
2. Click "Manual Deploy" → "Clear build cache & deploy"
3. This forces Render to rebuild from scratch

## Alternative: Check Environment Variables

While in Settings, verify these environment variables:
- **Remove**: `DATABASE_URL` (if present)
- **Keep**: Everything else

## Verification

After deployment, check logs for:
```
INFO:app_oct2025_enhanced:⚡ CPU Optimization: 16 cores detected
INFO:app_oct2025_enhanced:🔧 Using device: cpu
INFO:app_oct2025_enhanced:💾 Data storage path: /data
```

Should **NOT** see:
```
ModuleNotFoundError: No module named 'psycopg2'
File "/app/api.py", line 14
```

## Test After Fix

```bash
curl https://nexa-doc-analyzer-oct2025.onrender.com/spec-library
```

Should return JSON with library status, not an error.

---

**This is a Render dashboard configuration issue, not a code issue. Your code is correct!**
