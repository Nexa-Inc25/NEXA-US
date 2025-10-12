@echo off
REM Week 1 Deployment - Windows Version (Minimal Pipeline Usage)

echo ==================================================
echo NEXA Week 1 Deployment - Pipeline Efficient
echo ==================================================

REM Single commit with all changes
echo Committing Week 1 optimizations...
git add backend/pdf-service/app_oct2025_enhanced.py
git add backend/pdf-service/backup_manager.py
git add backend/pdf-service/test_week1_optimizations.py
git add backend/pdf-service/app_opt_week1.py
git add backend/pdf-service/deploy_week1_minimal.sh
git add deploy_week1_windows.bat

git commit -m "Week 1: Foundation Layer - rate_limit=200, chunk_size=400, backup system (minimal pipeline)"

REM Push once to trigger Render deployment
echo Pushing to GitHub (triggers Render auto-deploy)...
git push origin main

echo.
echo Deployment initiated! 
echo Wait 3-5 minutes for Render to build and deploy.
echo.
echo Next steps:
echo 1. Run: python backend/pdf-service/test_week1_optimizations.py
echo 2. Check: https://nexa-api-xpu3.onrender.com/health
echo 3. Set up UptimeRobot at https://uptimerobot.com
echo.
echo Pipeline usage: 1 push = ~3-5 minutes max
pause
