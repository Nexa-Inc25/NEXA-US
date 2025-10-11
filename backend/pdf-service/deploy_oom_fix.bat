@echo off
echo ========================================
echo DEPLOYING OOM FIX FOR VISION
echo ========================================
echo.
echo This will disable auto-training to prevent memory crashes
echo.

REM Run the fix script
echo Running fix script...
python fix_oom_vision.py

echo.
echo ========================================
echo COMMITTING AND DEPLOYING
echo ========================================
echo.

REM Add files
git add pole_vision_detector.py
git add training_config.py

REM Commit
git commit -m "Fix OOM: Disable auto-training on startup (uses >2GB RAM)"

REM Push
git push origin main

echo.
echo ========================================
echo ✅ FIX DEPLOYED!
echo ========================================
echo.
echo Monitor at: https://dashboard.render.com
echo.
echo The service will:
echo 1. Download Roboflow dataset ✅
echo 2. Skip training (saves 1.5GB RAM) ✅
echo 3. Use base YOLOv8 model ✅
echo.
echo To train later:
echo - Use /vision/train-on-specs endpoint
echo - Or train locally and upload model
echo ========================================

pause
