"""
Accelerated Trainer with Gradient Checkpointing
Full Accelerate integration for NEXA ML models
"""

import torch
import torch.nn as nn
from typing import Dict, Any, Optional, List
from pathlib import Path
import logging
from accelerate import Accelerator
from accelerate.utils import set_seed
from transformers import (
    AutoModelForTokenClassification,
    AutoTokenizer,
    get_scheduler
)
from peft import LoraConfig, get_peft_model, TaskType
from torch.utils.data import DataLoader
import os

logger = logging.getLogger(__name__)

class AcceleratedTrainer:
    """Production trainer with full Accelerate features including gradient checkpointing"""
    
    def __init__(
        self,
        model_name: str = "bert-base-uncased",
        num_labels: int = 7,  # PG&E entity types
        use_lora: bool = True,
        gradient_checkpointing: bool = True,
        mixed_precision: str = "fp16",
        gradient_accumulation_steps: int = 4
    ):
        """
        Initialize Accelerated Trainer
        
        Args:
            model_name: Base model to fine-tune
            num_labels: Number of classification labels
            use_lora: Whether to use LoRA for efficiency
            gradient_checkpointing: Enable gradient checkpointing
            mixed_precision: Mixed precision setting (no, fp16, bf16)
            gradient_accumulation_steps: Steps to accumulate gradients
        """
        # Initialize Accelerator
        self.accelerator = Accelerator(
            mixed_precision=mixed_precision,
            gradient_accumulation_steps=gradient_accumulation_steps,
            log_with="tensorboard",
            project_dir="./logs"
        )
        
        # Set seed for reproducibility
        set_seed(42)
        
        # Load model and tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForTokenClassification.from_pretrained(
            model_name,
            num_labels=num_labels
        )
        
        # Enable gradient checkpointing for memory efficiency
        if gradient_checkpointing and hasattr(self.model, 'gradient_checkpointing_enable'):
            self.model.gradient_checkpointing_enable()
            logger.info("Gradient checkpointing enabled - 50% memory savings expected")
        
        # Apply LoRA for parameter-efficient training
        if use_lora:
            lora_config = LoraConfig(
                r=8 if self.accelerator.device.type == 'cuda' else 4,
                lora_alpha=32,
                target_modules=["query", "key", "value"],
                lora_dropout=0.1,
                task_type=TaskType.TOKEN_CLS
            )
            self.model = get_peft_model(self.model, lora_config)
            self.model.print_trainable_parameters()
        
        self.gradient_checkpointing = gradient_checkpointing
        logger.info(f"AcceleratedTrainer initialized on {self.accelerator.device}")
    
    def prepare_data(
        self, 
        train_dataloader: DataLoader,
        eval_dataloader: Optional[DataLoader] = None
    ):
        """Prepare data with Accelerator"""
        self.train_dataloader = self.accelerator.prepare(train_dataloader)
        if eval_dataloader:
            self.eval_dataloader = self.accelerator.prepare(eval_dataloader)
        else:
            self.eval_dataloader = None
    
    def train(
        self,
        num_epochs: int = 3,
        learning_rate: float = 2e-5,
        warmup_steps: int = 500,
        output_dir: str = "./output",
        save_steps: int = 500,
        eval_steps: int = 500,
        logging_steps: int = 10
    ) -> Dict[str, Any]:
        """
        Train model with Accelerate optimizations
        
        Returns:
            Training metrics and final model state
        """
        # Setup optimizer
        optimizer = torch.optim.AdamW(
            self.model.parameters(),
            lr=learning_rate,
            weight_decay=0.01
        )
        
        # Setup scheduler
        num_training_steps = num_epochs * len(self.train_dataloader)
        lr_scheduler = get_scheduler(
            "linear",
            optimizer=optimizer,
            num_warmup_steps=warmup_steps,
            num_training_steps=num_training_steps
        )
        
        # Prepare with Accelerator
        self.model, optimizer, lr_scheduler = self.accelerator.prepare(
            self.model, optimizer, lr_scheduler
        )
        
        # Initialize tracking
        total_steps = 0
        best_eval_loss = float('inf')
        metrics = {
            'train_loss': [],
            'eval_loss': [],
            'learning_rate': []
        }
        
        # Training loop
        logger.info(f"Starting training for {num_epochs} epochs")
        
        for epoch in range(num_epochs):
            self.model.train()
            epoch_loss = 0
            num_batches = 0
            
            for batch in self.train_dataloader:
                # Use Accelerator's accumulate context
                with self.accelerator.accumulate(self.model):
                    # Forward pass
                    outputs = self.model(**batch)
                    loss = outputs.loss
                    
                    # Backward pass
                    self.accelerator.backward(loss)
                    
                    # Gradient clipping
                    self.accelerator.clip_grad_norm_(self.model.parameters(), 1.0)
                    
                    # Optimizer step
                    optimizer.step()
                    lr_scheduler.step()
                    optimizer.zero_grad()
                    
                    # Track metrics
                    epoch_loss += loss.detach().float()
                    num_batches += 1
                    total_steps += 1
                    
                    # Logging
                    if total_steps % logging_steps == 0:
                        avg_loss = epoch_loss / num_batches
                        current_lr = lr_scheduler.get_last_lr()[0]
                        
                        self.accelerator.log({
                            "train_loss": avg_loss,
                            "learning_rate": current_lr,
                            "epoch": epoch,
                            "step": total_steps
                        })
                        
                        logger.info(f"Step {total_steps}: Loss={avg_loss:.4f}, LR={current_lr:.6f}")
                    
                    # Evaluation
                    if self.eval_dataloader and total_steps % eval_steps == 0:
                        eval_loss = self.evaluate()
                        metrics['eval_loss'].append(eval_loss)
                        
                        # Save best model
                        if eval_loss < best_eval_loss:
                            best_eval_loss = eval_loss
                            self.save_checkpoint(
                                Path(output_dir) / "best_model",
                                optimizer=optimizer,
                                scheduler=lr_scheduler,
                                epoch=epoch,
                                step=total_steps
                            )
                    
                    # Periodic saving
                    if total_steps % save_steps == 0:
                        self.save_checkpoint(
                            Path(output_dir) / f"checkpoint-{total_steps}",
                            optimizer=optimizer,
                            scheduler=lr_scheduler,
                            epoch=epoch,
                            step=total_steps
                        )
                    
                    # Memory management
                    if self.accelerator.device.type == 'cuda' and total_steps % 100 == 0:
                        torch.cuda.empty_cache()
            
            # End of epoch
            avg_epoch_loss = epoch_loss / num_batches
            metrics['train_loss'].append(avg_epoch_loss)
            logger.info(f"Epoch {epoch + 1}/{num_epochs} complete. Avg Loss: {avg_epoch_loss:.4f}")
        
        # Final save
        self.save_checkpoint(
            Path(output_dir) / "final_model",
            optimizer=optimizer,
            scheduler=lr_scheduler,
            epoch=num_epochs,
            step=total_steps
        )
        
        # Cleanup
        self.accelerator.end_training()
        
        return metrics
    
    def evaluate(self) -> float:
        """Evaluate model on validation set"""
        if not self.eval_dataloader:
            return 0.0
        
        self.model.eval()
        total_loss = 0
        num_batches = 0
        
        with torch.no_grad():
            for batch in self.eval_dataloader:
                outputs = self.model(**batch)
                loss = outputs.loss
                total_loss += loss.detach().float()
                num_batches += 1
        
        avg_loss = total_loss / num_batches
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
        """Save model checkpoint with Accelerator"""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Let Accelerator handle the saving
        self.accelerator.wait_for_everyone()
        
        unwrapped_model = self.accelerator.unwrap_model(self.model)
        
        # Save model
        if self.accelerator.is_main_process:
            unwrapped_model.save_pretrained(
                output_dir,
                is_main_process=self.accelerator.is_main_process,
                save_function=self.accelerator.save,
                state_dict=self.accelerator.get_state_dict(self.model)
            )
            self.tokenizer.save_pretrained(output_dir)
            
            # Save training state
            if optimizer and scheduler:
                torch.save({
                    'optimizer_state_dict': optimizer.state_dict(),
                    'scheduler_state_dict': scheduler.state_dict(),
                    'accelerator_state': self.accelerator.state,
                    'gradient_checkpointing': self.gradient_checkpointing,
                    **kwargs
                }, output_dir / 'training_state.pt')
            
            logger.info(f"Checkpoint saved to {output_dir}")
    
    def load_checkpoint(self, checkpoint_dir: Path):
        """Load model checkpoint"""
        from peft import PeftModel
        
        # Load model
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
        
        # Re-enable gradient checkpointing if it was enabled
        if self.gradient_checkpointing and hasattr(self.model, 'gradient_checkpointing_enable'):
            self.model.gradient_checkpointing_enable()
        
        # Load tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(checkpoint_dir)
        
        logger.info(f"Checkpoint loaded from {checkpoint_dir}")

