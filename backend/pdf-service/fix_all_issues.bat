@echo off
echo ========================================
echo COMPREHENSIVE FIX FOR VISION DEPLOYMENT
echo ========================================
echo.

echo Step 1: Manual fix required for pole_vision_detector.py
echo.
echo PLEASE OPEN pole_vision_detector.py and find the download_roboflow_model method
echo.
echo Replace the entire method (around line 98-140) with this code:
echo.
echo def download_roboflow_model(self):
echo     """Download pre-trained utility pole model from Roboflow"""
echo     try:
echo         api_key = os.getenv('ROBOFLOW_API_KEY')
echo         if not api_key:
echo             logger.warning("ROBOFLOW_API_KEY not set")
echo             return
echo         
echo         from roboflow import Roboflow
echo         
echo         logger.info("loading Roboflow workspace...")
echo         rf = Roboflow(api_key=api_key)
echo         project = rf.workspace("unstructured").project("utility-pole-detection-birhf")
echo         
echo         logger.info("loading Roboflow project...")
echo         dataset = project.version(1).download("yolov8", location="/data/roboflow_dataset")
echo         
echo         logger.info("Roboflow dataset downloaded - training disabled to save memory")
echo         
echo         # Check if pre-trained model exists
echo         if os.path.exists('/data/yolo_pole.pt'):
echo             self.model = YOLO('/data/yolo_pole.pt')
echo         
echo     except Exception as e:
echo         logger.error(f"Error with Roboflow: {e}")
echo.
echo.
pause
echo.
echo Step 2: Deploying fixes...
git add pole_vision_detector.py requirements_oct2025.txt
git commit -m "Fix indentation error and ensure proper training disabled"
git push origin main

echo.
echo ========================================
echo DEPLOYMENT COMPLETE
echo ========================================
echo.
echo Monitor at: https://dashboard.render.com
echo Wait 3-5 minutes for rebuild
echo.
pause
