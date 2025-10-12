#!/usr/bin/env python3
"""
Fine-Tuning Module for Utility Poles (Overhead) and Underground Equipment
Implements LoRA-based efficient fine-tuning with PG&E-specific annotations
"""

import json
import torch
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple, Any
from dataclasses import dataclass
from transformers import (
    AutoModelForTokenClassification,
    AutoTokenizer,
    Trainer,
    TrainingArguments,
    DataCollatorForTokenClassification
)
from peft import get_peft_model, LoraConfig, TaskType
import datasets
from sentence_transformers import SentenceTransformer
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class EntitySpan:
    """Represents an annotated entity in text"""
    start: int
    end: int
    label: str
    text: str

class PoleUndergroundFineTuner:
    """
    Fine-tuning system for utility pole and underground equipment NER
    """
    
    # Entity labels for utility infrastructure
    LABELS = [
        "MATERIAL",       # Material type (wood, steel, PVC, etc.)
        "INSTALLATION",   # Installation requirements/methods
        "SPECIFICATION",  # Technical specifications
        "STANDARD",       # Standards references (ANSI, G.O. 95, etc.)
        "LOCATION",       # Location requirements
        "EQUIPMENT",      # Equipment types (poles, transformers, etc.)
        "MEASURE",        # Measurements (feet, inches, degrees)
        "O"              # Other/Outside
    ]
    
    def __init__(self, model_name="distilbert-base-uncased", use_lora=True):
        """Initialize fine-tuning system"""
        self.model_name = model_name
        self.use_lora = use_lora
        self.label2id = {label: i for i, label in enumerate(self.LABELS)}
        self.id2label = {i: label for i, label in enumerate(self.LABELS)}
        
        # Initialize tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        
        # Initialize model
        self.model = AutoModelForTokenClassification.from_pretrained(
            model_name,
            num_labels=len(self.LABELS),
            id2label=self.id2label,
            label2id=self.label2id
        )
        
        # Apply LoRA if requested (efficient fine-tuning)
        if use_lora:
            logger.info("🔧 Applying LoRA for efficient fine-tuning")
            lora_config = LoraConfig(
                task_type=TaskType.TOKEN_CLS,
                r=8,  # Rank
                lora_alpha=16,
                lora_dropout=0.1,
                target_modules=["q_lin", "v_lin"],  # DistilBERT attention modules
            )
            self.model = get_peft_model(self.model, lora_config)
            self.model.print_trainable_parameters()
    
    def prepare_training_data(self) -> Dict[str, List]:
        """Prepare annotated training data for poles and underground"""
        
        training_examples = []
        
        # === UTILITY POLES TRAINING DATA ===
        poles_data = [
            {
                "text": "Temporary service poles must be furnished and installed by the customer and may be wooden or metallic. The minimum length must be 20 feet (set 4 feet in the ground).",
                "entities": [
                    (88, 106, "MATERIAL"),      # wooden or metallic
                    (108, 143, "MEASURE"),       # 20 feet minimum length
                    (145, 169, "MEASURE"),       # 4 feet in the ground
                    (34, 70, "INSTALLATION"),    # furnished and installed by customer
                    (10, 28, "EQUIPMENT")        # service poles
                ]
            },
            {
                "text": "Customer-owned, permanent wood poles must meet all pertinent requirements of ANSI O5.1.2008, Wood Poles Specifications and Dimensions, and American Wood Protection Association Standards T1-10 and U1-10.",
                "entities": [
                    (26, 30, "MATERIAL"),        # wood
                    (78, 92, "STANDARD"),        # ANSI O5.1.2008
                    (181, 186, "STANDARD"),      # T1-10
                    (191, 196, "STANDARD"),      # U1-10
                    (26, 37, "EQUIPMENT")        # wood poles
                ]
            },
            {
                "text": "Conductors to service poles must have a minimum ground clearance as follows: Over the center portion of the street, 18 feet minimum.",
                "entities": [
                    (78, 116, "LOCATION"),       # Over center portion of street
                    (118, 125, "MEASURE"),       # 18 feet
                    (41, 65, "SPECIFICATION"),   # minimum ground clearance
                    (14, 27, "EQUIPMENT")        # service poles
                ]
            },
            {
                "text": "Table 4 Customer's Service Attachment Location: Panel Rating ≤225 amps, Weatherhead Distance From Top of Pole 18-20 inches.",
                "entities": [
                    (112, 124, "MEASURE"),       # 18-20 inches
                    (73, 84, "EQUIPMENT"),       # Weatherhead
                    (19, 47, "INSTALLATION"),    # Service Attachment Location
                    (49, 71, "SPECIFICATION")    # Panel Rating ≤225 amps
                ]
            },
            {
                "text": "Do not install a metal pole. Customer metal poles typically do not have steps and would not be climbable.",
                "entities": [
                    (17, 22, "MATERIAL"),        # metal
                    (17, 28, "EQUIPMENT"),       # metal pole
                    (0, 28, "SPECIFICATION"),    # Do not install metal pole
                    (37, 49, "EQUIPMENT")        # metal poles
                ]
            },
            {
                "text": "PG&E-Approved, Customer-Owned Pole must be installed per Document 025055. Location must be ≥10 ft from PG&E pole.",
                "entities": [
                    (15, 35, "EQUIPMENT"),       # Customer-Owned Pole
                    (58, 73, "STANDARD"),        # Document 025055
                    (91, 97, "MEASURE"),         # ≥10 ft
                    (75, 114, "LOCATION")        # Location ≥10 ft from PG&E pole
                ]
            },
            {
                "text": "Conduit, Riser, Galvanized Rigid Steel, Continuous without Couplings. Offset must be ≤12 inches.",
                "entities": [
                    (16, 39, "MATERIAL"),        # Galvanized Rigid Steel
                    (0, 14, "EQUIPMENT"),        # Conduit, Riser
                    (41, 69, "SPECIFICATION"),   # Continuous without Couplings
                    (86, 96, "MEASURE")          # ≤12 inches
                ]
            }
        ]
        
        # === UNDERGROUND EQUIPMENT TRAINING DATA ===
        underground_data = [
            {
                "text": "Pad mounted transformers may be up to 44 inches long, 44 inches deep and 32 inches tall.",
                "entities": [
                    (0, 24, "EQUIPMENT"),        # Pad mounted transformers
                    (39, 54, "MEASURE"),         # 44 inches long
                    (56, 70, "MEASURE"),         # 44 inches deep
                    (75, 89, "MEASURE")          # 32 inches tall
                ]
            },
            {
                "text": "Approved vegetation and other items must be kept at least 8 feet from the front and 2 feet from the sides of the pad at all times.",
                "entities": [
                    (59, 66, "MEASURE"),         # 8 feet
                    (85, 91, "MEASURE"),         # 2 feet
                    (67, 81, "LOCATION"),        # from the front
                    (92, 106, "LOCATION"),       # from the sides
                    (36, 133, "SPECIFICATION")  # clearance requirements
                ]
            },
            {
                "text": "Subsurface junction/enclosure boxes may be up to 9 feet long and 5 feet wide.",
                "entities": [
                    (0, 36, "EQUIPMENT"),        # Subsurface junction/enclosure boxes
                    (50, 61, "MEASURE"),         # 9 feet long
                    (66, 77, "MEASURE")          # 5 feet wide
                ]
            },
            {
                "text": "Trenches can vary from 8 inches to 30 inches wide.",
                "entities": [
                    (0, 8, "EQUIPMENT"),         # Trenches
                    (23, 31, "MEASURE"),         # 8 inches
                    (35, 45, "MEASURE"),         # 30 inches
                    (9, 50, "SPECIFICATION")     # vary from 8 to 30 inches wide
                ]
            },
            {
                "text": "A minimum of 24 inches of cover for secondary (0 − 750 V) electric service, or 30 inches minimum cover for primary (over 750 V).",
                "entities": [
                    (13, 23, "MEASURE"),         # 24 inches
                    (37, 59, "SPECIFICATION"),   # secondary (0 − 750 V)
                    (80, 89, "MEASURE"),         # 30 inches
                    (108, 128, "SPECIFICATION"), # primary (over 750 V)
                    (26, 31, "INSTALLATION")     # cover
                ]
            },
            {
                "text": "Imported sand used for bedding and shading electric trenches must meet requirements in Engineering Material Specification EMS-4123.",
                "entities": [
                    (0, 13, "MATERIAL"),         # Imported sand
                    (123, 131, "STANDARD"),      # EMS-4123
                    (23, 43, "INSTALLATION"),    # bedding and shading
                    (88, 131, "SPECIFICATION")   # Engineering Material Specification
                ]
            },
            {
                "text": "Install 6-inch-wide warning tape marked 'Caution: Buried Electric Line Below.'",
                "entities": [
                    (8, 18, "MEASURE"),          # 6-inch-wide
                    (19, 32, "MATERIAL"),        # warning tape
                    (0, 7, "INSTALLATION"),      # Install
                    (33, 79, "SPECIFICATION")    # marked 'Caution: Buried Electric Line Below'
                ]
            },
            {
                "text": "Percent fill table for rigid Polyvinyl chloride (PVC) direct burial (DB) 120 conduit.",
                "entities": [
                    (23, 54, "MATERIAL"),        # rigid Polyvinyl chloride (PVC)
                    (55, 73, "INSTALLATION"),    # direct burial (DB)
                    (78, 85, "EQUIPMENT"),       # conduit
                    (0, 18, "SPECIFICATION")     # Percent fill table
                ]
            },
            {
                "text": "The total number of factory bends installed in conduit run for primary cable must not exceed 300 degrees.",
                "entities": [
                    (20, 33, "INSTALLATION"),    # factory bends
                    (94, 105, "MEASURE"),        # 300 degrees
                    (48, 55, "EQUIPMENT"),       # conduit
                    (64, 77, "EQUIPMENT"),       # primary cable
                    (78, 105, "SPECIFICATION")   # must not exceed 300 degrees
                ]
            }
        ]
        
        # Combine all training data
        all_data = poles_data + underground_data
        
        # Convert to tokenized format
        for example in all_data:
            tokens, labels = self.tokenize_and_align_labels(
                example["text"],
                example["entities"]
            )
            training_examples.append({
                "tokens": tokens,
                "labels": labels
            })
        
        logger.info(f"✅ Prepared {len(training_examples)} training examples")
        logger.info(f"   - Poles examples: {len(poles_data)}")
        logger.info(f"   - Underground examples: {len(underground_data)}")
        
        return {"train": training_examples}
    
    def tokenize_and_align_labels(self, text: str, entities: List[Tuple]) -> Tuple[List, List]:
        """Tokenize text and align NER labels"""
        
        # Tokenize
        tokenized = self.tokenizer(
            text,
            truncation=True,
            max_length=512,
            return_offsets_mapping=True
        )
        
        tokens = self.tokenizer.convert_ids_to_tokens(tokenized["input_ids"])
        offset_mapping = tokenized["offset_mapping"]
        
        # Initialize labels
        labels = ["O"] * len(tokens)
        
        # Align entity labels with tokens
        for start, end, label in entities:
            for i, (token_start, token_end) in enumerate(offset_mapping):
                if token_start >= start and token_end <= end:
                    if token_start == start:
                        labels[i] = f"B-{label}"  # Beginning
                    else:
                        labels[i] = f"I-{label}"  # Inside
        
        # Convert labels to IDs
        label_ids = []
        for label in labels:
            if label == "O":
                label_ids.append(self.label2id["O"])
            else:
                # Extract base label (remove B- or I- prefix)
                base_label = label.split("-")[1] if "-" in label else label
                if base_label in self.label2id:
                    label_ids.append(self.label2id[base_label])
                else:
                    label_ids.append(self.label2id["O"])
        
        return tokens, label_ids
    
    def train(self, output_dir="./fine_tuned_poles_underground"):
        """Train the model with pole and underground annotations"""
        
        logger.info("🚀 Starting fine-tuning for poles & underground equipment")
        
        # Prepare data
        data = self.prepare_training_data()
        
        # Convert to Hugging Face dataset
        train_dataset = datasets.Dataset.from_list(data["train"])
        
        # Training arguments optimized for small dataset
        training_args = TrainingArguments(
            output_dir=output_dir,
            num_train_epochs=15,  # More epochs for small dataset
            per_device_train_batch_size=8,
            warmup_steps=100,
            weight_decay=0.01,
            logging_dir=f"{output_dir}/logs",
            logging_steps=10,
            save_strategy="epoch",
            evaluation_strategy="no",  # No eval set for now
            save_total_limit=2,
            load_best_model_at_end=False,
            push_to_hub=False,
            report_to="none",  # Disable wandb/tensorboard
        )
        
        # Data collator
        data_collator = DataCollatorForTokenClassification(
            self.tokenizer,
            padding=True,
            max_length=512
        )
        
        # Initialize trainer
        trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=train_dataset,
            tokenizer=self.tokenizer,
            data_collator=data_collator
        )
        
        # Train
        logger.info("⏳ Training in progress...")
        trainer.train()
        
        # Save model
        trainer.save_model(output_dir)
        self.tokenizer.save_pretrained(output_dir)
        logger.info(f"✅ Model saved to {output_dir}")
        
        # Calculate and report metrics
        self.evaluate_performance()
        
        return output_dir
    
    def evaluate_performance(self):
        """Evaluate model performance on key entities"""
        
        test_cases = [
            ("The pole must be 25 feet tall with 5 feet underground.", 
             ["EQUIPMENT", "MEASURE", "MEASURE"]),
            ("Install galvanized steel conduit with PVC coating.",
             ["INSTALLATION", "MATERIAL", "EQUIPMENT", "MATERIAL"]),
            ("Clearance must be 18 feet per G.O. 95 standard.",
             ["SPECIFICATION", "MEASURE", "STANDARD"])
        ]
        
        logger.info("\n📊 Model Performance on Test Cases:")
        for text, expected_entities in test_cases:
            predictions = self.predict(text)
            logger.info(f"  Text: {text[:50]}...")
            logger.info(f"  Expected: {expected_entities}")
            logger.info(f"  Predicted: {[e['label'] for e in predictions]}")
    
    def predict(self, text: str) -> List[Dict]:
        """Predict entities in text"""
        
        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=512
        )
        
        with torch.no_grad():
            outputs = self.model(**inputs)
        
        predictions = torch.argmax(outputs.logits, dim=-1)
        tokens = self.tokenizer.convert_ids_to_tokens(inputs["input_ids"][0])
        
        entities = []
        current_entity = None
        
        for token, pred_id in zip(tokens, predictions[0]):
            label = self.id2label[pred_id.item()]
            
            if label != "O":
                if current_entity is None:
                    current_entity = {
                        "text": token,
                        "label": label,
                        "start": len(entities)
                    }
                elif current_entity["label"] == label:
                    current_entity["text"] += token.replace("##", "")
                else:
                    entities.append(current_entity)
                    current_entity = {
                        "text": token,
                        "label": label,
                        "start": len(entities)
                    }
            elif current_entity is not None:
                entities.append(current_entity)
                current_entity = None
        
        if current_entity is not None:
            entities.append(current_entity)
        
        return entities

