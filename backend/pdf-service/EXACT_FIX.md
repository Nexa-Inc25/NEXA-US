# 🔧 EXACT FIX FOR pole_vision_detector.py

## Issue Found at Line 131:
```python
# Line 130:
#                 model.train(
# Line 131: (WRONG INDENTATION - NOT COMMENTED)
                    data=f"{dataset.location}/data.yaml",
```

## The Problem:
Line 130 has `#` comment, but line 131 does NOT have `#` and has wrong indentation.

---

## EXACT FIX:

**Find lines 128-138 which currently look like:**
```python
logger.info("Skipping training to save memory - use /vision/train-on-specs endpoint instead")
model = YOLO("yolov8n.pt")  # Start with nano
#                 model.train(
                    data=f"{dataset.location}/data.yaml",
                    epochs=10,
                    imgsz=640,
                    device='cpu',
                    batch=16,
                    project='/data',
                    name='roboflow_pole'
                )
```

**Replace with:**
```python
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
```

---

## Quick Command:

1. Open `pole_vision_detector.py`
2. Go to line 128
3. Delete lines 128-138
4. Paste the replacement code above
5. Save

Then deploy:
```bash
git add pole_vision_detector.py
git commit -m "Fix indentation error - comment out all training code"
git push origin main
```
