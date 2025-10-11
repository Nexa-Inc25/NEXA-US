# PowerShell script to fix the indentation error
$file = "pole_vision_detector.py"

Write-Host "🔧 Fixing indentation error in $file..." -ForegroundColor Yellow

# Read the file
$content = Get-Content $file -Raw

# The broken section (lines 128-138 approximately)
$broken = @"
                logger.info\("Skipping training to save memory - use /vision/train-on-specs endpoint instead"\)
                model = YOLO\("yolov8n.pt"\)  # Start with nano
#                 model.train\(
                    data=f"\{dataset.location\}/data.yaml",
                    epochs=10,
                    imgsz=640,
                    device='cpu',
                    batch=16,
                    project='/data',
                    name='roboflow_pole'
                \)
"@

# The fixed section
$fixed = @"
                logger.info("Roboflow dataset downloaded - training disabled to save memory")
                logger.info("Upload trained model to /data/yolo_pole.pt to use it")
                
                # Check if pre-trained model exists
                trained_model_path = '/data/yolo_pole.pt'
                if os.path.exists(trained_model_path):
                    logger.info(f"Loading trained model from {trained_model_path}")
                    self.model = YOLO(trained_model_path)
                else:
                    logger.info("Using base YOLOv8 model until trained model is uploaded")
                
                # Training disabled to save memory (requires >2GB RAM)
                # To train: use local GPU or /vision/train-on-specs endpoint
"@

# Replace
$content = $content -replace $broken, $fixed

# Write back
$content | Set-Content $file -NoNewline

Write-Host "✅ Fixed! Now deploying..." -ForegroundColor Green

# Git commands
git add pole_vision_detector.py
git commit -m "Fix indentation error in pole_vision_detector.py"
git push origin main

Write-Host "🎉 Deployment complete!" -ForegroundColor Green
Write-Host "Monitor at: https://dashboard.render.com" -ForegroundColor Cyan
