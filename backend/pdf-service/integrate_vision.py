"""
Integration code to add YOLOv8 vision detection to app_oct2025_enhanced.py

INSTRUCTIONS:
1. Add the vision router to the main app
2. Update celery worker if needed
3. Deploy with ultralytics dependency
"""

# ============================================
# ADD TO app_oct2025_enhanced.py IMPORTS
# ============================================
"""
from vision_endpoints import vision_router
"""

# ============================================
# ADD AFTER INCLUDING ASBUILT ROUTER
# ============================================
"""
# In app_oct2025_enhanced.py, after:
# app.include_router(asbuilt_router)

# Add this line:
app.include_router(vision_router)
"""

# ============================================
# COMPLETE INTEGRATION EXAMPLE
# ============================================

def add_vision_to_main_app(app):
    """
    Add this to app_oct2025_enhanced.py after creating FastAPI app
    """
    from fastapi import FastAPI
    from vision_endpoints import vision_router
    from asbuilt_endpoints import asbuilt_router
    
    # Include routers
    app.include_router(asbuilt_router)  # Existing
    app.include_router(vision_router)   # New vision endpoints
    
    # Add startup event to pre-load model
    @app.on_event("startup")
    async def startup_event():
        """Pre-load vision model on startup"""
        try:
            from pole_vision_detector import PoleVisionDetector
            
            # Initialize detector to download/load model
            detector = PoleVisionDetector()
            logger.info("Vision model pre-loaded successfully")
            
        except Exception as e:
            logger.warning(f"Could not pre-load vision model: {e}")
            # Non-critical, will load on first request

# ============================================
# DOCKERFILE UPDATE (if needed)
# ============================================
"""
# Add to Dockerfile.render or Dockerfile.oct2025:

# Install system dependencies for OpenCV
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# The Python packages are already in requirements_oct2025.txt
"""

# ============================================
# ENVIRONMENT VARIABLES (optional)
# ============================================
"""
# Add to Render environment variables:

# For Roboflow pre-trained model (optional)
ROBOFLOW_API_KEY=your_api_key_here

# For custom model path (optional)
YOLO_MODEL_PATH=/data/custom_pole_model.pt

# For performance tuning (optional)
YOLO_CONF_THRESHOLD=0.25  # Confidence threshold
YOLO_IOU_THRESHOLD=0.45    # IoU threshold for NMS
"""

# ============================================
# DEPLOYMENT COMMANDS
# ============================================
"""
# After making changes:
git add .
git commit -m "Add YOLOv8 computer vision for advanced pole detection"
git push origin main

# Render will auto-deploy with ultralytics
# First deployment will be slower (~5-7 min) due to package size
# Subsequent deploys will be faster (3-5 min)

# Monitor deployment:
# https://dashboard.render.com/web/srv-xxx/events
"""

# ============================================
# TESTING COMMANDS
# ============================================
"""
# Test vision model status:
curl https://nexa-doc-analyzer-oct2025.onrender.com/vision/model-status

# Test pole detection with image:
curl -X POST https://nexa-doc-analyzer-oct2025.onrender.com/vision/detect-pole \
  -F "images=@test_pole.jpg" \
  -F "return_annotated=true"

# Test combined classification:
curl -X POST https://nexa-doc-analyzer-oct2025.onrender.com/vision/classify-pole-with-text \
  -F "images=@pole_photo.jpg" \
  -F "text_description=Three-level pole with transformer bank" \
  -F "pm_number=07D" \
  -F "notification_number=12345"

# Run full test suite:
python test_vision_detection.py
"""

# ============================================
# USAGE IN AS-BUILT PROCESSING
# ============================================
"""
# The vision detection is automatically used when photos are provided:

POST /asbuilt/fill-async
files: as-built.pdf
photos: [pole1.jpg, pole2.jpg]  # Vision detection triggered
pm_number: "07D"
notification_number: "12345"

# Response will include vision-based classification:
{
  "pole_type": 3,
  "pole_confidence": 92.5,
  "pole_reason": "Vision detection: 3 levels detected. Components: crossarm: 2, transformer: 1",
  ...
}
"""

# ============================================
# PERFORMANCE OPTIMIZATION
# ============================================
"""
# For faster inference on CPU:

1. Use YOLOv8n (nano) model - smallest and fastest
2. Reduce image size before inference:
   - Resize to 640x640 (YOLO default)
   - JPEG compression

3. Cache detection results in Redis:
   - Key: image hash
   - Value: detection results
   - TTL: 1 hour

4. Batch processing:
   - Process multiple images in single inference
   - YOLOv8 supports batch inference natively

5. Consider quantization (advanced):
   - Export to ONNX format
   - Apply INT8 quantization
   - 2-4x faster with minimal accuracy loss
"""

# ============================================
# MONITORING AND LOGGING
# ============================================
"""
# Add to your monitoring:

# Track vision metrics
- Detection time per image
- Component detection accuracy
- Pole type classification accuracy
- Model confidence distribution

# Log important events
- Model loading/downloading
- Detection failures
- Low confidence results (<60%)
- Fine-tuning events

# Alerts
- Model not loading
- Inference time >3s
- Memory usage >2GB
- Repeated failures
"""
