# NEXA Project Cleanup Verification Script
# Shows what will be moved WITHOUT actually moving anything

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "NEXA PROJECT CLEANUP VERIFICATION" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

$basePath = "C:\Users\mikev\CascadeProjects\nexa-inc-mvp"
Set-Location $basePath

$totalFiles = 0
$rootDocs = 0
$rootDeployment = 0
$rootTests = 0
$rootScripts = 0
$pdfServiceArchive = 0
$pdfServiceModules = 0

Write-Host "ROOT DIRECTORY ANALYSIS:" -ForegroundColor Yellow
Write-Host "========================" -ForegroundColor Yellow

# Check docs to move
Write-Host "`n📄 Documentation files to move to /docs:" -ForegroundColor Green
$mdFiles = Get-ChildItem -Path . -Filter "*.md" | Where-Object {$_.Name -ne "README.md"}
foreach ($file in $mdFiles) {
    Write-Host "  - $($file.Name)" -ForegroundColor Gray
    $rootDocs++
}
Write-Host "  Total: $rootDocs files" -ForegroundColor Cyan

# Check deployment files
Write-Host "`n🚀 Deployment files to move to /deployment:" -ForegroundColor Green
$deploymentPatterns = @("*.yaml", "*.toml", "deploy_*.bat", "deploy_*.sh", "deploy_*.ps1", "Dockerfile.*")
foreach ($pattern in $deploymentPatterns) {
    $files = Get-ChildItem -Path . -Filter $pattern | Where-Object {$_.Name -ne "Dockerfile"}
    foreach ($file in $files) {
        Write-Host "  - $($file.Name)" -ForegroundColor Gray
        $rootDeployment++
    }
}
if (Test-Path "docker-compose.yml") {
    Write-Host "  - docker-compose.yml" -ForegroundColor Gray
    $rootDeployment++
}
Write-Host "  Total: $rootDeployment files" -ForegroundColor Cyan

# Check test files
Write-Host "`n🧪 Test files to move to /tests:" -ForegroundColor Green
$testFiles = Get-ChildItem -Path . -Filter "test_*.py"
$testScripts = Get-ChildItem -Path . -Filter "test_*.ps1"
foreach ($file in $testFiles) {
    Write-Host "  - $($file.Name)" -ForegroundColor Gray
    $rootTests++
}
foreach ($file in $testScripts) {
    Write-Host "  - $($file.Name)" -ForegroundColor Gray
    $rootTests++
}
Write-Host "  Total: $rootTests files" -ForegroundColor Cyan

# Check scripts
Write-Host "`n📝 Scripts to move to /scripts:" -ForegroundColor Green
$scriptPatterns = @("train_*.ps1", "upload_*.py", "create_*.py", "check_*.py", "check_*.js", 
                    "monitor_*.py", "fix_*.sh", "start-*.sh", "*.html")
foreach ($pattern in $scriptPatterns) {
    $files = Get-ChildItem -Path . -Filter $pattern
    foreach ($file in $files) {
        Write-Host "  - $($file.Name)" -ForegroundColor Gray
        $rootScripts++
    }
}
Write-Host "  Total: $rootScripts files" -ForegroundColor Cyan

# Check archive
Write-Host "`n📦 Files to archive:" -ForegroundColor Green
if (Test-Path "yolov8n.pt") {
    Write-Host "  - yolov8n.pt (6.5MB old YOLO model)" -ForegroundColor Gray
}

Write-Host "`n`nPDF-SERVICE DIRECTORY ANALYSIS:" -ForegroundColor Yellow
Write-Host "================================" -ForegroundColor Yellow

$pdfServicePath = "$basePath\backend\pdf-service"
Set-Location $pdfServicePath

# Old app versions to archive
Write-Host "`n📦 Old app versions to archive:" -ForegroundColor Green
$oldApps = @(
    "app.py", "app_api.py", "app_cable.py", "app_complete.py", 
    "app_electrical.py", "app_final.py", "app_langchain_xai.py",
    "app_latest.py", "app_multi_spec.py", "app_optimized_chunking.py",
    "app_production.py", "app_simple.py", "api_restored.py",
    "app_oct2025.py", "app_oct2025_enhanced_BACKUP.py"
)
foreach ($app in $oldApps) {
    if (Test-Path $app) {
        $size = (Get-Item $app).Length / 1KB
        Write-Host ("  - $app ({0:N1}KB)" -f $size) -ForegroundColor Gray
        $pdfServiceArchive++
    }
}
Write-Host "  Total: $pdfServiceArchive files" -ForegroundColor Cyan

