# PowerShell script to permanently add Python Scripts to PATH
# Run as Administrator for system-wide changes, or regular user for user-specific changes

param(
    [switch]$SystemWide = $false
)

Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "Permanent PATH Configuration for pytest" -ForegroundColor Yellow
Write-Host "=" * 60 -ForegroundColor Cyan

$pythonScriptsPath = "$env:APPDATA\Python\Python313\Scripts"

# Check if running as administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")

if ($SystemWide -and -not $isAdmin) {
    Write-Host "❌ System-wide changes require Administrator privileges" -ForegroundColor Red
    Write-Host "Please run PowerShell as Administrator and try again" -ForegroundColor Yellow
    exit 1
}

# Determine target (User or Machine)
$target = if ($SystemWide) { "Machine" } else { "User" }

Write-Host "`nConfiguring PATH for: $target" -ForegroundColor Green
Write-Host "Adding directory: $pythonScriptsPath" -ForegroundColor White

# Get current PATH
$currentPath = [Environment]::GetEnvironmentVariable("Path", $target)

# Check if already in PATH
if ($currentPath -like "*$pythonScriptsPath*") {
    Write-Host "✅ Directory already in PATH!" -ForegroundColor Green
} else {
    # Add to PATH
    $newPath = $currentPath + ";$pythonScriptsPath"
    
    try {
        [Environment]::SetEnvironmentVariable("Path", $newPath, $target)
        Write-Host "✅ PATH updated successfully!" -ForegroundColor Green
        Write-Host "⚠️  Please restart PowerShell for changes to take effect" -ForegroundColor Yellow
    } catch {
        Write-Host "❌ Failed to update PATH: $_" -ForegroundColor Red
        exit 1
    }
}

Write-Host "`n" + "=" * 60 -ForegroundColor Cyan
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "1. Close this PowerShell window" -ForegroundColor White
Write-Host "2. Open a new PowerShell window" -ForegroundColor White
Write-Host "3. Verify with: pytest --version" -ForegroundColor White
Write-Host "4. Run tests: pytest tests/" -ForegroundColor White
Write-Host "=" * 60 -ForegroundColor Cyan
