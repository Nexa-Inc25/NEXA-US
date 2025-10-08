@echo off
REM Deploy Multi-Spec Version to Render
echo.
echo ========================================
echo   NEXA MULTI-SPEC DEPLOYMENT v2.0
echo ========================================
echo.

echo Preparing multi-spec deployment...
echo.

REM Update the main Dockerfile to use multi-spec version
echo Updating Dockerfile...
copy /Y Dockerfile.multi Dockerfile
if errorlevel 1 (
    echo ERROR: Failed to update Dockerfile
    exit /b 1
)

REM Commit changes
echo.
echo Committing multi-spec changes...
git add -A
git commit -m "Deploy multi-spec support v2.0 - Multiple file upload and persistent storage"

REM Push to Render
echo.
echo Deploying to Render...
git push origin main

echo.
echo ========================================
echo   DEPLOYMENT COMPLETE!
echo ========================================
echo.
echo New endpoints available:
echo   - POST /upload-specs     (multiple files)
echo   - GET  /spec-library     (view all specs)
echo   - POST /manage-specs     (clear/remove)
echo.
echo Test with:
echo   python test_multi_spec.py
echo.
pause
