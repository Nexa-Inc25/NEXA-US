"""
Gradient Accumulation Utilities for Memory-Efficient Training
Enables large batch simulation on limited GPU memory
"""

import torch
from typing import Optional, Any
import logging

logger = logging.getLogger(__name__)

class GradientAccumulator:
    """Manages gradient accumulation for memory-efficient training"""
    
    def __init__(
        self,
        accumulation_steps: int = 4,
        max_grad_norm: float = 1.0,
        mixed_precision: bool = False
    ):
        """
        Initialize gradient accumulator
        
        Args:
            accumulation_steps: Number of steps to accumulate gradients
            max_grad_norm: Maximum gradient norm for clipping
            mixed_precision: Whether to use automatic mixed precision
        """
        self.accumulation_steps = accumulation_steps
        self.max_grad_norm = max_grad_norm
        self.mixed_precision = mixed_precision
        self.step_count = 0
        
        # Scaler for mixed precision
        if mixed_precision and torch.cuda.is_available():
            self.scaler = torch.cuda.amp.GradScaler()
        else:
            self.scaler = None
            
        logger.info(f"Gradient accumulator initialized - Steps: {accumulation_steps}, "
                   f"Mixed Precision: {mixed_precision}")
    
    def backward(
        self, 
        loss: torch.Tensor,
        optimizer: torch.optim.Optimizer,
        model: torch.nn.Module,
        scheduler: Optional[Any] = None,
        clear_cache_interval: int = 10
    ) -> bool:
        """
        Perform backward pass with accumulation
        
        Args:
            loss: Loss tensor (should be averaged)
            optimizer: Model optimizer
            model: Model being trained
            scheduler: Optional learning rate scheduler
            clear_cache_interval: Clear GPU cache every N optimizer steps
            
        Returns:
            True if optimizer step was performed
        """
        # Scale loss by accumulation steps
        scaled_loss = loss / self.accumulation_steps
        
        # Backward pass
        if self.scaler:
            self.scaler.scale(scaled_loss).backward()
        else:
            scaled_loss.backward()
        
        self.step_count += 1
        
        # Perform optimizer step after accumulation
        if self.step_count % self.accumulation_steps == 0:
            # Gradient clipping
            if self.scaler:
                self.scaler.unscale_(optimizer)
            
            torch.nn.utils.clip_grad_norm_(model.parameters(), self.max_grad_norm)
            
            # Optimizer step
            if self.scaler:
                self.scaler.step(optimizer)
                self.scaler.update()
            else:
                optimizer.step()
            
            # Scheduler step
            if scheduler:
                scheduler.step()
            
            # Zero gradients for next accumulation
            optimizer.zero_grad()
            
            # Periodic cache clearing
            if (self.step_count // self.accumulation_steps) % clear_cache_interval == 0:
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    logger.debug(f"GPU cache cleared at step {self.step_count}")
            
            return True
        
        return False
    
    def get_effective_batch_size(self, batch_size: int) -> int:
        """Calculate effective batch size with accumulation"""
        return batch_size * self.accumulation_steps
    
    def should_log(self) -> bool:
        """Check if metrics should be logged (after accumulation)"""
        return self.step_count % self.accumulation_steps == 0
    
    @staticmethod
    def calculate_accumulation_steps(
        desired_batch_size: int,
        max_device_batch_size: int
    ) -> int:
        """
        Calculate optimal accumulation steps
        
        Args:
            desired_batch_size: Target effective batch size
            max_device_batch_size: Maximum batch size that fits in memory
            
        Returns:
            Number of accumulation steps needed
        """
        steps = max(1, desired_batch_size // max_device_batch_size)
        logger.info(f"Calculated accumulation steps: {steps} "
                   f"(Desired: {desired_batch_size}, Device Max: {max_device_batch_size})")
        return steps

# Example usage in fine-tuner
def train_with_accumulation_example(model, train_loader, device):
    """Example training loop with gradient accumulation"""
    from modules.ml_device_utils import device_manager, to_device
    
    # Setup
    model = to_device(model)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4)
    
    # Determine accumulation steps based on memory
    device_batch_size = device_manager.get_batch_size(base_size=8, model_size_mb=1000)
    desired_batch_size = 32
    accumulation_steps = GradientAccumulator.calculate_accumulation_steps(
        desired_batch_size, device_batch_size
    )
    
    # Initialize accumulator
    accumulator = GradientAccumulator(
        accumulation_steps=accumulation_steps,
        mixed_precision=device.type == 'cuda'
    )
    
    # Training loop
    for epoch in range(3):
        for batch_idx, batch in enumerate(train_loader):
            inputs = to_device(batch['input_ids'])
            labels = to_device(batch['labels'])
            
            # Forward pass
            with torch.cuda.amp.autocast(enabled=accumulator.mixed_precision):
                outputs = model(inputs, labels=labels)
                loss = outputs.loss
            
            # Backward with accumulation
            step_performed = accumulator.backward(loss, optimizer, model)
            
            # Log after accumulation
            if step_performed:
                effective_batch = accumulator.get_effective_batch_size(len(inputs))
                logger.info(f"Step {batch_idx}, Loss: {loss.item():.4f}, "
                          f"Effective Batch: {effective_batch}")
                
                # Memory monitoring
                if batch_idx % 50 == 0 and device.type == 'cuda':
                    mem_stats = device_manager.get_memory_summary()
                    logger.info(f"GPU Memory - Allocated: {mem_stats['allocated_mb']:.1f}MB, "
                              f"Free: {mem_stats['free_mb']:.1f}MB")
        
        # End of epoch cleanup
        device_manager.clear_cache(deep_clean=True)

if __name__ == "__main__":
    # Test accumulation calculation
    steps = GradientAccumulator.calculate_accumulation_steps(
        desired_batch_size=64,
        max_device_batch_size=8
    )
    print(f"Need {steps} accumulation steps for effective batch size of 64")
