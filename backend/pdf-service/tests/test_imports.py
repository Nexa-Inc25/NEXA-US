#!/usr/bin/env python3
"""Test imports for transformers"""

print("Testing transformers imports...")

try:
    from transformers import __version__
    print(f"✅ Transformers version: {__version__}")
except ImportError as e:
    print(f"❌ Cannot import transformers: {e}")

try:
    from transformers.trainer import Trainer
    print("✅ Trainer imported from transformers.trainer")
except ImportError as e:
    print(f"❌ Cannot import Trainer: {e}")

try:
    from transformers import AutoTokenizer, AutoModelForTokenClassification
    print("✅ AutoTokenizer and AutoModelForTokenClassification imported")
except ImportError as e:
    print(f"❌ Cannot import Auto classes: {e}")

try:
    from transformers import TrainingArguments
    print("✅ TrainingArguments imported")
except ImportError as e:
    print(f"❌ Cannot import TrainingArguments: {e}")

try:
    from transformers import DataCollatorForTokenClassification
    print("✅ DataCollatorForTokenClassification imported")
except ImportError as e:
    print(f"❌ Cannot import DataCollator: {e}")

print("\nChecking other dependencies...")

try:
    import torch
    print(f"✅ PyTorch version: {torch.__version__}")
except ImportError as e:
    print(f"❌ Cannot import torch: {e}")

try:
    import datasets
    print(f"✅ Datasets imported")
except ImportError as e:
    print(f"❌ Cannot import datasets: {e}")

try:
    import peft
    print(f"✅ PEFT imported")
except ImportError as e:
    print(f"❌ Cannot import peft: {e}")

try:
    import evaluate
    print(f"✅ Evaluate imported")
except ImportError as e:
    print(f"❌ Cannot import evaluate: {e}")

print("\nAll tests complete.")
