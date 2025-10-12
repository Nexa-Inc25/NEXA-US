# URGENT: Fix Render Deployment

## Current Issue
Your deployment is failing because the DATABASE_URL has an invalid format with literal text "port" instead of a port number.

Error: `psycopg2.OperationalError: invalid integer value "port" for connection option "port"`

## Immediate Actions Required

### 1. Fix DATABASE_URL in Render Dashboard

**Option A: Use Render's PostgreSQL (Recommended)**
1. Go to https://dashboard.render.com
2. Navigate to your `nexa-api` service
3. Go to "Environment" tab
4. DELETE the current DATABASE_URL variable
5. Click "Connect Database"
6. Either:
   - Select existing `nexa-db` database if you have one
   - Or create new PostgreSQL database

**Option B: Manual DATABASE_URL**
1. Go to Environment variables
2. Find DATABASE_URL
3. Change from: `postgresql://user:password@host:port/database`
4. To actual values like: `postgresql://nexaadmin:actualpassword@dpg-xxxxx.render.com:5432/nexadb`

### 2. Force Docker Rebuild
The code has been updated with a timestamp comment to force Docker to rebuild without cache.

Push the changes:
```bash
git add .
git commit -m "Force Docker rebuild to fix database connection"
git push
```

### 3. Alternative: Deploy Without Database
If you want to deploy immediately without a database (using in-memory storage):

1. In Render Dashboard > Environment
2. DELETE the DATABASE_URL variable completely
3. The app will run with in-memory storage (data lost on restart)

## Verification Steps

After deployment:
1. Check health endpoint:
   ```bash
   curl https://nexa-api.onrender.com/health
   ```

2. Check logs in Render Dashboard for:
   - "Using in-memory storage" (if no database)
   - "Successfully connected to PostgreSQL database" (if database connected)

## DATABASE_URL Format Reference

Valid format:
```
postgresql://username:password@hostname:5432/databasename
```

Examples:
- Render Internal: `postgresql://nexauser:secret123@dpg-cm2abc.oregon-postgres.render.com:5432/nexadb`
- External: `postgresql://user:pass@external-db.com:5432/mydb`

Invalid formats that cause errors:
- `postgresql://user:password@host:port/database` (literal "port" text)
- `postgresql://[Will be provided]/database` (placeholder text)
- `postgres://user@host/db` (missing password)

## Need a Database?

To create a PostgreSQL database on Render:
1. New > PostgreSQL
2. Name: `nexa-postgres`  
3. Database: `nexadb`
4. User: `nexaadmin`
5. Region: Same as your web service
6. Plan: Starter ($7/month) or higher for pgvector support

After creation, Render will automatically provide the correct DATABASE_URL.
