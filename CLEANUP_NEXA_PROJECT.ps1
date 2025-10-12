# NEXA Project Cleanup Script
# Created: Oct 11, 2025
# Purpose: Organize 400+ scattered files into proper structure

Write-Host "==================================" -ForegroundColor Cyan
Write-Host "NEXA PROJECT CLEANUP SCRIPT" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""

# Safety check
$response = Read-Host "This will reorganize your NEXA project files. Continue? (y/n)"
if ($response -ne 'y') {
    Write-Host "Cleanup cancelled." -ForegroundColor Yellow
    exit
}

# Set base path
$basePath = "C:\Users\mikev\CascadeProjects\nexa-inc-mvp"
Set-Location $basePath

Write-Host "`n[1/8] Moving documentation files to /docs..." -ForegroundColor Green
# Move all .md files except README.md to docs folder
Get-ChildItem -Path . -Filter "*.md" | Where-Object {$_.Name -ne "README.md"} | ForEach-Object {
    Write-Host "  Moving: $($_.Name)" -ForegroundColor Gray
    Move-Item $_.FullName -Destination "docs\" -Force
}

Write-Host "`n[2/8] Moving deployment configs to /deployment..." -ForegroundColor Green
# Move deployment scripts
@("*.yaml", "*.toml", "deploy_*.bat", "deploy_*.sh", "deploy_*.ps1", "Dockerfile.*") | ForEach-Object {
    Get-ChildItem -Path . -Filter $_ | ForEach-Object {
        if ($_.Name -ne "Dockerfile") {
            Write-Host "  Moving: $($_.Name)" -ForegroundColor Gray
            Move-Item $_.FullName -Destination "deployment\" -Force
        }
    }
}
Move-Item "docker-compose.yml" -Destination "deployment\" -Force -ErrorAction SilentlyContinue

Write-Host "`n[3/8] Moving test files to /tests..." -ForegroundColor Green
# Move test files from root
Get-ChildItem -Path . -Filter "test_*.py" | ForEach-Object {
    Write-Host "  Moving: $($_.Name)" -ForegroundColor Gray
    Move-Item $_.FullName -Destination "tests\" -Force
}
Get-ChildItem -Path . -Filter "test_*.ps1" | ForEach-Object {
    Write-Host "  Moving: $($_.Name)" -ForegroundColor Gray
    Move-Item $_.FullName -Destination "tests\" -Force
}

Write-Host "`n[4/8] Moving utility scripts to /scripts..." -ForegroundColor Green
# Move utility scripts
@("train_*.ps1", "upload_*.py", "create_*.py", "check_*.py", "check_*.js", 
  "monitor_*.py", "fix_*.sh", "start-*.sh", "*.html") | ForEach-Object {
    Get-ChildItem -Path . -Filter $_ | ForEach-Object {
        Write-Host "  Moving: $($_.Name)" -ForegroundColor Gray
        Move-Item $_.FullName -Destination "scripts\" -Force
    }
}

Write-Host "`n[5/8] Archiving old YOLO model..." -ForegroundColor Green
# Archive old model
if (Test-Path "yolov8n.pt") {
    Write-Host "  Archiving: yolov8n.pt" -ForegroundColor Gray
    Move-Item "yolov8n.pt" -Destination "archive\" -Force
}

# Now handle backend/pdf-service
$pdfServicePath = "$basePath\backend\pdf-service"
Set-Location $pdfServicePath

Write-Host "`n[6/8] Creating modules folder in pdf-service..." -ForegroundColor Green
New-Item -ItemType Directory -Path "modules" -Force | Out-Null

Write-Host "`n[7/8] Archiving old app versions in pdf-service..." -ForegroundColor Green
# List of deprecated app versions to archive
$oldApps = @(
    "app.py", "app_api.py", "app_cable.py", "app_complete.py", 
    "app_electrical.py", "app_final.py", "app_langchain_xai.py",
    "app_latest.py", "app_multi_spec.py", "app_optimized_chunking.py",
    "app_production.py", "app_simple.py", "api_restored.py",
    "app_oct2025.py", "app_oct2025_enhanced_BACKUP.py"
)

foreach ($app in $oldApps) {
    if (Test-Path $app) {
        Write-Host "  Archiving: $app" -ForegroundColor Gray
        Move-Item $app -Destination "archive\" -Force
    }
}

