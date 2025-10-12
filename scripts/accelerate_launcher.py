#!/usr/bin/env python3
"""
Accelerate Launch Wrapper for NEXA ML Training
Provides unified interface for distributed training
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path
import yaml

def load_config(config_path: str = None) -> dict:
    """Load accelerate configuration"""
    if config_path and Path(config_path).exists():
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    # Default config
    return {
        'compute_environment': 'LOCAL_MACHINE',
        'distributed_type': 'NO',
        'fp16': True,
        'num_processes': 1,
        'gradient_accumulation_steps': 4
    }

def generate_launch_command(script: str, config_path: str = None, **kwargs) -> list:
    """Generate accelerate launch command with appropriate flags"""
    cmd = ['accelerate', 'launch']
    
    # Add config file if provided
    if config_path:
        cmd.extend(['--config_file', config_path])
    else:
        # Use environment-based configuration
        if os.getenv('ENABLE_MIXED_PRECISION', 'false').lower() == 'true':
            cmd.append('--mixed_precision=fp16')
        
        if os.getenv('GRADIENT_ACCUMULATION_STEPS'):
            cmd.extend(['--gradient_accumulation_steps', 
                       os.getenv('GRADIENT_ACCUMULATION_STEPS')])
        
        # CPU vs GPU
        if os.getenv('FORCE_CPU', 'false').lower() == 'true':
            cmd.append('--cpu')
        else:
            # Multi-GPU settings
            num_gpus = os.getenv('NUM_GPUS', '1')
            if int(num_gpus) > 1:
                cmd.extend(['--multi_gpu', '--num_processes', num_gpus])
    
    # Add the script to run
    cmd.append(script)
    
    # Add script arguments
    for key, value in kwargs.items():
        cmd.extend([f'--{key}', str(value)])
    
    return cmd

def launch_training(
    script: str,
    config: str = None,
    model: str = 'bert-base-uncased',
    data_dir: str = './data',
    output_dir: str = './output',
    epochs: int = 3,
    batch_size: int = 16,
    learning_rate: float = 2e-5,
    **kwargs
):
    """Launch training with Accelerate"""
    
    # Validate script exists
    script_path = Path(script)
    if not script_path.exists():
        print(f"Error: Script {script} not found")
        sys.exit(1)
    
    # Set up environment
    env = os.environ.copy()
    
    # Add NEXA-specific environment variables
    env['MODEL_NAME'] = model
    env['DATA_DIR'] = data_dir
    env['OUTPUT_DIR'] = output_dir
    env['NUM_EPOCHS'] = str(epochs)
    env['BATCH_SIZE'] = str(batch_size)
    env['LEARNING_RATE'] = str(learning_rate)
    
    # Render-specific optimizations
    if 'RENDER' in env:
        env['OMP_NUM_THREADS'] = '1'
        env['TOKENIZERS_PARALLELISM'] = 'false'
    
    # Generate command
    cmd = generate_launch_command(
        script=str(script_path),
        config_path=config,
        model_name=model,
        data_dir=data_dir,
        output_dir=output_dir,
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        learning_rate=learning_rate,
        **kwargs
    )
    
    print(f"Launching: {' '.join(cmd)}")
    
    # Execute
    try:
        result = subprocess.run(cmd, env=env, check=True)
        return result.returncode
    except subprocess.CalledProcessError as e:
        print(f"Training failed with error: {e}")
        return e.returncode

def main():
    """CLI interface for accelerate launcher"""
    parser = argparse.ArgumentParser(description='Launch NEXA ML training with Accelerate')
    
    parser.add_argument('script', help='Training script to run')
    parser.add_argument('--config', default='deployment/accelerate_config.yaml',
                       help='Accelerate config file')
    parser.add_argument('--model', default='bert-base-uncased',
                       help='Model name or path')
    parser.add_argument('--data-dir', default='./data',
                       help='Training data directory')
    parser.add_argument('--output-dir', default='./output',
                       help='Output directory for model')
    parser.add_argument('--epochs', type=int, default=3,
                       help='Number of training epochs')
    parser.add_argument('--batch-size', type=int, default=16,
                       help='Training batch size')
    parser.add_argument('--learning-rate', type=float, default=2e-5,
                       help='Learning rate')
    parser.add_argument('--gradient-checkpointing', action='store_true',
                       help='Enable gradient checkpointing')
    parser.add_argument('--test', action='store_true',
                       help='Run in test mode with reduced data')
    
    args = parser.parse_args()
    
    # Convert to kwargs
    kwargs = {}
    if args.gradient_checkpointing:
        kwargs['gradient_checkpointing'] = True
    if args.test:
        kwargs['max_steps'] = 10  # Quick test
    
    # Launch training
    exit_code = launch_training(
        script=args.script,
        config=args.config if Path(args.config).exists() else None,
        model=args.model,
        data_dir=args.data_dir,
        output_dir=args.output_dir,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        **kwargs
    )
    
    sys.exit(exit_code)

# Example launcher functions for specific NEXA models
def launch_ner_training():
    """Launch NER fine-tuning for utility jargon"""
    launch_training(
        script='backend/pdf-service/modules/train_ner_accelerated.py',
        config='deployment/accelerate_config.yaml',
        model='bert-base-uncased',
        data_dir='/data/training/ner',
        output_dir='/data/models/ner',
        epochs=5,
        batch_size=16,
        gradient_checkpointing=True
    )

def launch_yolo_training():
    """Launch YOLO training for pole detection"""
    launch_training(
        script='backend/pdf-service/modules/train_yolo_accelerated.py',
        config='deployment/accelerate_config.yaml',
        model='yolov8m.pt',
        data_dir='/data/training/yolo',
        output_dir='/data/models/yolo',
        epochs=100,
        batch_size=8
    )

def launch_sentence_transformer_training():
    """Launch Sentence Transformer fine-tuning"""
    launch_training(
        script='backend/pdf-service/modules/train_embeddings_accelerated.py',
        config='deployment/accelerate_config.yaml',
        model='all-MiniLM-L6-v2',
        data_dir='/data/training/embeddings',
        output_dir='/data/models/embeddings',
        epochs=3,
        batch_size=32
    )

if __name__ == '__main__':
    main()
