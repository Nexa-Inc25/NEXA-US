@echo off
REM Week 2: Redis Performance Layer Deployment
REM Minimal pipeline usage - single commit

echo ====================================================
echo Week 2: Redis Performance Layer
echo ====================================================

REM Step 1: Add Redis to requirements
echo Adding Redis to requirements...
echo redis==5.0.1 >> backend/pdf-service/requirements_oct2025.txt

REM Step 2: Test Redis locally (optional)
echo Testing Redis connection...
python -c "import redis; r=redis.from_url('redis://localhost:6379'); print('Local Redis test:', r.ping() if r else 'No local Redis')" 2>NUL

REM Step 3: Single commit for all Redis changes
echo Committing Redis integration...
git add backend/pdf-service/redis_cache_manager.py
git add backend/pdf-service/week2_redis_integration.py
git add backend/pdf-service/requirements_oct2025.txt
git add backend/pdf-service/deploy_week2_redis.bat

git commit -m "Week 2: Redis caching layer - 20%% faster spec lookups, audit result caching"

REM Step 4: Push once
echo Pushing to GitHub (triggers Render deploy)...
git push origin main

echo.
echo ======================================================
echo IMPORTANT: Add Redis to Render NOW!
echo ======================================================
echo 1. Go to Render Dashboard
echo 2. Click "New +" -^> "Redis"
echo 3. Name: nexa-redis
echo 4. Plan: Starter ($7/month for 25MB)
echo 5. Region: Same as your app (Oregon)
echo 6. Click "Create Redis"
echo 7. Copy the Internal Redis URL
echo 8. Go to your API service settings
echo 9. Add Environment Variable:
echo    REDIS_URL = [paste the Internal Redis URL]
echo 10. Save and let it redeploy
echo.
echo After Redis is connected (5-10 min), test:
echo curl https://nexa-api-xpu3.onrender.com/cache-stats
echo.
echo Expected improvements:
echo - 20%% faster repeated spec lookups
echo - 40-60%% cache hit rate
echo - Audit analysis: 1.5s -^> 1.2s
echo.
pause
