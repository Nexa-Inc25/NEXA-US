#!/usr/bin/env python3
"""
Complete NER Training Script for PG&E Document Analyzer
Trains on all annotated data: conduit, overhead, clearance
Target: F1 >0.85 for production deployment on Render.com
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np
from transformers import (
    AutoTokenizer,
    AutoModelForTokenClassification,
    Trainer,
    TrainingArguments,
    DataCollatorForTokenClassification
)
from peft import get_peft_model, LoraConfig, TaskType
from datasets import Dataset, DatasetDict
import evaluate
import torch

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NERTrainer:
    """Complete NER training system for PG&E spec compliance"""
    
    def __init__(self, output_dir: str = "/data/fine_tuned_ner"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Define all labels
        self.labels = [
            "O", "B-MATERIAL", "I-MATERIAL", "B-MEASURE", "I-MEASURE",
            "B-INSTALLATION", "I-INSTALLATION", "B-SPECIFICATION", "I-SPECIFICATION",
            "B-EQUIPMENT", "I-EQUIPMENT", "B-STANDARD", "I-STANDARD",
            "B-LOCATION", "I-LOCATION"
        ]
        self.label2id = {label: i for i, label in enumerate(self.labels)}
        self.id2label = {i: label for i, label in enumerate(self.labels)}
        
        self.tokenizer = AutoTokenizer.from_pretrained("distilbert-base-uncased")
        
    def load_all_annotations(self) -> List[Dict]:
        """Load all annotation files and compile training data"""
        
        all_data = []
        annotation_files = [
            "data/training/conduit_ner_annotations.json",
            "data/training/overhead_ner_annotations.json", 
            "data/training/clearance_ner_annotations.json"
        ]
        
        for file_path in annotation_files:
            if Path(file_path).exists():
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    annotations = data.get("annotations", [])
                    logger.info(f"Loaded {len(annotations)} annotations from {file_path}")
                    
                    # Convert to training format
                    for item in annotations:
                        tokens = self.tokenizer.tokenize(item["text"])
                        ner_tags = self._create_bio_tags(tokens, item["entities"])
                        all_data.append({"tokens": tokens, "ner_tags": ner_tags})
            else:
                logger.warning(f"Annotation file not found: {file_path}")
        
        # Add some hardcoded examples to ensure coverage
        additional_data = [
            # Poles and equipment
            {"tokens": ["Temporary", "service", "poles", "must", "be", "furnished", "and", "installed", "by", "the", "customer"],
             "ner_tags": [0, 0, 13, 0, 0, 0, 0, 5, 0, 0, 0]},  # B-EQUIPMENT, B-INSTALLATION
            
            # Clearances
            {"tokens": ["Clearance", "of", "18", "ft", "over", "street", "center", "per", "G.O.", "95"],
             "ner_tags": [0, 0, 3, 4, 0, 11, 12, 0, 9, 10]},  # B-MEASURE, I-MEASURE, B-LOCATION, I-LOCATION, B-STANDARD, I-STANDARD
            
            # Materials and specifications
            {"tokens": ["ACSR", "conductor", "with", "#4", "AWG", "size", "meets", "requirements"],
             "ner_tags": [1, 13, 0, 3, 4, 4, 0, 7]},  # B-MATERIAL, B-EQUIPMENT, B-MEASURE, I-MEASURE, I-MEASURE, B-SPECIFICATION
            
            # Railroad clearances
            {"tokens": ["8'-6\"", "clearance", "from", "railroad", "tangent", "track"],
             "ner_tags": [3, 0, 0, 11, 11, 12]},  # B-MEASURE, B-LOCATION, B-LOCATION, I-LOCATION
            
            # Voltage specifications
            {"tokens": ["750V", "to", "ground", "maximum", "for", "communication", "circuits"],
             "ner_tags": [3, 0, 11, 7, 0, 13, 14]},  # B-MEASURE, B-LOCATION, B-SPECIFICATION, B-EQUIPMENT, I-EQUIPMENT
            
            # Installation requirements
            {"tokens": ["Pin", "insulator", "installed", "in", "horizontal", "plane"],
             "ner_tags": [13, 14, 5, 0, 7, 8]},  # B-EQUIPMENT, I-EQUIPMENT, B-INSTALLATION, B-SPECIFICATION, I-SPECIFICATION
            
            # Standards and rules
            {"tokens": ["Per", "Rule", "37", "Table", "1", "requirements"],
             "ner_tags": [0, 9, 10, 9, 10, 7]},  # B-STANDARD, I-STANDARD, B-STANDARD, I-STANDARD, B-SPECIFICATION
        ]
        
        all_data.extend(additional_data)
        
        logger.info(f"Total training examples: {len(all_data)} (target: 800-1000 tokens)")
        total_tokens = sum(len(d["tokens"]) for d in all_data)
        logger.info(f"Total tokens: {total_tokens}")
        
        return all_data
    
    def _create_bio_tags(self, tokens: List[str], entities: List[Dict]) -> List[int]:
        """Convert entities to BIO tags for tokens"""
        
        tags = [0] * len(tokens)  # Initialize with O tags
        
        for entity in entities:
            entity_text = entity["text"].lower()
            entity_label = entity["label"]
            
            # Try to find entity in tokens
            entity_tokens = self.tokenizer.tokenize(entity_text)
            
            for i in range(len(tokens) - len(entity_tokens) + 1):
                # Check if tokens match
                match = True
                for j, et in enumerate(entity_tokens):
                    if i + j >= len(tokens) or tokens[i + j].lower() != et.lower():
                        match = False
                        break
                
                if match:
                    # Apply BIO tags
                    tags[i] = self.label2id[f"B-{entity_label}"]
                    for j in range(1, len(entity_tokens)):
                        if i + j < len(tokens):
                            tags[i + j] = self.label2id[f"I-{entity_label}"]
                    break
        
        return tags
    
    def prepare_dataset(self) -> DatasetDict:
        """Prepare dataset for training"""
        
        all_data = self.load_all_annotations()
        
        # Create Hugging Face Dataset
        dataset = Dataset.from_list(all_data)
        
        # Split 80/20 train/test
        dataset_split = dataset.train_test_split(test_size=0.2, seed=42)
        
        logger.info(f"Train examples: {len(dataset_split['train'])}")
        logger.info(f"Test examples: {len(dataset_split['test'])}")
        
        return dataset_split
    
    def tokenize_and_align_labels(self, examples):
        """Tokenize and align labels for subword tokenization"""
        
        tokenized_inputs = self.tokenizer(
            examples["tokens"],
            truncation=True,
            is_split_into_words=True,
            max_length=128,
            padding=True
        )
        
        labels = []
        for i, label in enumerate(examples["ner_tags"]):
            word_ids = tokenized_inputs.word_ids(batch_index=i)
            previous_word_idx = None
            label_ids = []
            
            for word_idx in word_ids:
                if word_idx is None:
                    label_ids.append(-100)
                elif word_idx != previous_word_idx:
                    label_ids.append(label[word_idx])
                else:
                    # For subword tokens, use -100 to ignore in loss
                    label_ids.append(-100)
                previous_word_idx = word_idx
            
            labels.append(label_ids)
        
        tokenized_inputs["labels"] = labels
        return tokenized_inputs
    
    def train(self):
        """Train the NER model with LoRA for efficiency"""
        
        logger.info("Starting NER training for PG&E spec compliance...")
        
        # Prepare dataset
        dataset = self.prepare_dataset()
        tokenized_dataset = dataset.map(
            self.tokenize_and_align_labels,
            batched=True,
            remove_columns=dataset["train"].column_names
        )
        
        # Initialize model
        model = AutoModelForTokenClassification.from_pretrained(
            "distilbert-base-uncased",
            num_labels=len(self.labels),
            id2label=self.id2label,
            label2id=self.label2id
        )
        
        # Apply LoRA for efficient fine-tuning
        lora_config = LoraConfig(
            r=8,
            lora_alpha=16,
            target_modules=["q_lin", "v_lin"],  # DistilBERT attention layers
            lora_dropout=0.1,
            bias="none",
            task_type=TaskType.TOKEN_CLS
        )
        
        model = get_peft_model(model, lora_config)
        model.print_trainable_parameters()
        
        # Data collator
        data_collator = DataCollatorForTokenClassification(
            tokenizer=self.tokenizer,
            padding=True
        )
        
        # Metrics
        seqeval = evaluate.load("seqeval")
        
        def compute_metrics(eval_preds):
            predictions, labels = eval_preds
            predictions = np.argmax(predictions, axis=2)
            
            # Convert to lists of labels
            true_predictions = [
                [self.labels[p] for (p, l) in zip(prediction, label) if l != -100]
                for prediction, label in zip(predictions, labels)
            ]
            true_labels = [
                [self.labels[l] for (p, l) in zip(prediction, label) if l != -100]
                for prediction, label in zip(predictions, labels)
            ]
            
            results = seqeval.compute(predictions=true_predictions, references=true_labels)
            
            return {
                "precision": results["overall_precision"],
                "recall": results["overall_recall"],
                "f1": results["overall_f1"],
                "accuracy": results["overall_accuracy"],
            }
        
        # Training arguments optimized for CPU
        training_args = TrainingArguments(
            output_dir=str(self.output_dir / "checkpoints"),
            learning_rate=2e-4,
            per_device_train_batch_size=8,
            per_device_eval_batch_size=8,
            num_train_epochs=20,
            weight_decay=0.01,
            evaluation_strategy="epoch",
            save_strategy="epoch",
            load_best_model_at_end=True,
            metric_for_best_model="f1",
            greater_is_better=True,
            push_to_hub=False,
            logging_steps=10,
            warmup_steps=100,
            fp16=torch.cuda.is_available(),  # Use mixed precision if GPU available
        )
        
        # Initialize trainer
        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=tokenized_dataset["train"],
            eval_dataset=tokenized_dataset["test"],
            tokenizer=self.tokenizer,
            data_collator=data_collator,
            compute_metrics=compute_metrics,
        )
        
        # Train
        logger.info("Training model (this may take 30-60 minutes on CPU)...")
        train_result = trainer.train()
        
        # Save model
        logger.info(f"Saving model to {self.output_dir}")
        trainer.save_model(str(self.output_dir))
        self.tokenizer.save_pretrained(str(self.output_dir))
        
        # Evaluate
        logger.info("Evaluating on test set...")
        metrics = trainer.evaluate()
        
        # Log metrics
        logger.info("\n" + "="*50)
        logger.info("TRAINING RESULTS")
        logger.info("="*50)
        for key, value in metrics.items():
            logger.info(f"{key}: {value:.4f}")
        logger.info("="*50)
        
        # Save metrics
        with open(self.output_dir / "training_metrics.json", "w") as f:
            json.dump(metrics, f, indent=2)
        
        return metrics
    
    def test_model(self, test_texts: List[str] = None):
        """Test the trained model on sample texts"""
        
        if test_texts is None:
            test_texts = [
                "Clearance of 18 ft over street center per G.O. 95",
                "8'-6\" clearance from railroad tangent track",
                "ACSR conductor with #4 AWG size",
                "Pin insulator installed in horizontal plane",
                "750V to ground maximum for communication",
                "Conduit depth only 20 inches below grade",
                "Missing vibration damper on 350 foot span"
            ]
        
        logger.info("\n" + "="*50)
        logger.info("TESTING MODEL")
        logger.info("="*50)
        
        # Load model
        model = AutoModelForTokenClassification.from_pretrained(str(self.output_dir))
        
        for text in test_texts:
            logger.info(f"\nInput: {text}")
            
            # Tokenize
            inputs = self.tokenizer(text, return_tensors="pt", truncation=True, padding=True)
            
            # Predict
            with torch.no_grad():
                outputs = model(**inputs)
                predictions = torch.argmax(outputs.logits, dim=2)
            
            # Convert predictions to labels
            tokens = self.tokenizer.convert_ids_to_tokens(inputs["input_ids"][0])
            predicted_labels = [self.id2label[p.item()] for p in predictions[0]]
            
            # Extract entities
            entities = []
            current_entity = None
            
            for token, label in zip(tokens, predicted_labels):
                if label.startswith("B-"):
                    if current_entity:
                        entities.append(current_entity)
                    current_entity = {"type": label[2:], "text": token.replace("##", "")}
                elif label.startswith("I-") and current_entity:
                    current_entity["text"] += token.replace("##", "")
                else:
                    if current_entity:
                        entities.append(current_entity)
                        current_entity = None
            
            if current_entity:
                entities.append(current_entity)
            
            # Clean up special tokens
            entities = [e for e in entities if not e["text"] in ["[CLS]", "[SEP]", "[PAD]"]]
            
            logger.info(f"Entities: {entities}")
        
        logger.info("="*50)

def main():
    """Main training execution"""
    
    trainer = NERTrainer()
    
    # Train model
    metrics = trainer.train()
    
    # Check if target met
    if metrics.get("eval_f1", 0) >= 0.85:
        logger.info("\n✅ SUCCESS: F1 score >= 0.85 target achieved!")
    else:
        logger.warning(f"\n⚠️ F1 score {metrics.get('eval_f1', 0):.4f} < 0.85 target")
        logger.info("Consider adding more training data or adjusting hyperparameters")
    
    # Test model
    trainer.test_model()
    
    logger.info("\n" + "="*50)
    logger.info("DEPLOYMENT READY")
    logger.info("="*50)
    logger.info(f"Model saved to: {trainer.output_dir}")
    logger.info("To deploy on Render.com:")
    logger.info("1. Update Dockerfile to include model")
    logger.info("2. Mount persistent disk at /data")
    logger.info("3. Load model in enhanced_spec_analyzer.py")
    logger.info("4. git push origin main")
    logger.info("="*50)

if __name__ == "__main__":
    main()
