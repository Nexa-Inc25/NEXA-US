# Create a safety backup before cleanup
# This creates a zip file of critical files before reorganization

Write-Host "Creating safety backup before cleanup..." -ForegroundColor Cyan

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupName = "nexa_backup_$timestamp"
$backupPath = "C:\Users\mikev\CascadeProjects\nexa-inc-mvp\$backupName"

# Create backup directory
New-Item -ItemType Directory -Path $backupPath -Force | Out-Null

Write-Host "Backing up critical files to: $backupPath" -ForegroundColor Green

# Copy main production files
$criticalFiles = @(
    "backend\pdf-service\app_oct2025_enhanced.py",
    "backend\pdf-service\middleware.py",
    "backend\pdf-service\utils.py",
    "backend\pdf-service\requirements_oct2025.txt",
    "backend\pdf-service\Dockerfile.oct2025",
    ".env",
    "README.md"
)

foreach ($file in $criticalFiles) {
    if (Test-Path $file) {
        $destPath = Join-Path $backupPath (Split-Path $file -Leaf)
        Copy-Item $file -Destination $destPath -Force
        Write-Host "  ✓ Backed up: $(Split-Path $file -Leaf)" -ForegroundColor Gray
    }
}

# Create list of all files that will be moved
$fileList = @"
NEXA Project File Backup Manifest
Created: $(Get-Date)
================================

This backup contains critical production files before project reorganization.
The full project has 400+ files that are being organized.

Files backed up:
- app_oct2025_enhanced.py (main production app)
- middleware.py (rate limiting, error handling)
- utils.py (utility functions)
- requirements_oct2025.txt (production dependencies)
- Dockerfile.oct2025 (production Docker config)
- .env (environment variables)
- README.md (project documentation)

To restore:
1. Copy these files back to their original locations
2. The main app is at: backend/pdf-service/app_oct2025_enhanced.py

Production URL: https://nexa-api-xpu3.onrender.com
"@

$fileList | Out-File -FilePath "$backupPath\BACKUP_MANIFEST.txt"

# Create a zip file
$zipPath = "$backupName.zip"
Write-Host "`nCreating zip archive: $zipPath" -ForegroundColor Cyan
Compress-Archive -Path $backupPath -DestinationPath $zipPath -Force

# Clean up temp folder
Remove-Item -Path $backupPath -Recurse -Force

Write-Host "`n✅ Backup complete!" -ForegroundColor Green
Write-Host "Backup saved as: $zipPath" -ForegroundColor Cyan
Write-Host "Size: $([math]::Round((Get-Item $zipPath).Length / 1MB, 2)) MB" -ForegroundColor Gray
Write-Host "`nYou can now safely run CLEANUP_NEXA_PROJECT.ps1" -ForegroundColor Yellow
