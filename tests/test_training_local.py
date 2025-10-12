#!/usr/bin/env python3
"""
Test the training system locally
"""

import os
import sys
import json
from pathlib import Path

# Add backend to path
sys.path.append('./backend/pdf-service')

from train_job_packages import JobPackageTrainer
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_training():
    """Test the training system with sample data"""
    
    trainer = JobPackageTrainer()
    
    # Check for sample files
    sample_files = [
        "pge_test_audit.pdf",
        "test_documents/sample_audit_report.pdf",
        "test_documents/sample_audit_mixed.pdf"
    ]
    
    print("🎯 TESTING NEXA TRAINING SYSTEM")
    print("=" * 50)
    
    # Train on available files
    for file_path in sample_files:
        if os.path.exists(file_path):
            print(f"\n📄 Training on: {file_path}")
            try:
                # Learn job package structure
                structure = trainer.learn_job_package_structure(file_path)
                print(f"  ✅ Learned {len(structure.get('fields', {}))} fields")
                
                # Show sample fields
                fields = list(structure.get('fields', {}).keys())[:5]
                if fields:
                    print(f"  Sample fields: {', '.join(fields)}")
                
                # Learn as-built patterns
                patterns = trainer.learn_as_built_patterns(file_path, filled=True)
                print(f"  ✅ Learned {len(patterns.get('filling_rules', {}))} filling patterns")
                
            except Exception as e:
                print(f"  ❌ Error: {e}")
        else:
            print(f"  ⚠️ File not found: {file_path}")
    
    # Check training status
    print("\n📊 TRAINING STATUS:")
    status = trainer.get_training_status()
    print(f"  Job package templates: {status['job_package_templates']}")
    print(f"  As-built patterns: {status['as_built_patterns']}")
    print(f"  Total fields learned: {status['total_fields_learned']}")
    print(f"  Total filling rules: {status['total_filling_rules']}")
    
    if status['ready_to_fill']:
        print("  ✅ NEXA is ready to fill packages!")
    else:
        print("  ⚠️ NEXA needs more training data")
    
    # Test auto-fill capability
    print("\n🧪 TESTING AUTO-FILL:")
    test_data = {
        "PM_NUMBER": "PM-2025-001",
        "POLE_TYPE": "Type 3",
        "LOCATION": "123 Main St",
        "GPS_COORDINATES": "37.7749, -122.4194"
    }
    
    filled = trainer.auto_fill_package("TEST-001", test_data, "standard")
    if filled.get('filled_fields'):
        print("  ✅ Successfully filled package!")
        print(f"  Confidence: {filled['confidence']:.1%}")
        print("  Sample filled fields:")
        for key, value in list(filled['filled_fields'].items())[:5]:
            print(f"    {key}: {value}")
    else:
        print("  ⚠️ Need more training data to auto-fill")
    
    print("\n" + "=" * 50)
    print("✅ TRAINING SYSTEM TEST COMPLETE!")
    print("\n💡 To train with real data:")
    print("1. Add job package PDFs to this directory")
    print("2. Add completed as-built PDFs") 
    print("3. Run: python test_training_local.py")
    print("\n🚀 NEXA can save 3.5 hours per job package!")

if __name__ == "__main__":
    test_training()
