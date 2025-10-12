@echo off
REM Deploy NER-enhanced analyzer to Render.com
REM Windows version

echo ============================================
echo  DEPLOYING NER-ENHANCED ANALYZER TO RENDER
echo ============================================
echo.

REM Check if we're in the right directory
if not exist "backend\pdf-service\test_full_flow_simple.py" (
    echo Error: Must run from project root directory
    exit /b 1
)

echo Preparing deployment...
echo --------------------------

REM Ensure data directory exists
if not exist "data" mkdir data

REM Copy model if it exists (optional - can train on Render)
if exist "backend\pdf-service\data\fine_tuned_ner" (
    echo Found trained model, copying to repo...
    xcopy /E /I /Y "backend\pdf-service\data\fine_tuned_ner" "data\fine_tuned_ner"
)

REM Copy embeddings if they exist
if exist "backend\pdf-service\data\spec_embeddings.pkl" (
    echo Found spec embeddings, copying to repo...
    copy "backend\pdf-service\data\spec_embeddings.pkl" "data\" /Y
)

echo.
echo Staging changes...
git add backend\pdf-service\*.py
git add backend\pdf-service\data\training\*.json 2>nul
git add data\* 2>nul
git add requirements*.txt
git add Dockerfile* 2>nul
git add render*.yaml 2>nul
git add *.md

echo.
echo Committing changes...
git commit -m "Deploy NER-enhanced analyzer with full flow testing" -m "- Simplified test flow for Python 3.13 compatibility" -m "- Mock embeddings for testing without dependencies" -m "- Pattern-based NER extraction fallback" -m "- Confidence scoring with spec matching" -m "- Ready for Render.com deployment"

echo.
echo Pushing to GitHub...
git push origin main

echo.
echo ============================================
echo  DEPLOYMENT INITIATED
echo ============================================
echo.
echo Next Steps on Render.com:
echo -------------------------
echo 1. Check Render dashboard for auto-deploy
echo 2. Ensure /data disk is mounted (10GB)
echo 3. Set environment variables if needed:
echo    - CONFIDENCE_THRESHOLD=0.85
echo    - MODEL_PATH=/data/fine_tuned_ner
echo.
echo Test endpoints after deployment:
echo ---------------------------------
echo # Health check
echo curl https://your-app.onrender.com/health
echo.
echo # Upload spec
echo curl -X POST https://your-app.onrender.com/upload-specs ^
echo   -F "files=@spec.pdf"
echo.
echo # Analyze go-backs
echo curl -X POST https://your-app.onrender.com/analyze-go-back ^
echo   -d "{\"infraction_text\": \"16 ft clearance over street\"}"
echo.
echo ============================================
echo Expected Performance:
echo - Confidence: 85-95%% for matches
echo - Response time: ^<100ms
echo - Repeal rate: 30-50%%
echo ============================================

pause
