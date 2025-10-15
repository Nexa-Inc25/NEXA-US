"""
ML Dependency Monitoring Module
Non-intrusive monitoring that can be optionally integrated
"""

import importlib
import torch
import os
from typing import Dict, Any
from pathlib import Path
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
# GPUtil is optional for GPU monitoring
try:
    import GPUtil
    GPUTIL_AVAILABLE = True
except ImportError:
    GPUTIL_AVAILABLE = False
try:
    from accelerate import Accelerator
    from accelerate.state import PartialState
    ACCELERATE_AVAILABLE = True
except Exception:
    ACCELERATE_AVAILABLE = False
    Accelerator = None
    class PartialState:
        def __init__(self):
            self.backend = None
            self.num_processes = 1
            self.process_index = 0
            self.device = torch.device('cpu')

class MLMonitor:
    """Standalone ML monitoring with Accelerate state tracking"""
    
    @staticmethod
    def get_accelerate_status() -> Dict[str, Any]:
        """Get Accelerate configuration and state"""
        if not ACCELERATE_AVAILABLE:
            return {'enabled': False, 'error': 'accelerate not installed'}
        try:
            # Initialize Accelerator with minimal parameters for version compatibility
            accelerator = Accelerator(cpu=not torch.cuda.is_available())
            state = PartialState()
            
            return {
                'enabled': True,
                'device': str(accelerator.device),
                'distributed_type': str(accelerator.distributed_type),
                'mixed_precision': str(accelerator.mixed_precision),
                'num_processes': accelerator.num_processes,
                'process_index': accelerator.process_index,
                'is_main_process': accelerator.is_main_process,
                'is_local_main_process': accelerator.is_local_main_process,
                'gradient_accumulation_steps': accelerator.gradient_accumulation_steps,
                'state': {
                    'backend': state.backend,
                    'num_processes': state.num_processes,
                    'process_index': state.process_index,
                    'device': str(state.device)
                }
            }
        except Exception as e:
            return {
                'enabled': False,
                'error': str(e)
            }
    
    @staticmethod
    def get_torch_status() -> Dict[str, Any]:
        """Get comprehensive torch configuration status with detailed memory"""
        status = {
            'version': torch.__version__,
            'cuda_available': torch.cuda.is_available(),
            'cuda_version': torch.version.cuda if torch.cuda.is_available() else None,
            'device': str(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'cpu'),
            'device_count': torch.cuda.device_count() if torch.cuda.is_available() else 0,
            'cudnn_enabled': torch.backends.cudnn.enabled if torch.cuda.is_available() else False,
        }
        
        # Detailed memory statistics
        if torch.cuda.is_available():
            allocated = torch.cuda.memory_allocated()
            reserved = torch.cuda.memory_reserved()
            total = torch.cuda.get_device_properties(0).total_memory
            
            status['memory'] = {
                'allocated_mb': allocated / 1024**2,
                'reserved_mb': reserved / 1024**2,
                'free_mb': (total - reserved) / 1024**2,
                'total_mb': total / 1024**2,
                'peak_allocated_mb': torch.cuda.max_memory_allocated() / 1024**2,
                'fragmentation': 1 - (allocated / max(reserved, 1)),
                'utilization': allocated / total * 100
            }
            
            # Memory summary if available
            if hasattr(torch.cuda, 'memory_summary'):
                status['memory_summary'] = torch.cuda.memory_summary(abbreviated=True)
        else:
            if PSUTIL_AVAILABLE:
                mem = psutil.virtual_memory()
                status['memory'] = {
                    'cpu_used_mb': mem.used / 1024**2,
                    'cpu_available_mb': mem.available / 1024**2,
                    'cpu_percent': mem.percent
                }
            else:
                status['memory'] = {
                    'cpu_used_mb': None,
                    'cpu_available_mb': None,
                    'cpu_percent': None
                }
        
        return status
    
    @staticmethod
    def check_ml_dependencies() -> Dict[str, Any]:
        """Check ML module dependency health with Accelerate"""
        status = {}
        
        # Add Accelerate status
        status['accelerate'] = MLMonitor.get_accelerate_status()
        
        # Check external deps
        ml_packages = [
            'torch', 'transformers', 'ultralytics', 'peft', 
            'accelerate', 'sentence_transformers', 'roboflow'
        ]
        
        for package in ml_packages:
            try:
                m = importlib.import_module(package)
                status[package] = {
                    'installed': True,
                    'version': getattr(m, '__version__', 'unknown'),
                    'location': getattr(m, '__file__', 'unknown')
                }
            except ImportError as e:
                status[package] = {
                    'installed': False,
                    'error': str(e)
                }
        
        # Check internal module availability
        modules_dir = Path(__file__).parent / 'modules'
        if modules_dir.exists():
            internal_modules = [
                'model_fine_tuner', 'conduit_ner_fine_tuner',
                'roboflow_dataset_integrator', 'spec_learning_endpoints'
            ]
            
            for module in internal_modules:
                module_path = modules_dir / f"{module}.py"
                status[f"modules.{module}"] = {
                    'available': module_path.exists(),
                    'size_kb': module_path.stat().st_size / 1024 if module_path.exists() else 0
                }
        
        return {
            'torch_config': MLMonitor.get_torch_status(),
            'accelerate_config': status.get('accelerate', {}),
            'dependencies': status,
            'healthy': all(
                v.get('installed', v.get('available', v.get('enabled', False))) 
                for v in status.values()
            )
        }
    
    @staticmethod
    def get_inference_config() -> Dict[str, Any]:
        """Get optimal inference configuration with memory considerations"""
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        # Calculate optimal batch size based on available memory
        if device.type == 'cuda':
            free_memory = (torch.cuda.get_device_properties(0).total_memory - 
                          torch.cuda.memory_reserved()) / 1024**3  # GB
            batch_size = 32 if free_memory > 8 else 16 if free_memory > 4 else 8
        else:
            batch_size = 8
        
        config = {
            'device': str(device),
            'batch_size': batch_size,
            'num_workers': min(4, os.cpu_count() or 1),
            'pin_memory': device.type == 'cuda',
            'mixed_precision': device.type == 'cuda',
            'compile_mode': 'reduce-overhead' if torch.__version__ >= '2.0' else None,
            'grad_enabled': False,  # Always false for inference
            'memory_config': {
                'clear_cache_interval': 10,
                'gradient_accumulation': 4 if device.type == 'cuda' else 1,
                'memory_efficient_attention': True
            },
            'environment': {
                'OMP_NUM_THREADS': os.getenv('OMP_NUM_THREADS', '1'),
                'CUDA_VISIBLE_DEVICES': os.getenv('CUDA_VISIBLE_DEVICES', ''),
                'ENABLE_MIXED_PRECISION': os.getenv('ENABLE_MIXED_PRECISION', 'false'),
                'PYTORCH_CUDA_ALLOC_CONF': os.getenv('PYTORCH_CUDA_ALLOC_CONF', 
                    'expandable_segments:True,garbage_collection_threshold:0.8')
            }
        }
        
        return config

# Optional FastAPI integration - only if explicitly imported
def create_monitoring_router():
    """Create router that can be optionally added to app"""
    from fastapi import APIRouter
    
    router = APIRouter(prefix="/ml-monitor", tags=["ML Monitoring"])
    
    @router.get("/status")
    async def ml_status():
        """Non-intrusive ML status endpoint"""
        return MLMonitor.check_ml_dependencies()
    
    @router.get("/inference-config")
    async def inference_config():
        """Get optimal inference settings"""
        return MLMonitor.get_inference_config()
    
    return router

# CLI usage for standalone monitoring
if __name__ == "__main__":
    import json
    
    print("=" * 60)
    print("NEXA ML Monitoring Report")
    print("=" * 60)
    
    status = MLMonitor.check_ml_dependencies()
    print(json.dumps(status, indent=2))
    
    print("\n" + "=" * 60)
    print("Inference Configuration")
    print("=" * 60)
    
    config = MLMonitor.get_inference_config()
    print(json.dumps(config, indent=2))
