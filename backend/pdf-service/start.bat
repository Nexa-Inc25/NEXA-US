@echo off
REM Startup script for NEXA PDF Processing & AI Analysis Service (Windows)

echo Starting NEXA PDF Processing ^& AI Analysis Service
echo ==================================================

REM Check Python version
python --version

REM Install dependencies
echo.
echo Installing dependencies...
pip install -r requirements.txt

REM Create data directory if it doesn't exist
if not exist "data" mkdir data

REM Set environment variables for local testing
set AUTH_ENABLED=false
set AUTH0_DOMAIN=dev-kbnx7pja3zpg0lud.us.auth0.com
set AUTH0_AUDIENCE=https://api.nexa.local

echo.
echo Dependencies installed
echo.
echo Configuration:
echo   - Auth: DISABLED (for local testing)
echo   - Port: 8000
echo   - Data: ./data/
echo.
echo Starting server...
echo.

REM Start the service
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