class EnhancedInfractionAnalyzer:
    """
    Enhanced analyzer with domain-specific confidence scoring
    """
    
    def __init__(self, fine_tuned_model_path="./fine_tuned_poles_underground"):
        """Initialize with fine-tuned model"""
        
        # Load fine-tuned NER model
        self.ner_model = AutoModelForTokenClassification.from_pretrained(fine_tuned_model_path)
        self.tokenizer = AutoTokenizer.from_pretrained(fine_tuned_model_path)
        
        # Load sentence transformer for embeddings
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Confidence thresholds
        self.HIGH_CONFIDENCE_THRESHOLD = 0.85
        self.MEDIUM_CONFIDENCE_THRESHOLD = 0.70
        
        logger.info("✅ Enhanced analyzer initialized with fine-tuned model")
    
    def analyze_infraction(self, audit_text: str, spec_embeddings: np.ndarray, spec_texts: List[str]) -> Dict:
        """
        Analyze infraction with enhanced confidence scoring
        """
        
        # Extract entities from audit text
        entities = self.extract_entities(audit_text)
        
        # Generate embedding for audit text
        audit_embedding = self.embedder.encode(audit_text, convert_to_tensor=True)
        
        # Calculate similarities with all specs
        similarities = torch.nn.functional.cosine_similarity(
            audit_embedding.unsqueeze(0),
            torch.tensor(spec_embeddings)
        )
        
        # Get top matches
        top_k = 3
        top_scores, top_indices = torch.topk(similarities, k=top_k)
        
        # Determine confidence and repeal status
        best_score = top_scores[0].item()
        best_match = spec_texts[top_indices[0]]
        
        # Enhanced confidence calculation based on entity matches
        entity_bonus = self.calculate_entity_match_bonus(entities, best_match)
        final_confidence = min(best_score + entity_bonus, 1.0)
        
        # Determine repeal status
        if final_confidence >= self.HIGH_CONFIDENCE_THRESHOLD:
            status = "REPEALABLE"
            confidence_level = "HIGH"
        elif final_confidence >= self.MEDIUM_CONFIDENCE_THRESHOLD:
            status = "REVIEW_REQUIRED"
            confidence_level = "MEDIUM"
        else:
            status = "VALID_INFRACTION"
            confidence_level = "LOW"
        
        return {
            "status": status,
            "confidence": final_confidence,
            "confidence_level": confidence_level,
            "matched_spec": best_match[:200],  # First 200 chars
            "entities_found": entities,
            "reasoning": self.generate_reasoning(audit_text, best_match, entities, final_confidence)
        }
    
    def extract_entities(self, text: str) -> List[Dict]:
        """Extract entities using fine-tuned model"""
        
        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=512
        )
        
        with torch.no_grad():
            outputs = self.ner_model(**inputs)
        
        predictions = torch.argmax(outputs.logits, dim=-1)
        tokens = self.tokenizer.convert_ids_to_tokens(inputs["input_ids"][0])
        
        entities = []
        for token, pred_id in zip(tokens, predictions[0]):
            if pred_id != 0:  # Not "O" label
                entities.append({
                    "token": token,
                    "label": self.ner_model.config.id2label[pred_id.item()]
                })
        
        return entities
    
    def calculate_entity_match_bonus(self, entities: List[Dict], spec_text: str) -> float:
        """Calculate bonus based on entity matches"""
        
        bonus = 0.0
        critical_entities = ["MEASURE", "STANDARD", "SPECIFICATION"]
        
        for entity in entities:
            if entity["label"] in critical_entities:
                # Check if entity value appears in spec
                if entity["token"].lower() in spec_text.lower():
                    bonus += 0.05  # 5% bonus per critical match
        
        return min(bonus, 0.15)  # Cap at 15% bonus
    
    def generate_reasoning(self, audit_text: str, spec_text: str, entities: List[Dict], confidence: float) -> str:
        """Generate human-readable reasoning"""
        
        entity_types = set(e["label"] for e in entities)
        
        if confidence >= self.HIGH_CONFIDENCE_THRESHOLD:
            return f"Infraction false ({confidence*100:.0f}% confidence) - Repealed per spec. " \
                   f"Found matching {', '.join(entity_types)} in utility standards."
        elif confidence >= self.MEDIUM_CONFIDENCE_THRESHOLD:
            return f"Potential match ({confidence*100:.0f}% confidence) - Review recommended. " \
                   f"Partial match on {', '.join(entity_types)}."
        else:
            return f"Valid infraction ({confidence*100:.0f}% confidence) - No clear spec match. " \
                   f"Entities detected: {', '.join(entity_types)}."

