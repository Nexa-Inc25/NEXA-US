#!/usr/bin/env python3
"""
Fix the unmatched ')' syntax error in pole_vision_detector.py
"""

def fix_syntax_error():
    file_path = 'pole_vision_detector.py'
    
    print("🔧 Reading pole_vision_detector.py...")
    
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    # Find and fix the problematic area around line 481
    fixed_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Look for the unmatched ')' comment
        if ')  # DISABLED' in line or ') # DISABLED' in line:
            print(f"Found problematic line at {i+1}: {line.strip()}")
            # Comment out this line too
            if not line.strip().startswith('#'):
                fixed_lines.append('#' + line)
                print(f"  → Commented out line {i+1}")
            else:
                fixed_lines.append(line)
        else:
            fixed_lines.append(line)
        
        i += 1
    
    # Write the fixed content
    print("💾 Writing fixed version...")
    with open(file_path, 'w') as f:
        f.writelines(fixed_lines)
    
    print("✅ Syntax error fixed!")
    print("\nNext steps:")
    print("  git add pole_vision_detector.py")
    print("  git commit -m 'Fix syntax error - comment out unmatched parenthesis'")
    print("  git push origin main")

if __name__ == "__main__":
    try:
        fix_syntax_error()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
