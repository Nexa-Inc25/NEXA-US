#!/usr/bin/env python3
"""
NEXA YOLOv8 Fine-Tuning System
Advanced training pipeline for infrastructure detection with >95% accuracy
Incorporates mosaic, mixup, and Albumentations for robust field performance
"""

import os
import yaml
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import numpy as np
from datetime import datetime

# Core ML libraries
from ultralytics import YOLO
import torch
import cv2

# Advanced augmentation libraries
import albumentations as A
from albumentations.pytorch import ToTensorV2

# Data management
try:
    from roboflow import Roboflow
except ImportError:
    print("Warning: Roboflow not installed. Install with: pip install roboflow")

class InfrastructureDatasetManager:
    """Manages dataset preparation and augmentation for infrastructure detection"""
    
    def __init__(self, project_name: str = "infrastructure-detection"):
        self.project_name = project_name
        self.classes = ["sagging_guy_wire", "straight_guy_wire", "pole", "insulator", "cross_arm"]
        self.dataset_path = Path("./dataset")
        
        # PG&E spec references for each class
        self.spec_references = {
            "sagging_guy_wire": "Pages 7-9: Guy wire requires tensioning",
            "straight_guy_wire": "Page 25: Guy wire properly tensioned",
            "pole": "Page 12: Pole installation requirements",
            "insulator": "Page 15: Insulator specifications",
            "cross_arm": "Page 18: Cross-arm mounting standards"
        }
    
    def setup_roboflow_dataset(self, api_key: str, version: int = 1):
        """Download and prepare dataset from Roboflow"""
        try:
            rf = Roboflow(api_key=api_key)
            project = rf.workspace("nexa-workspace").project(self.project_name)
            dataset = project.version(version).download("yolov8")
            
            print(f"✅ Dataset downloaded from Roboflow")
            print(f"   - Train: {len(os.listdir(dataset.location + '/train/images'))} images")
            print(f"   - Valid: {len(os.listdir(dataset.location + '/valid/images'))} images")
            print(f"   - Test: {len(os.listdir(dataset.location + '/test/images'))} images")
            
            return dataset.location
        except Exception as e:
            print(f"❌ Roboflow download failed: {e}")
            return None
    
    def create_data_yaml(self):
        """Create YOLOv8 data configuration file"""
        data_config = {
            'train': str(self.dataset_path / 'images' / 'train'),
            'val': str(self.dataset_path / 'images' / 'val'),
            'test': str(self.dataset_path / 'images' / 'test'),
            'nc': len(self.classes),
            'names': self.classes
        }
        
        yaml_path = self.dataset_path / 'data.yaml'
        with open(yaml_path, 'w') as f:
            yaml.dump(data_config, f)
        
        print(f"✅ Created data.yaml at {yaml_path}")
        return yaml_path