Write-Host "`n[8/8] Moving core modules to /modules..." -ForegroundColor Green
# Core modules to move - ALL modules imported by app_oct2025_enhanced.py
$coreModules = @(
    # Core functionality
    "enhanced_spec_analyzer.py", "pricing_integration.py", "pricing_endpoints.py",
    "pole_vision_detector.py", "vision_endpoints.py", 
    # Workflow management
    "job_workflow_api.py", "field_management_api.py",
    "job_package_training_api.py",
    # As-built processing
    "as_built_filler.py", "as_built_endpoints.py", "asbuilt_processor.py",
    # Mega bundle and estimation
    "mega_bundle_endpoints.py", "mega_bundle_analyzer.py",
    "spec_based_hour_estimator.py",
    # Spec learning
    "spec_learning_endpoints.py", "enhanced_spec_learning.py",
    # NER fine-tuning modules
    "model_fine_tuner.py", "conduit_ner_fine_tuner.py", 
    "overhead_ner_fine_tuner.py", "clearance_enhanced_fine_tuner.py",
    # Enhanced analyzers
    "clearance_analyzer.py", "conduit_enhanced_analyzer.py", 
    "overhead_enhanced_analyzer.py",
    # Roboflow integration
    "roboflow_dataset_integrator.py"
)

foreach ($module in $coreModules) {
    if (Test-Path $module) {
        Write-Host "  Moving to modules: $module" -ForegroundColor Gray
        Move-Item $module -Destination "modules\" -Force
    }
}

# Move documentation in pdf-service
Write-Host "`nMoving pdf-service documentation..." -ForegroundColor Green
Get-ChildItem -Path . -Filter "*.md" | Where-Object {$_.Name -ne "README.md"} | ForEach-Object {
    Write-Host "  Moving: $($_.Name)" -ForegroundColor Gray
    Move-Item $_.FullName -Destination "docs\" -Force
}

# Move test files in pdf-service
Write-Host "`nMoving pdf-service test files..." -ForegroundColor Green
Get-ChildItem -Path . -Filter "test_*.py" | ForEach-Object {
    Write-Host "  Moving: $($_.Name)" -ForegroundColor Gray
    Move-Item $_.FullName -Destination "tests\" -Force
}

# Archive old requirements files
Write-Host "`nArchiving duplicate requirements files..." -ForegroundColor Green
Get-ChildItem -Path . -Filter "requirements_*.txt" | Where-Object {
    $_.Name -ne "requirements_oct2025.txt" -and $_.Name -ne "requirements-test.txt"
} | ForEach-Object {
    Write-Host "  Archiving: $($_.Name)" -ForegroundColor Gray
    Move-Item $_.FullName -Destination "archive\" -Force
}

# Archive old Dockerfiles
Write-Host "`nArchiving old Dockerfiles..." -ForegroundColor Green
Get-ChildItem -Path . -Filter "Dockerfile.*" | Where-Object {
    $_.Name -ne "Dockerfile.oct2025" -and $_.Name -ne "Dockerfile"
} | ForEach-Object {
    Write-Host "  Archiving: $($_.Name)" -ForegroundColor Gray
    Move-Item $_.FullName -Destination "archive\" -Force
}

Write-Host "`n==================================" -ForegroundColor Green
Write-Host "CLEANUP COMPLETE!" -ForegroundColor Green
Write-Host "==================================" -ForegroundColor Green
Write-Host ""
Write-Host "Summary of changes:" -ForegroundColor Yellow
Write-Host "- Documentation moved to /docs folders"
Write-Host "- Deployment configs moved to /deployment"
Write-Host "- Test files moved to /tests"
Write-Host "- Old app versions archived in /archive"
Write-Host "- Core modules organized in pdf-service/modules"
Write-Host ""
Write-Host "Main production files preserved:" -ForegroundColor Cyan
Write-Host "- app_oct2025_enhanced.py (main app)"
Write-Host "- middleware.py"
Write-Host "- utils.py"
Write-Host "- Dockerfile.oct2025"
Write-Host "- requirements_oct2025.txt"
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Update imports in app_oct2025_enhanced.py to reference modules/"
Write-Host "2. Test the application to ensure everything still works"
Write-Host "3. Commit these changes to git"
