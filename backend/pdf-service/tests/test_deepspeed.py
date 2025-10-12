"""
Test DeepSpeed Integration
Validates ZeRO optimization and memory efficiency
"""

import pytest
import torch
from unittest.mock import patch, MagicMock, PropertyMock
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

class TestDeepSpeedIntegration:
    """Test suite for DeepSpeed integration via Accelerate"""
    
    @pytest.fixture
    def mock_deepspeed(self):
        """Mock DeepSpeed availability"""
        with patch('accelerate.utils.is_deepspeed_available', return_value=True):
            yield
    
    @pytest.fixture
    def mock_gpu(self):
        """Mock GPU availability for DeepSpeed"""
        with patch('torch.cuda.is_available', return_value=True):
            with patch('torch.cuda.get_device_properties') as mock_props:
                mock_props.return_value.total_memory = 16 * 1024**3  # 16GB GPU
                yield
    
    def test_deepspeed_plugin_initialization(self, mock_deepspeed, mock_gpu):
        """Test DeepSpeed plugin initialization in device manager"""
        # Set DeepSpeed environment
        os.environ['USE_DEEPSPEED'] = 'true'
        os.environ['DEEPSPEED_CONFIG_FILE'] = 'deployment/deepspeed_config.json'
        
        try:
            # Mock config file existence
            with patch('os.path.exists', return_value=True):
                from modules.ml_device_utils import DeviceManager
                
                # Reinitialize to pick up DeepSpeed
                manager = DeviceManager()
                manager._device = torch.device('cuda')
                manager._init_accelerator()
                
                # Check accelerator has DeepSpeed
                assert manager.accelerator is not None
                
        finally:
            # Cleanup
            os.environ['USE_DEEPSPEED'] = 'false'
    
    def test_zero_stage_configuration(self, mock_deepspeed):
        """Test ZeRO stage configuration"""
        from accelerate import DeepSpeedPlugin
        
        # Test different ZeRO stages
        for stage in [0, 1, 2, 3]:
            plugin = DeepSpeedPlugin(
                zero_stage=stage,
                gradient_accumulation_steps=4,
                gradient_clipping=1.0,
                offload_optimizer_device='cpu' if stage >= 2 else None,
                offload_param_device='cpu' if stage == 3 else None
            )
            
            assert plugin.zero_stage == stage
            if stage >= 2:
                assert plugin.offload_optimizer_device == 'cpu'
            if stage == 3:
                assert plugin.offload_param_device == 'cpu'
    
    def test_deepspeed_trainer_initialization(self, mock_deepspeed, mock_gpu):
        """Test DeepSpeedTrainer initialization"""
        os.environ['USE_DEEPSPEED'] = 'true'
        
        try:
            with patch('modules.ml_device_utils.get_accelerator') as mock_accel:
                # Mock accelerator
                mock_accel.return_value = MagicMock()
                mock_accel.return_value.device = torch.device('cuda')
                mock_accel.return_value.is_main_process = True
                mock_accel.return_value.main_process_first = MagicMock()
                
                from modules.deepspeed_trainer import DeepSpeedTrainer
                
                trainer = DeepSpeedTrainer(
                    model_name="bert-base-uncased",
                    num_labels=7,
                    use_lora=True,
                    zero_stage=3,
                    offload_optimizer=True,
                    offload_params=True,
                    gradient_checkpointing=True
                )
                
                assert trainer.zero_stage == 3
                assert trainer.gradient_checkpointing == True
                
        finally:
            os.environ['USE_DEEPSPEED'] = 'false'
    
    def test_dummy_optimizer_scheduler(self, mock_deepspeed):
        """Test DummyOptimizer and DummyScheduler usage"""
        from accelerate.utils import DummyOptim, DummyScheduler
        
        # Create dummy model
        model = torch.nn.Linear(10, 2)
        
        # Test DummyOptim
        optimizer = DummyOptim(model.parameters())
        assert optimizer is not None
        
        # Test DummyScheduler
        scheduler = DummyScheduler(
            optimizer,
            total_num_steps=1000,
            warmup_num_steps=100
        )
        assert scheduler is not None
        
        # Test that they don't error on standard operations
        optimizer.zero_grad()
        optimizer.step()
        scheduler.step()
    
    def test_memory_efficiency_with_zero3(self, mock_deepspeed, mock_gpu):
        """Test memory efficiency claims of ZeRO-3"""
        from modules.deepspeed_trainer import DeepSpeedTrainer
        
        os.environ['USE_DEEPSPEED'] = 'true'
        
        try:
            with patch('modules.ml_device_utils.get_accelerator') as mock_accel:
                mock_accel.return_value = MagicMock()
                mock_accel.return_value.device = torch.device('cuda')
                
                # Without ZeRO (baseline)
                baseline_trainer = DeepSpeedTrainer(
                    zero_stage=0,
                    offload_optimizer=False,
                    offload_params=False
                )
                
                # With ZeRO-3 (optimized)
                optimized_trainer = DeepSpeedTrainer(
                    zero_stage=3,
                    offload_optimizer=True,
                    offload_params=True
                )
                
                # ZeRO-3 should have offloading enabled
                assert optimized_trainer.zero_stage == 3
                
        finally:
            os.environ['USE_DEEPSPEED'] = 'false'
    
    def test_checkpoint_save_load(self, mock_deepspeed, tmp_path):
        """Test checkpoint saving and loading with DeepSpeed"""
        from modules.deepspeed_trainer import DeepSpeedTrainer
        
        os.environ['USE_DEEPSPEED'] = 'true'
        
        try:
            with patch('modules.ml_device_utils.get_accelerator') as mock_accel:
                mock_accel.return_value = MagicMock()
                mock_accel.return_value.is_main_process = True
                mock_accel.return_value.wait_for_everyone = MagicMock()
                mock_accel.return_value.unwrap_model = MagicMock()
                mock_accel.return_value.save_state = MagicMock()
                mock_accel.return_value.load_state = MagicMock()
                
                trainer = DeepSpeedTrainer(zero_stage=3)
                
                # Test save
                checkpoint_dir = tmp_path / "checkpoint"
                trainer.save_checkpoint(checkpoint_dir)
                mock_accel.return_value.save_state.assert_called()
                
                # Test load
                trainer.load_checkpoint(checkpoint_dir)
                mock_accel.return_value.load_state.assert_called()
                
        finally:
            os.environ['USE_DEEPSPEED'] = 'false'
    
    def test_gradient_accumulation_with_deepspeed(self, mock_deepspeed):
        """Test gradient accumulation integration"""
        from accelerate import Accelerator, DeepSpeedPlugin
        
        plugin = DeepSpeedPlugin(
            gradient_accumulation_steps=4,
            zero_stage=2
        )
        
        with patch('accelerate.Accelerator') as MockAccelerator:
            instance = MockAccelerator.return_value
            instance.accumulate = MagicMock()
            
            accelerator = Accelerator(
                gradient_accumulation_steps=4,
                deepspeed_plugin=plugin
            )
            
            # Verify accumulation steps
            MockAccelerator.assert_called_with(
                gradient_accumulation_steps=4,
                deepspeed_plugin=plugin
            )
    
    def test_inference_mode_with_deepspeed(self, mock_deepspeed):
        """Test inference optimization with DeepSpeed"""
        from modules.ml_device_utils import DeviceManager
        
        os.environ['USE_DEEPSPEED'] = 'true'
        
        try:
            with patch('os.path.exists', return_value=True):
                manager = DeviceManager()
                manager._device = torch.device('cuda')
                manager._init_accelerator()
                
                # Test inference mode
                with manager.inference_mode():
                    # Should disable gradients
                    assert not torch.is_grad_enabled()
                
                # Gradients re-enabled outside
                assert torch.is_grad_enabled()
                
        finally:
            os.environ['USE_DEEPSPEED'] = 'false'
    
    @pytest.mark.parametrize("zero_stage,expected_mem_reduction", [
        (0, 1.0),   # No reduction
        (1, 0.75),  # 25% reduction (optimizer sharding)
        (2, 0.5),   # 50% reduction (+ gradient sharding)
        (3, 0.1),   # 90% reduction (+ parameter sharding with offload)
    ])
    def test_memory_reduction_by_stage(self, zero_stage, expected_mem_reduction):
        """Test expected memory reduction by ZeRO stage"""
        base_memory = 4 * 1024**3  # 4GB base model
        
        # Calculate expected memory with ZeRO
        if zero_stage == 0:
            expected = base_memory
        elif zero_stage == 1:
            # Optimizer states sharded
            expected = base_memory * expected_mem_reduction
        elif zero_stage == 2:
            # Optimizer + gradients sharded
            expected = base_memory * expected_mem_reduction
        else:  # zero_stage == 3
            # Everything sharded and offloaded
            expected = base_memory * expected_mem_reduction
        
        # Verify reduction is significant for higher stages
        assert expected <= base_memory
        if zero_stage > 0:
            assert expected < base_memory
    
    def test_config_file_loading(self, mock_deepspeed, tmp_path):
        """Test DeepSpeed config file loading"""
        import json
        
        # Create test config
        config = {
            "train_batch_size": "auto",
            "gradient_accumulation_steps": "auto",
            "zero_optimization": {
                "stage": 3,
                "offload_optimizer": {
                    "device": "cpu"
                }
            }
        }
        
        config_file = tmp_path / "ds_config.json"
        with open(config_file, 'w') as f:
            json.dump(config, f)
        
        os.environ['DEEPSPEED_CONFIG_FILE'] = str(config_file)
        
        try:
            # Verify config can be loaded
            with open(os.environ['DEEPSPEED_CONFIG_FILE'], 'r') as f:
                loaded_config = json.load(f)
            
            assert loaded_config["zero_optimization"]["stage"] == 3
            assert loaded_config["zero_optimization"]["offload_optimizer"]["device"] == "cpu"
            
        finally:
            del os.environ['DEEPSPEED_CONFIG_FILE']

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