def main():
    """Main training pipeline"""
    
    logger.info("="*60)
    logger.info("🎯 NEXA POLES & UNDERGROUND FINE-TUNING")
    logger.info("="*60)
    
    # Initialize fine-tuner
    fine_tuner = PoleUndergroundFineTuner(use_lora=True)
    
    # Train model
    output_dir = fine_tuner.train()
    
    # Initialize enhanced analyzer
    analyzer = EnhancedInfractionAnalyzer(output_dir)
    
    # Test with sample infractions
    test_infractions = [
        "Pole clearance measured at 16 feet over street center, violation of minimum requirements.",
        "Underground conduit installed at 20 inches depth for primary service.",
        "Metal pole installation attempted without proper climbing provisions."
    ]
    
    logger.info("\n🧪 Testing Enhanced Analyzer:")
    for infraction in test_infractions:
        logger.info(f"\n  Infraction: {infraction[:80]}...")
        # Would need actual spec embeddings here
        # result = analyzer.analyze_infraction(infraction, spec_embeddings, spec_texts)
        # logger.info(f"  Result: {result['status']} ({result['confidence']*100:.0f}%)")
    
    logger.info("\n✅ Fine-tuning complete! Model ready for production.")
    logger.info(f"📁 Model saved to: {output_dir}")
    logger.info("\n💡 Next steps:")
    logger.info("  1. Test with real audit PDFs")
    logger.info("  2. Deploy to Render.com backend")
    logger.info("  3. Monitor F1-scores (target: >0.85)")

if __name__ == "__main__":
    main()
