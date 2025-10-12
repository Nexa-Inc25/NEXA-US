#!/usr/bin/env python3
"""
Deep Fine-tuning NER Model with LoRA for PG&E Document Analysis
Enhanced training with more epochs, larger LoRA rank, and comprehensive dataset
Target: F1 > 0.90 for production deployment
"""

import os
import sys
import json
import numpy as np
import torch
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

# VERSION CHECK - CRITICAL FOR DEBUGGING
import transformers
print("="*60)
print(f"ENVIRONMENT CHECK:")
print(f"Python version: {sys.version}")
print(f"Python executable: {sys.executable}")
print(f"Transformers version: {transformers.__version__}")
print(f"Torch version: {torch.__version__}")
print("="*60)

# Check transformers version and use correct parameter
from packaging import version
trans_version = version.parse(transformers.__version__)
if trans_version >= version.parse("4.46.0"):
    print(f"ℹ️ Transformers {transformers.__version__} uses 'eval_strategy' (not 'evaluation_strategy')")
    USE_EVAL_STRATEGY = True
else:
    print(f"ℹ️ Transformers {transformers.__version__} uses older parameter names")
    USE_EVAL_STRATEGY = False
print("="*60)
print()

from transformers import (
    AutoTokenizer,
    AutoModelForTokenClassification,
    Trainer,
    TrainingArguments,
    DataCollatorForTokenClassification
)
from peft import get_peft_model, LoraConfig, TaskType
from datasets import Dataset
from evaluate import load
import warnings

# Suppress warnings
warnings.filterwarnings('ignore')

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
class Config:
    """Training configuration for deep NER fine-tuning"""
    
    # Model settings
    BASE_MODEL = "distilbert-base-uncased"
    
    # LoRA settings (deeper adaptation)
    LORA_RANK = 16  # Increased from 8 for better adaptation
    LORA_ALPHA = 32  # Scaling factor
    LORA_DROPOUT = 0.1  # Prevent overfitting
    TARGET_MODULES = ["q_lin", "v_lin"]  # Attention layers
    
    # Training settings
    NUM_EPOCHS = 50  # Deep training
    BATCH_SIZE = 16  # Larger batch for stability
    LEARNING_RATE = 2e-5  # Conservative LR
    WEIGHT_DECAY = 0.01  # L2 regularization
    WARMUP_STEPS = 500
    
    # Evaluation settings
    EVAL_STRATEGY = "epoch"
    SAVE_STRATEGY = "epoch"
    METRIC_FOR_BEST = "f1"
    EARLY_STOPPING_PATIENCE = 5
    
    # Paths - Windows compatible
    OUTPUT_DIR = "./results_deep"
    MODEL_DIR = "./fine_tuned_ner_deep"  # Changed from /data/ to relative path
    CACHE_DIR = "./cache"

# Enhanced label set for PG&E domain
LABELS = [
    "O",  # Outside any entity
    "B-MATERIAL", "I-MATERIAL",  # PVC, ACSR, copper, etc.
    "B-MEASURE", "I-MEASURE",  # 18 ft, 750V, 24 inches, etc.
    "B-INSTALLATION", "I-INSTALLATION",  # installed, required, furnished
    "B-SPECIFICATION", "I-SPECIFICATION",  # clearance, cover, tensions
    "B-STANDARD", "I-STANDARD",  # G.O. 95, Table 8, ANSI
    "B-LOCATION", "I-LOCATION",  # street, track, underground
    "B-EQUIPMENT", "I-EQUIPMENT",  # poles, conductors, dampers
    "B-SECTION", "I-SECTION",  # Section A, Part 1.2
    "B-GRADE", "I-GRADE",  # Grade B, Grade C construction
    "B-ZONE", "I-ZONE",  # Light loading, Heavy loading
    "B-TEST", "I-TEST",  # test requirements, inspection
]

# Build label mappings
label2id = {label: idx for idx, label in enumerate(LABELS)}
id2label = {idx: label for label, idx in label2id.items()}
num_labels = len(LABELS)

