#!/usr/bin/env python3
"""
NEXA Transfer Learning System for YOLOv8
Implements transfer learning with layer freezing for >95% mAP accuracy
"""

import os
import yaml
import json
from pathlib import Path
from typing import Dict, List, Optional
import numpy as np
from datetime import datetime
import torch
from ultralytics import YOLO
import albumentations as A
from albumentations.pytorch import ToTensorV2

class TransferLearningPipeline:
    """Transfer learning pipeline for infrastructure detection"""
    
    def __init__(self):
        # Configuration
        self.base_model = "yolov8n.pt"  # COCO pre-trained
        self.output_model = "yolo_infrastructure_transfer.pt"
        self.dataset_path = Path("./dataset")
        self.classes = ["sagging_guy_wire", "straight_guy_wire", "pole", "insulator", "cross_arm"]
        
        # Transfer learning settings
        self.freeze_layers = 10  # Freeze first N backbone layers
        self.epochs = 100
        self.batch_size = 16
        self.lr0 = 0.001  # Lower learning rate for fine-tuning
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        
        # Target metrics
        self.target_map50 = 0.95
        self.target_f1 = 0.90
        
        self.model = None
        self.best_metrics = {'map50': 0, 'f1': 0}
    
    def load_and_freeze_model(self):
        """Load pre-trained model and freeze layers"""
        print(f"📦 Loading pre-trained model: {self.base_model}")
        self.model = YOLO(self.base_model)
        
        # Freeze backbone layers for transfer learning
        frozen = 0
        for i, param in enumerate(self.model.model.parameters()):
            if i < self.freeze_layers:
                param.requires_grad = False
                frozen += 1
            else:
                param.requires_grad = True
        
        print(f"❄️ Frozen {frozen} backbone layers")
        trainable = sum(p.numel() for p in self.model.model.parameters() if p.requires_grad)
        print(f"✅ Trainable parameters: {trainable:,}")
        
        return self.model
    
    def get_advanced_augmentations(self):
        """Get Albumentations pipeline for training"""
        return A.Compose([
            A.RandomBrightnessContrast(p=0.5),
            A.HorizontalFlip(p=0.5),
            A.MotionBlur(blur_limit=7, p=0.3),
            A.RandomFog(fog_coef_lower=0.1, fog_coef_upper=0.3, p=0.2),
            A.RandomRain(p=0.2),
            A.CoarseDropout(max_holes=3, max_height=40, max_width=40, p=0.3),
            A.Perspective(scale=(0.05, 0.1), p=0.3),
            A.GaussNoise(var_limit=(10.0, 50.0), p=0.2),
            A.RandAugment(num_ops=2, magnitude=9, p=0.3),
            A.Normalize(mean=[0, 0, 0], std=[1, 1, 1]),
            ToTensorV2()
        ], bbox_params=A.BboxParams(format='yolo', label_fields=['class_labels']))
    
    def train(self, data_yaml: str):
        """Execute transfer learning training"""
        if not self.model:
            self.load_and_freeze_model()
        
        print(f"\n🚀 Starting transfer learning...")
        print(f"   Dataset: {data_yaml}")
        print(f"   Epochs: {self.epochs}")
        print(f"   Device: {self.device}")
        
        # Train with transfer learning settings
        results = self.model.train(
            data=data_yaml,
            epochs=self.epochs,
            batch=self.batch_size,
            imgsz=640,
            device=self.device,
            lr0=self.lr0,
            lrf=0.01,
            patience=20,
            
            # Augmentations
            augment=True,
            mosaic=1.0,
            mixup=0.2,
            copy_paste=0.1,
            close_mosaic=10,
            
            # Advanced settings
            hsv_h=0.015,
            hsv_s=0.7,
            hsv_v=0.4,
            degrees=10.0,
            translate=0.1,
            scale=0.5,
            perspective=0.001,
            
            # Regularization
            weight_decay=0.0005,
            dropout=0.1,
            label_smoothing=0.1,
            
            # Optimization
            optimizer='AdamW',
            cos_lr=True,
            amp=True,
            
            # Other
            val=True,
            save=True,
            save_period=10,
            project='runs/transfer',
            name=f'infrastructure_{datetime.now().strftime("%Y%m%d")}',
            exist_ok=True
        )
        
        return results
    
    def evaluate(self, data_yaml: str):
        """Evaluate model performance"""
        if not self.model:
            raise ValueError("Model not loaded")
        
        print("\n📊 Evaluating model...")
        results = self.model.val(data=data_yaml, split='test')
        
        metrics = {
            'map50': float(results.box.map50),
            'map': float(results.box.map),
            'precision': float(results.box.mp),
            'recall': float(results.box.mr)
        }
        
        # Calculate F1
        if metrics['precision'] + metrics['recall'] > 0:
            metrics['f1'] = 2 * (metrics['precision'] * metrics['recall']) / (metrics['precision'] + metrics['recall'])
        else:
            metrics['f1'] = 0.0
        
        # Update best metrics
        if metrics['map50'] > self.best_metrics['map50']:
            self.best_metrics = metrics
        
        # Print results
        print(f"\n📈 Results:")
        print(f"   mAP@0.5: {metrics['map50']:.3f} (target: {self.target_map50})")
        print(f"   mAP: {metrics['map']:.3f}")
        print(f"   F1: {metrics['f1']:.3f} (target: {self.target_f1})")
        print(f"   Precision: {metrics['precision']:.3f}")
        print(f"   Recall: {metrics['recall']:.3f}")
        
        # Check targets
        if metrics['map50'] >= self.target_map50 and metrics['f1'] >= self.target_f1:
            print("\n✅ ALL TARGETS MET! Model ready for production.")
        else:
            print("\n⚠️ Targets not met. Consider more training or data.")
        
        return metrics
    
    def export_model(self):
        """Export model for deployment"""
        if not self.model:
            raise ValueError("Model not loaded")
        
        self.model.save(self.output_model)
        print(f"\n✅ Model exported to {self.output_model}")
        
        # Save metadata
        metadata = {
            'export_date': datetime.now().isoformat(),
            'best_metrics': self.best_metrics,
            'classes': self.classes,
            'freeze_layers': self.freeze_layers,
            'epochs': self.epochs
        }
        
        with open(self.output_model.replace('.pt', '_metadata.json'), 'w') as f:
            json.dump(metadata, f, indent=2)
        
        return self.output_model

