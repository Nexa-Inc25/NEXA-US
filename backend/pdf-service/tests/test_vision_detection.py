"""
Test Suite for YOLOv8-based Pole Vision Detection
Tests computer vision integration for pole classification
"""
import requests
import json
import base64
import os
from PIL import Image, ImageDraw
import numpy as np
import io

# Configuration
BASE_URL = "https://nexa-doc-analyzer-oct2025.onrender.com"
LOCAL_URL = "http://localhost:8000"
API_URL = BASE_URL  # Use production

def create_synthetic_pole_image(pole_type: int) -> bytes:
    """
    Create synthetic pole image for testing
    Simulates different pole types with drawn components
    """
    # Create blank image
    img = Image.new('RGB', (400, 600), color='lightblue')
    draw = ImageDraw.Draw(img)
    
    # Draw main pole
    pole_x = 200
    draw.rectangle([pole_x-10, 100, pole_x+10, 550], fill='brown')
    
    # Add components based on type
    if pole_type >= 1:
        # Primary level
        draw.line([pole_x-50, 150, pole_x+50, 150], fill='gray', width=5)
        draw.text((pole_x-30, 130), "Primary", fill='black')
    
    if pole_type >= 2:
        # Secondary level + transformer
        draw.line([pole_x-40, 250, pole_x+40, 250], fill='gray', width=5)
        draw.rectangle([pole_x+20, 240, pole_x+40, 270], fill='gray')
        draw.text((pole_x+25, 275), "XFMR", fill='white')
    
    if pole_type >= 3:
        # Buck arm + recloser
        draw.line([pole_x-45, 350, pole_x+45, 350], fill='gray', width=5)
        draw.rectangle([pole_x-40, 340, pole_x-20, 360], fill='darkgray')
        draw.text((pole_x-38, 365), "REC", fill='white')
    
    if pole_type >= 4:
        # Fourth level
        draw.line([pole_x-35, 450, pole_x+35, 450], fill='gray', width=5)
        draw.text((pole_x-30, 430), "Level 4", fill='black')
    
    if pole_type >= 5:
        # Extra complexity
        draw.line([pole_x-30, 500, pole_x+30, 500], fill='gray', width=5)
        draw.text((50, 50), "COMPLEX/DIFFICULT ACCESS", fill='red')
    
    # Add wires
    for y in [150, 250, 350]:
        draw.line([0, y, 400, y+10], fill='black', width=1)
    
    # Add label
    draw.text((10, 10), f"Type {pole_type} Pole (Synthetic)", fill='black')
    
    # Convert to bytes
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='JPEG')
    return img_bytes.getvalue()

