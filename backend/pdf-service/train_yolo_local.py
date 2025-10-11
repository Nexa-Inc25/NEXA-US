#!/usr/bin/env python3
"""
Local YOLOv8 Training Script for NEXA Utility Pole Detection
Trains a custom model for detecting poles, crossarms, and insulators in audit photos
"""

import os
import sys
import torch
from pathlib import Path
from ultralytics import YOLO
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PoleDetectionTrainer:
    def __init__(self, dataset_path='C:/datasets/utility_poles', model_size='n'):
        """
        Initialize trainer for utility pole detection
        
        Args:
            dataset_path: Path to dataset with images/ and labels/ folders
            model_size: YOLOv8 model size ('n', 's', 'm', 'l', 'x')
        """
        self.dataset_path = Path(dataset_path)
        self.model_size = model_size
        self.device = 0 if torch.cuda.is_available() else 'cpu'
        
        # Log system info
        if torch.cuda.is_available():
            logger.info(f"🎮 GPU detected: {torch.cuda.get_device_name(0)}")
            logger.info(f"💾 GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")
        else:
            logger.warning("⚠️ No GPU detected - training will be slow on CPU")
    
    def create_data_yaml(self):
        """Create data.yaml configuration file"""
        data_yaml = self.dataset_path / 'data.yaml'
        
        config = f"""
path: {self.dataset_path}
train: images/train
val: images/val

# Number of classes
nc: 5

# Class names (matching PG&E utility specs)
names: ['pole_type1', 'pole_type2', 'pole_type3', 'crossarm', 'insulator']

# Optional: Roboflow integration
# roboflow:
#   workspace: nexa-inc
#   project: utility-pole-detection
#   version: 1
#   api_key: YOUR_KEY
"""
        
        with open(data_yaml, 'w') as f:
            f.write(config.strip())
        
        logger.info(f"✅ Created data.yaml at {data_yaml}")
        return str(data_yaml)
    
    def validate_dataset(self):
        """Validate dataset structure and report statistics"""
        train_imgs = list((self.dataset_path / 'images' / 'train').glob('*.jpg'))
        val_imgs = list((self.dataset_path / 'images' / 'val').glob('*.jpg'))
        train_labels = list((self.dataset_path / 'labels' / 'train').glob('*.txt'))
        val_labels = list((self.dataset_path / 'labels' / 'val').glob('*.txt'))
        
        logger.info("📊 Dataset Statistics:")
        logger.info(f"  Training images: {len(train_imgs)}")
        logger.info(f"  Training labels: {len(train_labels)}")
        logger.info(f"  Validation images: {len(val_imgs)}")
        logger.info(f"  Validation labels: {len(val_labels)}")
        
        if len(train_imgs) != len(train_labels):
            logger.warning(f"⚠️ Mismatch: {len(train_imgs)} images vs {len(train_labels)} labels in training")
        
        if len(train_imgs) < 100:
            logger.warning("⚠️ Small dataset (<100 images) - consider data augmentation")
        
        return len(train_imgs) > 0 and len(val_imgs) > 0
    
    def train(self, epochs=100, batch_size=16, patience=20):
        """
        Train YOLOv8 model on utility pole dataset
        
        Args:
            epochs: Number of training epochs
            batch_size: Batch size (reduce if GPU OOM)
            patience: Early stopping patience
        """
        # Validate dataset
        if not self.validate_dataset():
            logger.error("❌ Dataset validation failed - check folder structure")
            return None
        
        # Create data.yaml
        data_yaml = self.create_data_yaml()
        
        # Load base model
        model_name = f'yolov8{self.model_size}.pt'
        logger.info(f"📦 Loading base model: {model_name}")
        model = YOLO(model_name)
        
        # Training parameters optimized for utility poles
        logger.info("🚀 Starting training...")
        results = model.train(
            data=data_yaml,
            epochs=epochs,
            imgsz=640,
            batch=batch_size,
            device=self.device,
            name=f'pole_detection_{datetime.now().strftime("%Y%m%d_%H%M")}',
            patience=patience,
            save=True,
            save_period=10,
            
            # Augmentation for field conditions
            augment=True,
            hsv_h=0.015,      # Color variation
            hsv_s=0.7,
            hsv_v=0.4,
            degrees=30,       # Rotation for tilted poles
            translate=0.1,
            scale=0.5,
            shear=0.0,
            perspective=0.0,
            flipud=0.0,       # No vertical flip for poles
            fliplr=0.5,       # Horizontal flip OK
            mosaic=1.0,       # Multi-image training
            mixup=0.0,
            
            # Loss weights
            box=7.5,          # Bounding box loss
            cls=0.5,          # Classification loss
            dfl=1.5,          # Distribution focal loss
            
            # Optimizer
            optimizer='AdamW',
            lr0=0.001,
            lrf=0.01,
            momentum=0.937,
            weight_decay=0.0005,
            warmup_epochs=3,
            warmup_momentum=0.8,
        )
        
        logger.info("✅ Training complete!")
        return results
    
    def evaluate(self, model_path):
        """Evaluate trained model performance"""
        logger.info(f"📈 Evaluating model: {model_path}")
        model = YOLO(model_path)
        
        # Validate on test set
        metrics = model.val(data=str(self.dataset_path / 'data.yaml'))
        
        # Report metrics
        logger.info("📊 Model Performance:")
        logger.info(f"  mAP@50: {metrics.box.map50:.3f}")
        logger.info(f"  mAP@50-95: {metrics.box.map:.3f}")
        logger.info(f"  Precision: {metrics.box.mp:.3f}")
        logger.info(f"  Recall: {metrics.box.mr:.3f}")
        
        # Per-class performance
        if hasattr(metrics.box, 'ap_class_index'):
            for i, class_name in enumerate(model.names.values()):
                if i < len(metrics.box.ap50):
                    logger.info(f"  {class_name}: AP@50={metrics.box.ap50[i]:.3f}")
        
        return metrics
    
    def export_for_deployment(self, model_path, output_dir='./'):
        """Export model for NEXA deployment"""
        logger.info("📤 Exporting model for deployment...")
        model = YOLO(model_path)
        
        # Export formats
        output_dir = Path(output_dir)
        
        # PyTorch format for Render
        pt_path = output_dir / 'yolo_pole_trained.pt'
        model.export(format='torchscript', imgsz=640)
        logger.info(f"  ✅ Exported PyTorch model to {pt_path}")
        
        # ONNX for edge/mobile
        onnx_path = output_dir / 'yolo_pole.onnx'
        model.export(format='onnx', imgsz=640, simplify=True)
        logger.info(f"  ✅ Exported ONNX model to {onnx_path}")
        
        return pt_path
    
    def test_inference(self, model_path, test_image):
        """Test model on a sample image"""
        logger.info(f"🔍 Testing inference on {test_image}")
        model = YOLO(model_path)
        
        results = model(test_image)
        
        for r in results:
            # Log detections
            for box in r.boxes:
                cls = int(box.cls)
                conf = float(box.conf)
                xyxy = box.xyxy[0].tolist()
                logger.info(f"  Detected: {model.names[cls]} (conf={conf:.2f})")
            
            # Save annotated image
            output_path = Path(test_image).stem + '_detected.jpg'
            r.save(output_path)
            logger.info(f"  💾 Saved annotated image to {output_path}")