def create_data_yaml():
    """Create data.yaml for training"""
    dataset_path = Path("./dataset")
    data_config = {
        'train': str(dataset_path / 'images' / 'train'),
        'val': str(dataset_path / 'images' / 'val'),
        'test': str(dataset_path / 'images' / 'test'),
        'nc': 5,
        'names': ["sagging_guy_wire", "straight_guy_wire", "pole", "insulator", "cross_arm"]
    }
    
    yaml_path = dataset_path / 'data.yaml'
    os.makedirs(dataset_path, exist_ok=True)
    
    with open(yaml_path, 'w') as f:
        yaml.dump(data_config, f)
    
    return yaml_path

def main():
    """Main transfer learning workflow"""
    print("="*60)
    print("🚀 NEXA TRANSFER LEARNING SYSTEM")
    print("="*60)
    
    # Initialize pipeline
    pipeline = TransferLearningPipeline()
    
    # Create data config
    data_yaml = create_data_yaml()
    print(f"✅ Dataset config: {data_yaml}")
    
    # Load and freeze model
    pipeline.load_and_freeze_model()
    
    # Train with transfer learning
    pipeline.train(str(data_yaml))
    
    # Evaluate
    metrics = pipeline.evaluate(str(data_yaml))
    
    # Export if targets met
    if metrics['map50'] >= pipeline.target_map50 and metrics['f1'] >= pipeline.target_f1:
        model_path = pipeline.export_model()
        print(f"\n🎉 Transfer learning complete!")
        print(f"   Model: {model_path}")
        print(f"   mAP@0.5: {metrics['map50']:.3f}")
        print(f"   F1: {metrics['f1']:.3f}")

if __name__ == "__main__":
    main()
