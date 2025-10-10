"""
Computer Vision API Endpoints for Pole Detection
Endpoints for YOLOv8-based pole classification
"""
from fastapi import APIRouter, File, UploadFile, HTTPException, Form
from typing import List, Optional, Dict
import json
import base64
import io
from PIL import Image
from pole_vision_detector import PoleVisionDetector
import tempfile
import os
import logging

logger = logging.getLogger(__name__)

# Create router for vision endpoints
vision_router = APIRouter(prefix="/vision", tags=["Computer Vision"])

# Initialize detector (shared instance)
detector = None

def get_detector():
    """Get or create vision detector instance"""
    global detector
    if detector is None:
        detector = PoleVisionDetector()
    return detector

@vision_router.post("/detect-pole")
async def detect_pole_components(
    images: List[UploadFile] = File(..., description="Pole images to analyze"),
    return_annotated: bool = Form(False, description="Return annotated images")
):
    """
    Detect pole components using YOLOv8
    Returns component counts, pole type classification, and confidence
    """
    try:
        detector = get_detector()
        
        # Save uploaded images temporarily
        temp_paths = []
        annotated_images = []
        
        for img_file in images:
            if not img_file.filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                continue
            
            # Save to temp file
            content = await img_file.read()
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
            temp_file.write(content)
            temp_file.close()
            temp_paths.append(temp_file.name)
        
        if not temp_paths:
            raise HTTPException(400, "No valid images provided")
        
        # Analyze images
        result = detector.analyze_pole_images(temp_paths)
        
        # Generate annotated images if requested
        if return_annotated:
            for path in temp_paths:
                components = detector.detect_components(path)
                annotated_path = detector.save_detection_results(path, components)
                if annotated_path:
                    with open(annotated_path, 'rb') as f:
                        annotated_data = base64.b64encode(f.read()).decode('utf-8')
                        annotated_images.append({
                            'filename': os.path.basename(annotated_path),
                            'data': annotated_data
                        })
                    os.remove(annotated_path)
        
        # Clean up temp files
        for path in temp_paths:
            try:
                os.remove(path)
            except:
                pass
        
        # Format response
        response = {
            'pole_type': result['pole_type'],
            'confidence': round(result['confidence'] * 100, 1),
            'confidence_explanation': detector.get_confidence_explanation(result['confidence']),
            'reason': result['reason'],
            'levels': result['levels'],
            'components': result['components'],
            'equipment': result['equipment'],
            'detection_count': result['detections'],
            'classification': f"Type {result['pole_type']} - {get_type_name(result['pole_type'])}"
        }
        
        if return_annotated:
            response['annotated_images'] = annotated_images
        
        return response
        
    except Exception as e:
        logger.error(f"Pole detection error: {e}")
        raise HTTPException(500, f"Detection failed: {str(e)}")

@vision_router.post("/classify-pole-with-text")
async def classify_pole_with_text_context(
    images: List[UploadFile] = File(None, description="Pole images"),
    text_description: str = Form(..., description="Text description of pole"),
    pm_number: str = Form(..., description="PM Number"),
    notification_number: str = Form(..., description="Notification Number")
):
    """
    Classify pole using both vision and text analysis
    Combines computer vision with text understanding for higher accuracy
    """
    try:
        from pole_classifier import PoleClassifier
        
        # Initialize classifier with vision enabled
        classifier = PoleClassifier(use_vision=True)
        
        # Process images if provided
        temp_paths = []
        if images:
            for img_file in images:
                if not img_file.filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                    continue
                
                content = await img_file.read()
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
                temp_file.write(content)
                temp_file.close()
                temp_paths.append(temp_file.name)
        
        # Classify using both vision and text
        pole_type, confidence, reason = classifier.classify_pole(
            text_description, 
            temp_paths if temp_paths else None
        )
        
        # Get pricing adjustment
        adjusted_price, price_calc = classifier.calculate_adjusted_price(1000, pole_type)
        
        # Generate report
        report = classifier.generate_pole_report(
            pole_type, confidence,
            {'levels': 0, 'equipment': []},  # Would be extracted from features
            {'base_price': 1000}
        )
        
        # Clean up
        for path in temp_paths:
            try:
                os.remove(path)
            except:
                pass
        
        return {
            'job_id': f"PM: {pm_number} / Notification: {notification_number}",
            'pole_type': pole_type,
            'type_name': report['type_name'],
            'confidence': round(confidence * 100, 1),
            'reason': reason,
            'difficulty': report['difficulty'],
            'pricing_multiplier': report['pricing_multiplier'],
            'pricing_calculation': price_calc,
            'description': report['description'],
            'classification_method': 'Vision + Text' if temp_paths else 'Text Only'
        }
        
    except Exception as e:
        logger.error(f"Classification error: {e}")
        raise HTTPException(500, f"Classification failed: {str(e)}")

@vision_router.post("/train-on-specs")
async def train_on_spec_images(
    spec_images: List[UploadFile] = File(..., description="Spec example images"),
    pole_types: str = Form(..., description="JSON array of pole types [1,2,3,4,5] matching image order")
):
    """
    Fine-tune model on PG&E spec example images
    This should be done once after uploading spec PDFs
    """
    try:
        detector = get_detector()
        
        # Parse pole types
        types_list = json.loads(pole_types)
        
        if len(spec_images) != len(types_list):
            raise HTTPException(400, "Number of images must match number of type labels")
        
        # Save images temporarily
        temp_paths = []
        for img_file in spec_images:
            content = await img_file.read()
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
            temp_file.write(content)
            temp_file.close()
            temp_paths.append(temp_file.name)
        
        # Train model
        detector.train_on_spec_images(temp_paths, types_list)
        
        # Clean up
        for path in temp_paths:
            try:
                os.remove(path)
            except:
                pass
        
        return {
            'status': 'success',
            'message': f'Model fine-tuned on {len(spec_images)} spec images',
            'images_processed': len(spec_images)
        }
        
    except json.JSONDecodeError:
        raise HTTPException(400, "Invalid pole_types format")
    except Exception as e:
        logger.error(f"Training error: {e}")
        raise HTTPException(500, f"Training failed: {str(e)}")

@vision_router.get("/model-status")
async def get_model_status():
    """
    Check vision model status and capabilities
    """
    try:
        detector = get_detector()
        
        # Check if model exists
        model_exists = os.path.exists(detector.model_path)
        
        # Get component classes
        components = list(detector.COMPONENT_CLASSES.keys())
        
        return {
            'status': 'ready' if model_exists else 'downloading',
            'model_path': detector.model_path,
            'model_exists': model_exists,
            'supported_components': components,
            'type2_equipment': detector.TYPE_2_EQUIPMENT,
            'type3_equipment': detector.TYPE_3_EQUIPMENT,
            'confidence_thresholds': detector.component_rules['confidence_thresholds'],
            'capabilities': {
                'pole_detection': True,
                'component_counting': True,
                'level_estimation': True,
                'type_classification': True,
                'annotation': True,
                'fine_tuning': True
            }
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }

def get_type_name(pole_type: int) -> str:
    """Get descriptive name for pole type"""
    names = {
        1: "Easy (Service pole, no equipment)",
        2: "Moderate (2 levels or Type 2 equipment)",
        3: "Medium (3 levels or Type 3 equipment)",
        4: "Difficult (4 levels or complex equipment)",
        5: "Bid/NTE (Special complexity)"
    }
    return names.get(pole_type, f"Type {pole_type}")