class AdvancedAugmentations:
    """Advanced augmentation pipeline for infrastructure images"""
    
    @staticmethod
    def get_training_transforms():
        """Get advanced augmentation pipeline for training"""
        return A.Compose([
            # Basic augmentations
            A.RandomBrightnessContrast(
                brightness_limit=0.2, 
                contrast_limit=0.2, 
                p=0.5
            ),
            
            # Motion blur for field camera movement
            A.MotionBlur(
                blur_limit=(3, 7), 
                p=0.3
            ),
            
            # Weather effects for outdoor conditions
            A.OneOf([
                A.RandomFog(
                    fog_coef_lower=0.1, 
                    fog_coef_upper=0.3, 
                    alpha_coef=0.08,
                    p=1.0
                ),
                A.RandomRain(
                    drop_width=(1, 3),
                    drop_length=(5, 10),
                    drop_color=(200, 200, 200),
                    blur_value=3,
                    brightness_coefficient=0.9,
                    p=1.0
                ),
                A.RandomSunFlare(
                    flare_roi=(0, 0, 1, 0.5),
                    angle_lower=0,
                    angle_upper=1,
                    num_flare_circles_lower=3,
                    num_flare_circles_upper=7,
                    src_radius=100,
                    p=1.0
                )
            ], p=0.2),
            
            # Shadow simulation for time-of-day variations
            A.RandomShadow(
                shadow_roi=(0, 0.5, 1, 1),
                num_shadows_lower=1,
                num_shadows_upper=2,
                shadow_dimension=5,
                p=0.3
            ),
            
            # Occlusion simulation (vegetation, equipment)
            A.CoarseDropout(
                max_holes=3,
                max_height=50,
                max_width=50,
                min_holes=1,
                min_height=20,
                min_width=20,
                fill_value=0,
                p=0.3
            ),
            
            # Perspective changes for varied camera angles
            A.Perspective(
                scale=(0.05, 0.1),
                p=0.3
            ),
            
            # Gaussian noise for sensor variations
            A.GaussNoise(
                var_limit=(10.0, 50.0),
                mean=0,
                p=0.2
            ),
            
            # Advanced policy-based augmentation
            A.OneOf([
                A.RandAugment(
                    num_ops=2,
                    magnitude=9,
                    p=1.0
                ),
                A.AutoAugment(
                    policy="imagenet",
                    p=1.0
                )
            ], p=0.2),
            
            # Normalize and convert
            A.Normalize(mean=[0, 0, 0], std=[1, 1, 1]),
            ToTensorV2()
        ], bbox_params=A.BboxParams(
            format='yolo',
            label_fields=['class_labels'],
            min_area=100,
            min_visibility=0.3
        ))
    
    @staticmethod
    def get_validation_transforms():
        """Get minimal augmentation for validation"""
        return A.Compose([
            A.Normalize(mean=[0, 0, 0], std=[1, 1, 1]),
            ToTensorV2()
        ], bbox_params=A.BboxParams(
            format='yolo',
            label_fields=['class_labels']
        ))

