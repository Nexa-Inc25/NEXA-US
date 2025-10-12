"""
DeepSpeed-Optimized Trainer for NEXA
Demonstrates ZeRO-3 offloading and billion-parameter model training
"""

import torch
import torch.nn as nn
from typing import Dict, Any, Optional
from pathlib import Path
import logging
from accelerate import Accelerator
from accelerate.utils import DummyOptim, DummyScheduler
from transformers import (
    AutoModelForTokenClassification,
    AutoTokenizer,
    get_scheduler
)
from peft import LoraConfig, get_peft_model, TaskType
from torch.utils.data import DataLoader
import os
import json

logger = logging.getLogger(__name__)

class DeepSpeedTrainer:
    """Production trainer with DeepSpeed ZeRO optimization"""
    
    def __init__(
        self,
        model_name: str = "bert-base-uncased",
        num_labels: int = 7,  # PG&E entity types
        use_lora: bool = True,
        zero_stage: int = 3,  # ZeRO optimization stage
        offload_optimizer: bool = True,
        offload_params: bool = True,
        gradient_checkpointing: bool = True
    ):
        """
        Initialize DeepSpeed Trainer with ZeRO optimization
        
        Args:
            model_name: Base model to fine-tune
            num_labels: Number of classification labels
            use_lora: Whether to use LoRA for efficiency
            zero_stage: ZeRO optimization stage (0-3)
            offload_optimizer: Offload optimizer to CPU
            offload_params: Offload parameters to CPU
            gradient_checkpointing: Enable gradient checkpointing
        """
        # Configure DeepSpeed
        os.environ['USE_DEEPSPEED'] = 'true'
        
        # Initialize Accelerator with DeepSpeed
        from modules.ml_device_utils import get_accelerator
        self.accelerator = get_accelerator(use_deepspeed=True)
        
        # Load model and tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        
        # For ZeRO-3, model initialization needs special handling
        if zero_stage == 3:
            # Initialize with context manager for parameter sharding
            with self.accelerator.main_process_first():
                self.model = AutoModelForTokenClassification.from_pretrained(
                    model_name,
                    num_labels=num_labels
                )
        else:
            self.model = AutoModelForTokenClassification.from_pretrained(
                model_name,
                num_labels=num_labels
            )
        
        # Enable gradient checkpointing for memory efficiency
        if gradient_checkpointing and hasattr(self.model, 'gradient_checkpointing_enable'):
            self.model.gradient_checkpointing_enable()
            logger.info("Gradient checkpointing enabled with DeepSpeed")
        
        # Apply LoRA for parameter-efficient training
        if use_lora:
            lora_config = LoraConfig(
                r=16 if zero_stage == 3 else 8,  # Higher rank with ZeRO-3
                lora_alpha=32,
                target_modules=["query", "key", "value", "dense"],  # More modules with DeepSpeed
                lora_dropout=0.1,
                task_type=TaskType.TOKEN_CLS
            )
            self.model = get_peft_model(self.model, lora_config)
            if self.accelerator.is_main_process:
                self.model.print_trainable_parameters()
        
        self.zero_stage = zero_stage
        self.gradient_checkpointing = gradient_checkpointing
        
        logger.info(f"DeepSpeedTrainer initialized with ZeRO Stage {zero_stage}")
        logger.info(f"Offload Optimizer: {offload_optimizer}, Offload Params: {offload_params}")
    
    def prepare_optimizer_scheduler(
        self,
        learning_rate: float = 2e-5,
        warmup_steps: int = 500,
        num_training_steps: int = 1000
    ):
        """Prepare optimizer and scheduler with DeepSpeed handling"""
        
        # Check if DeepSpeed is handling optimizer
        if self.accelerator.state.deepspeed_plugin:
            ds_config = self.accelerator.state.deepspeed_plugin.deepspeed_config
            
            # Use DummyOptim if DeepSpeed handles optimizer
            if "optimizer" in ds_config:
                optimizer_cls = DummyOptim
                optimizer_kwargs = {}
                logger.info("Using DeepSpeed's optimizer configuration")
            else:
                optimizer_cls = torch.optim.AdamW
                optimizer_kwargs = {
                    "lr": learning_rate,
                    "weight_decay": 0.01
                }
            
            # Use DummyScheduler if DeepSpeed handles scheduler
            if "scheduler" in ds_config:
                scheduler_cls = DummyScheduler
                scheduler_kwargs = {}
                logger.info("Using DeepSpeed's scheduler configuration")
            else:
                optimizer = optimizer_cls(self.model.parameters(), **optimizer_kwargs)
                scheduler_cls = get_scheduler
                scheduler_kwargs = {
                    "name": "linear",
                    "optimizer": optimizer,
                    "num_warmup_steps": warmup_steps,
                    "num_training_steps": num_training_steps
                }
        else:
            # Standard optimizer/scheduler
            optimizer_cls = torch.optim.AdamW
            optimizer = optimizer_cls(
                self.model.parameters(),
                lr=learning_rate,
                weight_decay=0.01
            )
            scheduler_cls = get_scheduler
            scheduler_kwargs = {
                "name": "linear",
                "optimizer": optimizer,
                "num_warmup_steps": warmup_steps,
                "num_training_steps": num_training_steps
            }
        
        # Create optimizer and scheduler
        if optimizer_cls == DummyOptim:
            optimizer = optimizer_cls(self.model.parameters())
            scheduler = DummyScheduler(optimizer, total_num_steps=num_training_steps, warmup_num_steps=warmup_steps)
        else:
            if "optimizer" not in locals():
                optimizer = optimizer_cls(self.model.parameters(), **optimizer_kwargs)
            scheduler = scheduler_cls(**scheduler_kwargs) if scheduler_cls != DummyScheduler else None
        
        return optimizer, scheduler
    
    def train(
        self,
        train_dataloader: DataLoader,
        eval_dataloader: Optional[DataLoader] = None,
        num_epochs: int = 3,
        learning_rate: float = 2e-5,
        warmup_steps: int = 500,
        output_dir: str = "./output",
        save_steps: int = 500,
        eval_steps: int = 500,
        logging_steps: int = 10
    ) -> Dict[str, Any]:
        """
        Train model with DeepSpeed optimization
        
        Returns:
            Training metrics
        """
        # Calculate training steps
        num_training_steps = num_epochs * len(train_dataloader)
        
        # Setup optimizer and scheduler
        optimizer, scheduler = self.prepare_optimizer_scheduler(
            learning_rate=learning_rate,
            warmup_steps=warmup_steps,
            num_training_steps=num_training_steps
        )
        
        # Prepare with Accelerator (handles DeepSpeed distribution)
        self.model, optimizer, train_dataloader, scheduler = self.accelerator.prepare(
            self.model, optimizer, train_dataloader, scheduler
        )
        
        if eval_dataloader:
            eval_dataloader = self.accelerator.prepare(eval_dataloader)
        
        # Training metrics
        total_steps = 0
        best_eval_loss = float('inf')
        metrics = {
            'train_loss': [],
            'eval_loss': [],
            'learning_rate': []
        }
        
        # Log initial memory state
        if self.accelerator.is_main_process:
            self._log_memory_state("Initial")
        
        logger.info(f"Starting DeepSpeed training for {num_epochs} epochs")
        
        for epoch in range(num_epochs):
            self.model.train()
            epoch_loss = 0
            num_batches = 0
            
            for batch_idx, batch in enumerate(train_dataloader):
                # Use Accelerator's accumulate context (handles gradient accumulation)
                with self.accelerator.accumulate(self.model):
                    # Forward pass
                    outputs = self.model(**batch)
                    loss = outputs.loss
                    
                    # Backward pass (DeepSpeed handles distribution)
                    self.accelerator.backward(loss)
                    
                    # Gradient clipping (if not handled by DeepSpeed)
                    if not self.accelerator.state.deepspeed_plugin or \
                       "gradient_clipping" not in self.accelerator.state.deepspeed_plugin.deepspeed_config:
                        self.accelerator.clip_grad_norm_(self.model.parameters(), 1.0)
                    
                    # Optimizer step
                    optimizer.step()
                    if scheduler:
                        scheduler.step()
                    optimizer.zero_grad()
                    
                    # Track metrics
                    epoch_loss += loss.detach().float()
                    num_batches += 1
                    total_steps += 1
                    
                    # Logging
                    if total_steps % logging_steps == 0 and self.accelerator.is_main_process:
                        avg_loss = epoch_loss / num_batches
                        current_lr = scheduler.get_last_lr()[0] if scheduler and hasattr(scheduler, 'get_last_lr') else learning_rate
                        
                        self.accelerator.log({
                            "train_loss": avg_loss,
                            "learning_rate": current_lr,
                            "epoch": epoch,
                            "step": total_steps
                        })
                        
                        logger.info(f"Step {total_steps}: Loss={avg_loss:.4f}, LR={current_lr:.6f}")
                        
                        # Log memory state periodically
                        if total_steps % 100 == 0:
                            self._log_memory_state(f"Step {total_steps}")
                    
                    # Evaluation
                    if eval_dataloader and total_steps % eval_steps == 0:
                        eval_loss = self.evaluate(eval_dataloader)
                        metrics['eval_loss'].append(eval_loss)
                        
                        # Save best model
                        if eval_loss < best_eval_loss:
                            best_eval_loss = eval_loss
                            self.save_checkpoint(
                                Path(output_dir) / "best_model",
                                optimizer=optimizer,
                                scheduler=scheduler,
                                epoch=epoch,
                                step=total_steps
                            )
                    
                    # Periodic saving
                    if total_steps % save_steps == 0:
                        self.save_checkpoint(
                            Path(output_dir) / f"checkpoint-{total_steps}",
                            optimizer=optimizer,
                            scheduler=scheduler,
                            epoch=epoch,
                            step=total_steps
                        )
            
            # End of epoch
            avg_epoch_loss = epoch_loss / num_batches
            metrics['train_loss'].append(avg_epoch_loss)
            
            if self.accelerator.is_main_process:
                logger.info(f"Epoch {epoch + 1}/{num_epochs} complete. Avg Loss: {avg_epoch_loss:.4f}")
                self._log_memory_state(f"End of Epoch {epoch + 1}")
        
        # Final save
        self.save_checkpoint(
            Path(output_dir) / "final_model",
            optimizer=optimizer,
            scheduler=scheduler,
            epoch=num_epochs,
            step=total_steps
        )
        
        # Cleanup
        self.accelerator.end_training()
        
        return metrics
    
    def evaluate(self, eval_dataloader: DataLoader) -> float:
        """Evaluate model with DeepSpeed inference optimization"""
        self.model.eval()
        total_loss = 0
        num_batches = 0
        
        with torch.no_grad():
            for batch in eval_dataloader:
                outputs = self.model(**batch)
                loss = outputs.loss
                total_loss += self.accelerator.gather(loss).mean().item()
                num_batches += 1
        
        avg_loss = total_loss / num_batches
        
        if self.accelerator.is_main_process:
            logger.info(f"Evaluation Loss: {avg_loss:.4f}")
            self.accelerator.log({"eval_loss": avg_loss})
        
        self.model.train()
        return avg_loss
    
    def save_checkpoint(
        self,
        output_dir: Path,
        optimizer: Optional[torch.optim.Optimizer] = None,
        scheduler: Optional[Any] = None,
        **kwargs
    ):
        """Save checkpoint with DeepSpeed ZeRO-3 support"""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Wait for all processes
        self.accelerator.wait_for_everyone()
        
        # Use Accelerator's save methods for DeepSpeed
        if self.accelerator.is_main_process:
            # Save model (handles ZeRO-3 gathering)
            unwrapped_model = self.accelerator.unwrap_model(self.model)
            
            # For ZeRO-3, use special save method
            if self.zero_stage == 3:
                # Save consolidated model
                self.accelerator.save_state(str(output_dir))
                logger.info(f"DeepSpeed ZeRO-3 checkpoint saved to {output_dir}")
            else:
                # Standard save
                unwrapped_model.save_pretrained(
                    output_dir,
                    is_main_process=self.accelerator.is_main_process,
                    save_function=self.accelerator.save
                )
                self.tokenizer.save_pretrained(output_dir)
                
                # Save training state
                if optimizer and scheduler:
                    torch.save({
                        'optimizer_state_dict': optimizer.state_dict() if hasattr(optimizer, 'state_dict') else None,
                        'scheduler_state_dict': scheduler.state_dict() if hasattr(scheduler, 'state_dict') else None,
                        **kwargs
                    }, output_dir / 'training_state.pt')
                
                logger.info(f"Checkpoint saved to {output_dir}")
    
    def load_checkpoint(self, checkpoint_dir: Path):
        """Load checkpoint with DeepSpeed support"""
        if self.zero_stage == 3:
            # Load DeepSpeed checkpoint
            self.accelerator.load_state(str(checkpoint_dir))
            logger.info(f"DeepSpeed checkpoint loaded from {checkpoint_dir}")
        else:
            # Standard loading
            from peft import PeftModel
            
            if (checkpoint_dir / 'adapter_config.json').exists():
                # LoRA model
                base_model = AutoModelForTokenClassification.from_pretrained(
                    checkpoint_dir / '..',
                    num_labels=self.model.config.num_labels
                )
                self.model = PeftModel.from_pretrained(base_model, checkpoint_dir)
            else:
                # Regular model
                self.model = AutoModelForTokenClassification.from_pretrained(
                    checkpoint_dir,
                    num_labels=self.model.config.num_labels
                )
            
            # Re-enable gradient checkpointing if needed
            if self.gradient_checkpointing and hasattr(self.model, 'gradient_checkpointing_enable'):
                self.model.gradient_checkpointing_enable()
            
            self.tokenizer = AutoTokenizer.from_pretrained(checkpoint_dir)
            logger.info(f"Checkpoint loaded from {checkpoint_dir}")
    
    def _log_memory_state(self, stage: str):
        """Log memory state for monitoring"""
        if torch.cuda.is_available():
            allocated = torch.cuda.memory_allocated() / 1024**3
            reserved = torch.cuda.memory_reserved() / 1024**3
            logger.info(f"[{stage}] GPU Memory - Allocated: {allocated:.2f}GB, Reserved: {reserved:.2f}GB")
            
            # Log DeepSpeed memory if available
            if hasattr(self.accelerator.state, 'deepspeed_plugin'):
                logger.info(f"[{stage}] DeepSpeed ZeRO Stage: {self.zero_stage}, "
                          f"Offloading: Optimizer={self.accelerator.state.deepspeed_plugin.offload_optimizer_device}, "
                          f"Params={self.accelerator.state.deepspeed_plugin.offload_param_device}")

