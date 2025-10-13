#!/usr/bin/env python3
"""
Enhanced Training for Wire Detection
Focuses on improving guy wire detection accuracy
"""

import os
import numpy as np
import cv2
from pathlib import Path
import yaml
import shutil
from ultralytics import YOLO
import random
from datetime import datetime

class EnhancedWireDatasetGenerator:
    """Generate enhanced dataset with focus on wire detection"""
    
    def __init__(self, num_images=200):
        self.num_images = num_images
        self.classes = {
            0: 'sagging_guy_wire',
            1: 'straight_guy_wire',
            2: 'pole',
            3: 'insulator', 
            4: 'cross_arm'
        }
        
    def generate_enhanced_wire_image(self, idx, split='train'):
        """Generate image with enhanced wire features"""
        height, width = 640, 640
        
        # Vary backgrounds more
        bg_type = idx % 5
        if bg_type == 0:
            img = np.ones((height, width, 3), dtype=np.uint8) * 220  # Light
        elif bg_type == 1:
            img = np.ones((height, width, 3), dtype=np.uint8) * 150  # Medium
        elif bg_type == 2:
            img = np.ones((height, width, 3), dtype=np.uint8) * 100  # Dark
        elif bg_type == 3:
            # Gradient background
            img = np.zeros((height, width, 3), dtype=np.uint8)
            for i in range(height):
                img[i, :] = int(100 + (150 * i / height))
        else:
            # Textured background
            img = np.random.randint(100, 200, (height, width, 3), dtype=np.uint8)
            img = cv2.GaussianBlur(img, (15, 15), 0)
        
        annotations = []
        
        # Always add at least one pole for reference
        px = random.randint(150, width-150)
        py_top = random.randint(100, 200)
        py_bottom = random.randint(450, 550)
        pole_width = random.randint(25, 35)
        
        # Draw pole
        cv2.rectangle(img, 
                     (px - pole_width//2, py_top),
                     (px + pole_width//2, py_bottom),
                     (80, 60, 40), -1)
        
        # Pole annotation
        annotations.append(f"2 {px/width:.6f} {(py_top+py_bottom)/2/height:.6f} "
                          f"{pole_width/width:.6f} {(py_bottom-py_top)/height:.6f}")
        
        # ENHANCED WIRE GENERATION - Add 3-5 wires per image
        num_wires = random.randint(3, 5)
        
        for w in range(num_wires):
            # Randomly choose wire type
            is_sagging = random.random() < 0.5
            
            # Wire endpoints
            if random.random() < 0.7:
                # From pole
                start_x = px + random.randint(-10, 10)
                start_y = py_top + random.randint(50, 150)
            else:
                # From random position
                start_x = random.randint(50, width-50)
                start_y = random.randint(150, 350)
            
            end_x = random.randint(50, width-50)
            end_y = random.randint(250, 550)
            
            # Make wires more visible - vary thickness
            wire_thickness = random.choice([2, 3, 4, 5])
            wire_color = random.choice([
                (40, 40, 40),    # Dark
                (60, 60, 60),    # Medium dark
                (80, 80, 80),    # Medium
                (20, 20, 20),    # Very dark
            ])
            
            if is_sagging:
                # Enhanced sagging wire with clearer curve
                num_points = 50
                t = np.linspace(0, 1, num_points)
                sag_amount = random.uniform(30, 80)
                
                points = []
                for i in range(num_points):
                    x = start_x + t[i] * (end_x - start_x)
                    # Parabolic sag
                    y = start_y + t[i] * (end_y - start_y) + sag_amount * 4 * t[i] * (1 - t[i])
                    points.append((int(x), int(y)))
                
                # Draw thick sagging wire
                for i in range(len(points) - 1):
                    cv2.line(img, points[i], points[i+1], wire_color, wire_thickness)
                
                # Add shadow for depth
                for i in range(len(points) - 1):
                    cv2.line(img, 
                            (points[i][0], points[i][1]+2),
                            (points[i+1][0], points[i+1][1]+2),
                            (wire_color[0]-20, wire_color[1]-20, wire_color[2]-20), 
                            max(1, wire_thickness-1))
                
                wire_class = 0  # sagging_guy_wire
                
                # Better bounding box for sagging wire
                xs = [p[0] for p in points]
                ys = [p[1] for p in points]
                min_x, max_x = min(xs), max(xs)
                min_y, max_y = min(ys), max(ys)
                
            else:
                # Straight wire with slight variations
                # Add very slight curve for realism
                mid_x = (start_x + end_x) // 2
                mid_y = (start_y + end_y) // 2 + random.randint(-5, 5)
                
                # Draw in segments for better visibility
                cv2.line(img, (start_x, start_y), (mid_x, mid_y), wire_color, wire_thickness)
                cv2.line(img, (mid_x, mid_y), (end_x, end_y), wire_color, wire_thickness)
                
                # Add shadow
                cv2.line(img, (start_x, start_y+2), (mid_x, mid_y+2), 
                        (wire_color[0]-20, wire_color[1]-20, wire_color[2]-20),
                        max(1, wire_thickness-1))
                cv2.line(img, (mid_x, mid_y+2), (end_x, end_y+2),
                        (wire_color[0]-20, wire_color[1]-20, wire_color[2]-20),
                        max(1, wire_thickness-1))
                
                wire_class = 1  # straight_guy_wire
                
                min_x, max_x = min(start_x, end_x), max(start_x, end_x)
                min_y, max_y = min(start_y, end_y), max(start_y, end_y)
            
            # Enhanced bounding box with padding
            padding = 10
            min_x = max(0, min_x - padding)
            max_x = min(width, max_x + padding)
            min_y = max(0, min_y - padding)
            max_y = min(height, max_y + padding)
            
            # YOLO annotation
            x_center = (min_x + max_x) / 2 / width
            y_center = (min_y + max_y) / 2 / height
            w = (max_x - min_x) / width
            h = (max_y - min_y) / height
            
            # Only add if box is reasonable size
            if w > 0.05 and h > 0.02:
                annotations.append(f"{wire_class} {x_center:.6f} {y_center:.6f} {w:.6f} {h:.6f}")
        
        # Add some insulators and cross-arms
        if random.random() < 0.7:
            # Cross-arm
            arm_y = py_top + random.randint(40, 100)
            arm_width = random.randint(80, 150)
            cv2.rectangle(img,
                        (px - arm_width//2, arm_y - 6),
                        (px + arm_width//2, arm_y + 6),
                        (70, 50, 30), -1)
            annotations.append(f"4 {px/width:.6f} {arm_y/height:.6f} "
                             f"{arm_width/width:.6f} {12/height:.6f}")
            
            # Insulators
            for side in [-1, 1]:
                if random.random() < 0.6:
                    ins_x = px + side * (arm_width//3)
                    cv2.circle(img, (ins_x, arm_y), 8, (120, 180, 200), -1)
                    annotations.append(f"3 {ins_x/width:.6f} {arm_y/height:.6f} "
                                     f"{16/width:.6f} {16/height:.6f}")
        
        # Add noise and variations
        noise = np.random.normal(0, 3, img.shape).astype(np.uint8)
        img = cv2.add(img, noise)
        
        # Random brightness/contrast
        alpha = random.uniform(0.8, 1.2)  # Contrast
        beta = random.randint(-10, 10)    # Brightness
        img = cv2.convertScaleAbs(img, alpha=alpha, beta=beta)
        
        return img, annotations
    
    def create_enhanced_dataset(self):
        """Create enhanced dataset with better wire representation"""
        print("🔧 Creating enhanced wire-focused dataset...")
        
        base_path = Path("./enhanced_wire_dataset")
        if base_path.exists():
            shutil.rmtree(base_path)
        
        # 70/20/10 split
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
            
            print(f"   Generating {count} enhanced {split} images...")
            
            for i in range(count):
                img, annotations = self.generate_enhanced_wire_image(i, split)
                
                # Save image
                img_path = img_dir / f"enhanced_{split}_{i:04d}.jpg"
                cv2.imwrite(str(img_path), img)
                
                # Save annotations
                if annotations:  # Only save if there are annotations
                    label_path = label_dir / f"enhanced_{split}_{i:04d}.txt"
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
        
        print(f"✅ Enhanced dataset created: {base_path}")
        return data_yaml_path

def train_enhanced_model():
    """Train with enhanced wire detection focus"""
    print("\n" + "="*60)
    print("🎯 ENHANCED WIRE DETECTION TRAINING")
    print("="*60)
    
    # Generate enhanced dataset
    generator = EnhancedWireDatasetGenerator(num_images=200)
    data_yaml = generator.create_enhanced_dataset()
    
    # Load the previous model for transfer learning
    print("\n📦 Loading previous model for fine-tuning...")
    if Path('yolo_infrastructure_production.pt').exists():
        model = YOLO('yolo_infrastructure_production.pt')
        print("   Using previous model as starting point")
    else:
        model = YOLO('yolov8n.pt')
        print("   Starting from base YOLOv8n")
    
    # Enhanced training configuration
    print("\n🚀 Starting enhanced training (50 epochs)...")
    
    results = model.train(
        data=str(data_yaml),
        epochs=50,  # Focused training
        batch=8,
        imgsz=640,
        device='cpu',
        
        # Optimized for wire detection
        optimizer='AdamW',
        lr0=0.0005,  # Lower learning rate for fine-tuning
        lrf=0.01,
        momentum=0.937,
        weight_decay=0.0005,
        
        # Augmentation for wires
        degrees=15.0,
        translate=0.2,
        scale=0.3,
        shear=5.0,
        perspective=0.002,
        flipud=0.0,
        fliplr=0.5,
        mosaic=0.8,
        mixup=0.1,
        copy_paste=0.0,  # Disabled for wires
        auto_augment='randaugment',
        
        # Training settings
        patience=15,
        save=True,
        save_period=10,
        project='runs/enhanced',
        name=f'wire_enhanced_{datetime.now().strftime("%Y%m%d_%H%M%S")}',
        exist_ok=True,
        verbose=True,
        seed=42,
        
        # Loss weights - emphasize classification
        box=7.5,
        cls=1.5,  # Increased for better class distinction
        dfl=1.5,
        
        # Validation
        val=True,
        plots=True
    )
    
    # Save enhanced model
    model.save('yolo_infrastructure_enhanced.pt')
    print(f"\n✅ Enhanced model saved to yolo_infrastructure_enhanced.pt")
    
    # Evaluate
    print("\n📊 Evaluating enhanced model...")
    metrics = model.val(data=str(data_yaml), split='test')
    
    print(f"\n📈 Enhanced Model Metrics:")
    print(f"   mAP@0.5: {metrics.box.map50:.3f}")
    print(f"   mAP@0.5:0.95: {metrics.box.map:.3f}")
    
    return metrics

if __name__ == "__main__":
    import sys
    
    if '--quick' in sys.argv:
        print("Quick mode: Using 50 images, 10 epochs")
        # Modify for quick testing
    
    metrics = train_enhanced_model()
    
    print("\n" + "="*60)
    print("✅ ENHANCED TRAINING COMPLETE!")
    print("="*60)
    print("\nModel ready for deployment:")
    print("   • yolo_infrastructure_enhanced.pt")
    print("   • Optimized for wire detection")
    print("   • Ready for infrastructure_analyzer.py")