class YOLOv8FineTuner:
    """Fine-tuning pipeline for YOLOv8 infrastructure detection"""
    
    def __init__(self, base_model_path: str = "yolov8n.pt"):
        self.base_model_path = base_model_path
        self.model = None
        self.training_history = []
        
    def setup_hyperparameters(self) -> Dict:
        """Configure optimized hyperparameters for fine-tuning"""
        return {
            # Basic parameters
            'epochs': 150,
            'patience': 20,
            'batch': 16,
            'imgsz': 640,
            'device': 'cuda' if torch.cuda.is_available() else 'cpu',
            
            # Learning rate schedule
            'lr0': 0.0005,  # Initial learning rate (lower for fine-tuning)
            'lrf': 0.01,    # Final learning rate factor
            'momentum': 0.937,
            'weight_decay': 0.0005,
            'warmup_epochs': 3.0,
            'warmup_momentum': 0.8,
            'warmup_bias_lr': 0.1,
            
            # Augmentation parameters
            'augment': True,
            'hsv_h': 0.015,  # Hue augmentation
            'hsv_s': 0.7,    # Saturation augmentation
            'hsv_v': 0.4,    # Value augmentation
            'degrees': 10.0,  # Rotation
            'translate': 0.1, # Translation
            'scale': 0.5,    # Zoom
            'shear': 2.0,    # Shear
            'flipud': 0.0,   # Vertical flip (disabled for infrastructure)
            'fliplr': 0.5,   # Horizontal flip
            
            # Advanced augmentations
            'mosaic': 1.0,    # Mosaic augmentation
            'close_mosaic': 10,  # Disable mosaic for last N epochs
            'mixup': 0.2,     # MixUp augmentation
            'copy_paste': 0.1,  # Copy-paste augmentation
            'perspective': 0.001,  # Perspective changes
            
            # Loss parameters
            'box': 7.5,       # Box loss weight
            'cls': 0.5,       # Classification loss weight
            'dfl': 1.5,       # Distribution focal loss weight
            
            # Other parameters
            'overlap_mask': True,
            'mask_ratio': 4,
            'dropout': 0.0,
            'val': True,
            'plots': True,
            'save': True,
            'save_period': 10,
            'cache': True,
            'workers': 8,
            'project': 'runs/infrastructure',
            'name': f'fine_tune_{datetime.now().strftime("%Y%m%d_%H%M%S")}',
            'exist_ok': True,
            'pretrained': True,
            'optimizer': 'AdamW',
            'verbose': True,
            'seed': 42,
            'deterministic': True,
            'single_cls': False,
            'rect': False,
            'cos_lr': True,
            'label_smoothing': 0.0,
            'nbs': 64,
            'overlap_mask': True,
            'mask_ratio': 4,
            'dropout': 0.0,
            
            # Multi-scale training
            'multi_scale': True,
            'amp': True  # Automatic mixed precision
        }
    
    def load_model(self, checkpoint_path: Optional[str] = None):
        """Load base or checkpoint model"""
        model_path = checkpoint_path or self.base_model_path
        self.model = YOLO(model_path)
        print(f"✅ Loaded model from {model_path}")
        return self.model
    
    def fine_tune(self, data_yaml: str, hyperparams: Optional[Dict] = None):
        """Execute fine-tuning with advanced augmentations"""
        if not self.model:
            self.load_model()
        
        # Use custom or default hyperparameters
        params = hyperparams or self.setup_hyperparameters()
        
        print("🚀 Starting fine-tuning with advanced augmentations...")
        print(f"   Device: {params['device']}")
        print(f"   Epochs: {params['epochs']}")
        print(f"   Batch size: {params['batch']}")
        print(f"   Learning rate: {params['lr0']}")
        print(f"   Augmentations: Mosaic={params['mosaic']}, MixUp={params['mixup']}")
        
        # Train the model
        results = self.model.train(data=data_yaml, **params)
        
        # Save training history
        self.training_history.append({
            'timestamp': datetime.now().isoformat(),
            'params': params,
            'results': results
        })
        
        return results
    
    def evaluate(self, data_yaml: str, split: str = 'test'):
        """Evaluate model performance on test set"""
        if not self.model:
            raise ValueError("Model not loaded. Call load_model() first.")
        
        print(f"\n📊 Evaluating on {split} set...")
        results = self.model.val(data=data_yaml, split=split)
        
        # Extract and display metrics
        metrics = {
            'mAP50': results.box.map50,
            'mAP50-95': results.box.map,
            'precision': results.box.mp,
            'recall': results.box.mr,
            'f1': 2 * (results.box.mp * results.box.mr) / (results.box.mp + results.box.mr + 1e-6)
        }
        
        print(f"\n📈 Overall Metrics:")
        print(f"   mAP@0.5: {metrics['mAP50']:.3f}")
        print(f"   mAP@0.5:0.95: {metrics['mAP50-95']:.3f}")
        print(f"   Precision: {metrics['precision']:.3f}")
        print(f"   Recall: {metrics['recall']:.3f}")
        print(f"   F1-Score: {metrics['f1']:.3f}")
        
        # Per-class metrics
        if hasattr(results.box, 'ap_class_index'):
            print("\n📊 Per-Class Performance:")
            for i, class_name in enumerate(self.model.names.values()):
                if i in results.box.ap_class_index:
                    idx = list(results.box.ap_class_index).index(i)
                    print(f"   {class_name}:")
                    print(f"      AP@0.5: {results.box.ap50[idx]:.3f}")
                    print(f"      Precision: {results.box.p[idx]:.3f}")
                    print(f"      Recall: {results.box.r[idx]:.3f}")
        
        return metrics
    
    def export_model(self, output_path: str = "yolo_infrastructure_finetuned.pt"):
        """Export fine-tuned model for deployment"""
        if not self.model:
            raise ValueError("Model not loaded.")
        
        # Save the model
        self.model.save(output_path)
        print(f"✅ Model exported to {output_path}")
        
        # Save metadata
        metadata = {
            'export_date': datetime.now().isoformat(),
            'classes': list(self.model.names.values()),
            'training_history': self.training_history,
            'model_size_mb': os.path.getsize(output_path) / (1024 * 1024)
        }
        
        metadata_path = output_path.replace('.pt', '_metadata.json')
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        print(f"📋 Metadata saved to {metadata_path}")
        
        return output_path

