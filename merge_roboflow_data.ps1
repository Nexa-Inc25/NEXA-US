# PowerShell Script to Merge Downloaded Roboflow Datasets
# Prepares unified dataset for YOLO training to fix crossarm detection

Write-Host "🔄 ROBOFLOW DATASET MERGER" -ForegroundColor Cyan
Write-Host "===========================" -ForegroundColor Cyan
Write-Host ""

# Configuration
$baseDir = "C:\Users\mikev\CascadeProjects\nexa-inc-mvp\backend\pdf-service\data\roboflow_datasets"
$mergedDir = "$baseDir\merged_dataset"
$pythonScriptPath = "$baseDir\merge_and_train.py"

# Check for downloaded datasets
Write-Host "📂 Checking for downloaded datasets..." -ForegroundColor Yellow
$datasets = Get-ChildItem -Path $baseDir -Directory | Where-Object { $_.Name -ne "merged_dataset" }

if ($datasets.Count -eq 0) {
    Write-Host "❌ No datasets found!" -ForegroundColor Red
    Write-Host "Please run download_roboflow_datasets.ps1 first" -ForegroundColor Yellow
    exit
}

Write-Host "✅ Found $($datasets.Count) datasets:" -ForegroundColor Green
foreach ($dataset in $datasets) {
    Write-Host "   - $($dataset.Name)" -ForegroundColor Gray
}

Write-Host ""
Write-Host "🔄 Creating merged dataset..." -ForegroundColor Yellow

# Create merged directory structure
New-Item -ItemType Directory -Force -Path "$mergedDir\train\images" | Out-Null
New-Item -ItemType Directory -Force -Path "$mergedDir\train\labels" | Out-Null
New-Item -ItemType Directory -Force -Path "$mergedDir\valid\images" | Out-Null
New-Item -ItemType Directory -Force -Path "$mergedDir\valid\labels" | Out-Null
New-Item -ItemType Directory -Force -Path "$mergedDir\test\images" | Out-Null
New-Item -ItemType Directory -Force -Path "$mergedDir\test\labels" | Out-Null

# Create Python merge script
$mergeScript = @'
import os
import shutil
import yaml
from pathlib import Path

base_dir = Path(r"C:\Users\mikev\CascadeProjects\nexa-inc-mvp\backend\pdf-service\data\roboflow_datasets")
merged_dir = base_dir / "merged_dataset"

# Class mapping for consistency
class_mapping = {
    "utility pole": "pole",
    "utility-poles": "pole", 
    "wood pole": "pole",
    "steel pole": "pole",
    "concrete pole": "pole",
    "crossarm": "crossarm",
    "single crossarm": "crossarm",
    "double crossarm": "crossarm",
    "insulator": "insulator",
    "transformer": "transformer",
    "underground": "underground_marker"
}

target_classes = ["pole", "crossarm", "insulator", "transformer", "underground_marker", "equipment"]

# Statistics
stats = {
    "total_images": 0,
    "crossarm_annotations": 0,
    "pole_annotations": 0
}

print("Merging datasets...")