def create_comprehensive_dataset() -> List[Dict[str, Any]]:
    """
    Create comprehensive training dataset from multiple sources
    Includes poles, conduits, clearances, overhead, underground, etc.
    Enhanced with real job package data for F1>0.9
    """
    
    data = []
    
    # Load additional job package data (200+ new tokens)
    # Use fixed data file with correct label indices
    additional_data_file = Path("additional_job_data_fixed.jsonl")
    if not additional_data_file.exists():
        # Fallback to original if fixed doesn't exist
        additional_data_file = Path("additional_job_data.jsonl")
    
    if additional_data_file.exists():
        logger.info(f"Loading additional job package data from {additional_data_file}")
        with open(additional_data_file, 'r') as f:
            for line in f:
                try:
                    data.append(json.loads(line))
                except json.JSONDecodeError as e:
                    logger.warning(f"Skipping invalid JSON line: {e}")
        logger.info(f"Loaded {len(data)} examples from additional job package data")
    else:
        logger.warning(f"Additional job package data not found at {additional_data_file}")
    
    # POLES EXAMPLES (original training data)
    data.extend([
        {
            "tokens": ["Temporary", "service", "poles", "must", "be", "furnished", 
                      "and", "installed", "by", "the", "customer", "and", "may", 
                      "be", "wooden", "or", "metallic", "."],
            "ner_tags": [0, 0, 13, 0, 0, 0, 0, 5, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0]
        },
        {
            "tokens": ["The", "minimum", "length", "must", "be", "20", "feet", 
                      "(", "set", "4", "feet", "in", "the", "ground", ")", "."],
            "ner_tags": [0, 0, 7, 0, 0, 3, 4, 0, 5, 3, 4, 0, 0, 11, 0, 0]
        },
        {
            "tokens": ["Wood", "poles", "shall", "comply", "with", "ANSI", "O5.1", 
                      "standards", "for", "preservative", "treatment", "."],
            "ner_tags": [1, 13, 0, 0, 0, 9, 10, 9, 0, 7, 8, 0]
        }
    ])
    
    # CONDUITS EXAMPLES
    data.extend([
        {
            "tokens": ["A", "minimum", "of", "24", "inches", "of", "cover", "for", 
                      "secondary", "(", "0", "−", "750", "V", ")", "electric", 
                      "service", ",", "or", "30", "inches", "minimum", "cover", 
                      "for", "primary", "(", "over", "750", "V", ")", "."],
            "ner_tags": [0, 0, 0, 3, 4, 0, 7, 0, 13, 0, 3, 0, 3, 4, 0, 0, 13, 
                        0, 0, 3, 4, 0, 7, 0, 13, 0, 0, 3, 4, 0, 0]
        },
        {
            "tokens": ["Rigid", "single", "wall", "or", "co-extruded", "cellular", 
                      "core", "wall", "PVC", "Schedule", "40", "conduits", ",", 
                      "couplings", ",", "fittings", "and", "bends", "must", "be", 
                      "gray", "in", "color", "."],
            "ner_tags": [1, 1, 2, 0, 1, 1, 2, 2, 1, 1, 2, 13, 0, 13, 0, 13, 0, 
                        13, 0, 0, 7, 8, 8, 0]
        },
        {
            "tokens": ["Underground", "conduit", "systems", "shall", "be", "installed",
                      "per", "G.O.", "128", "requirements", "."],
            "ner_tags": [11, 13, 14, 0, 0, 5, 0, 9, 10, 7, 0]
        }
    ])
    
    # CLEARANCES EXAMPLES
    data.extend([
        {
            "tokens": ["Conductors", "to", "service", "poles", "must", "have", "a", 
                      "minimum", "ground", "clearance", "as", "follows", ":", "A.", 
                      "Over", "the", "center", "portion", "of", "the", "street", 
                      ",", "18'", "0\"", "minimum", "."],
            "ner_tags": [13, 0, 13, 13, 0, 0, 0, 0, 11, 7, 0, 0, 0, 15, 0, 0, 
                        11, 12, 0, 0, 11, 0, 3, 4, 0, 0]
        },
        {
            "tokens": ["The", "8'-6\"", "clearance", "for", "tangent", "track", 
                      "and", "9'-6\"", "clearance", "for", "curved", "track", 
                      "are", "minimum", "requirements", "."],
            "ner_tags": [0, 3, 7, 0, 11, 11, 0, 3, 7, 0, 11, 11, 0, 0, 7, 0]
        },
        {
            "tokens": ["Clearances", "shall", "comply", "with", "Rule", "37", 
                      "of", "G.O.", "95", "for", "Grade", "B", "construction", "."],
            "ner_tags": [7, 0, 0, 0, 9, 10, 0, 9, 10, 0, 17, 18, 7, 0]
        }
    ])
    
    # VIBRATION DAMPERS EXAMPLES
    data.extend([
        {
            "tokens": ["Vibration", "dampers", "are", "required", "for", "covered", 
                      "tree", "wire", "spans", "greater", "than", "300", "feet", 
                      "in", "all", "loading", "areas", "."],
            "ner_tags": [13, 14, 0, 5, 0, 1, 1, 2, 7, 0, 0, 3, 4, 0, 0, 19, 20, 0]
        },
        {
            "tokens": ["Install", "dampers", "within", "24", "inches", "of", 
                      "suspension", "clamps", "on", "ACSR", "conductors", "."],
            "ner_tags": [5, 13, 0, 3, 4, 0, 13, 14, 0, 1, 13, 0]
        }
    ])
    
    # CROSSARMS EXAMPLES
    data.extend([
        {
            "tokens": ["Crossarms", "shall", "be", "Douglas", "fir", "or", 
                      "equivalent", ",", "treated", "per", "ANSI", "standards", "."],
            "ner_tags": [13, 0, 0, 1, 2, 0, 1, 0, 5, 0, 9, 9, 0]
        },
        {
            "tokens": ["Minimum", "crossarm", "size", ":", "3", "5/8\"", "x", 
                      "4", "5/8\"", "x", "8", "feet", "for", "standard", 
                      "installations", "."],
            "ner_tags": [0, 13, 7, 0, 3, 4, 0, 3, 4, 0, 3, 4, 0, 7, 5, 0]
        }
    ])
    
    # GROUNDING EXAMPLES
    data.extend([
        {
            "tokens": ["Ground", "rods", "shall", "be", "copper-clad", "steel", 
                      ",", "5/8", "inch", "diameter", ",", "8", "feet", "minimum", 
                      "length", "."],
            "ner_tags": [13, 14, 0, 0, 1, 1, 0, 3, 4, 7, 0, 3, 4, 0, 7, 0]
        },
        {
            "tokens": ["Grounding", "conductor", "size", ":", "#6", "AWG", "copper", 
                      "minimum", "for", "equipment", "grounding", "."],
            "ner_tags": [13, 14, 7, 0, 3, 4, 1, 0, 0, 13, 5, 0]
        }
    ])
    
    # INSULATORS EXAMPLES
    data.extend([
        {
            "tokens": ["Pin", "type", "insulators", "shall", "be", "ANSI", "55-2", 
                      "porcelain", "or", "polymer", "for", "15kV", "systems", "."],
            "ner_tags": [13, 14, 14, 0, 0, 9, 10, 1, 0, 1, 0, 3, 13, 0]
        },
        {
            "tokens": ["Suspension", "insulators", "required", "for", "spans", 
                      "over", "500", "feet", "in", "heavy", "loading", "zones", "."],
            "ner_tags": [13, 14, 5, 0, 7, 0, 3, 4, 0, 19, 19, 20, 0]
        }
    ])
    
    # TRANSFORMERS EXAMPLES
    data.extend([
        {
            "tokens": ["Pad-mounted", "transformers", "require", "5", "feet", 
                      "front", "clearance", ",", "3", "feet", "side", "clearance", "."],
            "ner_tags": [13, 14, 5, 3, 4, 11, 7, 0, 3, 4, 11, 7, 0]
        },
        {
            "tokens": ["Transformer", "installations", "shall", "comply", "with", 
                      "Section", "3.2", "of", "Document", "062288", "."],
            "ner_tags": [13, 5, 0, 0, 0, 15, 16, 0, 9, 10, 0]
        }
    ])
    
    # SPLICES AND TERMINATIONS
    data.extend([
        {
            "tokens": ["Compression", "splices", "required", "for", "ACSR", 
                      "conductors", "over", "#2", "AWG", "."],
            "ner_tags": [13, 14, 5, 0, 1, 13, 0, 3, 4, 0]
        },
        {
            "tokens": ["Heat", "shrink", "terminations", "shall", "be", "3M", 
                      "or", "Raychem", "approved", "types", "."],
            "ner_tags": [1, 2, 13, 0, 0, 1, 0, 1, 7, 7, 0]
        }
    ])
    
    # TESTING REQUIREMENTS
    data.extend([
        {
            "tokens": ["Insulation", "testing", "required", "at", "2.5", "times", 
                      "rated", "voltage", "for", "1", "minute", "."],
            "ner_tags": [21, 22, 5, 0, 3, 0, 7, 7, 0, 3, 4, 0]
        },
        {
            "tokens": ["Hi-pot", "test", "all", "underground", "cables", "before", 
                      "energizing", "per", "IEEE", "400", "."],
            "ner_tags": [21, 22, 0, 11, 13, 0, 5, 0, 9, 10, 0]
        }
    ])
    
    logger.info(f"Created dataset with {len(data)} examples")
    return data

