"""
Fix for PyTorch 2.6 weights_only compatibility issue with YOLOv8
Apply this fix to pole_vision_detector.py
"""

# The issue is in the YOLO model initialization
# PyTorch 2.6 changed the default weights_only from False to True

# OLD CODE (causing the error):
# model = YOLO(self.model_path)

# NEW CODE (with fix):
import torch
from ultralytics import YOLO

# Option 1: Set weights_only=False when loading (simplest fix)
def load_yolo_model(model_path):
    """Load YOLO model with PyTorch 2.6 compatibility"""
    try:
        # Try loading with the fix for PyTorch 2.6+
        import torch
        # Temporarily set default to False for YOLO model loading
        original_default = torch.serialization.get_default_load_endianness()
        
        # Add safe globals for ultralytics classes
        torch.serialization.add_safe_globals([
            'ultralytics.nn.tasks.DetectionModel',
            'ultralytics.nn.modules.Conv',
            'ultralytics.nn.modules.C2f',
            'ultralytics.nn.modules.SPPF',
            'ultralytics.nn.modules.Detect',
            'ultralytics.nn.modules.DFL'
        ])
        
        # Load the model
        model = YOLO(model_path)
        return model
        
    except Exception as e:
        # Fallback: Force weights_only=False
        import warnings
        warnings.filterwarnings('ignore', category=FutureWarning)
        
        # Monkey-patch torch.load temporarily
        original_load = torch.load
        def patched_load(*args, **kwargs):
            kwargs['weights_only'] = False
            return original_load(*args, **kwargs)
        
        torch.load = patched_load
        model = YOLO(model_path)
        torch.load = original_load  # Restore original
        
        return model

# Option 2: Pin PyTorch version in requirements_oct2025.txt
# Change from:
#   torch>=2.0.0
# To:
#   torch==2.5.1  # Last version before weights_only change

# Option 3: Update ultralytics to latest version that handles this
# In requirements_oct2025.txt:
#   ultralytics==8.3.0  # or latest

# COMPLETE FIX FOR pole_vision_detector.py
# Replace the __init__ method's model loading section:
"""
def __init__(self, model_path='/data/yolo_pole.pt'):
    self.data_path = '/data'
    self.model_path = model_path
    self.model = None
    
    # Create data directory if it doesn't exist
    os.makedirs(self.data_path, exist_ok=True)
    
    # Load or download model
    if not os.path.exists(self.model_path):
        self.download_model()
    
    # Load the model with PyTorch 2.6 fix
    try:
        # Add safe globals for ultralytics
        import torch
        torch.serialization.add_safe_globals([
            'ultralytics.nn.tasks.DetectionModel'
        ])
        self.model = YOLO(self.model_path)
    except Exception as e:
        # Fallback with weights_only=False
        logger.warning(f"Loading with weights_only=False due to: {e}")
        import torch
        original_load = torch.load
        torch.load = lambda *args, **kwargs: original_load(*args, **{**kwargs, 'weights_only': False})
        self.model = YOLO(self.model_path)
        torch.load = original_load
    
    logger.info(f"Model loaded from {self.model_path}")
"""
