# Memory-optimized training settings for Render (2GB limit)
# Use these settings in the /vision/train-on-specs endpoint

MEMORY_OPTIMIZED_TRAINING = {
    'epochs': 3,        # Reduced from 10
    'batch': 4,         # Reduced from 16
    'imgsz': 416,       # Reduced from 640
    'device': 'cpu',
    'cache': False,     # Don't cache images in RAM
    'workers': 0,       # Single threaded
    'amp': False,       # No mixed precision
    'patience': 10,     # Early stopping
    'save_period': 1,   # Save every epoch
    'exist_ok': True,   # Overwrite existing
    'project': '/data',
    'name': 'roboflow_pole_lite'
}

# Alternative: Train locally and upload the model
# 1. Train on your local machine with GPU
# 2. Upload the best.pt file to /data/roboflow_pole/weights/
# 3. The detector will automatically use it
