#!/usr/bin/env python3
"""
Train YOLOv8 locally for utility pole detection
GPU-optimized for best performance
"""

import os
from ultralytics import YOLO
from roboflow import Roboflow
import torch

def download_dataset():
    """Download Roboflow dataset locally"""
    print("=" * 60)
    print("📥 DOWNLOADING ROBOFLOW DATASET")
    print("=" * 60)
    
    api_key = input("Enter your Roboflow API Key (rf_...): ").strip()
    
    print("\nDownloading utility-pole-detection-birhf dataset...")
    rf = Roboflow(api_key=api_key)
    project = rf.workspace("unstructured").project("utility-pole-detection-birhf")
    dataset = project.version(1).download("yolov8", location="./roboflow_dataset")
    
    print(f"\n✅ Dataset downloaded to: ./roboflow_dataset")
    print(f"   - Training images: 920")
    print(f"   - Validation images: 375")
    return "./roboflow_dataset/data.yaml"

def check_gpu():
    """Check GPU availability"""
    print("\n" + "=" * 60)
    print("🖥️  CHECKING GPU")
    print("=" * 60)
    
    if torch.cuda.is_available():
        device = '0'
        gpu_name = torch.cuda.get_device_name(0)
        print(f"✅ GPU detected: {gpu_name}")
        print(f"   CUDA version: {torch.version.cuda}")
        print(f"   Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f}GB")
    elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
        device = 'mps'
        print("✅ Apple M1/M2 GPU detected (MPS)")
    else:
        device = 'cpu'
        print("⚠️  No GPU detected - training will use CPU (slower)")
    
    return device

def train_model(data_yaml, device='0'):
    """Train YOLOv8 on utility pole dataset"""
    print("\n" + "=" * 60)
    print("🚀 STARTING TRAINING")
    print("=" * 60)
    
    # Load base model
    model = YOLO('yolov8n.pt')
    
    # Training configuration
    config = {
        'data': data_yaml,
        'epochs': 50,              # Good balance of speed/accuracy
        'batch': 32 if device != 'cpu' else 8,  # Larger batch with GPU
        'imgsz': 640,              # Full resolution
        'device': device,
        'project': 'pole_training',
        'name': 'utility_pole_v1',
        'patience': 10,            # Early stopping
        'save': True,
        'cache': True if device != 'cpu' else False,  # Cache with GPU
        'workers': 8 if device != 'cpu' else 4,
        'optimizer': 'AdamW',
        'lr0': 0.001,              # Learning rate
        'verbose': True,
        'plots': True              # Generate training plots
    }
    
    print(f"\n📋 Training Configuration:")
    print(f"   Device: {device}")
    print(f"   Epochs: {config['epochs']}")
    print(f"   Batch Size: {config['batch']}")
    print(f"   Image Size: {config['imgsz']}px")
    print(f"   Cache: {config['cache']}")
    
    # Start training
    print(f"\n⏱️  Training started... (this may take 10-30 minutes)")
    results = model.train(**config)
    
    print("\n" + "=" * 60)
    print("✅ TRAINING COMPLETE!")
    print("=" * 60)
    
    # Print results
    best_model_path = 'pole_training/utility_pole_v1/weights/best.pt'
    print(f"\n📊 Training Results:")
    print(f"   Best model: {best_model_path}")
    print(f"   mAP50: {results.results_dict.get('metrics/mAP50(B)', 'N/A')}")
    print(f"   mAP50-95: {results.results_dict.get('metrics/mAP50-95(B)', 'N/A')}")
    
    return best_model_path

def test_model(model_path):
    """Test the trained model"""
    print("\n" + "=" * 60)
    print("🧪 TESTING MODEL")
    print("=" * 60)
    
    model = YOLO(model_path)
    
    # Validate on test set
    print("\nRunning validation...")
    metrics = model.val()
    
    print(f"\n📊 Validation Metrics:")
    print(f"   Precision: {metrics.box.p.mean():.3f}")
    print(f"   Recall: {metrics.box.r.mean():.3f}")
    print(f"   mAP50: {metrics.box.map50:.3f}")
    print(f"   mAP50-95: {metrics.box.map:.3f}")
    
    return metrics

def export_for_deployment(model_path):
    """Export model for production deployment"""
    print("\n" + "=" * 60)
    print("📦 EXPORTING FOR DEPLOYMENT")
    print("=" * 60)
    
    model = YOLO(model_path)
    
    # Export to ONNX for faster inference
    print("\nExporting to ONNX format...")
    onnx_path = model.export(format='onnx', imgsz=640, dynamic=True)
    
    print(f"\n✅ Model exported:")
    print(f"   PyTorch: {model_path}")
    print(f"   ONNX: {onnx_path}")
    
    return model_path, onnx_path

def print_deployment_instructions(model_path):
    """Print instructions for deploying to Render"""
    print("\n" + "=" * 60)
    print("🚀 DEPLOYMENT INSTRUCTIONS")
    print("=" * 60)
    
    print(f"\n1️⃣  Your trained model is ready:")
    print(f"   📁 {os.path.abspath(model_path)}")
    
    print(f"\n2️⃣  Deploy to Render:")
    print(f"   Option A - Upload via Render Dashboard:")
    print(f"   • Go to https://dashboard.render.com")
    print(f"   • Select your service")
    print(f"   • Go to 'Shell' tab")
    print(f"   • Upload {model_path} to /data/yolo_pole.pt")
    
    print(f"\n   Option B - SCP Upload (if you have Render SSH):")
    print(f"   • scp {model_path} render:/data/yolo_pole.pt")
    
    print(f"\n3️⃣  Restart your service:")
    print(f"   • The detector will auto-detect the trained model")
    print(f"   • Check /vision/model-status to verify")
    
    print(f"\n4️⃣  Test the deployment:")
    print(f"   • curl https://nexa-doc-analyzer-oct2025.onrender.com/vision/model-status")
    
    print("\n" + "=" * 60)

def main():
    """Main training workflow"""
    print("=" * 60)
    print("🎯 YOLOV8 LOCAL TRAINING FOR NEXA")
    print("   Utility Pole Detection Model")
    print("=" * 60)
    
    # Step 1: Download dataset
    data_yaml = download_dataset()
    
    # Step 2: Check GPU
    device = check_gpu()
    
    # Step 3: Train
    best_model = train_model(data_yaml, device)
    
    # Step 4: Test
    test_model(best_model)
    
    # Step 5: Export
    pytorch_model, onnx_model = export_for_deployment(best_model)
    
    # Step 6: Deployment instructions
    print_deployment_instructions(pytorch_model)
    
    print("\n🎉 ALL DONE! Your model is ready for deployment!")
    print("=" * 60)

if __name__ == "__main__":
    main()
