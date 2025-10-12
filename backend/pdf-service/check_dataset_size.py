#!/usr/bin/env python3
"""
Check the actual size of the training dataset
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from train_ner_deep import create_comprehensive_dataset

# Create the dataset
dataset = create_comprehensive_dataset()

print(f"Total training examples: {len(dataset)}")
print(f"Total tokens: {sum(len(ex['tokens']) for ex in dataset)}")

# Count label distribution
from collections import Counter
all_labels = []
for ex in dataset:
    all_labels.extend(ex['ner_tags'])

label_counts = Counter(all_labels)
print(f"\nLabel distribution:")
for label_id, count in sorted(label_counts.items()):
    print(f"  Label {label_id}: {count} occurrences")

# Check if labels are consistent
max_label = max(all_labels) if all_labels else 0
print(f"\nMax label index in data: {max_label}")
print(f"Expected max (22 for 23 labels): 22")

if max_label > 22:
    print("❌ ERROR: Some labels are out of range!")
else:
    print("✅ All labels are in valid range")

# Show some examples
print("\nFirst 3 examples:")
for i, ex in enumerate(dataset[:3], 1):
    print(f"\nExample {i}:")
    print(f"  Tokens: {' '.join(ex['tokens'][:10])}...")
    print(f"  Labels: {ex['ner_tags'][:10]}...")