# Core modules to move
Write-Host "`n⚙️ Core modules to organize in /modules:" -ForegroundColor Green
$coreModules = @(
    "enhanced_spec_analyzer.py", "pricing_integration.py", "pricing_endpoints.py",
    "pole_vision_detector.py", "vision_endpoints.py", "job_workflow_api.py",
    "field_management_api.py", "job_package_training_api.py",
    "as_built_filler.py", "as_built_endpoints.py", "asbuilt_processor.py",
    "mega_bundle_endpoints.py", "mega_bundle_analyzer.py",
    "spec_based_hour_estimator.py", "spec_learning_endpoints.py",
    "enhanced_spec_learning.py", "model_fine_tuner.py",
    "conduit_ner_fine_tuner.py", "overhead_ner_fine_tuner.py",
    "clearance_enhanced_fine_tuner.py", "clearance_analyzer.py",
    "conduit_enhanced_analyzer.py", "overhead_enhanced_analyzer.py",
    "roboflow_dataset_integrator.py"
)
foreach ($module in $coreModules) {
    if (Test-Path $module) {
        $size = (Get-Item $module).Length / 1KB
        Write-Host ("  - $module ({0:N1}KB)" -f $size) -ForegroundColor Gray
        $pdfServiceModules++
    }
}
Write-Host "  Total: $pdfServiceModules modules" -ForegroundColor Cyan

# Count other files
$pdfDocs = (Get-ChildItem -Path . -Filter "*.md" | Where-Object {$_.Name -ne "README.md"}).Count
$pdfTests = (Get-ChildItem -Path . -Filter "test_*.py").Count
$reqFiles = (Get-ChildItem -Path . -Filter "requirements_*.txt" | Where-Object {
    $_.Name -ne "requirements_oct2025.txt" -and $_.Name -ne "requirements-test.txt"
}).Count
$dockerFiles = (Get-ChildItem -Path . -Filter "Dockerfile.*" | Where-Object {
    $_.Name -ne "Dockerfile.oct2025" -and $_.Name -ne "Dockerfile"
}).Count

Write-Host "`n📄 PDF-Service documentation: $pdfDocs files" -ForegroundColor Green
Write-Host "🧪 PDF-Service test files: $pdfTests files" -ForegroundColor Green
Write-Host "📋 Duplicate requirements files: $reqFiles files" -ForegroundColor Green
Write-Host "🐳 Old Dockerfiles: $dockerFiles files" -ForegroundColor Green

$totalFiles = $rootDocs + $rootDeployment + $rootTests + $rootScripts + 
              $pdfServiceArchive + $pdfServiceModules + $pdfDocs + $pdfTests + $reqFiles + $dockerFiles

Write-Host "`n=====================================" -ForegroundColor Cyan
Write-Host "CLEANUP SUMMARY" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "📊 Total files to organize: $totalFiles" -ForegroundColor Yellow
Write-Host ""
Write-Host "Files that will REMAIN in place:" -ForegroundColor Green
Write-Host "  ✅ app_oct2025_enhanced.py (main production app)" -ForegroundColor Cyan
Write-Host "  ✅ middleware.py" -ForegroundColor Cyan
Write-Host "  ✅ utils.py" -ForegroundColor Cyan
Write-Host "  ✅ requirements_oct2025.txt" -ForegroundColor Cyan
Write-Host "  ✅ Dockerfile.oct2025" -ForegroundColor Cyan
Write-Host "  ✅ README.md files" -ForegroundColor Cyan
Write-Host ""
Write-Host "⚠️ IMPORTANT: After cleanup, you'll need to:" -ForegroundColor Yellow
Write-Host "  1. Run UPDATE_IMPORTS_AFTER_CLEANUP.ps1 to fix module imports"
Write-Host "  2. Test the application to ensure everything works"
Write-Host "  3. Commit changes to git"
Write-Host ""
Write-Host "Run CLEANUP_NEXA_PROJECT.ps1 to execute the cleanup" -ForegroundColor Green
