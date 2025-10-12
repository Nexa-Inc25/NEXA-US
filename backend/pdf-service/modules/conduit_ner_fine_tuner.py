#!/usr/bin/env python3
"""
NER Fine-Tuning for Underground Conduits
Enhances NER model to understand conduit materials, depths, and installation requirements
Target: F1-score > 0.9 for conduit-related entities
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

class ConduitNERFineTuner:
    """Fine-tunes a DistilBERT model for conduit-specific NER"""
    
    def __init__(self, 
                 data_path: str = "/data/training/conduit_ner_annotations.json",
                 output_dir: str = "/data/fine_tuned_conduits"):
        
        self.data_path = Path(data_path)
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
    
    def _load_and_prepare_data(self) -> DatasetDict:
        """Load annotated data and prepare it for training"""
        
        if not self.data_path.exists():
            raise FileNotFoundError(f"Annotation file not found: {self.data_path}")
        
        with open(self.data_path, 'r') as f:
            raw_data = json.load(f)["annotations"]
        
        # Convert annotations to BIO format
        processed_data = []
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
        
        # Create Hugging Face Dataset
        dataset = Dataset.from_list(processed_data)
        
        # Split into train/test
        return dataset.train_test_split(test_size=0.2)
    
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
                new_labels.append(-100) # Only label the first token of a word
        return new_labels

    def _tokenize_and_align_labels(self, examples):
        """Tokenize text and align labels for the trainer"""
        tokenized_inputs = self.tokenizer(
            examples["tokens"], 
            truncation=True, 
            is_split_into_words=True
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
        Fine-tune the NER model with LoRA for efficiency
        
        Returns:
            Training metrics and model path
        """
        
        logger.info("Starting conduit NER fine-tuning...")
        
        # 1. Load and prepare data
        try:
            tokenized_datasets = self._load_and_prepare_data().map(
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
        
        lora_config = LoraConfig(
            r=8,
            lora_alpha=16,
            target_modules=["q_lin", "v_lin"], # For DistilBERT
            lora_dropout=0.1,
            bias="none"
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
            return {
                "precision": results["overall_precision"],
                "recall": results["overall_recall"],
                "f1": results["overall_f1"],
                "accuracy": results["overall_accuracy"],
            }

        training_args = TrainingArguments(
            output_dir=str(self.output_dir / "results"),
            num_train_epochs=20,
            per_device_train_batch_size=8,
            per_device_eval_batch_size=8,
            evaluation_strategy="epoch",
            save_strategy="epoch",
            logging_steps=10,
            learning_rate=2e-4, # Higher LR for LoRA
            load_best_model_at_end=True,
            metric_for_best_model="f1",
            greater_is_better=True,
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
        logger.info("Training model...")
        train_result = trainer.train()
        
        # 5. Save model and tokenizer
        logger.info(f"Saving fine-tuned model to {self.output_dir}")
        trainer.save_model(str(self.output_dir))
        self.tokenizer.save_pretrained(str(self.output_dir))
        
        # 6. Evaluate and return metrics
        metrics = trainer.evaluate()
        logger.info(f"Final F1 Score: {metrics['eval_f1']:.4f}")
        
        return {
            "message": "Fine-tuning complete",
            "model_path": str(self.output_dir),
            "f1_score": metrics['eval_f1'],
            "target_met": metrics['eval_f1'] >= 0.9
        }

# API Integration
def integrate_conduit_ner_endpoints(app):
    """Add conduit NER fine-tuning endpoints to FastAPI app"""
    
    from fastapi import APIRouter, BackgroundTasks, HTTPException
    
    router = APIRouter(prefix="/fine-tune-conduits", tags=["Conduit NER Fine-Tuning"])
    
    @router.post("/start")
    async def start_conduit_ner_fine_tuning(background_tasks: BackgroundTasks):
        """
        Start conduit NER fine-tuning in the background.
        Target: F1 score > 0.9 for conduit entities.
        """
        
        def run_training():
            tuner = ConduitNERFineTuner()
            results = tuner.train()
            
            # Log results
            with open("/data/conduit_ner_finetune_results.json", "w") as f:
                json.dump(results, f, indent=2)
        
        background_tasks.add_task(run_training)
        
        return {
            "message": "Conduit NER fine-tuning started in background.",
            "check_status_at": "/data/conduit_ner_finetune_results.json"
        }
    
    @router.get("/status")
    async def get_fine_tuning_status():
        """Get the status and results of the last fine-tuning run."""
        results_path = Path("/data/conduit_ner_finetune_results.json")
        if not results_path.exists():
            raise HTTPException(404, "No fine-tuning results found.")
        
        with open(results_path, 'r') as f:
            return json.load(f)
    
    app.include_router(router)
    logger.info("✅ Conduit NER fine-tuning endpoints added: /fine-tune-conduits/start")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Example of running the fine-tuner directly
    tuner = ConduitNERFineTuner(
        data_path="./data/training/conduit_ner_annotations.json",
        output_dir="./fine_tuned_conduits_test"
    )
    
    results = tuner.train()
    print("\n--- Fine-Tuning Results ---")
    print(json.dumps(results, indent=2))
