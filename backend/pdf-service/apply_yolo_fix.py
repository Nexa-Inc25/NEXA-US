"""
Apply YOLO compatibility fix to app_oct2025_enhanced.py
This script updates the import to use the fixed pole_vision_detector
"""
import os
import shutil

def apply_fix():
    """Apply the YOLO compatibility fix"""
    
    # Read the current app file
    app_file = 'app_oct2025_enhanced.py'
    backup_file = 'app_oct2025_enhanced.py.backup'
    
    print(f"Backing up {app_file} to {backup_file}")
    shutil.copy(app_file, backup_file)
    
    with open(app_file, 'r') as f:
        content = f.read()
    
    # Replace the import statement
    old_import = "from modules.pole_vision_detector import PoleVisionDetector"
    new_import = "from modules.pole_vision_detector_fixed import PoleVisionDetector"
    
    if old_import in content:
        content = content.replace(old_import, new_import)
        print(f"✅ Updated import to use fixed detector")
    else:
        print(f"⚠️ Import not found, may already be fixed")
    
    # Write back
    with open(app_file, 'w') as f:
        f.write(content)
    
    print(f"✅ Fix applied to {app_file}")
    
    # Create a symlink or copy for the modules directory
    modules_dir = 'modules'
    if os.path.exists(modules_dir):
        detector_file = os.path.join(modules_dir, 'pole_vision_detector.py')
        fixed_file = os.path.join(modules_dir, 'pole_vision_detector_fixed.py')
        
        if os.path.exists(fixed_file):
            # Backup original if exists
            if os.path.exists(detector_file):
                backup = detector_file + '.original'
                if not os.path.exists(backup):
                    shutil.copy(detector_file, backup)
                    print(f"✅ Backed up original detector to {backup}")
            
            # Copy fixed version over
            shutil.copy(fixed_file, detector_file)
            print(f"✅ Copied fixed detector to {detector_file}")
    
    print("\nFix completed! The app should now handle YOLO model version mismatches.")
    print("\nTo deploy:")
    print("1. Commit these changes")
    print("2. Push to your repository")
    print("3. Render will auto-deploy the fix")
    
    return True

if __name__ == '__main__':
    apply_fix()
