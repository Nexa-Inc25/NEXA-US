#!/usr/bin/env python3
"""
Model Fine-Tuning System for NEXA
Handles domain-specific training for NER, embeddings, and YOLO models
Targets: NER F1 >0.85, YOLO mAP50-95 >0.6, Crossarm recall >0.5
"""

import os
import json
import pickle
import logging
import torch
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime
import random
from collections import defaultdict
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class TrainingConfig:
    """Configuration for model fine-tuning"""
    
    # Paths
    data_dir: str = "/data"
    models_dir: str = "/data/models"
    training_data_dir: str = "/data/training"
    
    # NER settings
    ner_model_name: str = "bert-base-uncased"
    ner_learning_rate: float = 2e-5
    ner_epochs: int = 20
    ner_batch_size: int = 16
    ner_patience: int = 5
    ner_target_f1: float = 0.85
    
    # Embedding settings
    embedding_model_name: str = "all-MiniLM-L6-v2"
    embedding_learning_rate: float = 2e-5
    embedding_epochs: int = 10
    embedding_batch_size: int = 32
    
    # YOLO settings
    yolo_model_name: str = "yolov8m.pt"
    yolo_epochs: int = 100
    yolo_patience: int = 30
    yolo_target_map: float = 0.6
    yolo_target_crossarm_recall: float = 0.5
    
    # Training settings
    val_split: float = 0.2
    test_split: float = 0.1
    seed: int = 42
    use_cuda: bool = torch.cuda.is_available()
    device: str = "cuda" if torch.cuda.is_available() else "cpu"
    
    # Monitoring
    log_interval: int = 10
    save_best_only: bool = True
    early_stopping: bool = True

class DataAugmenter:
    """Augments training data for better domain coverage"""
    
    def __init__(self, config: TrainingConfig):
        self.config = config
        self.synonyms = self._load_domain_synonyms()
    
    def _load_domain_synonyms(self) -> Dict[str, List[str]]:
        """Load domain-specific synonyms for augmentation"""
        
        return {
            # Utility domain synonyms
            "pole": ["post", "support structure", "utility pole"],
            "crossarm": ["cross-arm", "horizontal member", "attachment arm"],
            "clearance": ["spacing", "distance", "separation"],
            "voltage": ["electric potential", "electrical tension", "V"],
            "feet": ["ft", "foot", "'"],
            "inches": ["in", "inch", '"'],
            "specification": ["spec", "requirement", "standard"],
            "underground": ["UG", "buried", "subsurface"],
            "overhead": ["OH", "aerial", "above-ground"],
            "transformer": ["xfmr", "trans", "voltage converter"],
            "distribution": ["dist", "delivery", "power distribution"],
            "transmission": ["trans", "high-voltage", "bulk transfer"],
        }
    
    def augment_ner_data(self, examples: List[Dict]) -> List[Dict]:
        """
        Augment NER training data with variations
        
        Args:
            examples: List of NER training examples
            
        Returns:
            Augmented examples list
        """
        
        augmented = []
        
        for example in examples:
            # Original
            augmented.append(example)
            
            # Synonym replacement (non-entity words)
            text_tokens = example['text'].split()
            labels = example.get('labels', [])
            
            # Create variation with synonyms
            new_tokens = []
            for i, token in enumerate(text_tokens):
                token_lower = token.lower()
                
                # Check if token is not an entity
                is_entity = False
                if labels and i < len(labels):
                    is_entity = labels[i] != 'O'
                
                # Replace with synonym if not entity and available
                if not is_entity and token_lower in self.synonyms:
                    synonyms = self.synonyms[token_lower]
                    new_token = random.choice(synonyms)
                    # Preserve case
                    if token[0].isupper():
                        new_token = new_token.capitalize()
                    new_tokens.append(new_token)
                else:
                    new_tokens.append(token)
            
            # Add augmented example
            if new_tokens != text_tokens:
                augmented.append({
                    'text': ' '.join(new_tokens),
                    'labels': labels,
                    'is_augmented': True
                })
            
            # Case variations for measurements
            if any(tag in str(labels) for tag in ['B-MEASURE', 'I-MEASURE']):
                # Add variation with different units
                text_var = example['text']
                text_var = text_var.replace(' feet', ' ft')
                text_var = text_var.replace(' ft', ' feet')
                text_var = text_var.replace(' inches', ' in')
                
                if text_var != example['text']:
                    augmented.append({
                        'text': text_var,
                        'labels': labels,
                        'is_augmented': True
                    })
        
        logger.info(f"Augmented {len(examples)} examples to {len(augmented)}")
        return augmented
    
    def augment_embedding_pairs(self, pairs: List[Tuple[str, str, float]]) -> List[Tuple[str, str, float]]:
        """
        Augment embedding training pairs
        
        Args:
            pairs: List of (text1, text2, similarity) tuples
            
        Returns:
            Augmented pairs
        """
        
        augmented = []
        
        for text1, text2, similarity in pairs:
            # Original
            augmented.append((text1, text2, similarity))
            
            # Create variations
            for text in [text1, text2]:
                # Synonym replacement
                words = text.split()
                new_words = []
                
                for word in words:
                    word_lower = word.lower()
                    if word_lower in self.synonyms and random.random() < 0.3:
                        synonym = random.choice(self.synonyms[word_lower])
                        new_words.append(synonym)
                    else:
                        new_words.append(word)
                
                new_text = ' '.join(new_words)
                
                # Add augmented pair with same similarity
                if new_text != text:
                    if text == text1:
                        augmented.append((new_text, text2, similarity))
                    else:
                        augmented.append((text1, new_text, similarity))
        
        return augmented