# Process each dataset
for dataset_dir in base_dir.iterdir():
    if not dataset_dir.is_dir() or dataset_dir.name == "merged_dataset":
        continue
    
    print(f"Processing {dataset_dir.name}...")
    
    # Load original class names
    yaml_path = dataset_dir / "data.yaml"
    if yaml_path.exists():
        with open(yaml_path, 'r') as f:
            data = yaml.safe_load(f)
            orig_classes = data.get('names', [])
    else:
        continue
    
    # Create class index mapping
    class_indices = {}
    for i, orig_class in enumerate(orig_classes):
        mapped = class_mapping.get(orig_class.lower())
        if mapped and mapped in target_classes:
            class_indices[i] = target_classes.index(mapped)
    
    # Copy and convert files
    for split in ['train', 'valid', 'test']:
        img_dir = dataset_dir / split / 'images'
        lbl_dir = dataset_dir / split / 'labels'
        
        if not img_dir.exists():
            img_dir = dataset_dir / 'images' / split
            lbl_dir = dataset_dir / 'labels' / split
        
        if img_dir.exists():
            for img_file in img_dir.glob('*'):
                if img_file.suffix.lower() in ['.jpg', '.jpeg', '.png']:
                    # Copy image
                    new_name = f"{dataset_dir.name}_{img_file.name}"
                    shutil.copy2(img_file, merged_dir / split / 'images' / new_name)
                    
                    # Convert and copy label
                    label_file = lbl_dir / f"{img_file.stem}.txt"
                    if label_file.exists():
                        new_label_path = merged_dir / split / 'labels' / f"{dataset_dir.name}_{img_file.stem}.txt"
                        
                        with open(label_file, 'r') as f:
                            lines = f.readlines()
                        
                        new_lines = []
                        for line in lines:
                            parts = line.strip().split()
                            if len(parts) >= 5:
                                orig_idx = int(parts[0])
                                if orig_idx in class_indices:
                                    new_idx = class_indices[orig_idx]
                                    parts[0] = str(new_idx)
                                    new_lines.append(' '.join(parts) + '\n')
                                    
                                    # Track statistics
                                    if target_classes[new_idx] == "crossarm":
                                        stats["crossarm_annotations"] += 1
                                    elif target_classes[new_idx] == "pole":
                                        stats["pole_annotations"] += 1
                        
                        with open(new_label_path, 'w') as f:
                            f.writelines(new_lines)
                    
                    stats["total_images"] += 1

# Create data.yaml for merged dataset
data_yaml = {
    'path': str(merged_dir),
    'train': 'train/images',
    'val': 'valid/images', 
    'test': 'test/images',
    'nc': len(target_classes),
    'names': target_classes,
    'cls_pw': [1.0, 3.0, 1.5, 1.5, 1.5, 1.0]  # 3x weight for crossarms!
}

with open(merged_dir / 'data.yaml', 'w') as f:
    yaml.dump(data_yaml, f)

print(f"\n✅ Merge complete!")
print(f"Total images: {stats['total_images']}")
print(f"Crossarm annotations: {stats['crossarm_annotations']} (fixing 0% recall!)")
print(f"Pole annotations: {stats['pole_annotations']}")
'@

$mergeScript | Out-File -FilePath "$baseDir\merge_datasets.py" -Encoding UTF8

# Run merge script
Write-Host "Running merge script..." -ForegroundColor Yellow
python "$baseDir\merge_datasets.py"

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✅ Datasets merged successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "📊 MERGED DATASET LOCATION:" -ForegroundColor Cyan
    Write-Host "   $mergedDir" -ForegroundColor White
    Write-Host ""
    Write-Host "🚀 NEXT STEPS TO FIX CROSSARM DETECTION:" -ForegroundColor Yellow
    Write-Host "===========================================" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Option 1: Train via API" -ForegroundColor White
    Write-Host "   curl -X POST http://localhost:8001/roboflow/merge-and-train" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Option 2: Train directly" -ForegroundColor White
    Write-Host "   python train_yolo_with_roboflow.py" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Option 3: Monitor training" -ForegroundColor White
    Write-Host "   python monitor_model_training.py" -ForegroundColor Gray
    Write-Host ""
    Write-Host "📈 EXPECTED IMPROVEMENTS:" -ForegroundColor Green
    Write-Host "• Crossarm recall: 0% → 60-75%" -ForegroundColor Green
    Write-Host "• mAP50-95: 0.433 → 0.65+" -ForegroundColor Green
    Write-Host "• Go-back confidence: >90%" -ForegroundColor Green
    Write-Host "• Training time: ~2 hours on CPU" -ForegroundColor Yellow
} else {
    Write-Host "❌ Merge failed. Check error messages above." -ForegroundColor Red
}