class NERDataProcessor:
    """Process and prepare NER data for training"""
    
    def __init__(self, tokenizer):
        self.tokenizer = tokenizer
    
    def tokenize_and_align_labels(self, examples):
        """
        Tokenize text and align labels with subword tokens
        """
        tokenized_inputs = self.tokenizer(
            examples["tokens"],
            truncation=True,
            is_split_into_words=True,
            max_length=512,
            padding=False
        )
        
        labels = []
        for i, label in enumerate(examples["ner_tags"]):
            word_ids = tokenized_inputs.word_ids(batch_index=i)
            previous_word_idx = None
            label_ids = []
            
            for word_idx in word_ids:
                if word_idx is None:
                    # Special tokens get -100 (ignored in loss)
                    label_ids.append(-100)
                elif word_idx != previous_word_idx:
                    # First token of a word gets the label
                    label_ids.append(label[word_idx])
                else:
                    # Subsequent subword tokens get -100
                    label_ids.append(-100)
                previous_word_idx = word_idx
            
            labels.append(label_ids)
        
        tokenized_inputs["labels"] = labels
        return tokenized_inputs

class CustomTrainer(Trainer):
    """Custom trainer with additional logging"""
    
    def log(self, logs: Dict[str, float], start_time: Optional[float] = None) -> None:
        """Override log method for custom logging"""
        # Call parent log with both parameters
        if start_time is not None:
            super().log(logs, start_time)
        else:
            super().log(logs)
        
        # Log to console
        if "eval_f1" in logs:
            logger.info(f"Eval F1: {logs['eval_f1']:.4f}")
        if "loss" in logs:
            logger.info(f"Training Loss: {logs['loss']:.4f}")

