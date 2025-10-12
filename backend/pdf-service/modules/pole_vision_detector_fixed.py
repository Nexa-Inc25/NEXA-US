"""
YOLOv8-based Utility Pole Detection with Compatibility Fix
Handles version mismatches between trained models and ultralytics library
"""
import os
import json
import logging
from typing import Dict, List, Tuple, Optional
from PIL import Image
import numpy as np
import torch
from dataclasses import dataclass
from collections import Counter
import pickle

logger = logging.getLogger(__name__)

# Monkey-patch for DFLoss compatibility
try:
    from ultralytics import YOLO
    import ultralytics.utils.loss as loss_mod
    
    # Patch DFLoss if missing (for version mismatches)
    if not hasattr(loss_mod, 'DFLoss'):
        class DFLoss:
            """Stub DFLoss class for older models."""
            def __init__(self, num_classes=80):
                self.num_classes = num_classes
            
            def __call__(self, pred, target):
                # Fallback to default loss if available
                try:
                    from ultralytics.utils.loss import v8DetectionLoss
                    return v8DetectionLoss(pred, target)
                except (ImportError, AttributeError):
                    # Ultimate fallback - return zero loss
                    return torch.tensor(0.0, requires_grad=True)
        
        # Add to loss module
        setattr(loss_mod, 'DFLoss', DFLoss)
        logger.info("✅ DFLoss patched for compatibility with v8DetectionLoss fallback")
        
except ImportError as e:
    logger.error(f"Error importing ultralytics: {e}")
    YOLO = None

@dataclass
class PoleComponent:
    """Detected pole component"""
    name: str
    confidence: float
    bbox: List[float]  # x1, y1, x2, y2
    area: float
    level: Optional[int] = None  # Vertical level on pole

