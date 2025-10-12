#!/usr/bin/env python3
"""
Properly load and test the LoRA-adapted NER model
"""

import json
import torch
from pathlib import Path
from transformers import (
    AutoTokenizer,
    AutoModelForTokenClassification,
    pipeline
)
from peft import PeftModel

# Load label mappings
LABELS = [
    "O",  # Outside any entity
    "B-MATERIAL", "I-MATERIAL",
    "B-MEASURE", "I-MEASURE", 
    "B-INSTALLATION", "I-INSTALLATION",
    "B-SPECIFICATION", "I-SPECIFICATION",
    "B-STANDARD", "I-STANDARD",
    "B-EQUIPMENT", "I-EQUIPMENT",
    "B-LOCATION", "I-LOCATION",
    "B-REQUIREMENT", "I-REQUIREMENT",
    "B-GRADE", "I-GRADE",
    "B-ZONE", "I-ZONE",
    "B-TEST", "I-TEST"
]

label2id = {label: idx for idx, label in enumerate(LABELS)}
id2label = {idx: label for label, idx in label2id.items()}

def load_lora_ner_model(model_path="./fine_tuned_ner_deep"):
    """Load the LoRA-adapted NER model properly"""
    
    print("Loading LoRA-adapted NER model...")
    
    # Load base model
    base_model_name = "distilbert-base-uncased"
    tokenizer = AutoTokenizer.from_pretrained(base_model_name)
    
    # Load base model with correct number of labels
    base_model = AutoModelForTokenClassification.from_pretrained(
        base_model_name,
        num_labels=len(LABELS),
        id2label=id2label,
        label2id=label2id,
        ignore_mismatched_sizes=True  # Important for custom label count
    )
    
    # Load LoRA adapter
    model = PeftModel.from_pretrained(base_model, model_path)
    
    # Merge adapter with base model for inference
    model = model.merge_and_unload()
    
    print(f"Model loaded successfully with {len(LABELS)} labels")
    
    return model, tokenizer

def test_model():
    """Test the loaded model"""
    
    # Load model
    model, tokenizer = load_lora_ner_model()
    
    # Create pipeline
    ner_pipeline = pipeline(
        "ner",
        model=model,
        tokenizer=tokenizer,
        aggregation_strategy="simple",
        device="cpu"
    )
    
    # Test examples
    test_texts = [
        "Install 12kV deadend insulator at pole top with minimum clearance of 8 feet",
        "Replace existing 4/0 ACSR conductor with 336.4 MCM AAC per GO 95",
        "Trench depth shall be 48 inches for underground conduit",
    ]
    
    print("\n" + "="*60)
    print("TESTING LORA NER MODEL")
    print("="*60)
    
    for i, text in enumerate(test_texts, 1):
        print(f"\nExample {i}: {text}")
        
        try:
            entities = ner_pipeline(text)
            
            if entities:
                print("Entities found:")
                for entity in entities:
                    conf = entity['score'] * 100
                    print(f"  • {entity['entity_group']}: '{entity['word']}' ({conf:.1f}%)")
            else:
                print("  No entities found")
                
        except Exception as e:
            print(f"  Error: {e}")
    
    # Check training results
    metrics_file = Path("./fine_tuned_ner_deep/eval_metrics.json")
    if metrics_file.exists():
        with open(metrics_file) as f:
            metrics = json.load(f)
        print("\n" + "="*60)
        print("TRAINING METRICS")
        print("="*60)
        print(f"Final F1 Score: {metrics.get('eval_f1', 0):.4f}")
        print(f"Precision: {metrics.get('eval_precision', 0):.4f}")
        print(f"Recall: {metrics.get('eval_recall', 0):.4f}")
        print(f"Loss: {metrics.get('eval_loss', 0):.4f}")
        
        if metrics.get('eval_f1', 0) < 0.5:
            print("\n⚠️ WARNING: F1 score is very low!")
            print("Possible issues:")
            print("  1. Label mismatch in training data")
            print("  2. Learning rate too high/low")
            print("  3. Not enough training data")
            print("  4. Need more epochs or different hyperparameters")

if __name__ == "__main__":
    test_model()
