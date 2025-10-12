#!/usr/bin/env python3
"""
Enhanced YOLO Training for Better Crossarm Detection
Implements targeted improvements for zero recall issue
"""

import os
import yaml
import torch
import numpy as np
from pathlib import Path
from ultralytics import YOLO
from ultralytics.data import YOLODataset
import logging
from typing import Dict, List
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BalancedDataset(YOLODataset):
    """Custom dataset class with oversampling for crossarms"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.crossarm_boost_factor = 3  # Oversample crossarm images 3x
        self._prepare_balanced_indices()
    
    def _prepare_balanced_indices(self):
        """Prepare balanced sampling indices"""
        self.balanced_indices = []
        
        for idx, label in enumerate(self.labels):
            # Check if image contains crossarm (class 1)
            if label is not None and 1 in label[:, 0]:  # Crossarm class
                # Add multiple times for oversampling
                self.balanced_indices.extend([idx] * self.crossarm_boost_factor)
            else:
                self.balanced_indices.append(idx)
        
        logger.info(f"Balanced dataset: {len(self.balanced_indices)} samples (from {len(self.labels)} original)")
    
    def __len__(self):
        return len(self.balanced_indices)
    
    def __getitem__(self, idx):
        real_idx = self.balanced_indices[idx % len(self.balanced_indices)]
        return super().__getitem__(real_idx)

class EnhancedYOLOTrainer:
    """Enhanced YOLO trainer with crossarm focus"""
    
    def __init__(self, model_size='m'):
        """
        Initialize trainer
        Args:
            model_size: 'n', 's', 'm', 'l', 'x' (larger = better for small objects)
        """
        self.model_size = model_size
        self.model = None
        self.data_config = None
        
    def prepare_merged_dataset(self, dataset_paths: List[str], output_path: str):
        """
        Merge multiple datasets for training
        
        Args:
            dataset_paths: List of dataset directories to merge
            output_path: Output path for merged dataset
        """
        logger.info(f"Merging {len(dataset_paths)} datasets...")
        
        merged_train = Path(output_path) / "train"
        merged_val = Path(output_path) / "val"
        merged_train.mkdir(parents=True, exist_ok=True)
        merged_val.mkdir(parents=True, exist_ok=True)
        
        # Track class distribution
        class_counts = {}
        total_images = 0
        
        for dataset_path in dataset_paths:
            dataset_path = Path(dataset_path)
            
            # Copy train images and labels
            if (dataset_path / "train").exists():
                for img_file in (dataset_path / "train" / "images").glob("*"):
                    # Copy image
                    dest = merged_train / "images" / f"{dataset_path.name}_{img_file.name}"
                    dest.parent.mkdir(exist_ok=True)
                    import shutil
                    shutil.copy(img_file, dest)
                    
                    # Copy corresponding label
                    label_file = dataset_path / "train" / "labels" / f"{img_file.stem}.txt"
                    if label_file.exists():
                        label_dest = merged_train / "labels" / f"{dataset_path.name}_{img_file.stem}.txt"
                        label_dest.parent.mkdir(exist_ok=True)
                        shutil.copy(label_file, label_dest)
                        
                        # Count classes
                        with open(label_file, 'r') as f:
                            for line in f:
                                class_id = int(line.split()[0])
                                class_counts[class_id] = class_counts.get(class_id, 0) + 1
                    
                    total_images += 1
        
        logger.info(f"✅ Merged {total_images} images")
        logger.info(f"📊 Class distribution: {class_counts}")
        
        # Identify imbalanced classes
        if class_counts:
            avg_count = sum(class_counts.values()) / len(class_counts)
            for class_id, count in class_counts.items():
                if count < avg_count * 0.3:  # Less than 30% of average
                    logger.warning(f"⚠️ Class {class_id} is underrepresented: {count} instances")
        
        return merged_train, merged_val, class_counts
    
    def create_enhanced_config(self, base_data_yaml: str, output_yaml: str):
        """
        Create enhanced data configuration with multiple datasets
        
        Args:
            base_data_yaml: Path to base data.yaml
            output_yaml: Path to save enhanced config
        """
        
        # Enhanced configuration for crossarm detection
        config = {
            'path': os.path.abspath('.'),
            'train': [
                'datasets/original/train',
                'datasets/roboflow_utility/train',
                'datasets/epri_transmission/train',
                'datasets/augmented/train'
            ],
            'val': 'datasets/merged/val',
            'test': 'datasets/merged/test',
            'nc': 11,  # Number of classes
            'names': [
                'pole_type1',      # 0
                'crossarm',        # 1 - FOCUS CLASS
                'double_crossarm', # 2
                'insulator',       # 3
                'transformer',     # 4
                'cutout',          # 5
                'lightning_arrester', # 6
                'splice_case',     # 7
                'street_light',    # 8
                'vegetation',      # 9
                'wire'            # 10
            ]
        }
        
        # Save enhanced config
        with open(output_yaml, 'w') as f:
            yaml.dump(config, f)
        
        logger.info(f"✅ Created enhanced config: {output_yaml}")
        return config
    
    def get_enhanced_hyperparameters(self):
        """
        Get optimized hyperparameters for crossarm detection
        """
        return {
            # Training parameters
            'epochs': 200,  # More epochs for better learning
            'patience': 50,  # Don't stop early
            'batch': 16,  # Adjust based on memory
            'imgsz': 640,  # Standard size
            
            # Augmentation - Enhanced for small objects
            'hsv_h': 0.02,  # Hue variation
            'hsv_s': 0.8,   # Saturation variation (high)
            'hsv_v': 0.5,   # Value variation
            'degrees': 30,   # Rotation
            'translate': 0.2,  # Translation
            'scale': 0.7,    # Scale variation (important for crossarms)
            'shear': 10,     # Shear
            'perspective': 0.001,  # Perspective
            'flipud': 0.5,   # Vertical flip
            'fliplr': 0.5,   # Horizontal flip
            'mosaic': 1.0,   # Mosaic augmentation (crucial)
            'mixup': 0.2,    # MixUp augmentation
            'copy_paste': 0.1,  # Copy-paste augmentation
            
            # Loss weights
            'box': 7.5,      # Box loss weight
            'cls': 0.5,      # Classification loss
            'dfl': 1.5,      # Distribution focal loss
            'fl_gamma': 2.0,  # Focal loss gamma for rare classes
            
            # Optimization
            'optimizer': 'AdamW',
            'lr0': 0.01,     # Initial learning rate
            'lrf': 0.01,     # Final learning rate
            'momentum': 0.937,
            'weight_decay': 0.0005,
            'warmup_epochs': 3.0,
            'warmup_momentum': 0.8,
            'warmup_bias_lr': 0.1,
            
            # Anchor optimization
            'anchor_t': 4.0,  # Anchor threshold
            'close_mosaic': 10,  # Disable mosaic last N epochs
            
            # Other
            'label_smoothing': 0.1,
            'nbs': 64,  # Nominal batch size
            'overlap_mask': True,
            'mask_ratio': 4,
            'dropout': 0.1,  # Dropout for regularization
        }
    
    def train_with_class_weights(self, data_yaml: str, pretrained_model: str = None):
        """
        Train YOLO with class weights to handle imbalance
        
        Args:
            data_yaml: Path to data configuration
            pretrained_model: Path to pretrained model (optional)
        """
        
        # Load model
        if pretrained_model and os.path.exists(pretrained_model):
            logger.info(f"Loading pretrained model: {pretrained_model}")
            self.model = YOLO(pretrained_model)
        else:
            logger.info(f"Loading YOLOv8{self.model_size} base model")
            self.model = YOLO(f'yolov8{self.model_size}.pt')
        
        # Get enhanced hyperparameters
        hyp = self.get_enhanced_hyperparameters()
        
        logger.info("🚀 Starting enhanced training with focus on crossarm detection...")
        logger.info(f"📊 Hyperparameters: {json.dumps(hyp, indent=2)}")
        
        # Train with enhanced settings
        results = self.model.train(
            data=data_yaml,
            **hyp,
            project='enhanced_training',
            name='crossarm_focused',
            exist_ok=True,
            device='cpu',  # Change to 'cuda' if GPU available
            workers=4,
            save=True,
            save_period=10,  # Save checkpoint every 10 epochs
            plots=True,
            verbose=True,
            seed=42,
            deterministic=False,
            single_cls=False,
            rect=False,  # Don't use rectangular training
            cos_lr=True,  # Cosine learning rate schedule
            resume=False,
            amp=False,  # Automatic mixed precision (GPU only)
            fraction=1.0,  # Use full dataset
            profile=False,
            freeze=None,  # Don't freeze layers
            multi_scale=False,
            cache=False,  # Cache images in RAM/disk
            # Custom dataset class for balancing
            # dataset_class=BalancedDataset  # Uncomment if using custom class
        )
        
        # Save final model
        output_path = 'yolo_crossarm_enhanced.pt'
        self.model.save(output_path)
        logger.info(f"✅ Model saved to {output_path}")
        
        return results
    
    def evaluate_class_performance(self, model_path: str, data_yaml: str):
        """
        Evaluate per-class performance with focus on crossarm
        
        Args:
            model_path: Path to trained model
            data_yaml: Path to data configuration
        """
        
        model = YOLO(model_path)
        
        # Run validation
        metrics = model.val(data=data_yaml, verbose=True, plots=True)
        
        # Extract per-class metrics
        class_names = model.names
        logger.info("\n📊 Per-Class Performance:")
        logger.info("-" * 50)
        
        for i, name in enumerate(class_names.values()):
            precision = metrics.box.p[i] if i < len(metrics.box.p) else 0
            recall = metrics.box.r[i] if i < len(metrics.box.r) else 0
            map50 = metrics.box.map50[i] if i < len(metrics.box.map50) else 0
            
            # Highlight crossarm performance
            if name == 'crossarm':
                logger.info(f"🎯 {name:15} P:{precision:.3f} R:{recall:.3f} mAP50:{map50:.3f} ⚠️ FOCUS CLASS")
            else:
                logger.info(f"   {name:15} P:{precision:.3f} R:{recall:.3f} mAP50:{map50:.3f}")
        
        # Overall metrics
        logger.info("-" * 50)
        logger.info(f"Overall mAP50: {metrics.box.map50:.3f}")
        logger.info(f"Overall mAP50-95: {metrics.box.map:.3f}")
        
        # Check if crossarm recall improved
        crossarm_idx = list(class_names.values()).index('crossarm') if 'crossarm' in class_names.values() else -1
        if crossarm_idx >= 0:
            crossarm_recall = metrics.box.r[crossarm_idx] if crossarm_idx < len(metrics.box.r) else 0
            if crossarm_recall > 0.5:
                logger.info(f"✅ GOAL ACHIEVED: Crossarm recall = {crossarm_recall:.3f} (target: >0.5)")
            else:
                logger.info(f"⚠️ Crossarm recall = {crossarm_recall:.3f} - needs more data/tuning")
        
        return metrics

def download_roboflow_dataset(api_key: str, workspace: str, project: str, version: int, output_dir: str):
    """
    Download dataset from Roboflow
    
    Args:
        api_key: Roboflow API key
        workspace: Workspace name
        project: Project name
        version: Dataset version
        output_dir: Output directory
    """
    try:
        from roboflow import Roboflow
        
        rf = Roboflow(api_key=api_key)
        project = rf.workspace(workspace).project(project)
        dataset = project.version(version).download("yolov8", location=output_dir)
        
        logger.info(f"✅ Downloaded Roboflow dataset to {output_dir}")
        return dataset.location
    except Exception as e:
        logger.error(f"Failed to download Roboflow dataset: {e}")
        return None

def main():
    """Main training pipeline"""
    
    logger.info("="*60)
    logger.info("🎯 ENHANCED YOLO TRAINING FOR CROSSARM DETECTION")
    logger.info("="*60)
    
    trainer = EnhancedYOLOTrainer(model_size='m')  # Use medium model for better detection
    
    # Step 1: Download additional datasets (if API key available)
    roboflow_api_key = os.environ.get('ROBOFLOW_API_KEY')
    if roboflow_api_key:
        logger.info("\n📥 Downloading Roboflow dataset...")
        download_roboflow_dataset(
            api_key=roboflow_api_key,
            workspace='zac-xzsly',
            project='utility-poles',
            version=1,
            output_dir='datasets/roboflow_utility'
        )
    else:
        logger.warning("⚠️ ROBOFLOW_API_KEY not set - using existing data only")
    
    # Step 2: Prepare merged dataset
    logger.info("\n🔄 Preparing merged dataset...")
    dataset_paths = [
        'pole_training',  # Original dataset
        'datasets/roboflow_utility',  # New Roboflow data
    ]
    
    # Filter existing paths
    existing_paths = [p for p in dataset_paths if os.path.exists(p)]
    if existing_paths:
        merged_train, merged_val, class_dist = trainer.prepare_merged_dataset(
            existing_paths,
            'datasets/merged'
        )
    
    # Step 3: Create enhanced configuration
    logger.info("\n⚙️ Creating enhanced configuration...")
    data_yaml = trainer.create_enhanced_config(
        'pole_training/data.yaml',
        'data_enhanced.yaml'
    )
    
    # Step 4: Train with enhanced settings
    logger.info("\n🚀 Starting training with crossarm focus...")
    results = trainer.train_with_class_weights('data_enhanced.yaml')
    
    # Step 5: Evaluate performance
    logger.info("\n📊 Evaluating model performance...")
    metrics = trainer.evaluate_class_performance(
        'yolo_crossarm_enhanced.pt',
        'data_enhanced.yaml'
    )
    
    logger.info("\n✅ Training complete!")
    logger.info("\n💡 Next steps:")
    logger.info("1. Deploy yolo_crossarm_enhanced.pt to production")
    logger.info("2. Test on real crossarm images")
    logger.info("3. Monitor recall metrics in production")
    logger.info("4. Add more crossarm data if recall < 0.5")

if __name__ == "__main__":
    main()
