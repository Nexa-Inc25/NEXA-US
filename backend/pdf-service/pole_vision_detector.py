"""
YOLOv8-based Utility Pole Detection and Classification
Advanced computer vision for pole type identification
"""
import os
import json
import logging
from typing import Dict, List, Tuple, Optional
from PIL import Image
import numpy as np
import torch
from ultralytics import YOLO
from dataclasses import dataclass
from collections import Counter
import requests

logger = logging.getLogger(__name__)

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
    Advanced pole detection using YOLOv8
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
        self.model = self.load_model()
        self.component_rules = self.load_component_rules()
        
    def load_model(self) -> YOLO:
        """Load or download YOLOv8 model"""
        try:
            if os.path.exists(self.model_path):
                # Load existing model
                logger.info(f"Loading YOLO model from {self.model_path}")
                return YOLO(self.model_path)
            else:
                # Download pre-trained or use base model
                logger.info("Downloading YOLOv8 base model")
                
                # Option 1: Use YOLOv8n for fast CPU inference
                model = YOLO('yolov8n.pt')
                
                # Option 2: Download from Roboflow (if API key available)
                if os.getenv('ROBOFLOW_API_KEY'):
                    self.download_roboflow_model()
                    return YOLO(self.model_path)
                
                # Save base model
                model.save(self.model_path)
                return model
                
        except Exception as e:
            logger.error(f"Error loading YOLO model: {e}")
            # Fallback to basic YOLOv8
            return YOLO('yolov8n.pt')
    
    def download_roboflow_model(self):
        """Download pre-trained utility pole model from Roboflow"""
        try:
            api_key = os.getenv('ROBOFLOW_API_KEY')
            
            if not api_key:
                logger.warning("No ROBOFLOW_API_KEY found, using base model")
                return
            
            # Import Roboflow SDK
            try:
                from roboflow import Roboflow
            except ImportError:
                logger.warning("Roboflow SDK not installed, using base model")
                return
            
            # Download the specific utility-pole-detection-birhf model
            # 1310 images, mAP 85-90%, CC BY 4.0 license
            rf = Roboflow(api_key=api_key)
            project = rf.workspace("unstructured").project("utility-pole-detection-birhf")
            dataset = project.version(1).download("yolov8", location=f"{self.data_path}/roboflow_dataset")
            
            # Check for pre-trained model uploaded by user
            logger.info("Roboflow dataset downloaded successfully")
            logger.info("Training disabled to save memory (uses >2GB RAM on Render)")
            
            # Look for trained model at /data/yolo_pole.pt (upload from local training)
            trained_model_path = f"{self.data_path}/yolo_pole.pt"
            if os.path.exists(trained_model_path):
                logger.info(f"✅ Loading trained model from {trained_model_path}")
                self.model = YOLO(trained_model_path)
            else:
                # Check if Roboflow included pre-trained weights
                model_path = f"{dataset.location}/weights/best.pt"
                if os.path.exists(model_path):
                    import shutil
                    shutil.copy(model_path, self.model_path)
                    logger.info(f"✅ Downloaded Roboflow pre-trained model (1310 images)")
                    self.model = YOLO(self.model_path)
                else:
                    logger.info("ℹ️ No trained model found - using base YOLOv8")
                    logger.info("   Upload trained model to /data/yolo_pole.pt or use /vision/train-on-specs")
                
        except Exception as e:
            logger.error(f"Error downloading Roboflow model: {e}")
    
    def load_component_rules(self) -> Dict:
        """Load rules for component classification"""
        rules_path = f'{self.data_path}/component_rules.json'
        
        try:
            with open(rules_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            # Default rules
            return {
                'level_indicators': {
                    'crossarm': 1,  # Each crossarm adds a level
                    'transformer': 0.5,  # Transformer may be at existing level
                    'riser': 0,  # Riser doesn't add level
                    'wire': 0.2  # Multiple wires may indicate level
                },
                'difficulty_weights': {
                    'recloser': 2.0,
                    'regulator': 2.0,
                    'booster': 2.0,
                    'sectionalizer': 1.5,
                    'transformer_bank': 1.5,
                    'capacitor_bank': 1.5
                },
                'confidence_thresholds': {
                    'high': 0.8,
                    'medium': 0.6,
                    'low': 0.4
                }
            }
    
    def detect_components(self, image_path: str) -> List[PoleComponent]:
        """
        Detect pole components in image
        
        Args:
            image_path: Path to pole image
            
        Returns:
            List of detected components
        """
        try:
            # Run YOLO inference
            results = self.model(image_path)[0]
            
            components = []
            
            if results.boxes is not None:
                for box in results.boxes:
                    # Extract detection info
                    xyxy = box.xyxy[0].tolist()  # Bounding box
                    conf = box.conf[0].item()    # Confidence
                    cls = int(box.cls[0].item()) # Class ID
                    
                    # Get class name (map from model's classes)
                    class_name = self.model.names.get(cls, f'class_{cls}')
                    
                    # Map to our component classes
                    component_name = self.map_to_component(class_name)
                    
                    # Calculate area
                    area = (xyxy[2] - xyxy[0]) * (xyxy[3] - xyxy[1])
                    
                    # Determine vertical level based on y-coordinate
                    img_height = results.orig_shape[0]
                    y_center = (xyxy[1] + xyxy[3]) / 2
                    level = self.calculate_level(y_center, img_height)
                    
                    components.append(PoleComponent(
                        name=component_name,
                        confidence=conf,
                        bbox=xyxy,
                        area=area,
                        level=level
                    ))
            
            logger.info(f"Detected {len(components)} components in {image_path}")
            return components
            
        except Exception as e:
            logger.error(f"Error detecting components: {e}")
            return []
    
    def map_to_component(self, detected_class: str) -> str:
        """Map detected class to our component taxonomy"""
        # Mapping from common YOLO classes to our components
        mapping = {
            'pole': 'pole',
            'utility_pole': 'pole',
            'power_pole': 'pole',
            'cross_arm': 'crossarm',
            'crossarm': 'crossarm',
            'transformer': 'transformer',
            'power_transformer': 'transformer',
            'wire': 'wire',
            'power_line': 'wire',
            'insulator': 'insulator',
            'street_light': 'streetlight',
            'person': None,  # Ignore
            'car': None,     # Ignore
            'truck': None    # Ignore
        }
        
        # Try direct mapping
        component = mapping.get(detected_class.lower())
        if component:
            return component
        
        # Check if class contains keywords
        keywords = ['pole', 'arm', 'transformer', 'wire', 'insulator', 'light']
        for keyword in keywords:
            if keyword in detected_class.lower():
                return keyword if keyword != 'arm' else 'crossarm'
        
        # Default to original if no mapping
        return detected_class.lower().replace(' ', '_')
    
    def calculate_level(self, y_center: float, img_height: float) -> int:
        """
        Calculate vertical level of component on pole
        Top of image = higher level
        """
        # Divide image into levels (top to bottom)
        level_height = img_height / 5  # Max 5 levels
        
        level = int((img_height - y_center) / level_height) + 1
        return min(max(level, 1), 5)  # Clamp between 1-5
    
    def analyze_pole_images(self, image_paths: List[str]) -> Dict:
        """
        Analyze multiple pole images for complete classification
        
        Args:
            image_paths: List of paths to pole images
            
        Returns:
            Analysis results with pole type classification
        """
        all_components = []
        
        # Detect components in each image
        for path in image_paths:
            if os.path.exists(path):
                components = self.detect_components(path)
                all_components.extend(components)
            else:
                logger.warning(f"Image not found: {path}")
        
        if not all_components:
            return {
                'pole_type': 3,  # Default to Type 3
                'confidence': 0.5,
                'reason': 'No components detected, defaulting to Type 3',
                'components': []
            }
        
        # Count components by type
        component_counts = Counter(c.name for c in all_components)
        
        # Count levels (based on crossarms and vertical distribution)
        levels = self.count_levels(all_components)
        
        # Identify equipment types
        has_type2_equipment = any(
            comp in component_counts 
            for comp in self.TYPE_2_EQUIPMENT
        )
        has_type3_equipment = any(
            comp in component_counts 
            for comp in self.TYPE_3_EQUIPMENT
        )
        
        # Check for special conditions
        has_riser = 'riser' in component_counts
        has_multiple_transformers = component_counts.get('transformer', 0) >= 2
        
        # Classify pole type based on PG&E rules
        pole_type, reason = self.classify_by_rules(
            levels, has_type2_equipment, has_type3_equipment,
            has_riser, has_multiple_transformers, component_counts
        )
        
        # Calculate average confidence
        avg_confidence = np.mean([c.confidence for c in all_components])
        
        # Adjust confidence based on detection quality
        if len(all_components) < 3:
            avg_confidence *= 0.8  # Lower confidence with few detections
        
        return {
            'pole_type': pole_type,
            'confidence': float(avg_confidence),
            'reason': reason,
            'levels': levels,
            'components': component_counts,
            'detections': len(all_components),
            'equipment': {
                'type2': has_type2_equipment,
                'type3': has_type3_equipment,
                'riser': has_riser,
                'multi_transformer': has_multiple_transformers
            }
        }
    
    def count_levels(self, components: List[PoleComponent]) -> int:
        """Count pole levels based on components"""
        # Method 1: Count unique crossarm levels
        crossarm_levels = set(
            c.level for c in components 
            if c.name == 'crossarm' and c.level
        )
        
        if crossarm_levels:
            return len(crossarm_levels) + 1  # +1 for base level
        
        # Method 2: Use vertical distribution of all components
        component_levels = set(c.level for c in components if c.level)
        
        if component_levels:
            return len(component_levels)
        
        # Method 3: Estimate from component count
        crossarms = sum(1 for c in components if c.name == 'crossarm')
        if crossarms > 0:
            return min(crossarms + 1, 5)
        
        # Default
        return 2  # Assume at least 2 levels if pole detected
    
    def classify_by_rules(self, levels: int, has_type2: bool, has_type3: bool,
                         has_riser: bool, has_multi_transformer: bool,
                         component_counts: Dict[str, int]) -> Tuple[int, str]:
        """
        Classify pole type based on PG&E rules
        
        Returns:
            Tuple of (pole_type, reason)
        """
        # Type 5: More than 4 levels or special complexity
        if levels > 4:
            return 5, f"More than 4 levels detected ({levels} levels)"
        
        # Check for complex equipment combinations
        complexity_score = sum(
            component_counts.get(comp, 0) * self.component_rules['difficulty_weights'].get(comp, 1.0)
            for comp in component_counts
        )
        
        if complexity_score > 10:
            return 5, f"High complexity equipment (score: {complexity_score:.1f})"
        
        # Type 4: 4 levels OR 3 levels with Type 2/3 equipment
        if levels == 4:
            return 4, f"4 levels detected"
        
        if levels == 3 and (has_type2 or has_type3):
            equip_type = "Type 3" if has_type3 else "Type 2"
            return 4, f"3 levels with {equip_type} equipment"
        
        # Type 3: 3 levels OR Type 3 equipment OR riser OR multiple transformers
        if levels == 3:
            return 3, f"3 levels detected"
        
        if has_type3:
            equipment = [e for e in self.TYPE_3_EQUIPMENT if e in component_counts]
            return 3, f"Type 3 equipment detected: {', '.join(equipment)}"
        
        if has_riser:
            return 3, "Primary riser detected"
        
        if has_multi_transformer:
            return 3, f"Transformer bank detected ({component_counts['transformer']} transformers)"
        
        # Type 2: 2 levels OR Type 2 equipment
        if levels == 2:
            return 2, f"2 levels detected"
        
        if has_type2:
            equipment = [e for e in self.TYPE_2_EQUIPMENT if e in component_counts]
            return 2, f"Type 2 equipment detected: {', '.join(equipment)}"
        
        # Type 1: Simple pole
        return 1, f"Simple pole with {levels} level(s), no special equipment"
    
    def train_on_spec_images(self, spec_image_paths: List[str], labels: List[int]):
        """
        Fine-tune model on PG&E spec example images
        
        Args:
            spec_image_paths: Paths to example images from spec PDF
            labels: Corresponding pole type labels (1-5)
        """
        try:
            # Prepare training data
            dataset_path = f'{self.data_path}/pole_training'
            os.makedirs(f'{dataset_path}/images', exist_ok=True)
            os.makedirs(f'{dataset_path}/labels', exist_ok=True)
            
            # Copy images and create YOLO format labels
            for i, (img_path, label) in enumerate(zip(spec_image_paths, labels)):
                # Copy image
                img = Image.open(img_path)
                img.save(f'{dataset_path}/images/spec_{i}.jpg')
                
                # Create pseudo-label (pole type as class)
                # In real scenario, would need bounding box annotations
                with open(f'{dataset_path}/labels/spec_{i}.txt', 'w') as f:
                    # YOLO format: class x_center y_center width height
                    f.write(f"{label-1} 0.5 0.5 0.8 0.8\n")  # Dummy bbox
            
            # Create dataset YAML
            dataset_yaml = {
                'path': dataset_path,
                'train': 'images',
                'val': 'images',  # Using same for simplicity
                'names': {
                    0: 'Type1_Easy',
                    1: 'Type2_Moderate',
                    2: 'Type3_Medium',
                    3: 'Type4_Difficult',
                    4: 'Type5_BidNTE'
                }
            }
            
            yaml_path = f'{dataset_path}/dataset.yaml'
            with open(yaml_path, 'w') as f:
                import yaml
                yaml.dump(dataset_yaml, f)
            
            # Fine-tune model
            self.model.train(
                data=yaml_path,
                epochs=10,  # Quick fine-tuning
                imgsz=640,
                batch=8,
                device='cpu',  # Use CPU for Render
                project=self.data_path,
                name='pole_finetuned'
            )
            
            # Update model path to fine-tuned version
            self.model_path = f'{self.data_path}/pole_finetuned/weights/best.pt'
            self.model = YOLO(self.model_path)
            
            logger.info("Model fine-tuned on spec images")
            
        except Exception as e:
            logger.error(f"Error training model: {e}")
    
    def get_confidence_explanation(self, confidence: float) -> str:
        """Get human-readable confidence explanation"""
        thresholds = self.component_rules['confidence_thresholds']
        
        if confidence >= thresholds['high']:
            return "High confidence - clear detection with multiple components"
        elif confidence >= thresholds['medium']:
            return "Medium confidence - good detection with some components"
        elif confidence >= thresholds['low']:
            return "Low confidence - limited detection, manual review recommended"
        else:
            return "Very low confidence - unclear image or detection issues"
    
    def save_detection_results(self, image_path: str, components: List[PoleComponent],
                              output_path: Optional[str] = None):
        """Save annotated image with detection boxes"""
        try:
            from PIL import ImageDraw, ImageFont
            
            # Open image
            img = Image.open(image_path)
            draw = ImageDraw.Draw(img)
            
            # Draw bounding boxes
            for comp in components:
                # Color based on component type
                colors = {
                    'pole': 'brown',
                    'crossarm': 'orange',
                    'transformer': 'red',
                    'riser': 'blue',
                    'wire': 'yellow'
                }
                color = colors.get(comp.name, 'green')
                
                # Draw box
                draw.rectangle(comp.bbox, outline=color, width=3)
                
                # Draw label
                label = f"{comp.name} ({comp.confidence:.2f})"
                draw.text((comp.bbox[0], comp.bbox[1]-20), label, fill=color)
            
            # Save annotated image
            if output_path is None:
                output_path = image_path.replace('.', '_annotated.')
            
            img.save(output_path)
            logger.info(f"Saved annotated image to {output_path}")
            
            return output_path
            
        except Exception as e:
            logger.error(f"Error saving detection results: {e}")
            return None
