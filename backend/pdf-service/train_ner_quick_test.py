#!/usr/bin/env python3
"""
Quick test training with fixed data - 5 epochs only
"""

import os
import sys

# Modify the config for quick testing
sys.path.insert(0, os.path.dirname(__file__))

# Import and modify the training script
from train_ner_deep import *

# Override config for quick test
Config.NUM_EPOCHS = 5  # Just 5 epochs for testing
Config.MODEL_DIR = "./fine_tuned_ner_test"  # Different output dir

if __name__ == "__main__":
    print("="*60)
    print("QUICK NER TRAINING TEST - 5 EPOCHS")
    print("Testing with fixed label indices")
    print("="*60)
    
    # Run training
    results = train_deep_ner()
    
    # Check if it's learning
    if results.get('eval_f1', 0) > 0.3:
        print("\n✅ Model is learning! Fixed data works.")
        print(f"F1 after 5 epochs: {results.get('eval_f1', 0):.4f}")
        print("\nYou can now run full 50-epoch training with:")
        print("  python train_ner_deep.py")
    else:
        print("\n❌ Model still not learning properly.")
        print(f"F1 after 5 epochs: {results.get('eval_f1', 0):.4f}")
        print("Need to investigate further.")
