"""
Deployment Script for Roboflow Utility Pole Detection Integration
Run this to add vision detection to your main app
"""

import os
import sys

def integrate_vision_endpoints():
    """
    Add vision endpoints to main app
    """
    # Integration code to add to app_oct2025_enhanced.py
    integration_code = '''
# ===== ADD TO IMPORTS SECTION =====
try:
    from vision_endpoints import vision_router
    from pole_vision_detector import PoleVisionDetector
    VISION_ENABLED = True
    logger.info("Vision detection enabled with Roboflow model")
except ImportError as e:
    VISION_ENABLED = False
    logger.warning(f"Vision detection not available: {e}")
    vision_router = None

# ===== ADD TO ROUTERS SECTION (after app creation) =====
if VISION_ENABLED and vision_router:
    app.include_router(vision_router)
    logger.info("Vision endpoints registered at /vision/*")

# ===== ADD TO STARTUP EVENT =====
@app.on_event("startup")
async def startup_vision():
    """Pre-load Roboflow model on startup"""
    if VISION_ENABLED:
        try:
            # Check for Roboflow API key
            if not os.getenv('ROBOFLOW_API_KEY'):
                logger.warning("ROBOFLOW_API_KEY not set - vision will use base YOLOv8")
            else:
                logger.info(f"Roboflow API key found, will download utility-pole-detection-birhf model")
            
            # Pre-initialize detector to download model
            detector = PoleVisionDetector()
            logger.info("Vision model pre-loaded successfully")
            
            # Test model status
            if os.path.exists('/data/yolo_pole.pt'):
                logger.info("✅ Roboflow model ready at /data/yolo_pole.pt")
            else:
                logger.info("⏳ Model will download on first use")
                
        except Exception as e:
            logger.error(f"Could not pre-load vision model: {e}")
'''
    
    print("=" * 50)
    print("🚀 ROBOFLOW INTEGRATION CODE")
    print("=" * 50)
    print("\nAdd this code to your app_oct2025_enhanced.py:\n")
    print(integration_code)
    print("=" * 50)

def check_requirements():
    """
    Check if required packages are in requirements.txt
    """
    print("\n📦 CHECKING REQUIREMENTS...")
    
    required_packages = [
        "ultralytics==8.0.200",
        "opencv-python-headless==4.8.1.78", 
        "roboflow==1.1.9"
    ]
    
    try:
        with open("requirements_oct2025.txt", "r") as f:
            content = f.read()
            
        missing = []
        for pkg in required_packages:
            pkg_name = pkg.split("==")[0]
            if pkg_name not in content:
                missing.append(pkg)
        
        if missing:
            print(f"⚠️ Missing packages in requirements_oct2025.txt:")
            for pkg in missing:
                print(f"   - {pkg}")
            print("\nAdd these to requirements_oct2025.txt")
        else:
            print("✅ All required packages found in requirements")
            
    except FileNotFoundError:
        print("❌ requirements_oct2025.txt not found")

def generate_env_template():
    """
    Generate .env template for Roboflow
    """
    env_template = """
# Roboflow API Configuration
# Get your API key from: https://app.roboflow.com/settings/api-keys
ROBOFLOW_API_KEY=rf_xxxxxxxxxxxxxxxxxxxxxxxxxx

# Redis Configuration (existing)
REDIS_URL=redis://red-xxxxxxxxxxxxx:6379

# Optional: Custom model path
YOLO_MODEL_PATH=/data/yolo_pole.pt

# Optional: Detection thresholds
YOLO_CONF_THRESHOLD=0.25
YOLO_IOU_THRESHOLD=0.45
"""
    
    print("\n📝 ENVIRONMENT VARIABLES")
    print("=" * 50)
    print("Add these to your Render environment:\n")
    print(env_template)
    print("=" * 50)

