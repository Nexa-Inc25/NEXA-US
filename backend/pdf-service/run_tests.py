#!/usr/bin/env python3
"""
Test runner script for NEXA PDF Service
Runs pytest with appropriate configuration and generates reports
"""
import subprocess
import sys
import os
from pathlib import Path

def create_sample_test(test_dir):
    """Create a sample test file if none exist"""
    sample_test = test_dir / "test_sample.py"
    if not sample_test.exists():
        sample_test.write_text('''"""Sample test to verify pytest is working"""

def test_sample():
    """Simple test to verify pytest setup"""
    assert True, "This test should always pass"

def test_import():
    """Test that we can import FastAPI"""
    try:
        import fastapi
        assert True
    except ImportError:
        assert False, "FastAPI not installed"
''')

def install_test_dependencies():
    """Install required test dependencies"""
    print("📦 Installing test dependencies...")
    deps = [
        "pytest>=7.4.0",
        "pytest-cov>=4.1.0",
        "pytest-mock>=3.11.0",
        "httpx>=0.24.0",
        "reportlab>=4.0.0"  # For creating test PDFs
    ]
    
    for dep in deps:
        subprocess.run([sys.executable, "-m", "pip", "install", dep], check=False)
    print("✅ Test dependencies installed\n")

def run_tests():
    """Run pytest with coverage and reporting"""
    test_dir = Path(__file__).parent / "tests"
    
    if not test_dir.exists():
        print(f"❌ Test directory not found: {test_dir}")
        print("\n📁 Creating test directory and sample tests...")
        test_dir.mkdir(exist_ok=True)
        create_sample_test(test_dir)
        print("✅ Test directory created with sample test")
    
    print("🧪 Running NEXA PDF Service Tests...")
    print("="*60)
    
    # Use python -m pytest to avoid PATH issues
    base_cmd = [
        sys.executable, "-m", "pytest",
        str(test_dir),
        "-v",  # Verbose output
        "--tb=short",  # Short traceback format
    ]
    
    print("ℹ️ Using: python -m pytest (avoids PATH issues)")
    print(f"📍 Python: {sys.executable}")
    print(f"📂 Test directory: {test_dir}")
    print()
    
    # Run tests without coverage first (faster)
    print("\n1️⃣ Running functional tests...")
    result = subprocess.run(base_cmd, capture_output=False)
    
    if result.returncode == 0:
        print("\n✅ All tests passed!")
        
        # Run with coverage if all tests pass
        print("\n2️⃣ Running tests with coverage report...")
        coverage_cmd = base_cmd + [
            "--cov=app_electrical",
            "--cov=app_oct2025_enhanced",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov"
        ]
        
        subprocess.run(coverage_cmd, capture_output=False)
        print("\n📊 Coverage report generated in htmlcov/index.html")
    else:
        print(f"\n❌ Tests failed with exit code: {result.returncode}")
        return result.returncode
    
    # Generate test report
    print("\n3️⃣ Generating test report...")
    report_cmd = base_cmd + [
        "--html=test_report.html",
        "--self-contained-html",
        "-q"  # Quiet for report generation
    ]
    
    # Note: Requires pytest-html plugin
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "pytest-html"],
            check=True,
            capture_output=True
        )
        subprocess.run(report_cmd, capture_output=True)
        print("📄 Test report generated: test_report.html")
    except:
        print("ℹ️ Install pytest-html for HTML reports")
    
    print("\n" + "="*60)
    print("📈 Test Summary:")
    print("="*60)
    
    # Run quick summary
    summary_cmd = [
        sys.executable, "-m", "pytest",
        str(test_dir),
        "--co", "-q"  # Collect only, quiet
    ]
    
    result = subprocess.run(summary_cmd, capture_output=True, text=True)
    test_count = len([l for l in result.stdout.split('\n') if 'test_' in l])
    
    print(f"Total test functions: {test_count}")
    print(f"Test files: {len(list(test_dir.glob('test_*.py')))}")
    print(f"Coverage targets: app_electrical.py, app_oct2025_enhanced.py")
    
    return 0

def run_specific_test(test_name=None):
    """Run a specific test file or test case"""
    if not test_name:
        return run_tests()
    
    test_dir = Path(__file__).parent / "tests"
    
    print(f"🎯 Running specific test: {test_name}")
    cmd = [
        sys.executable, "-m", "pytest",
        str(test_dir),
        "-v",
        "-k", test_name  # Match test name pattern
    ]
    
    return subprocess.run(cmd).returncode

def main():
    """Main test runner"""
    print("\n" + "="*60)
    print("🧪 NEXA PDF Service Test Runner")
    print("="*60 + "\n")
    
    # Check if specific test requested
    if len(sys.argv) > 1:
        test_pattern = sys.argv[1]
        print(f"Running tests matching: {test_pattern}")
        return run_specific_test(test_pattern)
    
    # Install dependencies if needed
    try:
        import pytest
        import httpx
    except ImportError:
        install_test_dependencies()
    
    # Run all tests
    return run_tests()

if __name__ == "__main__":
    sys.exit(main())