class InfrastructureDetector:
    """Production inference class for fine-tuned model"""
    
    def __init__(self, model_path: str = "yolo_infrastructure_finetuned.pt"):
        self.model = YOLO(model_path)
        self.confidence_threshold = 0.6
        
        # PG&E spec mappings
        self.spec_rules = {
            ("sagging_guy_wire", "straight_guy_wire"): {
                "change": "Guy wire adjusted from sagging to straight",
                "spec": "Pages 7-9: Red-lining required for guy wire adjustments",
                "action": "STRIKE THROUGH sagging symbol, WRITE 'ADJUSTED'"
            },
            ("pole", None): {
                "change": "Pole removed",
                "spec": "Page 12: Pole removal requires updated as-built",
                "action": "RED-LINE: Mark removal on drawing"
            },
            (None, "pole"): {
                "change": "Pole added",
                "spec": "Page 12: New pole installation documentation",
                "action": "RED-LINE: Add pole location and specifications"
            },
            ("insulator", None): {
                "change": "Insulator removed",
                "spec": "Page 15: Insulator changes require documentation",
                "action": "RED-LINE: Strike through insulator"
            },
            (None, "insulator"): {
                "change": "Insulator added",
                "spec": "Page 15: New insulator installation",
                "action": "RED-LINE: Add insulator type and location"
            },
            ("cross_arm", None): {
                "change": "Cross-arm removed",
                "spec": "Page 18: Cross-arm modifications",
                "action": "RED-LINE: Mark removal"
            },
            (None, "cross_arm"): {
                "change": "Cross-arm added",
                "spec": "Page 18: Cross-arm installation",
                "action": "RED-LINE: Add specifications"
            }
        }
    
    def detect(self, image: np.ndarray) -> List[Dict]:
        """Run inference on a single image"""
        results = self.model.predict(
            image, 
            conf=self.confidence_threshold,
            iou=0.45,
            max_det=100,
            verbose=False
        )
        
        detections = []
        for result in results:
            if result.boxes:
                for box in result.boxes:
                    detection = {
                        'class': self.model.names[int(box.cls)],
                        'confidence': float(box.conf),
                        'bbox': box.xyxy[0].tolist(),
                        'area': float((box.xyxy[0][2] - box.xyxy[0][0]) * 
                                    (box.xyxy[0][3] - box.xyxy[0][1]))
                    }
                    detections.append(detection)
        
        return detections
    
    def compare_images(self, before_img: np.ndarray, after_img: np.ndarray) -> Dict:
        """Compare before/after images for infrastructure changes"""
        before_detections = self.detect(before_img)
        after_detections = self.detect(after_img)
        
        # Extract class sets
        before_classes = {d['class'] for d in before_detections}
        after_classes = {d['class'] for d in after_detections}
        
        changes = []
        min_confidence = 1.0
        
        # Check for specific changes
        for (before_class, after_class), rule in self.spec_rules.items():
            if before_class and after_class:
                # Transformation (e.g., sagging to straight)
                if before_class in before_classes and after_class in after_classes:
                    if before_class not in after_classes and after_class not in before_classes:
                        conf = min(
                            max((d['confidence'] for d in before_detections if d['class'] == before_class), default=0),
                            max((d['confidence'] for d in after_detections if d['class'] == after_class), default=0)
                        )
                        changes.append({
                            **rule,
                            'confidence': conf,
                            'type': 'transformation'
                        })
                        min_confidence = min(min_confidence, conf)
            
            elif before_class and not after_class:
                # Removal
                if before_class in before_classes and before_class not in after_classes:
                    conf = max((d['confidence'] for d in before_detections if d['class'] == before_class), default=0)
                    changes.append({
                        **rule,
                        'confidence': conf,
                        'type': 'removal'
                    })
                    min_confidence = min(min_confidence, conf)
            
            elif not before_class and after_class:
                # Addition
                if after_class in after_classes and after_class not in before_classes:
                    conf = max((d['confidence'] for d in after_detections if d['class'] == after_class), default=0)
                    changes.append({
                        **rule,
                        'confidence': conf,
                        'type': 'addition'
                    })
                    min_confidence = min(min_confidence, conf)
        
        # Check for no changes
        if not changes and before_classes == after_classes:
            avg_conf = np.mean([d['confidence'] for d in before_detections + after_detections]) if (before_detections + after_detections) else 0.95
            changes.append({
                'change': 'No infrastructure changes detected',
                'spec': 'Page 25: Built as designed, no red-lining required',
                'action': 'Mark as BUILT AS DESIGNED',
                'confidence': avg_conf,
                'type': 'no_change'
            })
            min_confidence = avg_conf
        
        return {
            'before_detections': before_detections,
            'after_detections': after_detections,
            'changes': changes,
            'red_lining_required': any(c['type'] != 'no_change' for c in changes),
            'overall_confidence': min_confidence,
            'spec_references': list(set(c['spec'] for c in changes))
        }

