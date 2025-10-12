#!/usr/bin/env python3
"""
Prepare YOLO Dataset for Utility Pole Detection
Creates proper folder structure and converts annotations
"""

import os
import shutil
import json
import random
from pathlib import Path
from typing import List, Dict, Tuple
import cv2
import numpy as np
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatasetPreparer:
    """
    Prepare utility pole images for YOLO training
    """
    
    # PG&E utility equipment classes
    CLASSES = {
        0: 'pole_type1',    # Wood pole
        1: 'pole_type2',    # Steel pole  
        2: 'pole_type3',    # Concrete pole
        3: 'crossarm',      # Crossarm/cross-brace
        4: 'insulator',     # Insulator
        5: 'transformer',   # Transformer
        6: 'guy_wire',      # Guy wire
        7: 'ground_wire',   # Grounding
        8: 'infraction',    # Safety/compliance issue
        9: 'vegetation'     # Vegetation encroachment
    }
    
    def __init__(self, source_dir: str, output_dir: str = 'C:/datasets/utility_poles'):
        """
        Initialize dataset preparer
        
        Args:
            source_dir: Directory with raw images and annotations
            output_dir: Output directory for YOLO dataset
        """
        self.source_dir = Path(source_dir)
        self.output_dir = Path(output_dir)
        self.train_split = 0.8
        self.val_split = 0.15
        self.test_split = 0.05
    
    def create_folder_structure(self):
        """Create YOLO dataset folder structure"""
        folders = [
            'images/train',
            'images/val', 
            'images/test',
            'labels/train',
            'labels/val',
            'labels/test'
        ]
        
        for folder in folders:
            folder_path = self.output_dir / folder
            folder_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"✅ Created {folder_path}")
    
    def convert_coco_to_yolo(self, coco_json_path: str):
        """
        Convert COCO format annotations to YOLO format
        
        Args:
            coco_json_path: Path to COCO annotations JSON
        """
        with open(coco_json_path, 'r') as f:
            coco = json.load(f)
        
        # Create image id to filename mapping
        img_map = {img['id']: img for img in coco['images']}
        
        # Group annotations by image
        img_annotations = {}
        for ann in coco['annotations']:
            img_id = ann['image_id']
            if img_id not in img_annotations:
                img_annotations[img_id] = []
            img_annotations[img_id].append(ann)
        
        # Convert each image's annotations
        for img_id, anns in img_annotations.items():
            if img_id not in img_map:
                continue
            
            img_info = img_map[img_id]
            img_width = img_info['width']
            img_height = img_info['height']
            img_name = Path(img_info['file_name']).stem
            
            # Convert annotations to YOLO format
            yolo_lines = []
            for ann in anns:
                # COCO bbox: [x, y, width, height]
                x, y, w, h = ann['bbox']
                
                # Convert to YOLO format (normalized center coordinates)
                cx = (x + w/2) / img_width
                cy = (y + h/2) / img_height
                norm_w = w / img_width
                norm_h = h / img_height
                
                # Map category to our classes
                category = ann['category_id']
                if category < len(self.CLASSES):
                    yolo_lines.append(f"{category} {cx} {cy} {norm_w} {norm_h}")
            
            # Save YOLO label file
            if yolo_lines:
                label_path = self.source_dir / f"{img_name}.txt"
                with open(label_path, 'w') as f:
                    f.write('\n'.join(yolo_lines))
    
    def create_synthetic_annotations(self, image_dir: str):
        """
        Create synthetic annotations for images without labels
        Uses basic CV to detect poles/crossarms
        """
        image_paths = list(Path(image_dir).glob('*.jpg'))
        
        for img_path in image_paths:
            label_path = img_path.with_suffix('.txt')
            
            # Skip if label already exists
            if label_path.exists():
                continue
            
            # Load image
            img = cv2.imread(str(img_path))
            if img is None:
                continue
            
            h, w = img.shape[:2]
            
            # Simple pole detection using vertical edge detection
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 50, 150)
            
            # Find vertical lines (potential poles)
            lines = cv2.HoughLinesP(edges, 1, np.pi/180, 100, 
                                   minLineLength=h//4, maxLineGap=10)
            
            annotations = []
            if lines is not None:
                for line in lines[:5]:  # Max 5 detections
                    x1, y1, x2, y2 = line[0]
                    
                    # Check if line is mostly vertical
                    angle = abs(np.arctan2(y2-y1, x2-x1) * 180 / np.pi)
                    if 70 < angle < 110:  # Vertical-ish
                        # Create bounding box around line
                        cx = (x1 + x2) / 2 / w
                        cy = (y1 + y2) / 2 / h
                        box_w = 0.1  # 10% of image width
                        box_h = abs(y2 - y1) / h
                        
                        # Assume pole_type1 (wood pole)
                        annotations.append(f"0 {cx:.4f} {cy:.4f} {box_w:.4f} {box_h:.4f}")
            
            # Save synthetic annotations
            if annotations:
                with open(label_path, 'w') as f:
                    f.write('\n'.join(annotations))
                logger.info(f"📝 Created synthetic annotation for {img_path.name}")
    
    def augment_dataset(self, img_path: Path, label_path: Path, num_augmentations: int = 3):
        """
        Augment image and annotations for more training data
        """
        img = cv2.imread(str(img_path))
        if img is None:
            return []
        
        augmented = []
        
        # Read original labels
        with open(label_path, 'r') as f:
            labels = f.readlines()
        
        for i in range(num_augmentations):
            aug_img = img.copy()
            aug_labels = labels.copy()
            
            # Random augmentation
            aug_type = random.choice(['brightness', 'rotation', 'flip', 'noise'])
            
            if aug_type == 'brightness':
                # Adjust brightness
                value = random.randint(-50, 50)
                aug_img = cv2.add(aug_img, value)
            
            elif aug_type == 'rotation':
                # Small rotation
                angle = random.uniform(-15, 15)
                center = (img.shape[1]//2, img.shape[0]//2)
                M = cv2.getRotationMatrix2D(center, angle, 1.0)
                aug_img = cv2.warpAffine(img, M, (img.shape[1], img.shape[0]))
            
            elif aug_type == 'flip':
                # Horizontal flip
                aug_img = cv2.flip(img, 1)
                # Update labels for flip
                aug_labels = []
                for label in labels:
                    parts = label.strip().split()
                    if len(parts) == 5:
                        cls, cx, cy, w, h = parts
                        cx = str(1 - float(cx))  # Mirror x coordinate
                        aug_labels.append(f"{cls} {cx} {cy} {w} {h}\n")
            
            elif aug_type == 'noise':
                # Add noise
                noise = np.random.normal(0, 25, img.shape).astype(np.uint8)
                aug_img = cv2.add(img, noise)
            
            # Save augmented image and labels
            aug_name = f"{img_path.stem}_aug{i}{img_path.suffix}"
            augmented.append((aug_img, aug_labels, aug_name))
        
        return augmented
    
    def split_dataset(self):
        """Split images into train/val/test sets"""
        # Get all image files
        image_files = list(self.source_dir.glob('*.jpg'))
        image_files.extend(list(self.source_dir.glob('*.png')))
        
        # Filter to only images with labels
        valid_images = []
        for img_path in image_files:
            label_path = img_path.with_suffix('.txt')
            if label_path.exists():
                valid_images.append(img_path)
        
        logger.info(f"📊 Found {len(valid_images)} images with labels")
        
        # Shuffle and split
        random.shuffle(valid_images)
        n = len(valid_images)
        train_end = int(n * self.train_split)
        val_end = int(n * (self.train_split + self.val_split))
        
        splits = {
            'train': valid_images[:train_end],
            'val': valid_images[train_end:val_end],
            'test': valid_images[val_end:]
        }
        
        # Copy files to respective folders
        for split_name, images in splits.items():
            for img_path in images:
                # Copy image
                img_dest = self.output_dir / 'images' / split_name / img_path.name
                shutil.copy(img_path, img_dest)
                
                # Copy label
                label_path = img_path.with_suffix('.txt')
                label_dest = self.output_dir / 'labels' / split_name / f"{img_path.stem}.txt"
                if label_path.exists():
                    shutil.copy(label_path, label_dest)
            
            logger.info(f"✅ {split_name}: {len(images)} images")
    
    def create_data_yaml(self):
        """Create data.yaml configuration file"""
        yaml_content = f"""
# NEXA Utility Pole Detection Dataset
path: {self.output_dir}
train: images/train
val: images/val
test: images/test

# Number of classes
nc: {len(self.CLASSES)}

# Class names
names: {list(self.CLASSES.values())}

# Training notes
# Optimized for PG&E utility infrastructure:
# - Multiple pole types (wood, steel, concrete)
# - Crossarms and insulators
# - Infraction detection for safety compliance
# - Vegetation encroachment detection
"""
        
        yaml_path = self.output_dir / 'data.yaml'
        with open(yaml_path, 'w') as f:
            f.write(yaml_content.strip())
        
        logger.info(f"✅ Created data.yaml")
    
    def prepare_dataset(self):
        """Main pipeline to prepare dataset"""
        logger.info("🚀 Starting dataset preparation...")
        
        # Create folder structure
        self.create_folder_structure()
        
        # Check for COCO annotations
        coco_json = self.source_dir / 'annotations.json'
        if coco_json.exists():
            logger.info("📋 Converting COCO annotations...")
            self.convert_coco_to_yolo(str(coco_json))
        
        # Create synthetic annotations for unlabeled images
        logger.info("🤖 Creating synthetic annotations...")
        self.create_synthetic_annotations(str(self.source_dir))
        
        # Split dataset
        logger.info("📂 Splitting dataset...")
        self.split_dataset()
        
        # Create data.yaml
        self.create_data_yaml()
        
        logger.info(f"""
✅ Dataset preparation complete!
━━━━━━━━━━━━━━━━━━━━━━━━━━━
📁 Output: {self.output_dir}
📊 Classes: {len(self.CLASSES)}
🏷️ Labels: YOLO format

Ready for training with:
python train_yolo_local.py --dataset {self.output_dir}
━━━━━━━━━━━━━━━━━━━━━━━━━━━
        """)

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Prepare YOLO dataset for pole detection')
    parser.add_argument('--source', type=str, required=True,
                       help='Source directory with images')
    parser.add_argument('--output', type=str, default='C:/datasets/utility_poles',
                       help='Output directory for YOLO dataset')
    parser.add_argument('--augment', action='store_true',
                       help='Apply data augmentation')
    
    args = parser.parse_args()
    
    preparer = DatasetPreparer(args.source, args.output)
    preparer.prepare_dataset()

if __name__ == '__main__':
    main()
