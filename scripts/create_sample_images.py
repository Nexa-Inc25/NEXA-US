#!/usr/bin/env python3
"""
Create sample placeholder images for YOLO training demonstration
In production, you would use real utility pole photos
"""

import cv2
import numpy as np
import os
from pathlib import Path

def create_sample_pole_image(output_path, image_num, pole_type="wood"):
    """Create a sample utility pole image with basic shapes"""
    
    # Create blank image
    img = np.ones((640, 480, 3), np.uint8) * 255
    
    # Add background gradient
    for i in range(640):
        img[i, :] = [200 + i//12, 220 + i//20, 240]
    
    # Draw pole (vertical rectangle)
    pole_color = {
        "wood": (50, 100, 150),
        "steel": (100, 100, 100),
        "concrete": (150, 150, 150)
    }[pole_type]
    
    # Main pole
    pole_x = 200 + (image_num * 20) % 100
    cv2.rectangle(img, (pole_x, 100), (pole_x + 40, 600), pole_color, -1)
    
    # Crossarm
    cv2.rectangle(img, (pole_x - 60, 150), (pole_x + 100, 165), (100, 75, 50), -1)
    
    # Insulators
    for i in range(3):
        x = pole_x - 40 + i * 40
        cv2.circle(img, (x, 157), 8, (50, 50, 200), -1)
    
    # Power lines
    for i in range(3):
        y = 140 + i * 15
        cv2.line(img, (0, y), (480, y + 10), (50, 50, 50), 2)
    
    # Add some noise for realism
    noise = np.random.normal(0, 10, img.shape).astype(np.uint8)
    img = cv2.add(img, noise)
    
    # Add text
    cv2.putText(img, f"Sample {image_num}", (10, 30), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (100, 100, 100), 2)
    
    # Save image
    cv2.imwrite(str(output_path), img)
    
    # Create corresponding YOLO label
    label_path = output_path.with_suffix('.txt')
    with open(label_path, 'w') as f:
        # Pole annotation (class 0, center_x, center_y, width, height)
        cx = (pole_x + 20) / 480  # Normalized center x
        cy = 350 / 640  # Normalized center y
        w = 40 / 480  # Normalized width
        h = 500 / 640  # Normalized height
        f.write(f"0 {cx:.4f} {cy:.4f} {w:.4f} {h:.4f}\n")
        
        # Crossarm annotation (class 3)
        cx_arm = (pole_x + 20) / 480
        cy_arm = 157 / 640
        w_arm = 160 / 480
        h_arm = 15 / 640
        f.write(f"3 {cx_arm:.4f} {cy_arm:.4f} {w_arm:.4f} {h_arm:.4f}\n")
    
    return output_path

def main():
    output_dir = Path("sample_pole_images")
    output_dir.mkdir(exist_ok=True)
    
    print("🎨 Creating sample training images...")
    
    # Create 20 sample images with variations
    pole_types = ["wood", "steel", "concrete"]
    for i in range(20):
        pole_type = pole_types[i % 3]
        img_path = output_dir / f"pole_{i+1:03d}.jpg"
        create_sample_pole_image(img_path, i, pole_type)
        print(f"  ✅ Created {img_path.name}")
    
    print(f"\n✅ Created 20 sample images in {output_dir}/")
    print("\n📝 Note: These are placeholder images for testing.")
    print("   For production, use real utility pole photos!")

if __name__ == "__main__":
    main()
