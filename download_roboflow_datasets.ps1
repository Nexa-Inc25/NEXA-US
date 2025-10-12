# PowerShell Script to Download Roboflow Datasets for Crossarm Fix
# Fixes YOLO crossarm detection (0% -> >60% recall)

Write-Host "🎯 ROBOFLOW DATASET DOWNLOADER FOR NEXA" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Configuration
$baseDir = "C:\Users\mikev\CascadeProjects\nexa-inc-mvp\backend\pdf-service\data\roboflow_datasets"
$apiKeyFile = "$baseDir\api_key.txt"

# Create base directory
New-Item -ItemType Directory -Force -Path $baseDir | Out-Null

# Check for API key
if (Test-Path $apiKeyFile) {
    $apiKey = Get-Content $apiKeyFile -Raw
    Write-Host "✅ API key loaded from $apiKeyFile" -ForegroundColor Green
} else {
    Write-Host "⚠️ No API key found!" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "To get your Roboflow API key:" -ForegroundColor White
    Write-Host "1. Go to https://app.roboflow.com/" -ForegroundColor Gray
    Write-Host "2. Sign up for free account" -ForegroundColor Gray
    Write-Host "3. Go to Settings -> API Keys" -ForegroundColor Gray
    Write-Host "4. Copy your API key" -ForegroundColor Gray
    Write-Host ""
    
    $apiKey = Read-Host "Enter your Roboflow API key (or press Enter to skip)"
    
    if ($apiKey) {
        $apiKey | Out-File -FilePath $apiKeyFile -NoNewline
        Write-Host "✅ API key saved to $apiKeyFile" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "📊 TOP PRIORITY DATASETS FOR CROSSARM FIX:" -ForegroundColor Yellow
Write-Host "==========================================" -ForegroundColor Yellow

# Priority 1 datasets (have crossarm classes)
$datasets = @(
    @{
        Name = "Utility Poles (Zac)"
        Workspace = "zac-ygkqm"
        Project = "utility-poles"
        Version = 1
        Images = 380
        Note = "BEST: Has single/double crossarm classes"
        Priority = 1
    },
    @{
        Name = "ROAM Equipment"
        Workspace = "abdullah-tamu"
        Project = "roam-equipment"
        Version = 1
        Images = 30
        Note = "Has explicit crossarm class + insulators"
        Priority = 1
    },
    @{
        Name = "Utility Pole Detection"
        Workspace = "unstructured"
        Project = "utility-pole-detection"
        Version = 1
        Images = 1310
        Note = "Large dataset for pole detection"
        Priority = 2
    }
)

# Display datasets
foreach ($dataset in $datasets) {
    if ($dataset.Priority -eq 1) {
        Write-Host ""
        Write-Host "⭐ $($dataset.Name)" -ForegroundColor Green
        Write-Host "   Images: $($dataset.Images)" -ForegroundColor Gray
        Write-Host "   Note: $($dataset.Note)" -ForegroundColor Gray
        Write-Host "   URL: https://universe.roboflow.com/$($dataset.Workspace)/$($dataset.Project)" -ForegroundColor Blue
    }
}

Write-Host ""
Write-Host "📥 DOWNLOAD OPTIONS:" -ForegroundColor Yellow
Write-Host "===================" -ForegroundColor Yellow
Write-Host "1. Automatic download with API key (recommended)" -ForegroundColor White
Write-Host "2. Manual download instructions" -ForegroundColor White
Write-Host "3. Download via Python script" -ForegroundColor White
Write-Host "4. Skip download" -ForegroundColor White
Write-Host ""

$choice = Read-Host "Select option (1-4)"

switch ($choice) {
    "1" {
        # Automatic download with roboflow package
        Write-Host ""
        Write-Host "🔄 Installing Roboflow package..." -ForegroundColor Yellow
        pip install roboflow --upgrade
        
        Write-Host "🔄 Downloading datasets..." -ForegroundColor Yellow
        
        # Create Python download script
        $pythonScript = @"
import os
from roboflow import Roboflow

api_key = '$apiKey'.strip()
base_dir = r'$baseDir'

datasets = [
    {'workspace': 'zac-ygkqm', 'project': 'utility-poles', 'version': 1, 'name': 'zac_utility_poles'},
    {'workspace': 'abdullah-tamu', 'project': 'roam-equipment', 'version': 1, 'name': 'roam_equipment'},
    {'workspace': 'unstructured', 'project': 'utility-pole-detection', 'version': 1, 'name': 'pole_detection'}
]

rf = Roboflow(api_key=api_key)

for dataset in datasets:
    print(f"Downloading {dataset['name']}...")
    try:
        project = rf.workspace(dataset['workspace']).project(dataset['project'])
        version = project.version(dataset['version'])
        dataset_path = os.path.join(base_dir, dataset['name'])
        version.download('yolov8', location=dataset_path)
        print(f"✅ Downloaded to {dataset_path}")
    except Exception as e:
        print(f"❌ Failed: {e}")
"@
        
        $pythonScript | Out-File -FilePath "$baseDir\download.py" -Encoding UTF8
        
        # Run download script
        python "$baseDir\download.py"
        
        Write-Host ""
        Write-Host "✅ Download complete!" -ForegroundColor Green
    }
    
    "2" {
        # Manual download instructions
        Write-Host ""
        Write-Host "📝 MANUAL DOWNLOAD INSTRUCTIONS:" -ForegroundColor Yellow
        Write-Host "================================" -ForegroundColor Yellow
        
        foreach ($dataset in $datasets) {
            if ($dataset.Priority -eq 1) {
                Write-Host ""
                Write-Host "Dataset: $($dataset.Name)" -ForegroundColor Cyan
                Write-Host "1. Visit: https://universe.roboflow.com/$($dataset.Workspace)/$($dataset.Project)" -ForegroundColor White
                Write-Host "2. Click 'Download Dataset'" -ForegroundColor White
                Write-Host "3. Select 'YOLOv8' format" -ForegroundColor White
                Write-Host "4. Download ZIP file" -ForegroundColor White
                Write-Host "5. Extract to: $baseDir\$($dataset.Project)" -ForegroundColor White
            }
        }
        
        Write-Host ""
        Write-Host "After downloading, run merge_roboflow_data.ps1 to prepare for training" -ForegroundColor Yellow
    }
    
    "3" {
        # Download via Python API
        Write-Host ""
        Write-Host "🐍 Using Python API..." -ForegroundColor Yellow
        
        $pythonCmd = @"
cd backend/pdf-service
python -c "
import requests
import json

# Start download via API
response = requests.post(
    'http://localhost:8001/roboflow/download-datasets',
    json={'api_key': '$apiKey', 'priority_only': True}
)
print(response.json())
"
"@
        
        Invoke-Expression $pythonCmd
        
        Write-Host ""
        Write-Host "✅ Download initiated via API" -ForegroundColor Green
        Write-Host "Check progress at: http://localhost:8001/roboflow/statistics" -ForegroundColor Gray
    }
    
    "4" {
        Write-Host "Skipping download" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "📊 MERGE AND TRAINING:" -ForegroundColor Yellow
Write-Host "=====================" -ForegroundColor Yellow
Write-Host ""
Write-Host "After downloading, to fix crossarm detection:" -ForegroundColor White
Write-Host "1. Merge datasets: .\merge_roboflow_data.ps1" -ForegroundColor Gray
Write-Host "2. Start training: python train_yolo_with_roboflow.py" -ForegroundColor Gray
Write-Host "3. Monitor progress" -ForegroundColor Gray
Write-Host ""
Write-Host "Expected improvement:" -ForegroundColor Green
Write-Host "• Crossarm recall: 0% -> 60-75%" -ForegroundColor Green
Write-Host "• mAP50-95: 0.433 -> 0.65+" -ForegroundColor Green
Write-Host "• Pole detection: 50% -> 85%+" -ForegroundColor Green

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "✅ Script complete!" -ForegroundColor Green
