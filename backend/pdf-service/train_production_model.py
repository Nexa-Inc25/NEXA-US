#!/usr/bin/env python3
"""
Production Transfer Learning for NEXA Infrastructure Detection
Trains on synthetic dataset simulating real infrastructure images
"""

import os
import shutil
from pathlib import Path
import yaml
import numpy as np
import cv2
from ultralytics import YOLO
import random
import json
from datetime import datetime

class ProductionDatasetGenerator:
    """Generate realistic synthetic infrastructure dataset"""
    
    def __init__(self, num_images=100):
        self.num_images = num_images
        self.classes = {
            0: 'sagging_guy_wire',
            1: 'straight_guy_wire', 
            2: 'pole',
            3: 'insulator',
            4: 'cross_arm'
        }
        
    def generate_realistic_image(self, idx, split='train'):
        """Generate a realistic infrastructure image with annotations"""
        # Create base image with varying backgrounds
        height, width = 640, 640
        
        # Vary background (sky, terrain, etc)
        if idx % 3 == 0:
            # Clear sky
            img = np.ones((height, width, 3), dtype=np.uint8)
            img[:] = (230, 220, 200)  # Light blue-gray sky
        elif idx % 3 == 1:
            # Cloudy
            img = np.ones((height, width, 3), dtype=np.uint8)
            img[:] = (180, 180, 180)  # Gray
            # Add cloud variations
            for _ in range(5):
                cx = random.randint(0, width)
                cy = random.randint(0, height//2)
                cv2.circle(img, (cx, cy), random.randint(30, 80), 
                          (200, 200, 200), -1)
        else:
            # Mixed terrain
            img = np.ones((height, width, 3), dtype=np.uint8)
            img[:height//2] = (210, 200, 180)  # Sky
            img[height//2:] = (100, 120, 80)   # Ground
            
        annotations = []
        
        # Add poles (1-3 poles per image)
        num_poles = random.randint(1, 3)
        pole_positions = []
        
        for p in range(num_poles):
            # Pole position
            px = random.randint(100, width-100)
            py_top = random.randint(50, 200)
            py_bottom = random.randint(400, 600)
            pole_width = random.randint(20, 40)
            
            # Draw pole with texture
            pole_color = (60 + random.randint(-20, 20),
                         40 + random.randint(-10, 10),
                         30 + random.randint(-10, 10))
            cv2.rectangle(img, 
                         (px - pole_width//2, py_top),
                         (px + pole_width//2, py_bottom),
                         pole_color, -1)
            
            # Add pole texture lines
            for i in range(3):
                line_x = px - pole_width//2 + (i+1) * pole_width//4
                cv2.line(img, (line_x, py_top), (line_x, py_bottom),
                        (pole_color[0]-20, pole_color[1]-20, pole_color[2]-20), 1)
            
            pole_positions.append((px, py_top, py_bottom, pole_width))
            
            # YOLO annotation for pole (class 2)
            x_center = px / width
            y_center = (py_top + py_bottom) / 2 / height
            w = pole_width / width
            h = (py_bottom - py_top) / height
            annotations.append(f"2 {x_center:.6f} {y_center:.6f} {w:.6f} {h:.6f}")
            
            # Add cross-arms (70% chance)
            if random.random() < 0.7:
                arm_y = py_top + random.randint(30, 80)
                arm_width = random.randint(100, 200)
                arm_thickness = random.randint(8, 15)
                
                # Draw cross-arm
                cv2.rectangle(img,
                            (px - arm_width//2, arm_y - arm_thickness//2),
                            (px + arm_width//2, arm_y + arm_thickness//2),
                            (pole_color[0]-10, pole_color[1]-10, pole_color[2]-10), -1)
                
                # YOLO annotation for cross-arm (class 4)
                x_center = px / width
                y_center = arm_y / height
                w = arm_width / width
                h = arm_thickness / height
                annotations.append(f"4 {x_center:.6f} {y_center:.6f} {w:.6f} {h:.6f}")
                
                # Add insulators on cross-arm (50% chance each side)
                for side in [-1, 1]:
                    if random.random() < 0.5:
                        ins_x = px + side * (arm_width//3)
                        ins_y = arm_y
                        ins_size = random.randint(10, 20)
                        
                        # Draw insulator
                        cv2.circle(img, (ins_x, ins_y), ins_size//2,
                                 (100, 180, 200), -1)
                        cv2.circle(img, (ins_x, ins_y), ins_size//2,
                                 (80, 150, 170), 2)
                        
                        # YOLO annotation for insulator (class 3)
                        x_center = ins_x / width
                        y_center = ins_y / height
                        w = h = ins_size / width
                        annotations.append(f"3 {x_center:.6f} {y_center:.6f} {w:.6f} {h:.6f}")
        
        # Add guy wires between poles or to ground
        if len(pole_positions) > 1 or random.random() < 0.6:
            for i in range(random.randint(1, 3)):
                if len(pole_positions) > 1 and random.random() < 0.5:
                    # Wire between poles
                    p1 = random.choice(pole_positions)
                    p2 = random.choice([p for p in pole_positions if p != p1])
                    start_x = p1[0]
                    start_y = p1[1] + random.randint(50, 150)
                    end_x = p2[0]
                    end_y = p2[1] + random.randint(50, 150)
                else:
                    # Wire from pole to ground
                    p = random.choice(pole_positions)
                    start_x = p[0]
                    start_y = p[1] + random.randint(50, 150)
                    end_x = random.randint(50, width-50)
                    end_y = random.randint(500, 600)
                
                # Determine if sagging or straight
                is_sagging = random.random() < 0.5
                
                if is_sagging:
                    # Draw sagging wire (parabola)
                    num_points = 30
                    t = np.linspace(0, 1, num_points)
                    sag = random.uniform(20, 60)
                    
                    for i in range(num_points - 1):
                        x1 = int(start_x + t[i] * (end_x - start_x))
                        x2 = int(start_x + t[i+1] * (end_x - start_x))
                        
                        # Parabolic sag
                        y1 = start_y + t[i] * (end_y - start_y) + sag * 4 * t[i] * (1 - t[i])
                        y2 = start_y + t[i+1] * (end_y - start_y) + sag * 4 * t[i+1] * (1 - t[i+1])
                        
                        cv2.line(img, (x1, int(y1)), (x2, int(y2)),
                               (50, 50, 50), random.randint(2, 4))
                    
                    wire_class = 0  # sagging_guy_wire
                else:
                    # Draw straight wire
                    cv2.line(img, (start_x, start_y), (end_x, end_y),
                           (50, 50, 50), random.randint(2, 4))
                    wire_class = 1  # straight_guy_wire
                
                # YOLO annotation for wire
                x_center = (start_x + end_x) / 2 / width
                y_center = (start_y + end_y) / 2 / height
                w = abs(end_x - start_x) / width
                h = (abs(end_y - start_y) + (60 if is_sagging else 10)) / height
                annotations.append(f"{wire_class} {x_center:.6f} {y_center:.6f} {w:.6f} {h:.6f}")
        
        # Add realistic noise and variations
        # Add grain
        noise = np.random.normal(0, 5, img.shape).astype(np.uint8)
        img = cv2.add(img, noise)
        
        # Vary brightness
        brightness = random.uniform(0.8, 1.2)
        img = cv2.convertScaleAbs(img, alpha=brightness, beta=0)
        
        # Add slight blur for realism
        if random.random() < 0.3:
            img = cv2.GaussianBlur(img, (3, 3), 0)
        
        return img, annotations
    
    def create_dataset(self):
        """Create full dataset structure"""
        print("📦 Creating production-quality synthetic dataset...")
        
        base_path = Path("./infrastructure_dataset")
        
        # Clear old dataset
        if base_path.exists():
            shutil.rmtree(base_path)
        
        # Create splits (70% train, 20% val, 10% test)
        splits = {
            'train': int(self.num_images * 0.7),
            'val': int(self.num_images * 0.2),
            'test': int(self.num_images * 0.1)
        }
        
        for split, count in splits.items():
            img_dir = base_path / 'images' / split
            label_dir = base_path / 'labels' / split
            img_dir.mkdir(parents=True, exist_ok=True)
            label_dir.mkdir(parents=True, exist_ok=True)
            
            print(f"   Generating {count} {split} images...")
            
            for i in range(count):
                # Generate image and annotations
                img, annotations = self.generate_realistic_image(i, split)
                
                # Save image
                img_name = f"infrastructure_{split}_{i:04d}.jpg"
                img_path = img_dir / img_name
                cv2.imwrite(str(img_path), img)
                
                # Save annotations
                label_path = label_dir / f"infrastructure_{split}_{i:04d}.txt"
                with open(label_path, 'w') as f:
                    f.write('\n'.join(annotations))
        
        # Create data.yaml
        data_config = {
            'path': str(base_path.absolute()),
            'train': 'images/train',
            'val': 'images/val', 
            'test': 'images/test',
            'nc': 5,
            'names': list(self.classes.values())
        }
        
        data_yaml_path = base_path / 'data.yaml'
        with open(data_yaml_path, 'w') as f:
            yaml.dump(data_config, f)
        
        print(f"✅ Dataset created: {base_path}")
        print(f"   • Train: {splits['train']} images")
        print(f"   • Val: {splits['val']} images")
        print(f"   • Test: {splits['test']} images")
        
        return data_yaml_path

class ProductionTrainer:
    """Production transfer learning trainer"""
    
    def __init__(self):
        self.model = None
        self.data_yaml = None
        
    def train(self, data_yaml, epochs=100):
        """Train model with production settings"""
        print("\n" + "="*60)
        print("🚀 PRODUCTION TRANSFER LEARNING")
        print("="*60)
        
        # Load pre-trained model
        print("📦 Loading YOLOv8n pre-trained model...")
        self.model = YOLO('yolov8n.pt')
        
        # Configure for transfer learning
        print("❄️ Configuring transfer learning...")
        
        # Training configuration for production
        print(f"\n🎯 Starting production training ({epochs} epochs)...")
        print("   This will take significant time on CPU")
        print("   Consider using GPU for faster training")
        
        results = self.model.train(
            data=str(data_yaml),
            epochs=epochs,
            batch=8,  # Smaller batch for CPU
            imgsz=640,
            device='cpu',  # Use 'cuda' if GPU available
            
            # Optimization
            optimizer='AdamW',
            lr0=0.001,
            lrf=0.01,
            momentum=0.937,
            weight_decay=0.0005,
            
            # Augmentation
            degrees=10.0,
            translate=0.1,
            scale=0.5,
            shear=2.0,
            perspective=0.001,
            flipud=0.0,
            fliplr=0.5,
            mosaic=1.0,
            mixup=0.15,
            copy_paste=0.1,
            auto_augment='randaugment',
            erasing=0.4,
            
            # Training settings
            patience=20,
            save=True,
            save_period=10,
            cache=False,
            workers=4,
            project='runs/production',
            name=f'infrastructure_{datetime.now().strftime("%Y%m%d_%H%M%S")}',
            exist_ok=True,
            pretrained=True,
            verbose=True,
            seed=42,
            deterministic=True,
            single_cls=False,
            rect=False,
            cos_lr=True,
            close_mosaic=10,
            
            # Validation
            val=True,
            plots=True
        )
        
        # Save final model
        model_path = 'yolo_infrastructure_production.pt'
        self.model.save(model_path)
        print(f"\n✅ Model saved to {model_path}")
        
        return results
    
    def evaluate(self, data_yaml):
        """Evaluate trained model"""
        print("\n📊 Evaluating model on test set...")
        
        if self.model is None:
            self.model = YOLO('yolo_infrastructure_production.pt')
        
        metrics = self.model.val(
            data=str(data_yaml),
            split='test',
            save_json=True,
            save_hybrid=True,
            conf=0.25,
            iou=0.6,
            max_det=300,
            plots=True
        )
        
        print(f"\n📈 Final Metrics:")
        print(f"   mAP@0.5: {metrics.box.map50:.3f}")
        print(f"   mAP@0.5:0.95: {metrics.box.map:.3f}")
        print(f"   Precision: {metrics.box.mp:.3f}")
        print(f"   Recall: {metrics.box.mr:.3f}")
        
        # Per-class metrics
        print("\n📊 Per-Class Performance:")
        class_names = ['sagging_guy_wire', 'straight_guy_wire', 'pole', 'insulator', 'cross_arm']
        for i, name in enumerate(class_names):
            if i < len(metrics.box.ap50):
                print(f"   {name}: AP@0.5={metrics.box.ap50[i]:.3f}")
        
        return metrics

def main():
    """Main training pipeline"""
    print("="*60)
    print("🏗️ NEXA INFRASTRUCTURE DETECTION")
    print("PRODUCTION TRAINING PIPELINE")
    print("="*60)
    
    # Parse arguments for quick vs full training
    import sys
    quick_mode = '--quick' in sys.argv
    
    if quick_mode:
        print("⚡ Running in QUICK mode (10 images, 5 epochs)")
        num_images = 10
        epochs = 5
    else:
        print("🚀 Running in PRODUCTION mode (100 images, 100 epochs)")
        print("   Add --quick flag for faster testing")
        num_images = 100
        epochs = 100
    
    # Generate dataset
    generator = ProductionDatasetGenerator(num_images=num_images)
    data_yaml = generator.create_dataset()
    
    # Train model
    trainer = ProductionTrainer()
    results = trainer.train(data_yaml, epochs=epochs)
    
    # Evaluate
    metrics = trainer.evaluate(data_yaml)
    
    # Summary
    print("\n" + "="*60)
    print("✅ TRAINING COMPLETE!")
    print("="*60)
    
    print("\n📊 Summary:")
    print(f"   • Dataset: {num_images} synthetic images")
    print(f"   • Training: {epochs} epochs completed")
    print(f"   • Model: yolo_infrastructure_production.pt")
    print(f"   • mAP@0.5: {metrics.box.map50:.3f}")
    
    print("\n🚀 Next Steps:")
    print("   1. Test with real field photos")
    print("   2. Fine-tune on actual PM 35125285 images")
    print("   3. Deploy with infrastructure_analyzer.py")
    print("   4. Monitor performance in production")
    
    print("\n💡 For better results:")
    print("   • Use GPU training (10-50x faster)")
    print("   • Collect real field photos")
    print("   • Label with Roboflow or LabelImg")
    print("   • Train for 200+ epochs")
    print("   • Use larger model (yolov8s or yolov8m)")

if __name__ == "__main__":
    main()
