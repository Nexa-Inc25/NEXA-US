"""
Fixed version of pole_vision_detector.py
Copy this content to replace the broken file
"""

# Around line 120-140, the download_roboflow_model method should look like this:

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
        
        logger.info("Roboflow dataset downloaded - training disabled to save memory")
        logger.info("Use /vision/train-on-specs endpoint or train locally")
        
        # Training disabled - uses >2GB RAM on Render
        # Check if pre-trained model exists
        if os.path.exists('/data/yolo_pole.pt'):
            logger.info("Loading pre-trained model from /data/yolo_pole.pt")
            self.model = YOLO('/data/yolo_pole.pt')
        else:
            logger.info("Using base YOLOv8 model (upload trained model to /data/yolo_pole.pt)")
        
    except Exception as e:
        logger.error(f"Error with Roboflow: {e}")