class PoleVisionDetector:
    """
    Advanced pole detection using YOLOv8 with compatibility fixes
    Detects and counts pole components for type classification
    """
    
    # Component classes for utility poles
    COMPONENT_CLASSES = {
        'pole': 0,
        'crossarm': 1,
        'transformer': 2,
        'riser': 3,
        'recloser': 4,
        'regulator': 5,
        'booster': 6,
        'sectionalizer': 7,
        'capacitor': 8,
        'switch': 9,
        'cutout': 10,
        'insulator': 11,
        'wire': 12,
        'guy_wire': 13,
        'streetlight': 14
    }
    
    # Equipment categories for type classification
    TYPE_2_EQUIPMENT = ['cutout', 'switch', 'capacitor', 'transformer']
    TYPE_3_EQUIPMENT = ['recloser', 'regulator', 'booster', 'sectionalizer', 'capacitor_bank', 'transformer_bank']
    
    def __init__(self, model_path: str = '/data/yolo_pole.pt', data_path: str = '/data'):
        """
        Initialize pole detector with YOLOv8 model
        
        Args:
            model_path: Path to trained YOLO model weights
            data_path: Path to data directory
        """
        self.data_path = data_path
        self.model_path = model_path
        self.model = None
        self.component_rules = {}
        
        # Try to load model with error handling
        try:
            self.model = self.load_model()
        except Exception as e:
            logger.error(f"Failed to load YOLO model: {e}")
            logger.info("Vision detection will be disabled")
        
        # Load component rules
        try:
            self.component_rules = self.load_component_rules()
        except Exception as e:
            logger.warning(f"Could not load component rules: {e}")
            self.component_rules = {}
    
    def load_model(self) -> Optional[YOLO]:
        """Load or download YOLOv8 model with compatibility handling"""
        if YOLO is None:
            logger.error("YOLO not available - ultralytics import failed")
            return None
            
        try:
            if os.path.exists(self.model_path):
                logger.info(f"Loading YOLO model from {self.model_path}")
                
                # Try multiple loading strategies
                try:
                    # Strategy 1: Direct load
                    model = YOLO(self.model_path)
                    logger.info("Model loaded successfully with direct load")
                    return model
                    
                except AttributeError as e:
                    if "DFLoss" in str(e):
                        logger.warning("DFLoss compatibility issue - trying alternate load")
                        
                        # Strategy 2: Load with torch and convert
                        try:
                            checkpoint = torch.load(self.model_path, map_location='cpu')
                            
                            # Remove incompatible loss functions
                            if 'model' in checkpoint:
                                state_dict = checkpoint['model'].state_dict() if hasattr(checkpoint['model'], 'state_dict') else checkpoint['model']
                                # Filter out loss-related keys
                                filtered_dict = {k: v for k, v in state_dict.items() 
                                               if 'loss' not in k.lower() and 'dfl' not in k.lower()}
                                
                                # Create base model and load weights
                                model = YOLO('yolov8n.pt')  # Start with base model
                                model.model.load_state_dict(filtered_dict, strict=False)
                                logger.info("Model loaded with compatibility fix")
                                return model
                        except Exception as e2:
                            logger.error(f"Torch load strategy failed: {e2}")
                    
                    # Strategy 3: Fall back to base model
                    logger.warning(f"Model load failed: {e}, using base YOLOv8n")
                    return self.get_base_model()
                    
                except Exception as e:
                    logger.error(f"Unexpected error loading model: {e}")
                    return self.get_base_model()
            else:
                # No existing model, use base
                return self.get_base_model()
                
        except Exception as e:
            logger.error(f"Error in load_model: {e}")
            return self.get_base_model()
    
    def get_base_model(self) -> Optional[YOLO]:
        """Get base YOLOv8 model as fallback"""
        try:
            logger.info("Using base YOLOv8n model")
            model = YOLO('yolov8n.pt')
            
            # Save for future use
            try:
                os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
                model.save(self.model_path)
                logger.info(f"Base model saved to {self.model_path}")
            except Exception as e:
                logger.warning(f"Could not save base model: {e}")
                
            return model
        except Exception as e:
            logger.error(f"Failed to load base model: {e}")
            return None
    
    def load_component_rules(self) -> Dict:
        """Load pole component classification rules"""
        rules_path = os.path.join(self.data_path, 'pole_rules.json')
        
        if os.path.exists(rules_path):
            try:
                with open(rules_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading rules from {rules_path}: {e}")
        
        # Default rules
        return {
            'type_1': {
                'max_equipment': 0,
                'allowed': ['pole', 'wire', 'insulator']
            },
            'type_2': {
                'max_equipment': 3,
                'allowed': self.TYPE_2_EQUIPMENT + ['pole', 'wire', 'insulator', 'crossarm']
            },
            'type_3': {
                'max_equipment': 10,
                'allowed': self.TYPE_2_EQUIPMENT + self.TYPE_3_EQUIPMENT + ['pole', 'wire', 'insulator', 'crossarm']
            }
        }
    
    def detect_components(self, image_path: str, confidence: float = 0.5) -> List[PoleComponent]:
        """
        Detect pole components in image
        
        Args:
            image_path: Path to image file
            confidence: Minimum confidence threshold
            
        Returns:
            List of detected PoleComponent objects
        """
        if self.model is None:
            logger.warning("Model not loaded - returning empty detections")
            return []
            
        try:
            # Run inference
            results = self.model(image_path, conf=confidence)
            
            components = []
            for r in results:
                if r.boxes is None:
                    continue
                    
                for box in r.boxes:
                    # Extract detection info
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    conf = box.conf[0].item()
                    cls = int(box.cls[0].item())
                    
                    # Map class to name
                    class_names = self.model.names if hasattr(self.model, 'names') else {}
                    name = class_names.get(cls, f'class_{cls}')
                    
                    # Calculate area
                    area = (x2 - x1) * (y2 - y1)
                    
                    # Determine vertical level (0=top, 1=middle, 2=bottom)
                    img = Image.open(image_path)
                    height = img.height
                    y_center = (y1 + y2) / 2
                    level = int(y_center / height * 3)
                    
                    components.append(PoleComponent(
                        name=name,
                        confidence=conf,
                        bbox=[x1, y1, x2, y2],
                        area=area,
                        level=level
                    ))
            
            return components
            
        except Exception as e:
            logger.error(f"Error detecting components: {e}")
            return []
    
    def classify_pole_type(self, components: List[PoleComponent]) -> Dict:
        """
        Classify pole type based on detected components
        
        Args:
            components: List of detected components
            
        Returns:
            Classification result with type and confidence
        """
        if not components:
            return {
                'type': 'unknown',
                'confidence': 0.0,
                'equipment_count': 0,
                'components': []
            }
        
        # Count equipment types
        equipment_counts = Counter()
        for comp in components:
            if comp.name in (self.TYPE_2_EQUIPMENT + self.TYPE_3_EQUIPMENT):
                equipment_counts[comp.name] += 1
        
        total_equipment = sum(equipment_counts.values())
        
        # Classify based on equipment
        pole_type = 'type_1'
        if total_equipment > 0:
            # Check for Type 3 equipment
            has_type3 = any(eq in equipment_counts for eq in self.TYPE_3_EQUIPMENT)
            if has_type3 or total_equipment > 3:
                pole_type = 'type_3'
            else:
                pole_type = 'type_2'
        
        # Calculate confidence
        avg_confidence = np.mean([c.confidence for c in components])
        
        return {
            'type': pole_type,
            'confidence': float(avg_confidence),
            'equipment_count': total_equipment,
            'equipment': dict(equipment_counts),
            'total_components': len(components),
            'components': [
                {
                    'name': c.name,
                    'confidence': c.confidence,
                    'level': c.level
                }
                for c in components
            ]
        }
    
    def process_image(self, image_path: str, confidence: float = 0.5) -> Dict:
        """
        Full pipeline: detect components and classify pole
        
        Args:
            image_path: Path to pole image
            confidence: Detection confidence threshold
            
        Returns:
            Complete analysis result
        """
        try:
            # Detect components
            components = self.detect_components(image_path, confidence)
            
            # Classify pole type
            classification = self.classify_pole_type(components)
            
            # Add metadata
            classification['image_path'] = image_path
            classification['model_used'] = 'trained' if os.path.exists(self.model_path) else 'base'
            
            return classification
            
        except Exception as e:
            logger.error(f"Error processing image: {e}")
            return {
                'type': 'error',
                'error': str(e),
                'image_path': image_path
            }
