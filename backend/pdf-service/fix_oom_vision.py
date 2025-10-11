#!/usr/bin/env python3
"""
Fix for OOM issue - disable auto-training in pole_vision_detector.py
Run this to patch the file before committing
"""

import os
import re

def patch_pole_vision_detector():
    """Patch pole_vision_detector.py to disable auto-training"""
    
    file_path = 'pole_vision_detector.py'
    
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found")
        return False
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Find and replace the training code
    # Look for the train() call and comment it out
    pattern = r'(.*model\.train\([^)]*\))'
    
    if 'model.train(' in content:
        # Replace training with a comment
        new_content = re.sub(
            pattern,
            r'# \1  # DISABLED - Training uses >2GB RAM on Render',
            content
        )
        
        # Add a log message instead
        new_content = new_content.replace(
            'logger.info("Training model on Roboflow dataset...")',
            'logger.info("Skipping training to save memory - use /vision/train-on-specs endpoint instead")'
        )
        
        # Write the patched file
        with open(file_path, 'w') as f:
            f.write(new_content)
        
        print(f"✅ Patched {file_path} - training disabled")
        print("   Training can be done via /vision/train-on-specs endpoint")
        return True
    else:
        print(f"⚠️ No model.train() found in {file_path}")
        print("   File may already be patched")
        return False

def create_memory_optimized_training():
    """Create a memory-optimized training configuration"""
    
    config = """# Memory-optimized training settings for Render (2GB limit)
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
"""
    
    with open('training_config.py', 'w') as f:
        f.write(config)
    
    print("✅ Created training_config.py with memory-optimized settings")

if __name__ == "__main__":
    print("🔧 Fixing OOM issue in pole_vision_detector.py")
    print("-" * 50)
    
    # Patch the file
    success = patch_pole_vision_detector()
    
    # Create optimized config
    create_memory_optimized_training()
    
    print("-" * 50)
    if success:
        print("\n✅ Fix applied! Next steps:")
        print("1. Review the changes in pole_vision_detector.py")
        print("2. Commit: git add pole_vision_detector.py")
        print("3. Push: git push origin main")
        print("4. Wait for Render to rebuild (3-5 min)")
        print("\n💡 Training can still be done via:")
        print("   - /vision/train-on-specs endpoint (with reduced settings)")
        print("   - Train locally and upload model to /data")
    else:
        print("\n⚠️ Manual fix may be needed")
        print("Look for model.train() calls and comment them out")
