@echo off
echo ========================================
echo DEPLOYING PYTORCH COMPATIBILITY FIX
echo ========================================

echo.
echo Adding requirements fix...
git add requirements_oct2025.txt

echo.
echo Committing fix...
git commit -m "Fix PyTorch 2.6 compatibility - pin to torch==2.5.1 for YOLOv8"

echo.
echo Pushing to main...
git push origin main

echo.
echo ========================================
echo ✅ FIX DEPLOYED!
echo ========================================
echo.
echo Monitor deployment at: https://dashboard.render.com
echo Service URL: https://nexa-doc-analyzer-oct2025.onrender.com
echo.
echo Test when ready (3-5 min):
echo   curl https://nexa-doc-analyzer-oct2025.onrender.com/vision/model-status
echo.
echo ========================================

pause