def main():
    """Main training pipeline"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Train YOLOv8 for NEXA Pole Detection')
    parser.add_argument('--dataset', type=str, default='C:/datasets/utility_poles',
                      help='Path to dataset folder')
    parser.add_argument('--model', type=str, default='n', choices=['n', 's', 'm', 'l', 'x'],
                      help='YOLOv8 model size')
    parser.add_argument('--epochs', type=int, default=100,
                      help='Number of training epochs')
    parser.add_argument('--batch', type=int, default=16,
                      help='Batch size (reduce if GPU OOM)')
    parser.add_argument('--test', type=str, help='Test image path for inference')
    
    args = parser.parse_args()
    
    # Initialize trainer
    trainer = PoleDetectionTrainer(args.dataset, args.model)
    
    # Train model
    results = trainer.train(epochs=args.epochs, batch_size=args.batch)
    
    if results:
        # Find best model
        best_model = Path('runs') / 'detect' / results.name / 'weights' / 'best.pt'
        
        # Evaluate
        metrics = trainer.evaluate(best_model)
        
        # Export for deployment
        deployment_model = trainer.export_for_deployment(best_model)
        
        # Test inference if image provided
        if args.test and os.path.exists(args.test):
            trainer.test_inference(best_model, args.test)
        
        logger.info(f"""
🎉 Training Complete!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Final mAP@50: {metrics.box.map50:.3f}
📦 Model saved: {best_model}
🚀 Ready for deployment: {deployment_model}

Next steps:
1. Copy {deployment_model} to backend/pdf-service/
2. Update Dockerfile.oct2025:
   COPY ./yolo_pole_trained.pt /data/yolo_pole.pt
3. Git commit and push to deploy on Render
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        """)

if __name__ == '__main__':
    main()