# Example usage
def train_ner_with_accelerate():
    """Example: Train NER model for utility jargon extraction"""
    from torch.utils.data import TensorDataset, DataLoader
    import torch
    
    # Initialize trainer with all optimizations
    trainer = AcceleratedTrainer(
        model_name="bert-base-uncased",
        num_labels=7,  # PG&E entities
        use_lora=True,
        gradient_checkpointing=True,  # Enable for memory savings
        mixed_precision="fp16",
        gradient_accumulation_steps=4
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
    
    # Prepare data
    trainer.prepare_data(train_loader, eval_loader)
    
    # Train with all optimizations
    metrics = trainer.train(
        num_epochs=3,
        learning_rate=2e-5,
        output_dir="./output/ner_accelerated",
        save_steps=500,
        eval_steps=100,
        logging_steps=10
    )
    
    logger.info(f"Training complete! Final metrics: {metrics}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Check Accelerate state
    accelerator = Accelerator()
    print(f"Accelerate Configuration:")
    print(f"  Device: {accelerator.device}")
    print(f"  Mixed Precision: {accelerator.mixed_precision}")
    print(f"  Distributed Type: {accelerator.distributed_type}")
    print(f"  Num Processes: {accelerator.num_processes}")
    
    # Run example if available
    if accelerator.device.type in ['cuda', 'cpu']:
        print("\nRunning Accelerated training example...")
        train_ner_with_accelerate()
