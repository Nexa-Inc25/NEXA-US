# Script to update imports in app_oct2025_enhanced.py after reorganization
# Run this AFTER running CLEANUP_NEXA_PROJECT.ps1

Write-Host "Updating imports in app_oct2025_enhanced.py..." -ForegroundColor Cyan

$appFile = "C:\Users\mikev\CascadeProjects\nexa-inc-mvp\backend\pdf-service\app_oct2025_enhanced.py"

if (-not (Test-Path $appFile)) {
    Write-Host "ERROR: app_oct2025_enhanced.py not found!" -ForegroundColor Red
    exit
}

# Read the file
$content = Get-Content $appFile -Raw

# Update imports to reference modules folder
$importMappings = @{
    # Core functionality
    "from enhanced_spec_analyzer import" = "from modules.enhanced_spec_analyzer import"
    "from pricing_integration import" = "from modules.pricing_integration import"
    "from pricing_endpoints import" = "from modules.pricing_endpoints import"
    "from pole_vision_detector import" = "from modules.pole_vision_detector import"
    "from vision_endpoints import" = "from modules.vision_endpoints import"
    # Workflow management
    "from job_workflow_api import" = "from modules.job_workflow_api import"
    "from field_management_api import" = "from modules.field_management_api import"
    "from job_package_training_api import" = "from modules.job_package_training_api import"
    # As-built processing
    "from as_built_filler import" = "from modules.as_built_filler import"
    "from as_built_endpoints import" = "from modules.as_built_endpoints import"
    "from asbuilt_processor import" = "from modules.asbuilt_processor import"
    # Mega bundle and estimation
    "from mega_bundle_endpoints import" = "from modules.mega_bundle_endpoints import"
    "from mega_bundle_analyzer import" = "from modules.mega_bundle_analyzer import"
    "from spec_based_hour_estimator import" = "from modules.spec_based_hour_estimator import"
    # Spec learning
    "from spec_learning_endpoints import" = "from modules.spec_learning_endpoints import"
    "from enhanced_spec_learning import" = "from modules.enhanced_spec_learning import"
    # NER fine-tuning
    "from model_fine_tuner import" = "from modules.model_fine_tuner import"
    "from conduit_ner_fine_tuner import" = "from modules.conduit_ner_fine_tuner import"
    "from overhead_ner_fine_tuner import" = "from modules.overhead_ner_fine_tuner import"
    "from clearance_enhanced_fine_tuner import" = "from modules.clearance_enhanced_fine_tuner import"
    # Enhanced analyzers
    "from clearance_analyzer import" = "from modules.clearance_analyzer import"
    "from conduit_enhanced_analyzer import" = "from modules.conduit_enhanced_analyzer import"
    "from overhead_enhanced_analyzer import" = "from modules.overhead_enhanced_analyzer import"
    # Roboflow integration
    "from roboflow_dataset_integrator import" = "from modules.roboflow_dataset_integrator import"
}

foreach ($mapping in $importMappings.GetEnumerator()) {
    if ($content -match $mapping.Key) {
        $content = $content -replace $mapping.Key, $mapping.Value
        Write-Host "  Updated: $($mapping.Key)" -ForegroundColor Green
    }
}

# Save the updated file
$content | Set-Content $appFile -NoNewline
Write-Host "Import updates complete!" -ForegroundColor Green

# Also create __init__.py in modules folder
$initFile = "C:\Users\mikev\CascadeProjects\nexa-inc-mvp\backend\pdf-service\modules\__init__.py"
if (-not (Test-Path $initFile)) {
    "# NEXA Core Modules" | Set-Content $initFile
    Write-Host "Created modules/__init__.py" -ForegroundColor Green
}

Write-Host "`nIMPORTANT: Test the application to ensure all imports work correctly!" -ForegroundColor Yellow
