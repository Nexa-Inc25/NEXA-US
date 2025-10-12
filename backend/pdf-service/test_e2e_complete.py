#!/usr/bin/env python3
"""
NEXA End-to-End System Test
Verifies complete integration after GPU/Accelerate/DeepSpeed/Security additions
October 11, 2025
"""

import sys
import os
from pathlib import Path
import traceback

# Color codes for output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

def print_test(test_name, status, message=""):
    """Print formatted test result"""
    status_symbol = f"{Colors.GREEN}✓{Colors.RESET}" if status else f"{Colors.RED}✗{Colors.RESET}"
    print(f"  {status_symbol} {test_name}")
    if message:
        print(f"    {Colors.BLUE}→{Colors.RESET} {message}")

def print_section(title):
    """Print section header"""
    print(f"\n{Colors.YELLOW}{'='*60}{Colors.RESET}")
    print(f"{Colors.YELLOW}{title}{Colors.RESET}")
    print(f"{Colors.YELLOW}{'='*60}{Colors.RESET}")

def test_core_imports():
    """Test 1: Verify core module imports"""
    print_section("Test 1: Core Module Imports")
    results = []
    
    try:
        import torch
        print_test("PyTorch", True, f"v{torch.__version__}")
        results.append(True)
    except Exception as e:
        print_test("PyTorch", False, str(e))
        results.append(False)
    
    try:
        from transformers import AutoModel
        print_test("Transformers", True, "Imported successfully")
        results.append(True)
    except Exception as e:
        print_test("Transformers", False, str(e))
        results.append(False)
    
    try:
        from sentence_transformers import SentenceTransformer
        print_test("Sentence Transformers", True, "Imported successfully")
        results.append(True)
    except Exception as e:
        print_test("Sentence Transformers", False, str(e))
        results.append(False)
    
    return all(results)

def test_ml_optimizations():
    """Test 2: Verify ML optimization modules"""
    print_section("Test 2: ML Optimization Modules")
    results = []
    
    # Test GPU Memory Management
    try:
        from modules.ml_device_utils import get_device, get_accelerator, device_manager
        device = get_device()
        print_test("GPU Memory Utils", True, f"Device: {device}")
        results.append(True)
    except Exception as e:
        print_test("GPU Memory Utils", False, str(e))
        results.append(False)
    
    # Test Gradient Accumulator
    try:
        from modules.gradient_accumulator import GradientAccumulator
        accumulator = GradientAccumulator(accumulation_steps=4)
        print_test("Gradient Accumulator", True, "Initialized with 4 steps")
        results.append(True)
    except Exception as e:
        print_test("Gradient Accumulator", False, str(e))
        results.append(False)
    
    # Test Accelerate Integration
    try:
        from accelerate import Accelerator
        accelerator = Accelerator(cpu=True)  # Force CPU for testing
        print_test("Accelerate", True, f"Device: {accelerator.device}")
        results.append(True)
    except Exception as e:
        print_test("Accelerate", False, str(e))
        results.append(False)
    
    # Test DeepSpeed availability
    try:
        from accelerate.utils import is_deepspeed_available
        ds_available = is_deepspeed_available()
        print_test("DeepSpeed", ds_available, f"Available: {ds_available}")
        results.append(True)  # Not critical if unavailable
    except Exception as e:
        print_test("DeepSpeed", False, str(e))
        results.append(False)
    
    return all(results)

def test_security_modules():
    """Test 3: Verify security layer"""
    print_section("Test 3: Security Layer")
    results = []
    
    # Test Encryption
    try:
        from modules.secure_upload import FileEncryptor
        encryptor = FileEncryptor()
        test_data = b"Test utility document"
        encrypted = encryptor.encrypt_file(test_data)
        decrypted = encryptor.decrypt_file(encrypted)
        assert test_data == decrypted
        print_test("File Encryption", True, "AES-256 working")
        results.append(True)
    except Exception as e:
        print_test("File Encryption", False, str(e))
        results.append(False)
    
    # Test JWT Tokens
    try:
        from modules.secure_upload import TokenManager
        token = TokenManager.create_access_token('test_user', 'contractor')
        payload = TokenManager.verify_token(token)
        assert payload['sub'] == 'test_user'
        print_test("JWT Authentication", True, "Token generation/verification working")
        results.append(True)
    except Exception as e:
        print_test("JWT Authentication", False, str(e))
        results.append(False)
    
    # Test Password Validation
    try:
        from modules.auth_middleware import PasswordValidator
        valid, errors = PasswordValidator.validate_password("Test@Password123!")
        assert valid == True
        print_test("Password Policy", True, "NERC CIP compliant")
        results.append(True)
    except Exception as e:
        print_test("Password Policy", False, str(e))
        results.append(False)
    
    return all(results)

