#!/usr/bin/env python3
"""
Quick verification script for Universal Standards setup
Checks that all files are in place and properly integrated
"""
import os
import sys
from pathlib import Path

def check_file(filepath, description):
    """Check if a file exists"""
    if Path(filepath).exists():
        size = Path(filepath).stat().st_size
        print(f"  ✅ {description} ({size:,} bytes)")
        return True
    else:
        print(f"  ❌ {description} - NOT FOUND")
        return False

def check_integration(filepath, search_string, description):
    """Check if code is integrated in a file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            if search_string in content:
                print(f"  ✅ {description}")
                return True
            else:
                print(f"  ❌ {description} - NOT INTEGRATED")
                return False
    except Exception as e:
        print(f"  ❌ {description} - ERROR: {e}")
        return False

def main():
    print("=" * 60)
    print("🔍 Universal Standards Engine Setup Verification")
    print("=" * 60)
    
    checks_passed = []
    
    print("\n📁 Checking Files:")
    checks_passed.append(
        check_file("modules/universal_standards.py", "Universal Standards module")
    )
    checks_passed.append(
        check_file("tests/test_universal.py", "Test script")
    )
    checks_passed.append(
        check_file("deploy_universal.ps1", "Deployment script")
    )
    checks_passed.append(
        check_file("app_oct2025_enhanced.py", "Main application")
    )
    
    print("\n🔧 Checking Integration:")
    checks_passed.append(
        check_integration(
            "app_oct2025_enhanced.py",
            "from modules.universal_standards import integrate_universal_endpoints",
            "Universal Standards import in main app"
        )
    )
    checks_passed.append(
        check_integration(
            "app_oct2025_enhanced.py",
            "Universal Standards endpoints registered",
            "Universal Standards endpoints registration"
        )
    )
    
    print("\n📊 Checking Module Content:")
    checks_passed.append(
        check_integration(
            "modules/universal_standards.py",
            "class UniversalStandardsEngine",
            "UniversalStandardsEngine class"
        )
    )
    checks_passed.append(
        check_integration(
            "modules/universal_standards.py",
            "def integrate_universal_endpoints",
            "Endpoint integration function"
        )
    )
    checks_passed.append(
        check_integration(
            "modules/universal_standards.py",
            "UTILITIES_DB",
            "Utilities database"
        )
    )
    
    # Summary
    print("\n" + "=" * 60)
    total = len(checks_passed)
    passed = sum(checks_passed)
    
    if passed == total:
        print("✅ All checks passed! ({}/{})".format(passed, total))
        print("\n🚀 Ready to deploy! Next steps:")
        print("   1. Test locally: python app_oct2025_enhanced.py")
        print("   2. Run tests: python tests\\test_universal.py")
        print("   3. Deploy: .\\deploy_universal.ps1")
    else:
        print("⚠️ Some checks failed ({}/{} passed)".format(passed, total))
        print("\n📋 Fix the issues above before deploying")
        return 1
    
    print("=" * 60)
    return 0

if __name__ == "__main__":
    sys.exit(main())