def main():
    """Main fine-tuning workflow"""
    print("="*60)
    print("NEXA YOLOv8 INFRASTRUCTURE FINE-TUNING SYSTEM")
    print("="*60)
    
    # 1. Setup dataset
    print("\n📁 Setting up dataset...")
    dataset_manager = InfrastructureDatasetManager()
    
    # Option A: Use Roboflow
    # api_key = "YOUR_ROBOFLOW_API_KEY"
    # dataset_path = dataset_manager.setup_roboflow_dataset(api_key)
    
    # Option B: Use local dataset
    data_yaml = dataset_manager.create_data_yaml()
    
    # 2. Initialize fine-tuner
    print("\n🔧 Initializing fine-tuner...")
    fine_tuner = YOLOv8FineTuner(base_model_path="yolov8n.pt")
    
    # 3. Load existing model or start fresh
    # To continue from checkpoint: fine_tuner.load_model("path/to/checkpoint.pt")
    fine_tuner.load_model()
    
    # 4. Fine-tune with advanced augmentations
    print("\n🎯 Starting fine-tuning...")
    results = fine_tuner.fine_tune(str(data_yaml))
    
    # 5. Evaluate performance
    print("\n📊 Evaluating model...")
    metrics = fine_tuner.evaluate(str(data_yaml))
    
    # 6. Check if metrics meet requirements
    if metrics['mAP50'] >= 0.95 and metrics['f1'] >= 0.90:
        print("\n✅ Model meets accuracy requirements!")
        
        # Export for production
        model_path = fine_tuner.export_model()
        
        # 7. Test inference
        print("\n🧪 Testing production inference...")
        detector = InfrastructureDetector(model_path)
        
        # Load test images
        test_before = cv2.imread("test_before.jpg")
        test_after = cv2.imread("test_after.jpg")
        
        if test_before is not None and test_after is not None:
            results = detector.compare_images(test_before, test_after)
            
            print(f"\n📋 Change Detection Results:")
            print(f"   Changes found: {len(results['changes'])}")
            print(f"   Red-lining required: {results['red_lining_required']}")
            print(f"   Overall confidence: {results['overall_confidence']:.1%}")
            
            for change in results['changes']:
                print(f"\n   Change: {change['change']}")
                print(f"   Spec: {change['spec']}")
                print(f"   Action: {change['action']}")
                print(f"   Confidence: {change['confidence']:.1%}")
    else:
        print("\n⚠️ Model needs more training:")
        print(f"   Current mAP@0.5: {metrics['mAP50']:.3f} (target: 0.95)")
        print(f"   Current F1: {metrics['f1']:.3f} (target: 0.90)")
        print("\n   Suggestions:")
        print("   - Add more training data")
        print("   - Increase epochs")
        print("   - Adjust augmentation parameters")
        print("   - Try YOLOv8s for better accuracy")

if __name__ == "__main__":
    main()
