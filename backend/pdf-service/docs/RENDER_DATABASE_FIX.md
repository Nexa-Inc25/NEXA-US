# 🚨 URGENT: Fix DATABASE_URL in Render Dashboard

## Your Service is Running! ✅
- **Live at:** https://nexa-api-ergv.onrender.com
- **Status:** Running with in-memory storage (no persistence)
- **Issue:** DATABASE_URL is set to placeholder text

## The Problem
Your DATABASE_URL in Render is literally set to:
```
postgresql://user:password@host:port/dbname
```

This is placeholder text with literal words "host" and "port" instead of actual values!

## IMMEDIATE FIX REQUIRED

### Step 1: Go to Render Dashboard
1. Open https://dashboard.render.com
2. Click on your `nexa-api` service
3. Go to "Environment" tab

### Step 2: Update DATABASE_URL
Replace the placeholder with your ACTUAL database URL:
```
postgresql://nexa_admin:h7L101QmZt1WTyVHrnm4rLOz2wKRVF4G@dpg-d3hh2i63jp1c73fht4hg-a:5432/nexa_aerh
```

**IMPORTANT:** Note the `:5432` port number is included!

### Step 3: Save & Deploy
1. Click "Save Changes"
2. Service will auto-redeploy
3. Monitor logs for: "Successfully connected to PostgreSQL database"

## Alternative: Connect Render Database

If you have a Render PostgreSQL database:
1. DELETE the current DATABASE_URL variable
2. Click "Connect Database"
3. Select your PostgreSQL instance
4. Render will automatically set the correct URL

## Testing After Fix

### Check Health:
```bash
curl https://nexa-api-ergv.onrender.com/health
```

Expected response when database is connected:
```json
{
  "status": "healthy",
  "database_connected": true,
  "chunks_loaded": 0
}
```

### Upload Spec Book:
```bash
curl -X POST -F "file=@spec_book.pdf" https://nexa-api-ergv.onrender.com/learn-spec/
```

### Analyze Audit:
```bash
curl -X POST -F "file=@audit.pdf" https://nexa-api-ergv.onrender.com/analyze-audit/
```

## Current Status
- ✅ Application deployed and running
- ✅ Listening on port 10000
- ❌ Database not connected (using placeholder URL)
- ⚠️ Using in-memory storage (data lost on restart)

## What the Code Does Now
1. **Detects placeholder URLs** - Checks for "host:port", "user:password", etc.
2. **Auto-fixes missing ports** - Adds :5432 if port is missing
3. **Clear error messages** - Shows exactly what's wrong
4. **Graceful fallback** - Uses in-memory storage if database unavailable

## After Fixing DATABASE_URL
The logs will show:
```
DATABASE_URL configured: postgresql://***@dpg-d3hh2i63jp1c73fht4hg-a:5432/nexa_aerh
Attempting to connect to database...
Successfully connected to PostgreSQL database
Database initialized with hnsw index
```

## Need Help?
If the provided DATABASE_URL doesn't work, you may need to:
1. Create a new PostgreSQL database on Render
2. Enable the pgvector extension
3. Or contact Render support for database access issues
