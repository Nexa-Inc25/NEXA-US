"""
ML Device Management Utilities
Handles CPU/GPU detection, memory management, and optimization
"""

import torch
import os
import contextlib
from typing import Optional, Union, Generator
import logging
try:
    from accelerate import Accelerator, DeepSpeedPlugin
    from accelerate.utils import set_seed, is_deepspeed_available
    ACCELERATE_AVAILABLE = True
except Exception:
    # Accelerate is optional in production CPU-only environments
    Accelerator = None  # type: ignore
    DeepSpeedPlugin = None  # type: ignore
    ACCELERATE_AVAILABLE = False
    def set_seed(seed: int):  # fallback
        torch.manual_seed(seed)
    def is_deepspeed_available() -> bool:  # fallback
        return False

logger = logging.getLogger(__name__)

class DeviceManager:
    """Centralized device management for ML modules with Accelerate integration"""
    
    _instance = None
    _device = None
    _accelerator = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._device is None:
            self._device = self._detect_device()
            self._init_accelerator()
    
    def _init_accelerator(self):
        """Initialize Accelerator with optimal settings and DeepSpeed support"""
        if not ACCELERATE_AVAILABLE:
            self._accelerator = None
            logger.info("Accelerate not available; continuing without Accelerator/DeepSpeed")
            return
        mixed_precision = 'fp16' if os.getenv('ENABLE_MIXED_PRECISION', 'false').lower() == 'true' else 'no'
        gradient_accumulation_steps = int(os.getenv('GRADIENT_ACCUMULATION_STEPS', '1'))
        
        # Check for DeepSpeed configuration
        deepspeed_plugin = None
        if os.getenv('USE_DEEPSPEED', 'false').lower() == 'true' and is_deepspeed_available():
            deepspeed_config_file = os.getenv('DEEPSPEED_CONFIG_FILE', 'deployment/deepspeed_config.json')
            if os.path.exists(deepspeed_config_file):
                deepspeed_plugin = DeepSpeedPlugin(
                    hf_ds_config=None,
                    gradient_accumulation_steps=gradient_accumulation_steps,
                    gradient_clipping=1.0,
                    zero_stage=3 if self._device.type == 'cuda' else 0,  # ZeRO-3 for GPU
                    offload_optimizer_device='cpu',
                    offload_param_device='cpu',
                    zero3_init_flag=True,  # Enable ZeRO-3 initialization
                    zero3_save_16bit_model=True
                )
                logger.info(f"DeepSpeed enabled with ZeRO Stage {deepspeed_plugin.zero_stage}")
        
        # Create Accelerator with compatible parameters for version 1.10.1
        accelerator_kwargs = {
            'mixed_precision': mixed_precision,
            'gradient_accumulation_steps': gradient_accumulation_steps,
            'cpu': self._device.type == 'cpu',
            'deepspeed_plugin': deepspeed_plugin,
            'log_with': None  # Can add 'tensorboard' or 'wandb'
        }
        
        # Note: dispatch_batches and split_batches parameters were removed 
        # as they're not compatible with accelerate 1.10.1
        
        self._accelerator = Accelerator(**accelerator_kwargs)
        
        # Set seed for reproducibility
        if os.getenv('SEED'):
            set_seed(int(os.getenv('SEED', '42')))
        
        logger.info(f"Accelerator initialized: Device={self._accelerator.device}, "
                   f"Mixed Precision={mixed_precision}, "
                   f"Accumulation Steps={gradient_accumulation_steps}")
    
    @property
    def accelerator(self) -> Accelerator:
        """Get the Accelerator instance"""
        return self._accelerator
    
    def _detect_device(self) -> torch.device:
        """Auto-detect best available device"""
        # Check environment override
        force_cpu = os.getenv('FORCE_CPU', 'false').lower() == 'true'
        
        if force_cpu:
            logger.info("Forcing CPU usage (FORCE_CPU=true)")
            return torch.device('cpu')
        
        if torch.cuda.is_available():
            # GPU available
            device_id = int(os.getenv('CUDA_DEVICE_ID', '0'))
            device = torch.device(f'cuda:{device_id}')
            logger.info(f"Using GPU: {torch.cuda.get_device_name(device_id)}")
            
            # Set memory fraction to prevent OOM on shared GPUs
            if os.getenv('CUDA_MEMORY_FRACTION'):
                fraction = float(os.getenv('CUDA_MEMORY_FRACTION', '0.8'))
                torch.cuda.set_per_process_memory_fraction(fraction, device_id)
                logger.info(f"GPU memory fraction set to {fraction}")
            
            return device
        else:
            logger.info("Using CPU (no GPU available)")
            return torch.device('cpu')
    
    @property
    def device(self) -> torch.device:
        """Get the current device"""
        return self._device
    
    def to_device(self, tensor_or_model: Union[torch.Tensor, torch.nn.Module]):
        """Move tensor or model to the configured device"""
        return tensor_or_model.to(self._device)
    
    @contextlib.contextmanager
    def inference_mode(self) -> Generator:
        """Context manager for efficient inference"""
        with torch.inference_mode():  # Better than no_grad for inference
            if self._device.type == 'cuda':
                with torch.cuda.amp.autocast():  # Auto mixed precision
                    yield
            else:
                yield
    
    def optimize_for_inference(self, model: torch.nn.Module) -> torch.nn.Module:
        """Optimize model for inference with Accelerate support"""
        model.eval()
        
        # Use Accelerator if available
        if self._accelerator:
            model = self._accelerator.prepare_model(model, evaluation_mode=True)
        
        # Move to device
        model = self.to_device(model)
        
        # Compile if available (PyTorch 2.0+)
        if hasattr(torch, 'compile') and not os.getenv('DISABLE_COMPILE', 'false').lower() == 'true':
            try:
                model = torch.compile(model, mode='reduce-overhead')
                logger.info("Model compiled for optimized inference")
            except Exception as e:
                logger.warning(f"Model compilation failed: {e}")
        
        # Disable gradient computation for all parameters
        for param in model.parameters():
            param.requires_grad = False
        
        return model
    
    def get_batch_size(self, base_size: int = 16, model_size_mb: float = 500) -> int:
        """Get optimal batch size with adaptive scaling"""
        if self._device.type == 'cuda':
            # Get actual available memory
            props = torch.cuda.get_device_properties(0)
            total_memory = props.total_memory
            reserved_memory = torch.cuda.memory_reserved()
            available_memory = total_memory - reserved_memory
            
            # Estimate memory per batch item (model + activations)
            estimated_item_memory = model_size_mb * 1024**2 * 1.5  # 1.5x for activations
            
            # Calculate safe batch size (use 80% of available)
            safe_memory = available_memory * 0.8
            max_batch = int(safe_memory / estimated_item_memory)
            
            # Apply constraints
            if available_memory > 8 * 1024**3:  # >8GB
                return min(max_batch, base_size * 2)
            elif available_memory > 4 * 1024**3:  # >4GB
                return min(max_batch, base_size)
            else:
                return min(max_batch, base_size // 2, 4)  # Min 4 for stability
        else:
            # CPU: Conservative batch size
            import psutil
            available_ram = psutil.virtual_memory().available
            if available_ram > 8 * 1024**3:
                return base_size // 2
            return min(base_size // 4, 8)
    
    def clear_cache(self, deep_clean: bool = False):
        """Clear GPU cache with optional deep cleaning"""
        import gc
        
        # Python garbage collection first
        gc.collect()
        
        if self._device.type == 'cuda':
            # Clear PyTorch cache
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
            
            # Reset peak memory stats for monitoring
            if deep_clean:
                torch.cuda.reset_peak_memory_stats()
                torch.cuda.reset_accumulated_memory_stats()
            
            # Log memory state
            allocated = torch.cuda.memory_allocated() / 1024**2
            reserved = torch.cuda.memory_reserved() / 1024**2
            logger.info(f"GPU cache cleared - Allocated: {allocated:.1f}MB, Reserved: {reserved:.1f}MB")
        else:
            logger.info("CPU mode - Python GC completed")
    
    def get_memory_summary(self) -> dict:
        """Get comprehensive memory statistics"""
        if self._device.type == 'cuda':
            return {
                'allocated_mb': torch.cuda.memory_allocated() / 1024**2,
                'reserved_mb': torch.cuda.memory_reserved() / 1024**2,
                'free_mb': (torch.cuda.get_device_properties(0).total_memory - 
                           torch.cuda.memory_reserved()) / 1024**2,
                'peak_allocated_mb': torch.cuda.max_memory_allocated() / 1024**2,
                'fragmentation_ratio': 1 - (torch.cuda.memory_allocated() / 
                                           max(torch.cuda.memory_reserved(), 1))
            }
        else:
            import psutil
            mem = psutil.virtual_memory()
            return {
                'used_mb': mem.used / 1024**2,
                'available_mb': mem.available / 1024**2,
                'percent': mem.percent
            }
    
    def memory_snapshot(self, filename: Optional[str] = None) -> Optional[dict]:
        """Capture detailed memory snapshot for debugging"""
        if self._device.type == 'cuda' and hasattr(torch.cuda, '_memory_viz'):
            try:
                snapshot = torch.cuda._memory_viz.snapshot()
                if filename:
                    import json
                    with open(filename, 'w') as f:
                        json.dump(snapshot, f, indent=2)
                    logger.info(f"Memory snapshot saved to {filename}")
                return snapshot
            except Exception as e:
                logger.warning(f"Memory snapshot failed: {e}")
        return None

# Global instance
device_manager = DeviceManager()

# Convenience functions
def get_device() -> torch.device:
    """Get the configured device"""
    return device_manager.device

def get_accelerator(use_deepspeed: bool = None) -> Accelerator:
    """Get the configured Accelerator with optional DeepSpeed override"""
    if use_deepspeed is not None:
        # Temporarily override DeepSpeed setting
        old_val = os.getenv('USE_DEEPSPEED', 'false')
        os.environ['USE_DEEPSPEED'] = 'true' if use_deepspeed else 'false'
        device_manager._init_accelerator()  # Reinitialize
        os.environ['USE_DEEPSPEED'] = old_val
    return device_manager.accelerator

def to_device(tensor_or_model):
    """Move to configured device"""
    return device_manager.to_device(tensor_or_model)

@contextlib.contextmanager
def inference_mode():
    """Context manager for inference"""
    with device_manager.inference_mode():
        yield

def optimize_model(model: torch.nn.Module) -> torch.nn.Module:
    """Optimize model for inference"""
    return device_manager.optimize_for_inference(model)

# Example usage in ML modules
def example_fine_tuner_usage():
    """Example of how to use device utilities in fine-tuners"""
    import torch.nn as nn
    from transformers import AutoModelForTokenClassification
    
    # Get device
    device = get_device()
    
    # Load model
    model = AutoModelForTokenClassification.from_pretrained('bert-base-uncased')
    model = to_device(model)
    
    # Training mode
    model.train()
    optimizer = torch.optim.AdamW(model.parameters())
    
    # ... training loop ...
    
    # Switch to inference
    model = optimize_model(model)
    
    # Inference with optimization
    with inference_mode():
        # Input already on device
        inputs = to_device(torch.tensor([[1, 2, 3]]))
        outputs = model(inputs)
        # Results automatically optimized
    
    # Clean up
    device_manager.clear_cache()

if __name__ == "__main__":
    # Test device detection
    print(f"Detected device: {get_device()}")
    print(f"Optimal batch size: {device_manager.get_batch_size()}")
    
    # Test inference optimization
    dummy_model = torch.nn.Linear(10, 2)
    optimized = optimize_model(dummy_model)
    
    with inference_mode():
        test_input = to_device(torch.randn(4, 10))
        output = optimized(test_input)
        print(f"Inference output shape: {output.shape}")