# Example usage
def train_with_deepspeed():
    """Example: Train NER model with DeepSpeed ZeRO-3"""
    from torch.utils.data import TensorDataset, DataLoader
    import torch
    
    # Initialize DeepSpeed trainer
    trainer = DeepSpeedTrainer(
        model_name="bert-base-uncased",
        num_labels=7,  # PG&E entities
        use_lora=True,
        zero_stage=3,  # ZeRO-3 for maximum memory efficiency
        offload_optimizer=True,  # Offload to CPU
        offload_params=True,  # Offload parameters to CPU
        gradient_checkpointing=True  # Additional memory savings
    )
    
    # Create dummy data for example
    num_samples = 1000
    seq_length = 128
    batch_size = 8
    
    # Dummy datasets
    train_data = TensorDataset(
        torch.randint(0, 1000, (num_samples, seq_length)),  # input_ids
        torch.ones(num_samples, seq_length, dtype=torch.long),  # attention_mask
        torch.randint(0, 7, (num_samples, seq_length))  # labels
    )
    
    eval_data = TensorDataset(
        torch.randint(0, 1000, (100, seq_length)),
        torch.ones(100, seq_length, dtype=torch.long),
        torch.randint(0, 7, (100, seq_length))
    )
    
    # Create dataloaders
    train_loader = DataLoader(train_data, batch_size=batch_size, shuffle=True)
    eval_loader = DataLoader(eval_data, batch_size=batch_size)
    
    # Train with DeepSpeed
    metrics = trainer.train(
        train_dataloader=train_loader,
        eval_dataloader=eval_loader,
        num_epochs=2,
        learning_rate=2e-5,
        output_dir="./output/deepspeed_ner",
        save_steps=500,
        eval_steps=100,
        logging_steps=10
    )
    
    logger.info(f"DeepSpeed training complete! Metrics: {metrics}")
    
    # Demonstrate memory efficiency
    logger.info(f"Peak memory usage with ZeRO-3: "
              f"{torch.cuda.max_memory_allocated() / 1024**3:.2f}GB" 
              if torch.cuda.is_available() else "CPU mode")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Check DeepSpeed availability
    from accelerate.utils import is_deepspeed_available
    
    if is_deepspeed_available():
        print("DeepSpeed is available! Configuration:")
        print(f"  Version: Check with 'deepspeed --version'")
        print(f"  ZeRO Stages: 0 (disabled), 1 (optimizer), 2 (+gradients), 3 (+parameters)")
        print(f"  Offloading: CPU/NVMe for optimizer and parameters")
        
        # Run example if GPU available
        if torch.cuda.is_available():
            print("\nRunning DeepSpeed ZeRO-3 training example...")
            train_with_deepspeed()
        else:
            print("\nNo GPU available - DeepSpeed would run in CPU mode")
    else:
        print("DeepSpeed not installed. Install with: pip install deepspeed")