def test_model_status():
    """Test if vision model is available"""
    print("=" * 50)
    print("🔍 Testing Vision Model Status")
    print("=" * 50)
    
    try:
        r = requests.get(f"{API_URL}/vision/model-status")
        
        if r.status_code == 200:
            data = r.json()
            print(f"✅ Model Status: {data['status']}")
            print(f"   Model Path: {data.get('model_path', 'N/A')}")
            print(f"   Components: {len(data.get('supported_components', []))}")
            
            # Display capabilities
            caps = data.get('capabilities', {})
            if caps:
                print("\n📊 Capabilities:")
                for cap, enabled in caps.items():
                    status = "✅" if enabled else "❌"
                    print(f"   {status} {cap.replace('_', ' ').title()}")
            
            return True
        else:
            print(f"❌ Status check failed: {r.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_pole_detection():
    """Test pole component detection"""
    print("\n" + "=" * 50)
    print("🎯 Testing Pole Component Detection")
    print("=" * 50)
    
    results = []
    
    for pole_type in range(1, 6):
        print(f"\n📍 Testing Type {pole_type} Pole")
        
        # Create synthetic image
        img_data = create_synthetic_pole_image(pole_type)
        
        # Submit for detection
        files = [('images', (f'pole_type_{pole_type}.jpg', img_data, 'image/jpeg'))]
        data = {'return_annotated': 'true'}
        
        try:
            r = requests.post(f"{API_URL}/vision/detect-pole", files=files, data=data)
            
            if r.status_code == 200:
                result = r.json()
                
                detected_type = result['pole_type']
                confidence = result['confidence']
                
                success = detected_type == pole_type
                status = "✅" if success else "❌"
                
                print(f"   {status} Expected: Type {pole_type}, Got: Type {detected_type}")
                print(f"   Confidence: {confidence:.1f}%")
                print(f"   Reason: {result['reason']}")
                print(f"   Levels: {result.get('levels', 'N/A')}")
                
                # Display detected components
                components = result.get('components', {})
                if components:
                    print(f"   Components: {dict(list(components.items())[:3])}")
                
                results.append(success)
                
                # Save annotated image if provided
                if 'annotated_images' in result and result['annotated_images']:
                    ann_img = result['annotated_images'][0]
                    img_data = base64.b64decode(ann_img['data'])
                    with open(f"annotated_pole_type_{pole_type}.jpg", 'wb') as f:
                        f.write(img_data)
                    print(f"   Saved annotated image")
                    
            else:
                print(f"   ❌ Detection failed: {r.status_code}")
                if r.text:
                    print(f"   Error: {r.text[:100]}")
                results.append(False)
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
            results.append(False)
    
    # Summary
    print(f"\n{'=' * 50}")
    print(f"Results: {sum(results)}/{len(results)} pole types detected correctly")
    accuracy = (sum(results)/len(results)*100) if results else 0
    print(f"Accuracy: {accuracy:.1f}%")
    
    return sum(results) == len(results)

def test_combined_classification():
    """Test vision + text classification"""
    print("\n" + "=" * 50)
    print("🔀 Testing Combined Vision + Text Classification")
    print("=" * 50)
    
    test_cases = [
        {
            'pole_type': 2,
            'text': "Two-level pole with single-phase transformer and cutouts",
            'pm': "TEST-VIS-002",
            'notification': "VIS-20002"
        },
        {
            'pole_type': 3,
            'text': "Main line configuration with buck arm, transformer bank, and recloser",
            'pm': "TEST-VIS-003",
            'notification': "VIS-30003"
        },
        {
            'pole_type': 4,
            'text': "Four-level configuration with multiple circuits and Type 3 equipment",
            'pm': "TEST-VIS-004",
            'notification': "VIS-40004"
        }
    ]
    
    results = []
    
    for test_case in test_cases:
        print(f"\n📊 Testing: {test_case['text'][:50]}...")
        
        # Create image
        img_data = create_synthetic_pole_image(test_case['pole_type'])
        
        # Submit for combined classification
        files = [('images', ('test_pole.jpg', img_data, 'image/jpeg'))]
        data = {
            'text_description': test_case['text'],
            'pm_number': test_case['pm'],
            'notification_number': test_case['notification']
        }
        
        try:
            r = requests.post(f"{API_URL}/vision/classify-pole-with-text", files=files, data=data)
            
            if r.status_code == 200:
                result = r.json()
                
                detected_type = result['pole_type']
                expected_type = test_case['pole_type']
                
                success = detected_type == expected_type
                status = "✅" if success else "❌"
                
                print(f"   {status} Expected: Type {expected_type}, Got: Type {detected_type}")
                print(f"   Confidence: {result['confidence']:.1f}%")
                print(f"   Method: {result['classification_method']}")
                print(f"   Difficulty: {result['difficulty']}")
                print(f"   Pricing: {result['pricing_calculation']}")
                
                results.append(success)
                
            else:
                print(f"   ❌ Classification failed: {r.status_code}")
                results.append(False)
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
            results.append(False)
    
    print(f"\n{'=' * 50}")
    print(f"Results: {sum(results)}/{len(results)} combined classifications correct")
    
    return sum(results) == len(results)

def test_performance():
    """Test detection performance metrics"""
    print("\n" + "=" * 50)
    print("⚡ Testing Detection Performance")
    print("=" * 50)
    
    import time
    
    # Create test image
    img_data = create_synthetic_pole_image(3)
    
    # Test single image processing time
    times = []
    
    for i in range(5):
        start = time.time()
        
        files = [('images', ('perf_test.jpg', img_data, 'image/jpeg'))]
        r = requests.post(f"{API_URL}/vision/detect-pole", files=files)
        
        elapsed = time.time() - start
        times.append(elapsed)
        
        print(f"   Run {i+1}: {elapsed:.2f}s")
    
    avg_time = np.mean(times)
    print(f"\n📊 Performance Metrics:")
    print(f"   Average Time: {avg_time:.2f}s")
    print(f"   Min Time: {min(times):.2f}s")
    print(f"   Max Time: {max(times):.2f}s")
    
    # Check if meets target
    target = 1.5  # Target <1.5s per photo
    if avg_time < target:
        print(f"   ✅ Meets target (<{target}s)")
        return True
    else:
        print(f"   ⚠️ Above target ({target}s)")
        return False

def test_batch_detection():
    """Test batch image processing"""
    print("\n" + "=" * 50)
    print("📦 Testing Batch Detection")
    print("=" * 50)
    
    # Create multiple images
    images = []
    for pole_type in [2, 3, 3, 4]:  # Multiple Type 3 to test consistency
        img_data = create_synthetic_pole_image(pole_type)
        images.append(('images', (f'batch_{pole_type}.jpg', img_data, 'image/jpeg')))
    
    try:
        r = requests.post(f"{API_URL}/vision/detect-pole", files=images)
        
        if r.status_code == 200:
            result = r.json()
            
            print(f"✅ Batch processed {len(images)} images")
            print(f"   Detected Type: {result['pole_type']}")
            print(f"   Overall Confidence: {result['confidence']:.1f}%")
            print(f"   Total Detections: {result.get('detection_count', 0)}")
            
            # Check if Type 3 dominated (as we had 2 Type 3s)
            if result['pole_type'] == 3:
                print("   ✅ Correctly identified dominant type (Type 3)")
                return True
            else:
                print("   ⚠️ Unexpected classification")
                return False
                
        else:
            print(f"❌ Batch processing failed: {r.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def run_all_tests():
    """Run complete vision detection test suite"""
    print("=" * 50)
    print("🚀 YOLOv8 Pole Vision Detection Test Suite")
    print("=" * 50)
    
    # Check API health first
    print("\n🔍 Checking API health...")
    try:
        r = requests.get(f"{API_URL}/health", timeout=5)
        if r.status_code == 200:
            print("✅ API is healthy")
        else:
            print("❌ API not responding properly")
            return
    except:
        print("❌ Cannot connect to API")
        print("💡 Try running locally with: uvicorn app_oct2025_enhanced:app --reload")
        return
    
    results = {}
    
    # Run tests
    print("\nRunning vision tests...")
    
    results['Model Status'] = test_model_status()
    results['Component Detection'] = test_pole_detection()
    results['Combined Classification'] = test_combined_classification()
    results['Performance'] = test_performance()
    results['Batch Processing'] = test_batch_detection()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 FINAL TEST RESULTS")
    print("=" * 50)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name:.<30} {status}")
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    
    print(f"\nOverall: {passed}/{total} test suites passed")
    
    if passed == total:
        print("🎉 All vision tests passed! YOLOv8 detection ready!")
        print("\n💡 Next Steps:")
        print("1. Upload real pole images for better accuracy")
        print("2. Fine-tune on PG&E spec examples")
        print("3. Deploy to production")
    else:
        print("⚠️ Some tests failed. Check model installation and configuration.")
        print("\n💡 Troubleshooting:")
        print("1. Ensure ultralytics is installed: pip install ultralytics")
        print("2. Check if YOLOv8 model downloaded: /data/yolo_pole.pt")
        print("3. Verify OpenCV installation: pip install opencv-python-headless")

if __name__ == "__main__":
    run_all_tests()