def test_roboflow_connection():
    """
    Test Roboflow API key if available
    """
    print("\n🔍 TESTING ROBOFLOW CONNECTION...")
    
    api_key = os.getenv('ROBOFLOW_API_KEY')
    
    if not api_key:
        print("⚠️ ROBOFLOW_API_KEY not set")
        print("Set it with: export ROBOFLOW_API_KEY=your_key")
        return False
    
    try:
        from roboflow import Roboflow
        
        rf = Roboflow(api_key=api_key)
        
        # Try to access the specific model
        project = rf.workspace("unstructured").project("utility-pole-detection-birhf")
        
        print(f"✅ Connected to Roboflow successfully!")
        print(f"   Model: utility-pole-detection-birhf")
        print(f"   Dataset: 1310 images (920 train/375 val/15 test)")
        print(f"   Classes: pole (extensible)")
        
        return True
        
    except ImportError:
        print("❌ Roboflow SDK not installed")
        print("Install with: pip install roboflow")
        return False
        
    except Exception as e:
        print(f"❌ Roboflow connection failed: {e}")
        return False

def generate_test_script():
    """
    Generate test script for vision endpoints
    """
    test_script = '''#!/usr/bin/env python3
"""
Test Roboflow Vision Detection Endpoints
"""
import requests
import sys

BASE_URL = "https://nexa-doc-analyzer-oct2025.onrender.com"

def test_model_status():
    """Check if model is loaded"""
    r = requests.get(f"{BASE_URL}/vision/model-status")
    if r.status_code == 200:
        data = r.json()
        print(f"✅ Model Status: {data['status']}")
        print(f"   Model exists: {data.get('model_exists', False)}")
        print(f"   Components: {len(data.get('supported_components', []))}")
        return True
    else:
        print(f"❌ Model status failed: {r.status_code}")
        return False

def test_detection():
    """Test pole detection with synthetic image"""
    # Create simple test image
    from PIL import Image
    import io
    
    img = Image.new('RGB', (640, 640), color='white')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='JPEG')
    img_bytes.seek(0)
    
    files = {'images': ('test.jpg', img_bytes, 'image/jpeg')}
    r = requests.post(f"{BASE_URL}/vision/detect-pole", files=files)
    
    if r.status_code == 200:
        data = r.json()
        print(f"✅ Detection successful!")
        print(f"   Pole Type: {data.get('pole_type', 'N/A')}")
        print(f"   Confidence: {data.get('confidence', 0)}%")
        return True
    else:
        print(f"❌ Detection failed: {r.status_code}")
        return False

if __name__ == "__main__":
    print("Testing Roboflow Vision Detection...")
    print("-" * 40)
    
    if test_model_status():
        test_detection()
    else:
        print("Model not ready, skipping detection test")
'''
    
    with open("test_roboflow_endpoints.py", "w") as f:
        f.write(test_script)
    
    print("\n📄 TEST SCRIPT GENERATED")
    print("Run with: python test_roboflow_endpoints.py")

def main():
    """
    Main deployment helper
    """
    print("=" * 60)
    print("🚀 ROBOFLOW UTILITY POLE DETECTION DEPLOYMENT HELPER")
    print("=" * 60)
    print("\nModel: utility-pole-detection-birhf")
    print("Dataset: 1310 images, mAP 85-90%")
    print("License: CC BY 4.0")
    print("=" * 60)
    
    # Show integration code
    integrate_vision_endpoints()
    
    # Check requirements
    check_requirements()
    
    # Generate env template
    generate_env_template()
    
    # Test connection if possible
    test_roboflow_connection()
    
    # Generate test script
    generate_test_script()
    
    print("\n" + "=" * 60)
    print("📋 DEPLOYMENT CHECKLIST")
    print("=" * 60)
    print("""
1. [ ] Get Roboflow API key from https://app.roboflow.com
2. [ ] Add integration code to app_oct2025_enhanced.py
3. [ ] Add packages to requirements_oct2025.txt
4. [ ] Set ROBOFLOW_API_KEY in Render environment
5. [ ] Commit and push to main branch
6. [ ] Wait for Render deployment (5-7 min first time)
7. [ ] Test with: python test_roboflow_endpoints.py
8. [ ] Fine-tune on spec images (optional)
    """)
    
    print("=" * 60)
    print("✨ Ready to deploy Roboflow vision detection!")
    print("=" * 60)

if __name__ == "__main__":
    main()
