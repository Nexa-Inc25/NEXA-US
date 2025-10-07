@echo off
REM NEXA AI Document Analyzer - Render.com Deployment Script
REM October 07, 2025 Version - Windows

echo ================================================
echo  NEXA Document Analyzer - Deployment Script
echo    October 07, 2025 Enhanced Version
echo ================================================
echo.

REM Configuration
set RENDER_SERVICE_NAME=nexa-doc-analyzer-oct2025
set GITHUB_REPO=nexa-inc-mvp
set DOCKERFILE=Dockerfile.oct2025
set APP_FILE=app_oct2025_enhanced.py
set REQUIREMENTS=requirements_oct2025.txt

REM Check if files exist
echo Checking required files...
echo.

if not exist "%APP_FILE%" (
    echo ERROR: Missing %APP_FILE%
    exit /b 1
)

if not exist "%REQUIREMENTS%" (
    echo ERROR: Missing %REQUIREMENTS%
    exit /b 1
)

if not exist "%DOCKERFILE%" (
    echo ERROR: Missing %DOCKERFILE%
    exit /b 1
)

echo [OK] All required files present
echo.

REM Test locally first
echo Testing locally...
echo Starting server for testing...
echo.

REM Start server in background
start /B uvicorn app_oct2025_enhanced:app --port 8000
timeout /t 5 /nobreak > nul

REM Run tests
echo Running test suite...
python test_oct07_full.py

if %ERRORLEVEL% neq 0 (
    echo.
    echo ERROR: Tests failed. Fix issues before deploying.
    taskkill /F /IM uvicorn.exe 2>nul
    exit /b 1
)

echo [OK] Local tests passed
taskkill /F /IM uvicorn.exe 2>nul
echo.

REM Prepare for deployment
echo Preparing deployment...
echo.

REM Create render.yaml if it doesn't exist
if not exist "render.yaml" (
    echo Creating render.yaml...
    (
        echo services:
        echo   - type: web
        echo     name: %RENDER_SERVICE_NAME%
        echo     env: docker
        echo     dockerfilePath: ./%DOCKERFILE%
        echo     dockerContext: .
        echo     disk:
        echo       name: embeddings
        echo       mountPath: /data
        echo       sizeGB: 1
        echo     envVars:
        echo       - key: PYTHON_VERSION
        echo         value: "3.9"
        echo     healthCheckPath: /health
    ) > render.yaml
    echo [OK] render.yaml created
)

REM Git operations
echo.
echo Pushing to GitHub...

git add %APP_FILE% %REQUIREMENTS% %DOCKERFILE% test_oct07_full.py render.yaml deploy_to_render.bat
git commit -m "Deploy October 07, 2025 Enhanced Version - FuseSaver/Recloser improvements"
git push origin main

if %ERRORLEVEL% neq 0 (
    echo ERROR: Git push failed. Check your repository settings.
    exit /b 1
)

echo [OK] Code pushed to GitHub
echo.

REM Instructions for Render deployment
echo ================================================
echo  RENDER.COM DEPLOYMENT INSTRUCTIONS
echo ================================================
echo.
echo 1. Go to https://dashboard.render.com
echo.
echo 2. Click 'New +' then 'Web Service'
echo.
echo 3. Connect your GitHub repository: %GITHUB_REPO%
echo.
echo 4. Configure service:
echo    - Name: %RENDER_SERVICE_NAME%
echo    - Environment: Docker
echo    - Docker Path: %DOCKERFILE%
echo    - Instance Type: Starter ($7/month) for persistence
echo.
echo 5. Add Disk (for Starter plan):
echo    - Name: embeddings
echo    - Mount Path: /data
echo    - Size: 1 GB
echo.
echo 6. Environment Variables (optional):
echo    - LOG_LEVEL: INFO
echo.
echo 7. Click 'Create Web Service'
echo.
echo 8. Wait for build to complete (5-10 minutes)
echo.
echo 9. Test your deployment:
echo    curl https://%RENDER_SERVICE_NAME%.onrender.com/health
echo.
echo ================================================
echo  Deployment preparation complete!
echo ================================================
pause
