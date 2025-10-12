@echo off
echo ============================================
echo    DEEP NER TRAINING FOR F1 ^> 0.9
echo ============================================
echo.
echo Training with enhanced job package data:
echo - Dataset: ~1100 tokens (900 original + 200 new)
echo - Target: F1 ^> 0.90 for production
echo - Duration: ~1-2 hours on CPU
echo.

cd /d "%~dp0"

REM Check for additional job package data
if not exist additional_job_data.jsonl (
    echo ERROR: additional_job_data.jsonl not found!
    echo Please ensure the file exists in the current directory.
    pause
    exit /b 1
)

echo Starting deep NER training...
echo.

REM Run the training
python train_ner_deep.py

if errorlevel 1 (
    echo.
    echo ERROR: Training failed!
    pause
    exit /b 1
)

echo.
echo ============================================
echo    TRAINING COMPLETE
echo ============================================
echo.
echo Check the results above:
echo - F1 ^>= 0.90: Ready for production!
echo - F1 0.85-0.89: Good, but add more data
echo - F1 ^< 0.85: Needs more training data
echo.
echo Model saved to: /data/fine_tuned_ner_deep
echo.
pause
