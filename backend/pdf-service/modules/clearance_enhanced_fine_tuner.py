#!/usr/bin/env python3
"""
Enhanced NER Fine-Tuning for Clearances and Separations
Combines overhead + clearance data to achieve F1 >0.9
Focus on railroad crossings, ground clearances, and G.O. 95 compliance
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Any
import torch
import numpy as np
from datasets import Dataset, DatasetDict
from transformers import (
    AutoTokenizer,
    AutoModelForTokenClassification,
    TrainingArguments,
    Trainer,
    DataCollatorForTokenClassification
)
from peft import get_peft_model, LoraConfig
import evaluate

logger = logging.getLogger(__name__)

class ClearanceEnhancedFineTuner:
    """Fine-tunes NER for clearances combining overhead + clearance-specific data"""
    
    def __init__(self, 
                 overhead_data_path: str = "/data/training/overhead_ner_annotations.json",
                 clearance_data_path: str = "/data/training/clearance_ner_annotations.json",
                 output_dir: str = "/data/fine_tuned_clearances"):
        
        self.overhead_data_path = Path(overhead_data_path)
        self.clearance_data_path = Path(clearance_data_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.base_model = "distilbert-base-uncased"
        
        # Define all labels for the model
        self.labels = [
            "O", "B-MATERIAL", "I-MATERIAL", "B-MEASURE", "I-MEASURE",
            "B-INSTALLATION", "I-INSTALLATION", "B-SPECIFICATION", "I-SPECIFICATION",
            "B-EQUIPMENT", "I-EQUIPMENT", "B-STANDARD", "I-STANDARD",
            "B-LOCATION", "I-LOCATION"
        ]
        self.label2id = {label: i for i, label in enumerate(self.labels)}
        self.id2label = {i: label for i, label in enumerate(self.labels)}
        
        self.tokenizer = AutoTokenizer.from_pretrained(self.base_model)
    
    def _load_and_combine_data(self) -> List[Dict]:
        """Load and combine overhead + clearance annotations"""
        
        all_annotations = []
        
        # Load overhead data if exists
        if self.overhead_data_path.exists():
            with open(self.overhead_data_path, 'r') as f:
                overhead_data = json.load(f)["annotations"]
                all_annotations.extend(overhead_data)
                logger.info(f"Loaded {len(overhead_data)} overhead annotations")
        
        # Load clearance data
        if not self.clearance_data_path.exists():
            raise FileNotFoundError(f"Clearance data not found: {self.clearance_data_path}")
        
        with open(self.clearance_data_path, 'r') as f:
            clearance_data = json.load(f)["annotations"]
            all_annotations.extend(clearance_data)
            logger.info(f"Loaded {len(clearance_data)} clearance annotations")
        
        logger.info(f"Total annotations: {len(all_annotations)}")
        return all_annotations
    
    def _prepare_dataset(self) -> DatasetDict:
        """Prepare combined dataset for training"""
        
        raw_data = self._load_and_combine_data()
        
        # Convert annotations to BIO format
        processed_data = []
        total_tokens = 0
        
        for item in raw_data:
            text = item["text"]
            tokens = self.tokenizer.tokenize(text)
            labels = ['O'] * len(tokens)
            
            for entity in item["entities"]:
                entity_text = entity["text"]
                entity_label = entity["label"]
                
                # Find start and end tokens for the entity
                entity_tokens = self.tokenizer.tokenize(entity_text)
                
                for i in range(len(tokens) - len(entity_tokens) + 1):
                    if tokens[i:i+len(entity_tokens)] == entity_tokens:
                        labels[i] = f"B-{entity_label}"
                        for j in range(1, len(entity_tokens)):
                            labels[i+j] = f"I-{entity_label}"
                        break
            
            processed_data.append({"tokens": tokens, "ner_tags": [self.label2id[l] for l in labels]})
            total_tokens += len(tokens)
        
        logger.info(f"Total tokens in dataset: {total_tokens} (target: 800-1000)")
        
        # Create Hugging Face Dataset
        dataset = Dataset.from_list(processed_data)
        
        # Split into train/test (80/20)
        return dataset.train_test_split(test_size=0.2, seed=42)
    
    def _align_labels_with_tokens(self, labels, word_ids):
        """Align token-level labels with word-level labels"""
        new_labels = []
        current_word = None
        for word_id in word_ids:
            if word_id != current_word:
                current_word = word_id
                label = -100 if word_id is None else labels[word_id]
                new_labels.append(label)
            elif word_id is None:
                new_labels.append(-100)
            else:
                new_labels.append(-100)  # Only label the first token of a word
        return new_labels

    def _tokenize_and_align_labels(self, examples):
        """Tokenize text and align labels for the trainer"""
        tokenized_inputs = self.tokenizer(
            examples["tokens"], 
            truncation=True, 
            is_split_into_words=True,
            max_length=128,
            padding=True
        )
        all_labels = examples["ner_tags"]
        new_labels = []
        for i, labels in enumerate(all_labels):
            word_ids = tokenized_inputs.word_ids(i)
            new_labels.append(self._align_labels_with_tokens(labels, word_ids))
        
        tokenized_inputs["labels"] = new_labels
        return tokenized_inputs
    
    def train(self) -> Dict[str, Any]:
        """
        Fine-tune the NER model with LoRA for F1 >0.9
        
        Returns:
            Training metrics and model path
        """
        
        logger.info("Starting enhanced clearance NER fine-tuning (target F1 >0.9)...")
        
        # 1. Prepare combined dataset
        try:
            tokenized_datasets = self._prepare_dataset().map(
                self._tokenize_and_align_labels, 
                batched=True
            )
        except FileNotFoundError as e:
            logger.error(e)
            return {"error": str(e)}

        # 2. Initialize model and apply LoRA
        model = AutoModelForTokenClassification.from_pretrained(
            self.base_model,
            id2label=self.id2label,
            label2id=self.label2id,
        )
        
        # Enhanced LoRA configuration for F1 >0.9
        lora_config = LoraConfig(
            r=12,  # Increased from 8 for better capacity
            lora_alpha=24,  # Increased proportionally
            target_modules=["q_lin", "v_lin"],  # For DistilBERT
            lora_dropout=0.05,  # Reduced dropout for better learning
            bias="none",
            task_type="TOKEN_CLS"
        )
        
        model = get_peft_model(model, lora_config)
        model.print_trainable_parameters()
        
        # 3. Set up Trainer
        data_collator = DataCollatorForTokenClassification(tokenizer=self.tokenizer)
        
        # Metrics
        seqeval = evaluate.load("seqeval")
        
        def compute_metrics(p):
            predictions, labels = p
            predictions = np.argmax(predictions, axis=2)

            true_predictions = [
                [self.labels[p] for (p, l) in zip(prediction, label) if l != -100]
                for prediction, label in zip(predictions, labels)
            ]
            true_labels = [
                [self.labels[l] for (p, l) in zip(prediction, label) if l != -100]
                for prediction, label in zip(predictions, labels)
            ]

            results = seqeval.compute(predictions=true_predictions, references=true_labels)
            
            # Add per-entity metrics for key categories
            entity_results = {}
            for entity_type in ["MEASURE", "STANDARD", "LOCATION", "SPECIFICATION"]:
                entity_predictions = []
                entity_labels = []
                
                for pred_seq, label_seq in zip(true_predictions, true_labels):
                    entity_pred = [1 if entity_type in p else 0 for p in pred_seq]
                    entity_label = [1 if entity_type in l else 0 for l in label_seq]
                    entity_predictions.extend(entity_pred)
                    entity_labels.extend(entity_label)
                
                if sum(entity_labels) > 0:
                    from sklearn.metrics import f1_score, precision_score, recall_score
                    entity_results[f"{entity_type}_f1"] = f1_score(entity_labels, entity_predictions)
                    entity_results[f"{entity_type}_precision"] = precision_score(entity_labels, entity_predictions)
                    entity_results[f"{entity_type}_recall"] = recall_score(entity_labels, entity_predictions)
            
            return {
                "precision": results["overall_precision"],
                "recall": results["overall_recall"],
                "f1": results["overall_f1"],
                "accuracy": results["overall_accuracy"],
                **entity_results
            }

        # Enhanced training arguments for F1 >0.9
        training_args = TrainingArguments(
            output_dir=str(self.output_dir / "results"),
            num_train_epochs=25,  # More epochs for better convergence
            per_device_train_batch_size=16,  # Larger batch for stability
            per_device_eval_batch_size=16,
            evaluation_strategy="epoch",
            save_strategy="epoch",
            logging_steps=5,
            learning_rate=3e-4,  # Slightly higher for faster convergence
            load_best_model_at_end=True,
            metric_for_best_model="f1",
            greater_is_better=True,
            warmup_steps=200,
            weight_decay=0.01,
            gradient_accumulation_steps=2,  # Effective batch size of 32
            fp16=torch.cuda.is_available(),  # Use mixed precision if GPU available
            push_to_hub=False,
        )
        
        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=tokenized_datasets["train"],
            eval_dataset=tokenized_datasets["test"],
            data_collator=data_collator,
            tokenizer=self.tokenizer,
            compute_metrics=compute_metrics,
        )
        
        # 4. Train
        logger.info("Training model for clearance entities (target F1 >0.9)...")
        train_result = trainer.train()
        
        # 5. Save model and tokenizer
        logger.info(f"Saving fine-tuned model to {self.output_dir}")
        trainer.save_model(str(self.output_dir))
        self.tokenizer.save_pretrained(str(self.output_dir))
        
        # 6. Evaluate and return metrics
        metrics = trainer.evaluate()
        logger.info(f"Final F1 Score: {metrics['eval_f1']:.4f}")
        
        # Check entity-specific performance
        clearance_metrics = {
            "MEASURE": metrics.get('eval_MEASURE_f1', 0),
            "STANDARD": metrics.get('eval_STANDARD_f1', 0),
            "LOCATION": metrics.get('eval_LOCATION_f1', 0),
            "SPECIFICATION": metrics.get('eval_SPECIFICATION_f1', 0)
        }
        
        logger.info(f"Entity-specific F1 scores: {clearance_metrics}")
        
        return {
            "message": "Fine-tuning complete",
            "model_path": str(self.output_dir),
            "f1_score": metrics['eval_f1'],
            "precision": metrics['eval_precision'],
            "recall": metrics['eval_recall'],
            "entity_scores": clearance_metrics,
            "target_met": metrics['eval_f1'] >= 0.9
        }

# API Integration
def integrate_clearance_fine_tuning_endpoints(app):
    """Add clearance fine-tuning endpoints to FastAPI app"""
    
    from fastapi import APIRouter, BackgroundTasks, HTTPException
    from pydantic import BaseModel
    from typing import Dict
    
    router = APIRouter(prefix="/fine-tune-clearances", tags=["Clearance NER Fine-Tuning"])
    
    class TrainingStatus(BaseModel):
        status: str
        model_path: str = None
        f1_score: float = None
        entity_scores: Dict[str, float] = None
        target_met: bool = False
    
    @router.post("/start")
    async def start_clearance_fine_tuning(background_tasks: BackgroundTasks):
        """
        Start clearance NER fine-tuning combining overhead + clearance data.
        Target: F1 score > 0.9 for clearance entities.
        Dataset: 800-1000 tokens from railroad/ground clearance specs.
        """
        
        def run_training():
            tuner = ClearanceEnhancedFineTuner()
            results = tuner.train()
            
            # Log results
            with open("/data/clearance_finetune_results.json", "w") as f:
                json.dump(results, f, indent=2)
        
        background_tasks.add_task(run_training)
        
        return {
            "message": "Clearance NER fine-tuning started in background.",
            "dataset_size": "800-1000 tokens (overhead + clearance)",
            "target_f1": 0.9,
            "check_status_at": "/fine-tune-clearances/status",
            "expected_time": "45-90 minutes on CPU"
        }
    
    @router.get("/status", response_model=TrainingStatus)
    async def get_clearance_fine_tuning_status():
        """Get the status and results of clearance fine-tuning."""
        
        results_path = Path("/data/clearance_finetune_results.json")
        
        if not results_path.exists():
            # Check if training is in progress
            temp_path = Path("/data/fine_tuned_clearances/results")
            if temp_path.exists():
                return TrainingStatus(status="training_in_progress")
            else:
                raise HTTPException(404, "No fine-tuning results found. Start training first.")
        
        with open(results_path, 'r') as f:
            results = json.load(f)
        
        return TrainingStatus(
            status="completed",
            model_path=results.get("model_path"),
            f1_score=results.get("f1_score"),
            entity_scores=results.get("entity_scores"),
            target_met=results.get("target_met", False)
        )
    
    @router.get("/entities")
    async def list_clearance_entities():
        """List the clearance-specific entities the model recognizes."""
        
        return {
            "focus_entities": [
                "MEASURE (8'-6\", 60°F, 750V, clearances)",
                "STANDARD (G.O. 95, Rule 37, Table 1)",
                "LOCATION (railroad tracks, tangent, curved)",
                "SPECIFICATION (minimum requirements, shall apply)"
            ],
            "total_training_examples": 36,  # 20 overhead + 16 clearance
            "documents_used": [
                "022822 Railroad track clearances",
                "022187 Vertical Separation", 
                "022158 Clearance Tables G.O. 95",
                "066198 Equipment Clearances",
                "Plus 9 overhead documents"
            ],
            "target_performance": "F1 >0.9 for clearance entities"
        }
    
    app.include_router(router)
    logger.info("✅ Clearance fine-tuning endpoints added: /fine-tune-clearances/*")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Example of running the fine-tuner directly
    tuner = ClearanceEnhancedFineTuner(
        overhead_data_path="./data/training/overhead_ner_annotations.json",
        clearance_data_path="./data/training/clearance_ner_annotations.json",
        output_dir="./fine_tuned_clearances_test"
    )
    
    results = tuner.train()
    print("\n--- Clearance Fine-Tuning Results ---")
    print(json.dumps(results, indent=2))
