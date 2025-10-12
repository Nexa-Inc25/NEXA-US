"""
GPU-Optimized Training Example for NEXA ML Modules
Demonstrates all memory management techniques
"""

import torch
import torch.nn as nn
from typing import Dict, List, Any, Optional
import logging
from pathlib import Path
import gc

# Import our enhanced utilities
from modules.ml_device_utils import (
    device_manager, get_device, to_device, 
    inference_mode, optimize_model
)
from modules.gradient_accumulator import GradientAccumulator
from modules.ml_monitoring import MLMonitor

logger = logging.getLogger(__name__)

class GPUOptimizedTrainer:
    """Production-ready trainer with comprehensive GPU memory management"""
    
    def __init__(
        self,
        model: nn.Module,
        model_size_mb: float = 1000,
        desired_batch_size: int = 32,
        mixed_precision: bool = None
    ):
        """
        Initialize GPU-optimized trainer
        
        Args:
            model: PyTorch model to train
            model_size_mb: Estimated model size in MB
            desired_batch_size: Target effective batch size
            mixed_precision: Use mixed precision (auto-detect if None)
        """
        self.device = get_device()
        self.model = to_device(model)
        
        # Auto-detect mixed precision capability
        if mixed_precision is None:
            mixed_precision = self.device.type == 'cuda'
        self.mixed_precision = mixed_precision
        
        # Calculate optimal batch size for device
        self.device_batch_size = device_manager.get_batch_size(
            base_size=desired_batch_size,
            model_size_mb=model_size_mb
        )
        
        # Setup gradient accumulation if needed
        accumulation_steps = max(1, desired_batch_size // self.device_batch_size)
        self.accumulator = GradientAccumulator(
            accumulation_steps=accumulation_steps,
            mixed_precision=mixed_precision
        )
        
        logger.info(f"GPU Optimized Trainer initialized:")
        logger.info(f"  Device: {self.device}")
        logger.info(f"  Device batch size: {self.device_batch_size}")
        logger.info(f"  Accumulation steps: {accumulation_steps}")
        logger.info(f"  Effective batch size: {self.accumulator.get_effective_batch_size(self.device_batch_size)}")
        logger.info(f"  Mixed precision: {mixed_precision}")
        
        # Log initial memory state
        if self.device.type == 'cuda':
            mem_stats = device_manager.get_memory_summary()
            logger.info(f"Initial GPU memory - Allocated: {mem_stats['allocated_mb']:.1f}MB, "
                       f"Free: {mem_stats['free_mb']:.1f}MB")
    
    def train_epoch(
        self,
        train_loader,
        optimizer: torch.optim.Optimizer,
        criterion: nn.Module = None,
        scheduler: Optional[Any] = None,
        log_interval: int = 10
    ) -> Dict[str, float]:
        """
        Train one epoch with memory optimization
        
        Returns:
            Dictionary with training metrics
        """
        self.model.train()
        
        total_loss = 0
        batch_count = 0
        samples_processed = 0
        
        # Pre-allocate metrics dict to avoid memory fragmentation
        metrics = {
            'loss': 0.0,
            'samples': 0,
            'gpu_peak_mb': 0.0 if self.device.type == 'cuda' else 0.0
        }
        
        for batch_idx, batch in enumerate(train_loader):
            # Move batch to device
            if isinstance(batch, dict):
                inputs = to_device(batch.get('input_ids', batch.get('inputs')))
                labels = to_device(batch.get('labels', batch.get('targets')))
            else:
                inputs, labels = batch
                inputs = to_device(inputs)
                labels = to_device(labels)
            
            # Forward pass with mixed precision
            if self.mixed_precision:
                with torch.cuda.amp.autocast():
                    outputs = self.model(inputs)
                    if criterion:
                        loss = criterion(outputs, labels)
                    else:
                        loss = outputs.loss if hasattr(outputs, 'loss') else outputs
            else:
                outputs = self.model(inputs)
                if criterion:
                    loss = criterion(outputs, labels)
                else:
                    loss = outputs.loss if hasattr(outputs, 'loss') else outputs
            
            # Backward pass with gradient accumulation
            step_performed = self.accumulator.backward(
                loss=loss,
                optimizer=optimizer,
                model=self.model,
                scheduler=scheduler,
                clear_cache_interval=20  # Clear cache every 20 optimizer steps
            )
            
            # Update metrics
            total_loss += loss.item()
            batch_count += 1
            samples_processed += len(inputs)
            
            # Log progress
            if step_performed and batch_idx % log_interval == 0:
                avg_loss = total_loss / batch_count
                
                # Memory monitoring
                if self.device.type == 'cuda':
                    mem_stats = device_manager.get_memory_summary()
                    metrics['gpu_peak_mb'] = max(metrics['gpu_peak_mb'], mem_stats['allocated_mb'])
                    
                    # Check for high fragmentation
                    if mem_stats['fragmentation_ratio'] > 0.3:
                        logger.warning(f"High memory fragmentation detected: {mem_stats['fragmentation_ratio']:.2f}")
                        device_manager.clear_cache(deep_clean=True)
                    
                    logger.info(f"Batch {batch_idx}/{len(train_loader)}, "
                               f"Loss: {avg_loss:.4f}, "
                               f"GPU Mem: {mem_stats['allocated_mb']:.1f}MB, "
                               f"Fragmentation: {mem_stats['fragmentation_ratio']:.2f}")
                else:
                    logger.info(f"Batch {batch_idx}/{len(train_loader)}, Loss: {avg_loss:.4f}")
            
            # Periodic deep memory cleanup
            if batch_idx % 100 == 0 and batch_idx > 0:
                self._cleanup_memory()
        
        # Final metrics
        metrics['loss'] = total_loss / batch_count
        metrics['samples'] = samples_processed
        
        # End of epoch cleanup
        self._cleanup_memory(deep=True)
        
        return metrics
    
    def validate(
        self,
        val_loader,
        criterion: nn.Module = None
    ) -> Dict[str, float]:
        """
        Validation with memory-efficient inference
        
        Returns:
            Dictionary with validation metrics
        """
        # Optimize model for inference
        self.model = optimize_model(self.model)
        
        total_loss = 0
        batch_count = 0
        correct = 0
        total = 0
        
        # Use inference mode for memory efficiency
        with inference_mode():
            for batch in val_loader:
                # Move batch to device
                if isinstance(batch, dict):
                    inputs = to_device(batch.get('input_ids', batch.get('inputs')))
                    labels = to_device(batch.get('labels', batch.get('targets')))
                else:
                    inputs, labels = batch
                    inputs = to_device(inputs)
                    labels = to_device(labels)
                
                # Forward pass only
                outputs = self.model(inputs)
                
                # Calculate loss
                if criterion:
                    loss = criterion(outputs, labels)
                else:
                    loss = outputs.loss if hasattr(outputs, 'loss') else outputs
                
                total_loss += loss.item()
                batch_count += 1
                
                # Calculate accuracy if classification
                if hasattr(outputs, 'logits'):
                    preds = torch.argmax(outputs.logits, dim=-1)
                    correct += (preds == labels).sum().item()
                    total += labels.numel()
                
                # Clear cache periodically during validation
                if batch_count % 50 == 0:
                    device_manager.clear_cache()
        
        # Final cleanup
        self._cleanup_memory()
        
        metrics = {
            'val_loss': total_loss / batch_count,
            'val_accuracy': correct / total if total > 0 else 0
        }
        
        return metrics
    
    def _cleanup_memory(self, deep: bool = False):
        """Internal method for memory cleanup"""
        # Python garbage collection
        gc.collect()
        
        # PyTorch cache clearing
        device_manager.clear_cache(deep_clean=deep)
        
        # Log memory state after cleanup
        if self.device.type == 'cuda' and deep:
            mem_stats = device_manager.get_memory_summary()
            logger.info(f"Memory after cleanup - Allocated: {mem_stats['allocated_mb']:.1f}MB, "
                       f"Free: {mem_stats['free_mb']:.1f}MB")
    
    def save_checkpoint(self, path: str, optimizer: torch.optim.Optimizer = None, **kwargs):
        """Save model checkpoint with memory optimization"""
        # Move model to CPU before saving to reduce checkpoint size
        cpu_state = self.model.cpu().state_dict()
        
        checkpoint = {
            'model_state_dict': cpu_state,
            'device': str(self.device),
            'mixed_precision': self.mixed_precision,
            **kwargs
        }
        
        if optimizer:
            checkpoint['optimizer_state_dict'] = optimizer.state_dict()
        
        torch.save(checkpoint, path)
        logger.info(f"Checkpoint saved to {path}")
        
        # Move model back to original device
        self.model = to_device(self.model)
    
    def load_checkpoint(self, path: str, optimizer: torch.optim.Optimizer = None):
        """Load model checkpoint"""
        checkpoint = torch.load(path, map_location='cpu')
        
        # Load model state
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.model = to_device(self.model)
        
        # Load optimizer state if provided
        if optimizer and 'optimizer_state_dict' in checkpoint:
            optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        
        logger.info(f"Checkpoint loaded from {path}")
        
        return checkpoint

# Example usage for NEXA fine-tuning
def train_nexa_model_with_gpu_optimization():
    """Example of training a NEXA model with full GPU optimization"""
    from transformers import AutoModelForTokenClassification
    from torch.utils.data import DataLoader, TensorDataset
    import torch.optim as optim
    
    # Initialize model (example: NER for utility jargon)
    model = AutoModelForTokenClassification.from_pretrained(
        'bert-base-uncased',
        num_labels=7  # PG&E entity types
    )
    
    # Create dummy data for example
    batch_size = 8  # Small for demo
    num_samples = 100
    seq_length = 128
    
    dummy_inputs = torch.randint(0, 1000, (num_samples, seq_length))
    dummy_labels = torch.randint(0, 7, (num_samples, seq_length))
    dataset = TensorDataset(dummy_inputs, dummy_labels)
    
    train_loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(dataset, batch_size=batch_size, shuffle=False)
    
    # Initialize trainer with GPU optimization
    trainer = GPUOptimizedTrainer(
        model=model,
        model_size_mb=1000,  # BERT-base is ~400MB, but with gradients ~1GB
        desired_batch_size=32,  # Target batch size
        mixed_precision=True  # Auto-detect based on device
    )
    
    # Setup optimizer
    optimizer = optim.AdamW(model.parameters(), lr=2e-5)
    
    # Training loop with memory monitoring
    for epoch in range(2):
        logger.info(f"\n=== Epoch {epoch + 1} ===")
        
        # Log system status before epoch
        ml_status = MLMonitor.get_torch_status()
        if 'memory' in ml_status:
            logger.info(f"Pre-epoch GPU status: {ml_status['memory']}")
        
        # Train
        train_metrics = trainer.train_epoch(
            train_loader=train_loader,
            optimizer=optimizer,
            log_interval=10
        )
        
        # Validate
        val_metrics = trainer.validate(val_loader)
        
        logger.info(f"Epoch {epoch + 1} complete:")
        logger.info(f"  Train Loss: {train_metrics['loss']:.4f}")
        logger.info(f"  Val Loss: {val_metrics['val_loss']:.4f}")
        logger.info(f"  Val Accuracy: {val_metrics['val_accuracy']:.2%}")
        logger.info(f"  Peak GPU Memory: {train_metrics['gpu_peak_mb']:.1f}MB")
        
        # Save checkpoint
        trainer.save_checkpoint(
            f"checkpoint_epoch_{epoch + 1}.pt",
            optimizer=optimizer,
            epoch=epoch + 1,
            metrics={**train_metrics, **val_metrics}
        )
    
    # Final memory snapshot for debugging
    if trainer.device.type == 'cuda':
        device_manager.memory_snapshot("final_memory_snapshot.json")
    
    logger.info("Training complete with GPU optimization!")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Show configuration
    config = MLMonitor.get_inference_config()
    print("GPU Optimization Configuration:")
    print(f"  Device: {config['device']}")
    print(f"  Batch Size: {config['batch_size']}")
    print(f"  Mixed Precision: {config['mixed_precision']}")
    print(f"  Memory Config: {config['memory_config']}")
    print(f"  CUDA Allocator: {config['environment']['PYTORCH_CUDA_ALLOC_CONF']}")
    
    # Run example if GPU available
    if torch.cuda.is_available():
        print("\nRunning GPU-optimized training example...")
        train_nexa_model_with_gpu_optimization()
    else:
        print("\nNo GPU available - example would run on CPU")
