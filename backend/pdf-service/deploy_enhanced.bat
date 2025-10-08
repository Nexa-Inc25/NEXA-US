@echo off
REM Enhanced deployment script with validation and middleware
REM October 2025 - With improved error handling

echo 🚀 NEXA Document Analyzer - Enhanced Deployment
echo ==============================================
echo.

REM Check for required files
echo 📋 Pre-deployment checks...

if not exist "app_oct2025_enhanced.py" (
    echo ❌ Error: app_oct2025_enhanced.py not found
    exit /b 1
)

if not exist "middleware.py" (
    echo ❌ Error: middleware.py not found
    exit /b 1
)

if not exist "Dockerfile.oct2025" (
    echo ❌ Error: Dockerfile.oct2025 not found
    exit /b 1
)

echo ✅ All required files present
echo.

REM Create static directory if it doesn't exist
if not exist "static" mkdir static

REM Create a simple favicon if it doesn't exist
if not exist "static\favicon.ico" (
    echo Creating placeholder favicon...
    type nul > static\favicon.ico
)

REM Commit changes
echo 📦 Committing changes...
git add -A
git commit -m "Enhanced error handling, middleware, and monitoring - %date% %time%"

REM Push to Render
echo.
echo 🚀 Deploying to Render.com...
git push origin main

echo.
echo ✅ Deployment initiated!
echo.
echo 📊 Monitor deployment at:
echo    https://dashboard.render.com/web/srv-cs47qp88fa8c73ccvotg
echo.
echo 🔍 View logs at:
echo    https://dashboard.render.com/web/srv-cs47qp88fa8c73ccvotg/logs
echo.
echo 🌐 Once deployed, test endpoints:
echo    - Health: https://nexa-doc-analyzer-oct2025.onrender.com/health
echo    - Status: https://nexa-doc-analyzer-oct2025.onrender.com/status
echo    - Docs: https://nexa-doc-analyzer-oct2025.onrender.com/docs
echo.
echo 📝 Key improvements in this deployment:
echo    ✅ Request validation middleware
echo    ✅ Correlation IDs for request tracking
echo    ✅ Enhanced error messages
echo    ✅ Rate limiting (100 req/min)
echo    ✅ Status endpoint for spec book availability
echo.
pause