class ModelFineTuningOrchestrator:
    """Orchestrates the complete fine-tuning pipeline"""
    
    def __init__(self, config: Optional[TrainingConfig] = None):
        self.config = config or TrainingConfig()
        self.augmenter = DataAugmenter(self.config)
        self.metrics_history = []
        
        # Import model-specific tuners
        try:
            from ner_fine_tuner import NERFineTuner
            from embedding_fine_tuner import EmbeddingFineTuner
            from yolo_fine_tuner import YOLOFineTuner
            
            self.ner_tuner = NERFineTuner(self.config)
            self.embedding_tuner = EmbeddingFineTuner(self.config)
            self.yolo_tuner = YOLOFineTuner(self.config)
            self.tuners_available = True
        except ImportError as e:
            logger.warning(f"Some tuners not available: {e}")
            self.tuners_available = False
    
    def load_training_data(self) -> Dict[str, Any]:
        """Load all training data from disk"""
        
        training_data = {
            'ner_examples': [],
            'spec_chunks': [],
            'embedding_pairs': [],
            'yolo_data_path': None
        }
        
        # Load NER training data
        ner_path = Path(self.config.training_data_dir) / "ner_examples.json"
        if ner_path.exists():
            with open(ner_path, 'r') as f:
                training_data['ner_examples'] = json.load(f)
            logger.info(f"Loaded {len(training_data['ner_examples'])} NER examples")
        
        # Load spec chunks
        spec_path = Path(self.config.data_dir) / "spec_embeddings.pkl"
        if spec_path.exists():
            with open(spec_path, 'rb') as f:
                spec_data = pickle.load(f)
                training_data['spec_chunks'] = spec_data.get('chunks', [])
            logger.info(f"Loaded {len(training_data['spec_chunks'])} spec chunks")
        
        # Load embedding pairs
        pairs_path = Path(self.config.training_data_dir) / "similarity_pairs.json"
        if pairs_path.exists():
            with open(pairs_path, 'r') as f:
                pairs_data = json.load(f)
                training_data['embedding_pairs'] = [
                    (p['text1'], p['text2'], p['similarity'])
                    for p in pairs_data
                ]
            logger.info(f"Loaded {len(training_data['embedding_pairs'])} embedding pairs")
        
        # Check for YOLO dataset
        yolo_path = Path(self.config.training_data_dir) / "yolo_dataset"
        if yolo_path.exists():
            training_data['yolo_data_path'] = str(yolo_path)
            logger.info(f"Found YOLO dataset at {yolo_path}")
        
        return training_data
    
    def run_fine_tuning_pipeline(self) -> Dict[str, Any]:
        """
        Run complete fine-tuning pipeline
        
        Returns:
            Combined metrics from all models
        """
        
        logger.info("="*60)
        logger.info("Starting Model Fine-Tuning Pipeline")
        logger.info("="*60)
        
        if not self.tuners_available:
            return {"error": "Model tuners not fully available"}
        
        # Load training data
        training_data = self.load_training_data()
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'config': asdict(self.config),
            'models': {}
        }
        
        # 1. Fine-tune NER model
        if training_data['ner_examples']:
            logger.info("\n📝 Fine-tuning NER Model...")
            
            # Augment data
            augmented_examples = self.augmenter.augment_ner_data(
                training_data['ner_examples']
            )
            
            # Train
            ner_metrics = self.ner_tuner.train(augmented_examples)
            results['models']['ner'] = ner_metrics
            
            if ner_metrics.get('target_met'):
                logger.info("✅ NER target F1 achieved!")
            else:
                logger.warning(f"⚠️ NER F1 {ner_metrics.get('val_f1', 0):.3f} below target {self.config.ner_target_f1}")
        
        # 2. Fine-tune embeddings
        if training_data['spec_chunks']:
            logger.info("\n🔍 Fine-tuning Embeddings...")
            
            # Unsupervised adaptation
            self.embedding_tuner.train_unsupervised(training_data['spec_chunks'])
            
            # Supervised fine-tuning if pairs available
            if training_data['embedding_pairs']:
                augmented_pairs = self.augmenter.augment_embedding_pairs(
                    training_data['embedding_pairs']
                )
                embedding_metrics = self.embedding_tuner.train_supervised(augmented_pairs)
                results['models']['embeddings'] = embedding_metrics
                
                if embedding_metrics.get('target_met'):
                    logger.info("✅ Embedding correlation target achieved!")
        
        # 3. Fine-tune YOLO
        if training_data['yolo_data_path']:
            logger.info("\n📸 Fine-tuning YOLO Model...")
            
            yolo_metrics = self.yolo_tuner.train(training_data['yolo_data_path'])
            results['models']['yolo'] = yolo_metrics
            
            if yolo_metrics.get('target_map_met'):
                logger.info("✅ YOLO mAP target achieved!")
            if yolo_metrics.get('target_crossarm_met'):
                logger.info("✅ YOLO crossarm recall target achieved!")
            else:
                logger.warning(f"⚠️ Crossarm recall {yolo_metrics.get('crossarm_mAP50', 0):.3f} below target")
        
        # Save results
        results_path = Path(self.config.models_dir) / "fine_tuning_results.json"
        with open(results_path, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info("\n" + "="*60)
        logger.info("Fine-Tuning Pipeline Complete")
        logger.info("="*60)
        
        # Summary
        self._print_summary(results)
        
        return results
    
    def _print_summary(self, results: Dict):
        """Print summary of fine-tuning results"""
        
        print("\n📊 FINE-TUNING SUMMARY")
        print("-"*40)
        
        for model_name, metrics in results['models'].items():
            print(f"\n{model_name.upper()}:")
            
            if model_name == 'ner':
                print(f"  F1 Score: {metrics.get('val_f1', 0):.3f}")
                print(f"  Target Met: {'✅' if metrics.get('target_met') else '❌'}")
            elif model_name == 'embeddings':
                print(f"  Correlation: {metrics.get('similarity_correlation', 0):.3f}")
                print(f"  Target Met: {'✅' if metrics.get('target_met') else '❌'}")
            elif model_name == 'yolo':
                print(f"  mAP50-95: {metrics.get('mAP50_95', 0):.3f}")
                print(f"  Crossarm Recall: {metrics.get('crossarm_mAP50', 0):.3f}")
                print(f"  Targets Met: mAP={'✅' if metrics.get('target_map_met') else '❌'}, "
                      f"Crossarm={'✅' if metrics.get('target_crossarm_met') else '❌'}")
        
        print("\n" + "-"*40)
        print("Models saved to:", self.config.models_dir)
    
    def monitor_training_progress(self) -> Dict[str, Any]:
        """Monitor and return training progress metrics"""
        
        progress = {
            'timestamp': datetime.now().isoformat(),
            'models': {},
            'recommendations': []
        }
        
        # Check for saved metrics
        results_path = Path(self.config.models_dir) / "fine_tuning_results.json"
        if results_path.exists():
            with open(results_path, 'r') as f:
                latest_results = json.load(f)
            
            # Analyze each model
            for model_name, metrics in latest_results.get('models', {}).items():
                progress['models'][model_name] = {
                    'status': 'completed',
                    'target_met': metrics.get('target_met', False),
                    'metrics': metrics
                }
                
                # Add recommendations
                if not metrics.get('target_met'):
                    if model_name == 'ner':
                        progress['recommendations'].append(
                            f"NER: Add more labeled examples (current F1: {metrics.get('val_f1', 0):.3f})"
                        )
                    elif model_name == 'yolo' and not metrics.get('target_crossarm_met'):
                        progress['recommendations'].append(
                            "YOLO: Add more crossarm images from Roboflow dataset"
                        )
        else:
            progress['status'] = 'no_training_found'
            progress['recommendations'].append("Run fine-tuning pipeline first")
        
        return progress

# API Integration
def integrate_fine_tuning_endpoints(app):
    """Add fine-tuning endpoints to FastAPI app"""
    
    from fastapi import APIRouter, BackgroundTasks, HTTPException
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel
    from typing import Optional
    
    router = APIRouter(prefix="/fine-tune", tags=["Model Fine-Tuning"])
    orchestrator = ModelFineTuningOrchestrator()
    
    class FineTuneRequest(BaseModel):
        models: Optional[List[str]] = ["ner", "embeddings", "yolo"]
        epochs: Optional[int] = None
        learning_rate: Optional[float] = None
    
    @router.post("/start")
    async def start_fine_tuning(
        request: FineTuneRequest,
        background_tasks: BackgroundTasks
    ):
        """
        Start model fine-tuning in background
        Improves NER F1 >0.85, YOLO mAP >0.6, Crossarm recall >0.5
        """
        
        # Run in background
        background_tasks.add_task(orchestrator.run_fine_tuning_pipeline)
        
        return {
            "message": "Fine-tuning started in background",
            "models": request.models,
            "check_progress": "/fine-tune/progress"
        }
    
    @router.get("/progress")
    async def get_fine_tuning_progress():
        """Get current fine-tuning progress and metrics"""
        
        progress = orchestrator.monitor_training_progress()
        return progress
    
    @router.get("/models")
    async def list_fine_tuned_models():
        """List available fine-tuned models"""
        
        models_dir = Path(orchestrator.config.models_dir)
        models = {}
        
        # Check for each model type
        if (models_dir / "ner_finetuned").exists():
            models['ner'] = str(models_dir / "ner_finetuned")
        
        if (models_dir / "embeddings_finetuned").exists():
            models['embeddings'] = str(models_dir / "embeddings_finetuned")
        
        if (models_dir / "yolo_crossarm_enhanced.pt").exists():
            models['yolo'] = str(models_dir / "yolo_crossarm_enhanced.pt")
        
        return models
    
    @router.post("/evaluate")
    async def evaluate_models(test_text: str = "Install pole with 18 ft clearance per G.O. 95"):
        """Evaluate fine-tuned models on sample text"""
        
        results = {
            "input": test_text,
            "models": {}
        }
        
        # Test each available model
        # This would load and test models - simplified for example
        
        return results
    
    app.include_router(router)
    logger.info("✅ Fine-tuning endpoints added: /fine-tune/start, /fine-tune/progress")

if __name__ == "__main__":
    # Test the orchestrator
    orchestrator = ModelFineTuningOrchestrator()
    
    print("🎯 Model Fine-Tuning System")
    print("="*60)
    print("Targets:")
    print("  - NER F1: >0.85")
    print("  - YOLO mAP50-95: >0.6")
    print("  - Crossarm Recall: >0.5")
    print("\nStarting pipeline...")
    
    results = orchestrator.run_fine_tuning_pipeline()
    
    if 'error' not in results:
        print("\n✅ Fine-tuning complete!")
    else:
        print(f"\n❌ Error: {results['error']}")
