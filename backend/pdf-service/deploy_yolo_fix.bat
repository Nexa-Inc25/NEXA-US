@echo off
REM Deploy YOLO Compatibility Fix to Render
REM This script commits and pushes the YOLO fix to trigger Render auto-deploy

echo ========================================
echo   YOLO Model Compatibility Fix Deployment
echo ========================================
echo.

REM Check if we're in the right directory
if not exist "app_oct2025_enhanced.py" (
    echo ERROR: Not in the backend/pdf-service directory!
    echo Please cd to backend/pdf-service first
    exit /b 1
)

echo [1/4] Applying YOLO fix...
python apply_yolo_fix.py
if errorlevel 1 (
    echo Failed to apply fix!
    exit /b 1
)

echo.
echo [2/4] Adding files to git...
git add modules/pole_vision_detector_fixed.py
git add requirements_yolo_compat.txt
git add Dockerfile.yolo_fixed
git add apply_yolo_fix.py
git add YOLO_FIX_DEPLOYMENT.md
git add deploy_yolo_fix.bat

echo.
echo [3/4] Committing changes...
git commit -m "Fix: YOLO model DFLoss compatibility issue for ultralytics 8.0.x"

echo.
echo [4/4] Pushing to trigger Render deployment...
git push

echo.
echo ========================================
echo   Deployment triggered successfully!
echo ========================================
echo.
echo Monitor deployment at:
echo https://dashboard.render.com/
echo.
echo Once deployed, test at:
echo https://nexa-doc-analyzer-oct2025.onrender.com/health
echo.
echo If using new Dockerfile, update render.yaml:
echo   dockerfilePath: ./backend/pdf-service/Dockerfile.yolo_fixed
echo.
pause
