#!/usr/bin/env python3
"""
Safe test runner that avoids memory-intensive tests by default
Provides options to run different test suites based on system resources
"""
import subprocess
import sys
import psutil
import os
from pathlib import Path

def get_system_info():
    """Get system memory and CPU info"""
    memory = psutil.virtual_memory()
    return {
        "total_memory_gb": memory.total / (1024**3),
        "available_memory_gb": memory.available / (1024**3),
        "cpu_count": psutil.cpu_count(),
        "memory_percent": memory.percent
    }

def run_test_suite(test_type="safe"):
    """Run different test suites based on type"""
    base_cmd = [sys.executable, "-m", "pytest", "tests/", "-v"]
    
    if test_type == "safe":
        # Run tests excluding memory-intensive ones
        cmd = base_cmd + [
            "-m", "not memory_intensive and not integration",
            "--tb=short"
        ]
        print("🧪 Running SAFE test suite (excludes large file tests)")
        
    elif test_type == "unit":
        # Run only unit tests
        cmd = base_cmd + [
            "-m", "unit or not (integration or memory_intensive)",
            "--tb=line"
        ]
        print("⚡ Running UNIT tests only (fastest)")
        
    elif test_type == "integration":
        # Run integration tests (requires more resources)
        system_info = get_system_info()
        if system_info["available_memory_gb"] < 2.0:
            print("⚠️ Warning: Low memory detected. Integration tests may fail.")
            print(f"Available: {system_info['available_memory_gb']:.1f}GB")
            
        cmd = base_cmd + [
            "-m", "integration",
            "--tb=short",
            "-x"  # Stop on first failure
        ]
        print("🔧 Running INTEGRATION tests (may use more memory)")
        
    elif test_type == "smoke":
        # Run smoke tests (basic functionality)
        cmd = base_cmd + [
            "tests/test_electrical.py::TestBasicEndpoints",
            "tests/test_oct2025_enhanced.py::TestBasicEndpoints",
            "--tb=line"
        ]
        print("💨 Running SMOKE tests (basic endpoints only)")
        
    elif test_type == "all":
        # Run all tests with memory monitoring
        system_info = get_system_info()
        print(f"💻 System: {system_info['available_memory_gb']:.1f}GB available")
        
        if system_info["available_memory_gb"] < 4.0:
            print("⚠️ Warning: Running all tests with limited memory may cause issues")
            response = input("Continue? (y/N): ")
            if response.lower() != 'y':
                return 1
                
        cmd = base_cmd + ["--tb=short"]
        print("🚀 Running ALL tests (including memory-intensive)")
        
    else:
        print(f"❌ Unknown test type: {test_type}")
        return 1
    
    print(f"Command: {' '.join(cmd)}")
    print("=" * 60)
    
    # Run the tests
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        print("\n✅ Tests completed successfully!")
    else:
        print(f"\n❌ Tests failed with exit code: {result.returncode}")
        
        if test_type == "all":
            print("\n💡 Try running with 'safe' mode to avoid memory issues:")
            print("   python run_safe_tests.py safe")
    
    return result.returncode

def main():
    """Main test runner with command line options"""
    print("🧪 NEXA Safe Test Runner")
    print("=" * 60)
    
    # Get system info
    system_info = get_system_info()
    print(f"💻 System Info:")
    print(f"   Memory: {system_info['available_memory_gb']:.1f}GB available / {system_info['total_memory_gb']:.1f}GB total")
    print(f"   CPU: {system_info['cpu_count']} cores")
    print(f"   Memory usage: {system_info['memory_percent']:.1f}%")
    print()
    
    # Determine test type
    if len(sys.argv) > 1:
        test_type = sys.argv[1].lower()
    else:
        # Auto-select based on available memory
        if system_info["available_memory_gb"] < 2.0:
            test_type = "unit"
            print("🔍 Auto-selected: UNIT tests (low memory detected)")
        elif system_info["available_memory_gb"] < 4.0:
            test_type = "safe"
            print("🔍 Auto-selected: SAFE tests (moderate memory)")
        else:
            test_type = "safe"
            print("🔍 Auto-selected: SAFE tests (recommended)")
        print()
    
    # Show available options
    if test_type not in ["safe", "unit", "integration", "smoke", "all"]:
        print("Available test types:")
        print("  safe        - Exclude memory-intensive tests (recommended)")
        print("  unit        - Unit tests only (fastest)")
        print("  smoke       - Basic endpoint tests only")
        print("  integration - Integration tests (requires more memory)")
        print("  all         - All tests including large file tests")
        print()
        print("Usage: python run_safe_tests.py [test_type]")
        return 1
    
    # Check if test directory exists
    test_dir = Path("tests")
    if not test_dir.exists():
        print("❌ Tests directory not found!")
        print("Make sure you're running from the pdf-service directory")
        return 1
    
    # Run the selected test suite
    return run_test_suite(test_type)

if __name__ == "__main__":
    sys.exit(main())
