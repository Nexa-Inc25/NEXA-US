# 🚨 URGENT FIX NEEDED

## Two Issues to Fix:

### 1. IndentationError in pole_vision_detector.py

**Line 131 has bad indentation.** The fix script broke it.

**TO FIX:**
Open `pole_vision_detector.py` and find line 131. It should look like:
```python
            logger.info("Skipping training to save memory - use /vision/train-on-specs endpoint instead")
            # Don't train - just download dataset
```

**NOT like:**
```python
    data=f"{dataset.location}/data.yaml",  # ← WRONG INDENTATION
```

**CORRECT FIX:**
Around line 110-135, find the `download_roboflow_model` method and make sure it looks like this:

```python
def download_roboflow_model(self):
    """Download pre-trained utility pole model from Roboflow"""
    try:
        api_key = os.getenv('ROBOFLOW_API_KEY')
        if not api_key:
            logger.warning("ROBOFLOW_API_KEY not set")
            return
        
        from roboflow import Roboflow
        
        logger.info("loading Roboflow workspace...")
        rf = Roboflow(api_key=api_key)
        project = rf.workspace("unstructured").project("utility-pole-detection-birhf")
        
        logger.info("loading Roboflow project...")
        dataset = project.version(1).download("yolov8", location="/data/roboflow_dataset")
        
        logger.info("Skipping training to save memory - use /vision/train-on-specs endpoint instead")
        # Training disabled - uses >2GB RAM on Render
        # self.model.train(
        #     data=f"{dataset.location}/data.yaml",
        #     epochs=10,
        #     batch=16,
        #     device='cpu',
        #     project='/data',
        #     name='roboflow_pole'
        # )
        
    except Exception as e:
        logger.error(f"Error loading YOLO model: {e}")
```

### 2. PyTorch 2.6 Still Being Used

**Check requirements_oct2025.txt** - make sure line 9 says:
```
torch==2.5.1  # Pinned to avoid weights_only issue with YOLOv8
```

**NOT:**
```
torch==2.8.0+cpu
```

## Quick Commands to Fix:

```bash
# 1. Fix the indentation manually in pole_vision_detector.py

# 2. Verify requirements
cat requirements_oct2025.txt | grep torch

# 3. Commit and deploy
git add pole_vision_detector.py requirements_oct2025.txt
git commit -m "Fix indentation error and ensure torch 2.5.1"
git push origin main
```