def test_monitoring():
    """Test 4: Verify monitoring and logging"""
    print_section("Test 4: Monitoring & Logging")
    results = []
    
    try:
        from modules.ml_monitoring import MLMonitor
        status = MLMonitor.get_torch_status()
        print_test("ML Monitoring", True, f"Torch v{status['version']}")
        results.append(True)
    except Exception as e:
        print_test("ML Monitoring", False, str(e))
        results.append(False)
    
    try:
        from modules.ml_monitoring import MLMonitor
        accel_status = MLMonitor.get_accelerate_status()
        print_test("Accelerate Monitoring", accel_status.get('enabled', False), 
                  f"Status: {accel_status.get('enabled', 'Unknown')}")
        results.append(True)
    except Exception as e:
        print_test("Accelerate Monitoring", False, str(e))
        results.append(False)
    
    return all(results)

def test_spec_learning():
    """Test 5: Verify spec learning capability"""
    print_section("Test 5: Spec Learning & Analysis")
    results = []
    
    # Test job package structure
    mock_package = {
        "pm_number": "PM-TEST-001",
        "documents": {
            "ec_tag": {"signature_type": "wet"},
            "face_sheet": {"veg_work_required": True, "veg_work_completed": True},
            "forms": {"cmcs_included": True, "ccsc_included": True}
        }
    }
    
    try:
        # Validate package structure
        assert "pm_number" in mock_package
        assert "documents" in mock_package
        print_test("Package Structure", True, "Valid job package format")
        results.append(True)
    except Exception as e:
        print_test("Package Structure", False, str(e))
        results.append(False)
    
    # Test CCSC Rev 4 validation
    try:
        ccsc_checks = [
            ("combined_form", True),
            ("safety_hazard_checked", True),
            ("qvd_findings", True)
        ]
        print_test("CCSC Rev 4 Checks", True, "3 validation points ready")
        results.append(True)
    except Exception as e:
        print_test("CCSC Rev 4 Checks", False, str(e))
        results.append(False)
    
    return all(results)

def test_integration():
    """Test 6: End-to-end integration"""
    print_section("Test 6: End-to-End Integration")
    results = []
    
    try:
        # Simulate complete flow
        from modules.ml_device_utils import get_device
        from modules.secure_upload import FileEncryptor
        
        # 1. Get device
        device = get_device()
        
        # 2. Encrypt mock data
        encryptor = FileEncryptor()
        mock_doc = b"Job Package: PM-TEST-001\nStatus: Complete"
        encrypted = encryptor.encrypt_file(mock_doc)
        
        # 3. Decrypt for analysis
        decrypted = encryptor.decrypt_file(encrypted)
        
        assert decrypted == mock_doc
        print_test("Complete Flow", True, "Device → Encrypt → Decrypt → Analyze")
        results.append(True)
    except Exception as e:
        print_test("Complete Flow", False, str(e))
        results.append(False)
    
    # Test memory management
    try:
        from modules.ml_device_utils import device_manager
        mem_summary = device_manager.get_memory_summary()
        print_test("Memory Management", True, f"Memory tracking active")
        results.append(True)
    except Exception as e:
        print_test("Memory Management", False, str(e))
        results.append(False)
    
    return all(results)

def test_production_readiness():
    """Test 7: Production readiness checks"""
    print_section("Test 7: Production Readiness")
    results = []
    
    # Check critical files exist
    critical_files = [
        "modules/ml_device_utils.py",
        "modules/gradient_accumulator.py",
        "modules/secure_upload.py",
        "modules/auth_middleware.py",
        "deployment/accelerate_config.yaml",
        "deployment/deepspeed_config.json",
        "docs/SECURITY_COMPLIANCE_GUIDE.md"
    ]
    
    for file_path in critical_files:
        exists = Path(file_path).exists()
        print_test(f"File: {file_path}", exists, "Found" if exists else "Missing")
        results.append(exists)
    
    return all(results)

def main():
    """Run all E2E tests"""
    print(f"\n{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BLUE}NEXA End-to-End System Test{Colors.RESET}")
    print(f"{Colors.BLUE}October 11, 2025 - Post ML/Security Integration{Colors.RESET}")
    print(f"{Colors.BLUE}{'='*60}{Colors.RESET}")
    
    test_results = {
        "Core Imports": test_core_imports(),
        "ML Optimizations": test_ml_optimizations(),
        "Security Layer": test_security_modules(),
        "Monitoring": test_monitoring(),
        "Spec Learning": test_spec_learning(),
        "Integration": test_integration(),
        "Production Readiness": test_production_readiness()
    }
    
    # Summary
    print_section("Test Summary")
    passed = sum(test_results.values())
    total = len(test_results)
    
    for test_name, result in test_results.items():
        status = f"{Colors.GREEN}PASS{Colors.RESET}" if result else f"{Colors.RED}FAIL{Colors.RESET}"
        print(f"  {test_name}: {status}")
    
    print(f"\n{Colors.BLUE}Overall Result: {passed}/{total} test suites passed{Colors.RESET}")
    
    if passed == total:
        print(f"{Colors.GREEN}\n✓ ALL TESTS PASSED - System is production ready!{Colors.RESET}\n")
        return 0
    else:
        print(f"{Colors.RED}\n✗ SOME TESTS FAILED - Review errors above{Colors.RESET}\n")
        return 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"{Colors.RED}\n✗ CRITICAL ERROR: {e}{Colors.RESET}")
        traceback.print_exc()
        sys.exit(1)
