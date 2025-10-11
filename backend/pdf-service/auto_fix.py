#!/usr/bin/env python3
"""
Automatic fix for indentation error in pole_vision_detector.py
"""

import re

def fix_indentation():
    file_path = 'pole_vision_detector.py'
    
    print("🔧 Reading pole_vision_detector.py...")
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Find and replace the broken training section
    # Look for the specific pattern around line 128-138
    pattern = r'''                logger\.info\("Skipping training to save memory.*?\n.*?model = YOLO\("yolov8n\.pt"\).*?\n#\s+model\.train\(\n\s+data=f"\{dataset\.location\}/data\.yaml",\n\s+epochs=10,\n\s+imgsz=640,\n\s+device='cpu',\n\s+batch=16,\n\s+project='/data',\n\s+name='roboflow_pole'\n\s+\)'''
    
    replacement = '''                logger.info("Roboflow dataset downloaded - training disabled to save memory")
                logger.info("Upload trained model to /data/yolo_pole.pt to use it")
                
                # Check if pre-trained model exists
                trained_model_path = '/data/yolo_pole.pt'
                if os.path.exists(trained_model_path):
                    logger.info(f"Loading trained model from {trained_model_path}")
                    self.model = YOLO(trained_model_path)
                else:
                    logger.info("Using base YOLOv8 model until trained model is uploaded")
                
                # Training disabled to save memory (requires >2GB RAM)'''
    
    # Try the replacement
    new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    
    if new_content == content:
        print("⚠️  Pattern not found, trying simpler fix...")
        # Simpler approach: just comment out the problematic lines
        lines = content.split('\n')
        for i, line in enumerate(lines):
            # Find the line with the wrong indentation
            if 'data=f"{dataset.location}/data.yaml"' in line and not line.strip().startswith('#'):
                print(f"Found problematic line at {i+1}: {line[:50]}...")
                # Comment out this and next few lines
                for j in range(i, min(i+8, len(lines))):
                    if not lines[j].strip().startswith('#') and lines[j].strip():
                        lines[j] = '#' + lines[j]
                new_content = '\n'.join(lines)
                break
    
    # Write the fixed content
    print("💾 Writing fixed version...")
    with open(file_path, 'w') as f:
        f.write(new_content)
    
    print("✅ Fixed!")
    print("\nNext steps:")
    print("  git add pole_vision_detector.py")
    print("  git commit -m 'Fix indentation error'")
    print("  git push origin main")

if __name__ == "__main__":
    try:
        fix_indentation()
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nPlease fix manually using EXACT_FIX.md")
