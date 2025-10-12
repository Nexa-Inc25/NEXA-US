@echo off
REM Universal test runner for NEXA PDF Service
REM Works regardless of PATH configuration

echo ============================================================
echo NEXA PDF Service Test Runner
echo ============================================================
echo.

REM Use python -m to run pytest (always works)
echo Running tests with python -m pytest...
echo.

REM Basic test run
echo [1] Running all tests...
python -m pytest tests/ -v --tb=short

REM Check if tests passed
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ============================================================
    echo Tests FAILED! See errors above.
    echo ============================================================
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo ============================================================
echo All tests PASSED!
echo ============================================================
echo.

REM Run with coverage if requested
choice /C YN /M "Run tests with coverage report"
if %ERRORLEVEL% EQU 1 (
    echo.
    echo [2] Running tests with coverage...
    python -m pytest tests/ --cov=app_electrical --cov=app_oct2025_enhanced --cov-report=term --cov-report=html
    echo.
    echo Coverage report saved to htmlcov/index.html
)

echo.
echo ============================================================
echo Test run complete!
echo ============================================================
pause
