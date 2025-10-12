#!/usr/bin/env python3
"""
Diagnose why the NER model isn't training
"""

import json
import torch
import numpy as np
from pathlib import Path
from transformers import AutoTokenizer
from datasets import Dataset

# Load the tokenizer
tokenizer = AutoTokenizer.from_pretrained("distilbert-base-uncased")

# Define labels - must match training script exactly
LABELS = [
    "O",  # 0: Outside any entity
    "B-MATERIAL", "I-MATERIAL",  # 1-2
    "B-MEASURE", "I-MEASURE",  # 3-4
    "B-INSTALLATION", "I-INSTALLATION",  # 5-6
    "B-SPECIFICATION", "I-SPECIFICATION",  # 7-8
    "B-STANDARD", "I-STANDARD",  # 9-10
    "B-EQUIPMENT", "I-EQUIPMENT",  # 11-12
    "B-LOCATION", "I-LOCATION",  # 13-14
    "B-REQUIREMENT", "I-REQUIREMENT",  # 15-16
    "B-GRADE", "I-GRADE",  # 17-18
    "B-ZONE", "I-ZONE",  # 19-20
    "B-TEST", "I-TEST",  # 21-22
]

print(f"Total labels: {len(LABELS)}")
print("Label mappings:")
for i, label in enumerate(LABELS):
    print(f"  {i}: {label}")

# Load and check the training data
print("\n" + "="*60)
print("CHECKING TRAINING DATA")
print("="*60)

# Check both data files
for filename in ["additional_job_data.jsonl", "additional_job_data_fixed.jsonl"]:
    if Path(filename).exists():
        print(f"\nFile: {filename}")
        with open(filename, 'r') as f:
            lines = f.readlines()
            
        # Check first example
        if lines:
            example = json.loads(lines[0])
            print(f"First example:")
            print(f"  Tokens: {example['tokens']}")
            print(f"  Tags: {example['ner_tags']}")
            
            # Check if tags are valid
            max_tag = max(example['ner_tags'])
            print(f"  Max tag index: {max_tag}")
            
            if max_tag >= len(LABELS):
                print(f"  ❌ ERROR: Tag {max_tag} is out of range! (max should be {len(LABELS)-1})")
            else:
                print(f"  ✅ All tags are in valid range")
            
            # Show what the labels mean
            print("  Token-Label mapping:")
            for token, tag in zip(example['tokens'][:5], example['ner_tags'][:5]):
                if tag < len(LABELS):
                    print(f"    '{token}' -> {tag} ({LABELS[tag]})")
                else:
                    print(f"    '{token}' -> {tag} (OUT OF RANGE!)")

# Test tokenization alignment
print("\n" + "="*60)
print("TESTING TOKENIZATION ALIGNMENT")
print("="*60)

test_sentence = ["Install", "12kV", "deadend", "insulator"]
test_tags = [5, 3, 11, 11]  # B-INSTALLATION, B-MEASURE, B-EQUIPMENT, B-EQUIPMENT

print(f"Original: {test_sentence}")
print(f"Tags: {test_tags}")

# Tokenize
encoding = tokenizer(
    test_sentence,
    is_split_into_words=True,
    truncation=True,
    max_length=512
)

print(f"\nTokenized: {tokenizer.convert_ids_to_tokens(encoding['input_ids'])}")
print(f"Word IDs: {encoding.word_ids()}")

# Create aligned labels
label_ids = []
previous_word_idx = None
for word_idx in encoding.word_ids():
    if word_idx is None:
        # Special tokens get -100
        label_ids.append(-100)
    elif word_idx != previous_word_idx:
        # First token of a word gets the label
        label_ids.append(test_tags[word_idx])
    else:
        # Subsequent subword tokens
        # For B- tags, subsequent subwords should get I- tag
        prev_label = test_tags[word_idx]
        if prev_label > 0 and prev_label % 2 == 1:  # It's a B- tag (odd number)
            label_ids.append(prev_label + 1)  # Convert to I- tag
        else:
            label_ids.append(prev_label)
    previous_word_idx = word_idx

print(f"Aligned labels: {label_ids}")

# Show the alignment
print("\nToken-Label alignment:")
for token, label in zip(tokenizer.convert_ids_to_tokens(encoding['input_ids']), label_ids):
    if label != -100:
        print(f"  '{token}' -> {label} ({LABELS[label]})")
    else:
        print(f"  '{token}' -> -100 (ignored)")

print("\n✅ If alignment looks correct, the issue might be:")
print("  1. Learning rate too high/low")
print("  2. Not enough diverse training data")
print("  3. Labels too sparse (too many O tags)")
print("  4. Need different model architecture")
