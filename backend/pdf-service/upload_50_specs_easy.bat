@echo off
REM Easy Upload Script for 50 Spec PDFs
REM Just place this file in the folder with your PDFs and double-click!

echo.
echo ============================================
echo    NEXA 50-SPEC BATCH UPLOADER
echo ============================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.7+ from python.org
    pause
    exit /b 1
)

REM Check for PDFs in current directory
echo Checking for PDF files in current directory...
dir /b *.pdf >nul 2>&1
if errorlevel 1 (
    echo.
    echo ERROR: No PDF files found in this directory!
    echo Please place this script in the folder with your 50 spec PDFs
    echo.
    pause
    exit /b 1
)

REM Count PDFs
setlocal enabledelayedexpansion
set count=0
for %%f in (*.pdf) do set /a count+=1

echo.
echo Found !count! PDF files in this directory
echo.

REM Show first few files
echo First 5 files:
set shown=0
for %%f in (*.pdf) do (
    if !shown! lss 5 (
        echo   - %%f
        set /a shown+=1
    )
)
if !count! gtr 5 echo   ... and !count! more files

echo.
echo ============================================
echo.
echo This script will upload all !count! PDFs to NEXA
echo in batches of 10 files at a time.
echo.
echo Choose upload mode:
echo   1. APPEND - Add to existing spec library (recommended)
echo   2. REPLACE - Clear library and start fresh
echo   3. CANCEL - Exit without uploading
echo.
choice /c 123 /n /m "Enter your choice (1, 2, or 3): "

if errorlevel 3 (
    echo.
    echo Upload cancelled.
    pause
    exit /b 0
)

if errorlevel 2 (
    set MODE=replace
    echo.
    echo WARNING: This will REPLACE the entire spec library!
    choice /c YN /n /m "Are you sure? (Y/N): "
    if errorlevel 2 (
        echo Upload cancelled.
        pause
        exit /b 0
    )
) else (
    set MODE=append
)

echo.
echo ============================================
echo Starting upload in %MODE% mode...
echo ============================================
echo.

REM Download the batch upload script if it doesn't exist
if not exist batch_upload_50_specs.py (
    echo Downloading upload script...
    powershell -Command "Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/Nexa-Inc25/NEXA-US/main/backend/pdf-service/batch_upload_50_specs.py' -OutFile 'batch_upload_50_specs.py'" >nul 2>&1
    if errorlevel 1 (
        echo ERROR: Could not download upload script
        echo Please ensure you have internet connection
        pause
        exit /b 1
    )
)

REM Install required Python packages if needed
echo Checking Python dependencies...
pip show requests >nul 2>&1
if errorlevel 1 (
    echo Installing required packages...
    pip install requests
)

REM Run the batch upload
echo.
echo ============================================
echo UPLOADING YOUR 50 SPEC FILES...
echo ============================================
echo.

python batch_upload_50_specs.py . --mode %MODE% --batch-size 10

if errorlevel 1 (
    echo.
    echo ============================================
    echo ERROR: Upload failed!
    echo Please check your internet connection and try again
    echo ============================================
) else (
    echo.
    echo ============================================
    echo SUCCESS! All spec files uploaded!
    echo ============================================
    echo.
    echo Your 50-section spec book is now ready to use!
    echo You can analyze audits at:
    echo https://nexa-doc-analyzer-oct2025.onrender.com
    echo.
)

echo.
pause
