#!/usr/bin/env python3
"""
Quick Transfer Learning Demo for NEXA Infrastructure Detection
Downloads a sample dataset or creates synthetic data for demonstration
"""

import os
import shutil
from pathlib import Path
import yaml
import numpy as np
import cv2
from ultralytics import YOLO

def create_sample_dataset():
    """Create a minimal synthetic dataset for demonstration"""
    print("📦 Creating sample dataset for demonstration...")
    
    # Create dataset structure
    base_path = Path("./dataset")
    for split in ['train', 'val', 'test']:
        img_dir = base_path / 'images' / split
        label_dir = base_path / 'labels' / split
        img_dir.mkdir(parents=True, exist_ok=True)
        label_dir.mkdir(parents=True, exist_ok=True)
        
        # Create synthetic images and labels
        for i in range(3):  # Just 3 images per split for demo
            # Create a synthetic image
            img = np.ones((640, 640, 3), dtype=np.uint8) * 200
            
            # Add some features
            # Draw pole
            cv2.rectangle(img, (300, 200), (340, 500), (100, 50, 20), -1)
            
            # Draw guy wire (sagging or straight)
            if i % 2 == 0:
                # Sagging wire
                x = np.linspace(340, 550, 30)
                y = 0.001 * (x - 445)**2 + 300
                points = np.column_stack([x, y]).astype(int)
                for j in range(len(points) - 1):
                    cv2.line(img, tuple(points[j]), tuple(points[j+1]), (50, 50, 50), 3)
                wire_class = 0  # sagging_guy_wire
            else:
                # Straight wire
                cv2.line(img, (340, 300), (550, 300), (50, 50, 50), 3)
                wire_class = 1  # straight_guy_wire
            
            # Save image
            img_path = img_dir / f'sample_{split}_{i}.jpg'
            cv2.imwrite(str(img_path), img)
            
            # Create corresponding label file (YOLO format)
            # Format: class x_center y_center width height (normalized)
            labels = []
            
            # Pole annotation
            labels.append(f"2 0.5 0.55 0.0625 0.47")  # pole class
            
            # Wire annotation
            if wire_class == 0:
                labels.append(f"0 0.695 0.47 0.33 0.05")  # sagging_guy_wire
            else:
                labels.append(f"1 0.695 0.47 0.33 0.02")  # straight_guy_wire
            
            # Save label
            label_path = label_dir / f'sample_{split}_{i}.txt'
            with open(label_path, 'w') as f:
                f.write('\n'.join(labels))
    
    print(f"✅ Created sample dataset in {base_path}")

def train_quick_demo():
    """Quick training demonstration"""
    print("\n" + "="*60)
    print("🚀 NEXA TRANSFER LEARNING - QUICK DEMO")
    print("="*60)
    
    # Create sample dataset
    create_sample_dataset()
    
    # Create data.yaml
    data_config = {
        'path': str(Path.cwd() / 'dataset'),
        'train': 'images/train',
        'val': 'images/val',
        'test': 'images/test',
        'nc': 5,
        'names': ['sagging_guy_wire', 'straight_guy_wire', 'pole', 'insulator', 'cross_arm']
    }
    
    data_yaml_path = Path('dataset/data.yaml')
    with open(data_yaml_path, 'w') as f:
        yaml.dump(data_config, f)
    
    print(f"✅ Created data.yaml")
    
    # Load pre-trained model
    print("\n📦 Loading YOLOv8n pre-trained model...")
    model = YOLO('yolov8n.pt')
    
    # Quick training (just 3 epochs for demo)
    print("\n🎯 Starting quick training demo (3 epochs)...")
    print("   Note: This is just a demonstration with minimal data")
    print("   For production, use 1500+ real images and 100+ epochs")
    
    results = model.train(
        data=str(data_yaml_path),
        epochs=3,  # Very quick for demo
        batch=2,   # Small batch for demo
        imgsz=320, # Smaller size for speed
        device='cpu',
        patience=3,
        save=True,
        project='runs/demo',
        name='infrastructure_demo',
        exist_ok=True,
        pretrained=True,
        verbose=True
    )
    
    # Save the model
    model_path = 'yolo_infrastructure_demo.pt'
    model.save(model_path)
    print(f"\n✅ Demo model saved to {model_path}")
    
    # Quick evaluation
    print("\n📊 Quick evaluation on test set...")
    metrics = model.val(data=str(data_yaml_path), split='test')
    
    print(f"\n📈 Demo Results:")
    print(f"   mAP@0.5: {metrics.box.map50:.3f}")
    print(f"   Note: Low scores expected with minimal synthetic data")
    
    print("\n" + "="*60)
    print("✅ DEMO COMPLETE!")
    print("="*60)
    print("\nFor production training:")
    print("1. Collect 1500+ real infrastructure images")
    print("2. Label with Roboflow or LabelImg")
    print("3. Run transfer_learning.py with full dataset")
    print("4. Train for 100+ epochs")
    print("5. Expect mAP@0.5 > 0.95")
    
    return model_path

def test_demo_model(model_path):
    """Test the demo model"""
    print("\n🧪 Testing demo model...")
    
    # Load model
    model = YOLO(model_path)
    
    # Create a test image
    test_img = np.ones((640, 640, 3), dtype=np.uint8) * 200
    cv2.rectangle(test_img, (300, 200), (340, 500), (100, 50, 20), -1)
    cv2.line(test_img, (340, 350), (550, 350), (50, 50, 50), 3)
    
    # Run inference
    results = model.predict(test_img, conf=0.25)
    
    print(f"✅ Inference working!")
    print(f"   Detected {len(results[0].boxes) if results[0].boxes else 0} objects")
    
    return True

if __name__ == "__main__":
    # Run quick demo
    model_path = train_quick_demo()
    
    # Test the model
    test_demo_model(model_path)
    
    print("\n🎉 Demo training complete!")
    print("   • Created sample dataset")
    print("   • Trained for 3 epochs")
    print("   • Model saved and tested")
    print("\n📚 Next steps for production:")
    print("   1. Get real field photos from PM 35125285")
    print("   2. Label with infrastructure classes")
    print("   3. Train with transfer_learning.py")
    print("   4. Deploy with infrastructure_analyzer.py")
