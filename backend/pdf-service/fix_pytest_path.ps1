# PowerShell script to fix pytest PATH issue
# Run this script to add Python Scripts to PATH and test pytest

Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "Fixing pytest PATH Configuration" -ForegroundColor Yellow
Write-Host "=" * 60 -ForegroundColor Cyan

# Add Python Scripts directory to PATH for current session
$pythonScriptsPath = "$env:APPDATA\Python\Python313\Scripts"

Write-Host "`nChecking if pytest is installed..." -ForegroundColor Green
if (Test-Path "$pythonScriptsPath\pytest.exe") {
    Write-Host "✅ pytest found at: $pythonScriptsPath\pytest.exe" -ForegroundColor Green
} else {
    Write-Host "❌ pytest not found in expected location" -ForegroundColor Red
    Write-Host "Installing pytest..." -ForegroundColor Yellow
    python -m pip install pytest --user
}

# Add to PATH for current session
Write-Host "`nAdding Python Scripts to PATH for current session..." -ForegroundColor Yellow
$env:PATH += ";$pythonScriptsPath"
Write-Host "✅ PATH updated for current session" -ForegroundColor Green

# Verify pytest is now accessible
Write-Host "`nVerifying pytest installation..." -ForegroundColor Yellow
try {
    $version = pytest --version 2>&1
    Write-Host "✅ pytest is working: $version" -ForegroundColor Green
} catch {
    Write-Host "⚠️  pytest command still not recognized" -ForegroundColor Yellow
    Write-Host "Using python -m pytest instead..." -ForegroundColor Yellow
}

Write-Host "`n" + "=" * 60 -ForegroundColor Cyan
Write-Host "You can now run pytest commands in this session:" -ForegroundColor Green
Write-Host "  pytest tests/" -ForegroundColor White
Write-Host "  pytest tests/ -v" -ForegroundColor White
Write-Host "  pytest tests/ --cov=app_electrical" -ForegroundColor White
Write-Host "`nOr use python -m pytest (always works):" -ForegroundColor Green
Write-Host "  python -m pytest tests/" -ForegroundColor White
Write-Host "=" * 60 -ForegroundColor Cyan
