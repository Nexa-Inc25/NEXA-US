"""
Example ML Integration showing proper torch patterns for NEXA
Demonstrates device handling, memory management, and optimization
"""

import torch
import torch.nn as nn
from transformers import AutoModelForTokenClassification, AutoTokenizer
from peft import LoraConfig, get_peft_model, TaskType
from accelerate import Accelerator
from typing import List, Dict, Any
import logging

# Import our utilities
from ml_device_utils import (
    get_device, to_device, inference_mode, 
    optimize_model, device_manager
)

logger = logging.getLogger(__name__)

class NEXAFineTuner:
    """Example fine-tuner with proper torch patterns"""
    
    def __init__(self, model_name: str = "bert-base-uncased"):
        self.device = get_device()
        self.accelerator = Accelerator(
            mixed_precision='fp16' if self.device.type == 'cuda' else 'no',
            cpu=self.device.type == 'cpu'
        )
        
        # Load model and tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForTokenClassification.from_pretrained(
            model_name,
            num_labels=7  # PG&E entity types
        )
        
        # Apply LoRA for efficient fine-tuning
        if self.device.type == 'cpu':
            # Smaller LoRA rank for CPU
            lora_config = LoraConfig(
                r=4,  # Lower rank for CPU
                lora_alpha=16,
                target_modules=["query", "value"],
                lora_dropout=0.1,
                task_type=TaskType.TOKEN_CLS
            )
        else:
            # Larger rank for GPU
            lora_config = LoraConfig(
                r=8,
                lora_alpha=32,
                target_modules=["query", "key", "value"],
                lora_dropout=0.1,
                task_type=TaskType.TOKEN_CLS
            )
        
        self.model = get_peft_model(self.model, lora_config)
        self.model = to_device(self.model)
        
        logger.info(f"Model loaded on {self.device}")
        logger.info(f"Trainable parameters: {self.model.print_trainable_parameters()}")
    
    def train_batch(self, texts: List[str], labels: List[List[int]]) -> float:
        """Train on a batch with proper device handling"""
        self.model.train()
        
        # Tokenize and move to device
        encoding = self.tokenizer(
            texts,
            truncation=True,
            padding=True,
            max_length=128,
            return_tensors='pt'
        )
        
        # Move all tensors to device
        input_ids = to_device(encoding['input_ids'])
        attention_mask = to_device(encoding['attention_mask'])
        labels_tensor = to_device(torch.tensor(labels))
        
        # Use accelerator for distributed training
        model, input_ids, attention_mask, labels_tensor = self.accelerator.prepare(
            self.model, input_ids, attention_mask, labels_tensor
        )
        
        # Forward pass with automatic mixed precision
        with self.accelerator.autocast():
            outputs = model(
                input_ids=input_ids,
                attention_mask=attention_mask,
                labels=labels_tensor
            )
            loss = outputs.loss
        
        # Backward pass
        self.accelerator.backward(loss)
        
        # Clear cache periodically on GPU
        if self.device.type == 'cuda' and torch.cuda.memory_allocated() > 1e9:
            device_manager.clear_cache()
        
        return loss.item()
    
    def inference(self, texts: List[str]) -> List[Dict[str, Any]]:
        """Inference with all optimizations"""
        # Optimize model for inference
        self.model = optimize_model(self.model)
        
        results = []
        
        # Use inference mode context
        with inference_mode():
            for text in texts:
                # Tokenize
                encoding = self.tokenizer(
                    text,
                    truncation=True,
                    padding=True,
                    max_length=128,
                    return_tensors='pt'
                )
                
                # Move to device
                input_ids = to_device(encoding['input_ids'])
                attention_mask = to_device(encoding['attention_mask'])
                
                # No gradient computation needed
                outputs = self.model(
                    input_ids=input_ids,
                    attention_mask=attention_mask
                )
                
                # Get predictions
                predictions = torch.argmax(outputs.logits, dim=-1)
                
                # Convert to CPU for post-processing
                predictions = predictions.cpu().numpy()
                
                results.append({
                    'text': text,
                    'predictions': predictions.tolist(),
                    'confidence': torch.softmax(outputs.logits, dim=-1).max().item()
                })
        
        # Clear cache after batch inference
        device_manager.clear_cache()
        
        return results
    
    def save_model(self, path: str):
        """Save model with device handling"""
        # Move to CPU before saving to ensure portability
        cpu_model = self.model.cpu()
        cpu_model.save_pretrained(path)
        self.tokenizer.save_pretrained(path)
        
        # Move back to original device
        self.model = to_device(self.model)
        
        logger.info(f"Model saved to {path}")
    
    def load_model(self, path: str):
        """Load model and move to appropriate device"""
        from peft import PeftModel
        
        # Load on CPU first
        self.model = PeftModel.from_pretrained(
            self.model.base_model,
            path,
            device_map={'': 'cpu'}
        )
        
        # Then move to target device
        self.model = to_device(self.model)
        
        # Optimize if for inference
        if not self.model.training:
            self.model = optimize_model(self.model)
        
        logger.info(f"Model loaded from {path} to {self.device}")

class YOLOIntegration:
    """Example YOLO integration with device handling"""
    
    def __init__(self):
        from ultralytics import YOLO
        
        self.device = get_device()
        
        # Load model
        self.model = YOLO('yolov8n.pt')
        
        # Configure for device
        if self.device.type == 'cuda':
            self.model.to('cuda')
            # Enable TensorRT if available
            try:
                self.model.export(format='engine')
                logger.info("YOLO exported to TensorRT for faster inference")
            except:
                pass
    
    def detect(self, image_path: str) -> Dict[str, Any]:
        """Run detection with optimizations"""
        with inference_mode():
            # Run inference
            results = self.model(
                image_path,
                device=self.device.type,
                half=self.device.type == 'cuda',  # FP16 on GPU
                batch=device_manager.get_batch_size(),
                verbose=False
            )
            
            # Process results
            detections = []
            for r in results:
                for box in r.boxes:
                    detections.append({
                        'class': int(box.cls),
                        'confidence': float(box.conf),
                        'bbox': box.xyxy.cpu().numpy().tolist()
                    })
            
            return {
                'image': image_path,
                'detections': detections,
                'device_used': str(self.device)
            }

# Example usage
def main():
    """Demonstrate proper ML integration"""
    import time
    
    # Initialize fine-tuner
    tuner = NEXAFineTuner()
    
    # Example training data
    texts = [
        "Install FuseSaver on single-phase tap per Document 092813",
        "TripSaver II device required for this configuration"
    ]
    labels = [[1, 0, 2, 0, 0, 0, 3, 3, 3], [2, 2, 0, 0, 0, 0, 0]]
    
    # Train
    start = time.time()
    loss = tuner.train_batch(texts, labels)
    train_time = time.time() - start
    print(f"Training loss: {loss:.4f}, Time: {train_time:.2f}s")
    
    # Inference
    start = time.time()
    results = tuner.inference(texts[:1])
    inference_time = time.time() - start
    print(f"Inference results: {results}")
    print(f"Inference time: {inference_time:.3f}s")
    
    # YOLO example
    yolo = YOLOIntegration()
    # detection = yolo.detect('path/to/pole/image.jpg')
    
    # Show device info
    print(f"\nDevice configuration:")
    print(f"  Device: {get_device()}")
    print(f"  Optimal batch size: {device_manager.get_batch_size()}")
    
    # Clean up
    device_manager.clear_cache()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