def compute_metrics(eval_pred):
    """
    Compute NER metrics using seqeval
    """
    predictions, labels = eval_pred
    predictions = np.argmax(predictions, axis=2)
    
    # Convert to label sequences
    true_predictions = []
    true_labels = []
    
    for prediction, label in zip(predictions, labels):
        true_pred = []
        true_label = []
        
        for pred_id, label_id in zip(prediction, label):
            if label_id != -100:  # Ignore special tokens
                true_pred.append(id2label[pred_id])
                true_label.append(id2label[label_id])
        
        if true_pred:  # Only add non-empty sequences
            true_predictions.append(true_pred)
            true_labels.append(true_label)
    
    # Load metric
    metric = load("seqeval")
    
    # Compute metrics
    results = metric.compute(
        predictions=true_predictions,
        references=true_labels
    )
    
    return {
        "f1": results["overall_f1"],
        "precision": results["overall_precision"],
        "recall": results["overall_recall"],
        "accuracy": results["overall_accuracy"]
    }

def train_deep_ner():
    """
    Main training function for deep NER fine-tuning
    """
    
    logger.info("=" * 60)
    logger.info("DEEP NER FINE-TUNING WITH LoRA")
    logger.info("=" * 60)
    
    # Create output directories
    Path(Config.OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    Path(Config.MODEL_DIR).mkdir(parents=True, exist_ok=True)
    Path(Config.CACHE_DIR).mkdir(parents=True, exist_ok=True)
    
    # Load tokenizer
    logger.info(f"Loading tokenizer: {Config.BASE_MODEL}")
    tokenizer = AutoTokenizer.from_pretrained(
        Config.BASE_MODEL,
        cache_dir=Config.CACHE_DIR
    )
    
    # Create dataset
    logger.info("Creating comprehensive training dataset...")
    raw_data = create_comprehensive_dataset()
    
    # Convert to Dataset
    dataset = Dataset.from_list(raw_data)
    
    # Split into train/validation
    dataset = dataset.train_test_split(test_size=0.2, seed=42)
    logger.info(f"Train examples: {len(dataset['train'])}")
    logger.info(f"Validation examples: {len(dataset['test'])}")
    
    # Process data
    processor = NERDataProcessor(tokenizer)
    tokenized_dataset = dataset.map(
        processor.tokenize_and_align_labels,
        batched=True,
        remove_columns=dataset["train"].column_names
    )
    
    # Load model
    logger.info(f"Loading base model: {Config.BASE_MODEL}")
    model = AutoModelForTokenClassification.from_pretrained(
        Config.BASE_MODEL,
        num_labels=num_labels,
        id2label=id2label,
        label2id=label2id,
        cache_dir=Config.CACHE_DIR
    )
    
    # Configure LoRA
    logger.info("Configuring LoRA for deep adaptation...")
    lora_config = LoraConfig(
        r=Config.LORA_RANK,
        lora_alpha=Config.LORA_ALPHA,
        lora_dropout=Config.LORA_DROPOUT,
        target_modules=Config.TARGET_MODULES,
        task_type=TaskType.TOKEN_CLS,
        bias="none"
    )
    
    # Apply LoRA
    model = get_peft_model(model, lora_config)
    
    # Print trainable parameters
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    all_params = sum(p.numel() for p in model.parameters())
    logger.info(f"Trainable params: {trainable_params:,} ({100 * trainable_params / all_params:.2f}%)")
    logger.info(f"All params: {all_params:,}")
    
    # Data collator
    data_collator = DataCollatorForTokenClassification(
        tokenizer=tokenizer,
        padding=True
    )
    
    # Training arguments - using correct parameter names for transformers 4.46+
    if USE_EVAL_STRATEGY:
        # For transformers >= 4.46.0 (uses eval_strategy, NOT evaluation_strategy)
        training_args = TrainingArguments(
            output_dir=Config.OUTPUT_DIR,
            num_train_epochs=Config.NUM_EPOCHS,
            per_device_train_batch_size=Config.BATCH_SIZE,
            per_device_eval_batch_size=Config.BATCH_SIZE,
            learning_rate=Config.LEARNING_RATE,
            weight_decay=Config.WEIGHT_DECAY,
            warmup_steps=Config.WARMUP_STEPS,
            eval_strategy=Config.EVAL_STRATEGY,  # CHANGED: eval_strategy for 4.46+
            save_strategy=Config.SAVE_STRATEGY,
            metric_for_best_model=Config.METRIC_FOR_BEST,
            greater_is_better=True,
            load_best_model_at_end=True,
            save_total_limit=3,
            logging_dir=f"{Config.OUTPUT_DIR}/logs",
            logging_steps=10,
            report_to=["tensorboard"],
            push_to_hub=False,
            fp16=torch.cuda.is_available(),
            gradient_checkpointing=True,
            optim="adamw_torch",
            seed=42
        )
        logger.info("Using 'eval_strategy' parameter (transformers >= 4.46.0)")
    else:
        # For older versions < 4.46.0
        logger.info("Using older parameter names for transformers < 4.46.0")
        
        training_args = TrainingArguments(
            output_dir=Config.OUTPUT_DIR,
            num_train_epochs=Config.NUM_EPOCHS,
            per_device_train_batch_size=Config.BATCH_SIZE,
            per_device_eval_batch_size=Config.BATCH_SIZE,
            learning_rate=Config.LEARNING_RATE,
            weight_decay=Config.WEIGHT_DECAY,
            warmup_steps=Config.WARMUP_STEPS,
            eval_steps=500,  # Evaluate every 500 steps
            save_steps=500,  # Save every 500 steps
            metric_for_best_model=Config.METRIC_FOR_BEST,
            greater_is_better=True,
            load_best_model_at_end=True,
            save_total_limit=3,
            logging_dir=f"{Config.OUTPUT_DIR}/logs",
            logging_steps=10,
            report_to=["tensorboard"],
            push_to_hub=False,
            fp16=torch.cuda.is_available(),
            gradient_checkpointing=True,
            optim="adamw_torch",
            seed=42,
            do_eval=True  # Ensure evaluation is enabled
        )
    
    # Initialize trainer
    trainer = CustomTrainer(
        model=model,
        args=training_args,
        data_collator=data_collator,
        train_dataset=tokenized_dataset["train"],
        eval_dataset=tokenized_dataset["test"],
        tokenizer=tokenizer,
        compute_metrics=compute_metrics
    )
    
    # Train
    logger.info("Starting deep training...")
    logger.info(f"Target: F1 > 0.90")
    train_result = trainer.train()
    
    # Save final model
    logger.info(f"Saving model to {Config.MODEL_DIR}")
    trainer.save_model(Config.MODEL_DIR)
    tokenizer.save_pretrained(Config.MODEL_DIR)
    
    # Save training metrics
    metrics = train_result.metrics
    with open(f"{Config.MODEL_DIR}/training_metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)
    
    # Evaluate on test set
    logger.info("Evaluating on validation set...")
    eval_results = trainer.evaluate()
    
    # Save evaluation metrics
    with open(f"{Config.MODEL_DIR}/eval_metrics.json", "w") as f:
        json.dump(eval_results, f, indent=2)
    
    # Print results
    logger.info("=" * 60)
    logger.info("TRAINING COMPLETE")
    logger.info("=" * 60)
    logger.info(f"Final Training Loss: {metrics.get('train_loss', 0):.4f}")
    logger.info(f"Validation F1: {eval_results.get('eval_f1', 0):.4f}")
    logger.info(f"Validation Precision: {eval_results.get('eval_precision', 0):.4f}")
    logger.info(f"Validation Recall: {eval_results.get('eval_recall', 0):.4f}")
    logger.info(f"Validation Accuracy: {eval_results.get('eval_accuracy', 0):.4f}")
    
    # Check if target met
    val_f1 = eval_results.get('eval_f1', 0)
    if val_f1 >= 0.90:
        logger.info("✅ TARGET ACHIEVED: F1 >= 0.90")
        logger.info("Model ready for production deployment!")
    elif val_f1 >= 0.85:
        logger.info("⚠️ Good performance but below target (F1 >= 0.90)")
        logger.info("Consider adding more training data")
    else:
        logger.warning("❌ Performance below minimum (F1 < 0.85)")
        logger.warning("Add more data or adjust hyperparameters")
    
    logger.info(f"Model saved to: {Config.MODEL_DIR}")
    logger.info("=" * 60)
    
    return eval_results

def test_inference():
    """
    Test the trained model with sample infractions
    """
    
    logger.info("\nTesting inference with sample infractions...")
    
    # Load model and tokenizer
    from transformers import pipeline
    
    model_path = Config.MODEL_DIR
    if not Path(model_path).exists():
        logger.error(f"Model not found at {model_path}")
        return
    
    # Create NER pipeline
    ner_pipeline = pipeline(
        "ner",
        model=model_path,
        tokenizer=model_path,
        aggregation_strategy="simple"
    )
    
    # Test examples
    test_texts = [
        "Pole clearance only 16 ft over street - violation",
        "Conduit cover 20 inches for secondary - infraction",
        "18 ft clearance over street meets G.O. 95 requirement",
        "ACSR conductor with #4 AWG installed per specifications",
        "Vibration dampers required for 350 foot spans"
    ]
    
    logger.info("\nInference Results:")
    logger.info("-" * 50)
    
    for text in test_texts:
        entities = ner_pipeline(text)
        logger.info(f"\nText: {text}")
        logger.info("Entities:")
        for entity in entities:
            logger.info(f"  - {entity['entity_group']}: '{entity['word']}' (score: {entity['score']:.3f})")

if __name__ == "__main__":
    # Run deep training
    results = train_deep_ner()
    
    # Test inference if training successful
    if results.get('eval_f1', 0) >= 0.85:
        test_inference()
    
    # Print deployment instructions
    print("\n" + "=" * 60)
    print("DEPLOYMENT INSTRUCTIONS")
    print("=" * 60)
    print("1. Model saved to: /data/fine_tuned_ner_deep")
    print("2. Update analyzer to use deep model:")
    print("   fine_tuned_model_path='/data/fine_tuned_ner_deep'")
    print("3. Deploy to Render:")
    print("   git add . && git commit -m 'Deep NER model'")
    print("   git push origin main")
    print("4. Test production endpoints after deployment")
    print("=" * 60)
