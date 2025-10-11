"""
Fix for Render OOM - Disable auto-training on startup
Replace the download_roboflow_model method in pole_vision_detector.py
"""

def download_roboflow_model(self, api_key):
    """Download Roboflow dataset WITHOUT auto-training to save memory"""
    try:
        from roboflow import Roboflow
        
        logger.info("Downloading Roboflow dataset...")
        rf = Roboflow(api_key=api_key)
        project = rf.workspace("unstructured").project("utility-pole-detection-birhf")
        dataset = project.version(1).download("yolov8", location="/data/roboflow_dataset")
        
        logger.info(f"Roboflow dataset downloaded (920 train, 375 val images)")
        
        # Check if pre-trained model exists
        trained_model_path = '/data/roboflow_pole/weights/best.pt'
        if os.path.exists(trained_model_path):
            self.model = YOLO(trained_model_path)
            logger.info("Loaded pre-trained Roboflow model from /data")
        else:
            # DON'T TRAIN - Just use base model
            logger.info("Using base YOLOv8 model (training disabled - use /vision/train-on-specs endpoint)")
            # Training would use >2GB RAM and crash on Render
            # Users should train locally or use the training endpoint with smaller batch size
            
    except Exception as e:
        logger.error(f"Error with Roboflow: {e}")
        logger.info("Using base YOLOv8 model")

# Also modify the train_on_specs endpoint to use smaller batch size:
def train_on_spec_images(spec_images: List[UploadFile] = File(...)):
    """Train with reduced memory usage"""
    try:
        detector = get_detector()
        
        # Train with memory-optimized settings
        model = YOLO(detector.model_path)
        results = model.train(
            data="/data/roboflow_dataset/data.yaml",
            epochs=3,  # Reduced from 10
            batch=4,   # Reduced from 16
            imgsz=416, # Reduced from 640
            device='cpu',
            cache=False,  # Don't cache images in RAM
            workers=0,    # Single threaded
            amp=False     # No mixed precision
        )
        
        return {"status": "training_complete", "metrics": results}
        
    except Exception as e:
        return {"error": f"Training failed (likely OOM): {str(e)}"}
