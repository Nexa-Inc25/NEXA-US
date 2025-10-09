@echo off
REM Quick fix for Render deployment - use October 2025 Dockerfile

echo Backing up current Dockerfile...
copy Dockerfile Dockerfile.backup

echo Using October 2025 Dockerfile as default...
copy /Y Dockerfile.oct2025 Dockerfile

echo Done! Now commit and push:
echo   git add Dockerfile
echo   git commit -m "Use October 2025 Dockerfile as default for Render"
echo   git push
