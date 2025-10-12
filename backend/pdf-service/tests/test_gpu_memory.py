"""
Test GPU Memory Management
Validates memory optimization strategies
"""

import pytest
import torch
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

class TestGPUMemoryManagement:
    """Test suite for GPU memory optimization"""
    
    @pytest.fixture
    def mock_cuda(self):
        """Mock CUDA availability for testing"""
        with patch('torch.cuda.is_available', return_value=True):
            with patch('torch.cuda.get_device_properties') as mock_props:
                mock_props.return_value.total_memory = 16 * 1024**3  # 16GB
                with patch('torch.cuda.memory_allocated', return_value=4 * 1024**3):  # 4GB allocated
                    with patch('torch.cuda.memory_reserved', return_value=6 * 1024**3):  # 6GB reserved
                        yield
    
    def test_device_manager_memory_functions(self, mock_cuda):
        """Test DeviceManager memory management functions"""
        from modules.ml_device_utils import DeviceManager
        
        manager = DeviceManager()
        
        # Test memory summary
        summary = manager.get_memory_summary()
        assert 'allocated_mb' in summary
        assert 'reserved_mb' in summary
        assert 'free_mb' in summary
        assert 'fragmentation_ratio' in summary
        
        # Verify calculations
        assert summary['allocated_mb'] == 4 * 1024  # 4GB in MB
        assert summary['reserved_mb'] == 6 * 1024  # 6GB in MB
        assert summary['free_mb'] == 10 * 1024  # 16GB - 6GB = 10GB
    
    def test_cache_clearing(self, mock_cuda):
        """Test GPU cache clearing with deep clean"""
        from modules.ml_device_utils import DeviceManager
        
        with patch('torch.cuda.empty_cache') as mock_empty:
            with patch('torch.cuda.synchronize') as mock_sync:
                with patch('torch.cuda.reset_peak_memory_stats') as mock_reset:
                    manager = DeviceManager()
                    
                    # Standard clear
                    manager.clear_cache(deep_clean=False)
                    mock_empty.assert_called_once()
                    mock_sync.assert_called_once()
                    mock_reset.assert_not_called()
                    
                    # Deep clean
                    manager.clear_cache(deep_clean=True)
                    assert mock_empty.call_count == 2
                    mock_reset.assert_called_once()
    
    def test_adaptive_batch_size(self, mock_cuda):
        """Test adaptive batch size calculation"""
        from modules.ml_device_utils import DeviceManager
        
        manager = DeviceManager()
        
        # Test with different model sizes
        batch_small_model = manager.get_batch_size(base_size=16, model_size_mb=500)
        batch_large_model = manager.get_batch_size(base_size=16, model_size_mb=2000)
        
        # Larger model should get smaller batch
        assert batch_small_model >= batch_large_model
        
        # Test minimum batch constraint
        with patch('torch.cuda.memory_reserved', return_value=15.5 * 1024**3):  # Almost full
            batch_low_mem = manager.get_batch_size(base_size=16, model_size_mb=1000)
            assert batch_low_mem >= 4  # Minimum batch size
    
    def test_gradient_accumulation(self):
        """Test gradient accumulation for memory efficiency"""
        from modules.gradient_accumulator import GradientAccumulator
        
        # Test accumulation step calculation
        steps = GradientAccumulator.calculate_accumulation_steps(
            desired_batch_size=64,
            max_device_batch_size=8
        )
        assert steps == 8  # 64 / 8 = 8
        
        # Test accumulator behavior
        accumulator = GradientAccumulator(
            accumulation_steps=4,
            mixed_precision=False
        )
        
        # Mock model and optimizer
        model = MagicMock()
        optimizer = MagicMock()
        
        # Simulate training steps
        for i in range(5):
            loss = torch.tensor(1.0, requires_grad=True)
            step_performed = accumulator.backward(loss, optimizer, model)
            
            if i < 3:
                # First 3 steps: accumulate, no optimizer step
                assert not step_performed
                optimizer.step.assert_not_called()
            elif i == 3:
                # 4th step: perform optimizer step
                assert step_performed
                optimizer.step.assert_called_once()
                optimizer.zero_grad.assert_called_once()
    
    def test_memory_monitoring(self, mock_cuda):
        """Test ML monitoring memory features"""
        from modules.ml_monitoring import MLMonitor
        
        monitor = MLMonitor()
        
        # Test torch status with memory
        status = monitor.get_torch_status()
        assert 'memory' in status
        assert 'allocated_mb' in status['memory']
        assert 'fragmentation' in status['memory']
        assert status['memory']['utilization'] == 25.0  # 4GB/16GB = 25%
        
        # Test inference config with memory
        config = monitor.get_inference_config()
        assert 'memory_config' in config
        assert config['memory_config']['gradient_accumulation'] == 4  # GPU mode
        assert 'PYTORCH_CUDA_ALLOC_CONF' in config['environment']
    
    def test_memory_snapshot(self, mock_cuda):
        """Test memory snapshot for debugging"""
        from modules.ml_device_utils import DeviceManager
        
        manager = DeviceManager()
        
        # Mock snapshot function
        with patch('torch.cuda._memory_viz.snapshot', return_value={'test': 'data'}):
            snapshot = manager.memory_snapshot()
            assert snapshot == {'test': 'data'}
            
            # Test saving to file
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
                manager.memory_snapshot(filename=f.name)
    
    @pytest.mark.parametrize("device_type,expected_batch", [
        ("cuda", 16),  # GPU gets larger batch
        ("cpu", 8),    # CPU gets smaller batch
    ])
    def test_device_specific_batch_size(self, device_type, expected_batch):
        """Test batch size varies by device type"""
        from modules.ml_device_utils import DeviceManager
        
        with patch('torch.cuda.is_available', return_value=(device_type == 'cuda')):
            if device_type == 'cuda':
                with patch('torch.cuda.get_device_properties') as mock_props:
                    mock_props.return_value.total_memory = 8 * 1024**3
                    with patch('torch.cuda.memory_reserved', return_value=2 * 1024**3):
                        manager = DeviceManager()
                        batch = manager.get_batch_size(base_size=16)
                        assert batch <= expected_batch
            else:
                manager = DeviceManager()
                batch = manager.get_batch_size(base_size=16)
                assert batch <= expected_batch
    
    def test_memory_efficient_inference(self, mock_cuda):
        """Test inference mode with memory optimization"""
        from modules.ml_device_utils import device_manager, inference_mode
        
        # Test inference context
        with inference_mode():
            # Should enable no_grad and mixed precision on GPU
            assert not torch.is_grad_enabled()
        
        # Grad should be re-enabled outside context
        assert torch.is_grad_enabled()
    
    def test_allocator_configuration(self):
        """Test CUDA allocator environment configuration"""
        import os
        
        # Set allocator config
        os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'expandable_segments:True,garbage_collection_threshold:0.8'
        
        from modules.ml_monitoring import MLMonitor
        config = MLMonitor.get_inference_config()
        
        # Verify config is in environment
        assert 'expandable_segments:True' in config['environment']['PYTORCH_CUDA_ALLOC_CONF']
        assert 'garbage_collection_threshold:0.8' in config['environment']['PYTORCH_CUDA_ALLOC_CONF']

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
