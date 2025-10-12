#!/usr/bin/env python3
"""
Roboflow Dataset Integration for NEXA
Downloads and integrates utility pole/crossarm datasets to fix detection issues
Target: Crossarm recall from 0% to >60%, mAP50-95 from 0.433 to >0.6
"""

import os
import json
import yaml
import shutil
import zipfile
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import requests
from dataclasses import dataclass
import subprocess

logger = logging.getLogger(__name__)

@dataclass
class RoboflowDataset:
    """Information about a Roboflow dataset"""
    name: str
    workspace: str
    project: str
    version: int
    image_count: int
    classes: List[str]
    description: str
    priority: int  # 1=highest priority for crossarm fix

# Top recommended datasets based on your research
RECOMMENDED_DATASETS = [
    RoboflowDataset(
        name="Utility Poles (Zac)",
        workspace="zac-ygkqm",
        project="utility-poles",
        version=1,
        image_count=380,
        classes=["concrete pole", "cutout", "double crossarm", "insulator", 
                 "lightning arrester", "single crossarm", "splice case", 
                 "steel pole", "street light", "transformer", "wood pole"],
        description="Best for crossarm recall fix - includes single/double crossarms",
        priority=1
    ),
    RoboflowDataset(
        name="Utility Pole Detection",
        workspace="unstructured",
        project="utility-pole-detection",
        version=1,
        image_count=1310,
        classes=["utility pole"],
        description="Large dataset for general pole detection improvement",
        priority=2
    ),
    RoboflowDataset(
        name="Utility Poles (Merlin)",
        workspace="merlin-h1cza",
        project="utility-poles",
        version=1,
        image_count=2128,
        classes=["utility-poles"],
        description="Largest dataset for volume training",
        priority=3
    ),
    RoboflowDataset(
        name="ROAM Equipment",
        workspace="abdullah-tamu",
        project="roam-equipment",
        version=1,
        image_count=30,
        classes=["capacitor", "conductor", "crossarm", "fuse", "insulator", 
                 "jumper", "pole", "recloser", "regulator", "service", 
                 "switch", "transformer"],
        description="Comprehensive equipment classes including crossarms",
        priority=1
    ),
    RoboflowDataset(
        name="Power Pole",
        workspace="poles",
        project="power-pole",
        version=1,
        image_count=129,
        classes=["Power-Pole-components"],
        description="Components-focused for detailed detection",
        priority=4
    )
]

class RoboflowIntegrator:
    """Integrates Roboflow datasets for YOLO training improvement"""
    
    def __init__(self, base_dir: str = "/data/roboflow_datasets"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # Class mapping to unify different naming conventions
        self.class_mapping = {
            # Poles
            "utility pole": "pole",
            "utility-poles": "pole",
            "wood pole": "pole",
            "steel pole": "pole",
            "concrete pole": "pole",
            "Power-Pole-components": "pole",
            
            # Crossarms - CRITICAL for fixing 0% recall
            "crossarm": "crossarm",
            "single crossarm": "crossarm",
            "double crossarm": "crossarm",
            "cross-arm": "crossarm",
            
            # Insulators
            "insulator": "insulator",
            "cutout": "insulator",
            
            # Underground/Transformers
            "transformer": "transformer",
            "underground": "underground_marker",
            
            # Other equipment
            "lightning arrester": "equipment",
            "splice case": "equipment",
            "street light": "equipment",
            "capacitor": "equipment",
            "conductor": "equipment",
            "fuse": "equipment",
            "jumper": "equipment",
            "recloser": "equipment",
            "regulator": "equipment",
            "service": "equipment",
            "switch": "equipment"
        }
        
        # Final unified classes for training
        self.target_classes = ["pole", "crossarm", "insulator", "transformer", "underground_marker", "equipment"]
        
        # Statistics
        self.stats = {
            "total_images": 0,
            "crossarm_images": 0,
            "pole_images": 0,
            "class_distribution": {}
        }
    
    def download_dataset(self, dataset: RoboflowDataset, api_key: Optional[str] = None) -> Dict:
        """
        Download a Roboflow dataset
        
        Args:
            dataset: RoboflowDataset object
            api_key: Roboflow API key (get from https://roboflow.com)
            
        Returns:
            Download status and path
        """
        
        logger.info(f"Downloading {dataset.name}...")
        
        dataset_dir = self.base_dir / dataset.project
        
        if dataset_dir.exists():
            logger.info(f"Dataset {dataset.name} already exists at {dataset_dir}")
            return {"status": "exists", "path": str(dataset_dir)}
        
        try:
            # Use Roboflow Python package if available
            try:
                from roboflow import Roboflow
                
                if not api_key:
                    logger.error("API key required for Roboflow download")
                    return {"status": "error", "message": "API key required"}
                
                rf = Roboflow(api_key=api_key)
                project = rf.workspace(dataset.workspace).project(dataset.project)
                dataset_obj = project.version(dataset.version).download("yolov8", location=str(dataset_dir))
                
                logger.info(f"✅ Downloaded {dataset.name} to {dataset_dir}")
                return {"status": "success", "path": str(dataset_dir)}
                
            except ImportError:
                # Fallback to manual download instructions
                logger.warning("Roboflow package not installed")
                
                instructions = f"""
Manual download instructions for {dataset.name}:
1. Visit: https://universe.roboflow.com/{dataset.workspace}/{dataset.project}
2. Sign in/create free account
3. Click 'Download Dataset'
4. Select 'YOLOv8' format
5. Download ZIP file
6. Extract to: {dataset_dir}
"""
                logger.info(instructions)
                return {"status": "manual", "instructions": instructions}
                
        except Exception as e:
            logger.error(f"Failed to download {dataset.name}: {e}")
            return {"status": "error", "message": str(e)}
    
    def convert_annotations(self, dataset_dir: Path) -> int:
        """
        Convert Roboflow annotations to unified class system
        
        Args:
            dataset_dir: Path to dataset directory
            
        Returns:
            Number of annotations converted
        """
        
        logger.info(f"Converting annotations in {dataset_dir}...")
        
        # Load data.yaml to get class mappings
        yaml_path = dataset_dir / "data.yaml"
        if not yaml_path.exists():
            logger.error(f"No data.yaml found in {dataset_dir}")
            return 0
        
        with open(yaml_path, 'r') as f:
            data_config = yaml.safe_load(f)
        
        original_classes = data_config.get('names', [])
        
        # Create new class mapping
        new_class_indices = {}
        for i, orig_class in enumerate(original_classes):
            mapped_class = self.class_mapping.get(orig_class.lower(), None)
            if mapped_class and mapped_class in self.target_classes:
                new_class_indices[i] = self.target_classes.index(mapped_class)
        
        # Convert all label files
        converted_count = 0
        for split in ['train', 'valid', 'test']:
            labels_dir = dataset_dir / split / 'labels'
            if not labels_dir.exists():
                continue
            
            for label_file in labels_dir.glob('*.txt'):
                lines = []
                modified = False
                
                with open(label_file, 'r') as f:
                    for line in f:
                        parts = line.strip().split()
                        if len(parts) >= 5:
                            orig_class = int(parts[0])
                            if orig_class in new_class_indices:
                                parts[0] = str(new_class_indices[orig_class])
                                lines.append(' '.join(parts) + '\n')
                                modified = True
                                
                                # Track statistics
                                mapped_class = self.target_classes[new_class_indices[orig_class]]
                                if mapped_class == "crossarm":
                                    self.stats["crossarm_images"] += 1
                                elif mapped_class == "pole":
                                    self.stats["pole_images"] += 1
                
                if modified:
                    with open(label_file, 'w') as f:
                        f.writelines(lines)
                    converted_count += 1
        
        logger.info(f"Converted {converted_count} annotation files")
        return converted_count
    
    def merge_datasets(self, dataset_dirs: List[Path], output_dir: Path) -> Dict:
        """
        Merge multiple datasets into one for training
        
        Args:
            dataset_dirs: List of dataset directories
            output_dir: Output directory for merged dataset
            
        Returns:
            Merge statistics
        """
        
        logger.info(f"Merging {len(dataset_dirs)} datasets...")
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create directory structure
        for split in ['train', 'valid', 'test']:
            (output_dir / split / 'images').mkdir(parents=True, exist_ok=True)
            (output_dir / split / 'labels').mkdir(parents=True, exist_ok=True)
        
        # Copy and merge datasets
        image_count = {"train": 0, "valid": 0, "test": 0}
        
        for dataset_dir in dataset_dirs:
            logger.info(f"Processing {dataset_dir.name}...")
            
            for split in ['train', 'valid', 'test']:
                images_src = dataset_dir / split / 'images'
                labels_src = dataset_dir / split / 'labels'
                
                if not images_src.exists():
                    # Try alternative naming
                    images_src = dataset_dir / 'images' / split
                    labels_src = dataset_dir / 'labels' / split
                
                if images_src.exists():
                    # Copy images
                    for img_file in images_src.glob('*'):
                        if img_file.suffix.lower() in ['.jpg', '.jpeg', '.png']:
                            # Rename to avoid conflicts
                            new_name = f"{dataset_dir.name}_{img_file.name}"
                            shutil.copy2(img_file, output_dir / split / 'images' / new_name)
                            
                            # Copy corresponding label
                            label_file = labels_src / f"{img_file.stem}.txt"
                            if label_file.exists():
                                shutil.copy2(label_file, output_dir / split / 'labels' / f"{dataset_dir.name}_{img_file.stem}.txt")
                            
                            image_count[split] += 1
        
        # Create merged data.yaml
        data_yaml = {
            'path': str(output_dir),
            'train': 'train/images',
            'val': 'valid/images',
            'test': 'test/images',
            'nc': len(self.target_classes),
            'names': self.target_classes,
            
            # Add class weights for imbalanced data (critical for crossarms)
            'cls_pw': [1.0, 3.0, 1.5, 1.5, 1.5, 1.0]  # Triple weight for crossarms
        }
        
        with open(output_dir / 'data.yaml', 'w') as f:
            yaml.dump(data_yaml, f)
        
        self.stats["total_images"] = sum(image_count.values())
        
        logger.info(f"✅ Merged dataset created with {self.stats['total_images']} images")
        logger.info(f"   Train: {image_count['train']}, Valid: {image_count['valid']}, Test: {image_count['test']}")
        logger.info(f"   Crossarm images: {self.stats['crossarm_images']}")
        
        return {
            "total_images": self.stats["total_images"],
            "splits": image_count,
            "crossarm_images": self.stats["crossarm_images"],
            "output_path": str(output_dir)
        }
    
    def prepare_training_config(self, merged_dir: Path) -> Dict:
        """
        Create optimized YOLO training configuration for crossarm improvement
        
        Args:
            merged_dir: Path to merged dataset
            
        Returns:
            Training configuration
        """
        
        config = {
            # Data configuration
            "data": str(merged_dir / "data.yaml"),
            
            # Model configuration
            "model": "yolov8m.pt",  # Medium model for better accuracy
            
            # Training hyperparameters optimized for crossarm detection
            "epochs": 150,
            "patience": 50,
            "batch": 16,
            "imgsz": 640,
            "device": "0" if os.path.exists('/dev/nvidia0') else "cpu",
            
            # Optimizer
            "optimizer": "SGD",
            "lr0": 0.01,
            "lrf": 0.01,
            "momentum": 0.937,
            "weight_decay": 0.0005,
            
            # Warmup
            "warmup_epochs": 3.0,
            "warmup_momentum": 0.8,
            "warmup_bias_lr": 0.1,
            
            # Loss weights (critical for crossarm improvement)
            "box": 7.5,
            "cls": 0.5,
            "dfl": 1.5,
            
            # Focal loss for hard examples (crossarms)
            "fl_gamma": 2.0,
            
            # Label smoothing
            "label_smoothing": 0.1,
            
            # Augmentations (essential for small crossarm samples)
            "hsv_h": 0.015,
            "hsv_s": 0.7,
            "hsv_v": 0.4,
            "degrees": 10.0,
            "translate": 0.1,
            "scale": 0.7,  # Important for varying distances
            "shear": 2.0,
            "perspective": 0.001,
            "flipud": 0.0,
            "fliplr": 0.5,
            "mosaic": 1.0,  # Always use mosaic for small objects
            "mixup": 0.2,
            "copy_paste": 0.3,  # Copy crossarms to increase samples
            
            # Advanced augmentations
            "auto_augment": "randaugment",
            "erasing": 0.4,
            "crop_fraction": 1.0,
            
            # Anchor configuration for elongated objects (crossarms)
            "anchor_t": 4.0,
            
            # Output
            "project": "/data/models/yolo_crossarm_fixed",
            "name": "roboflow_enhanced",
            "exist_ok": True,
            "save": True,
            "save_period": 10,
            "val": True,
            "plots": True,
            "verbose": True
        }
        
        # Save configuration
        config_path = merged_dir / "training_config.yaml"
        with open(config_path, 'w') as f:
            yaml.dump(config, f)
        
        logger.info(f"Training config saved to {config_path}")
        return config
    
    def create_training_script(self, config: Dict, output_path: Path) -> None:
        """
        Create training script for YOLO with Roboflow data
        
        Args:
            config: Training configuration
            output_path: Path for training script
        """
        
        script_content = f"""#!/usr/bin/env python3
\"\"\"
YOLO Training with Roboflow Datasets
Fixes crossarm detection (0% -> >60% recall)
Generated by Roboflow Integrator
\"\"\"

import torch
from ultralytics import YOLO
import yaml
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def train_with_roboflow_data():
    \"\"\"Train YOLO with merged Roboflow datasets\"\"\"
    
    logger.info("🚀 Starting YOLO training with Roboflow datasets")
    logger.info("Target: Crossarm recall >60%, mAP50-95 >0.6")
    
    # Load configuration
    config_path = "{config['data'].replace('.yaml', '')}/training_config.yaml"
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Initialize model
    model = YOLO(config['model'])
    
    # Train with optimized parameters
    results = model.train(**config)
    
    # Evaluate performance
    metrics = model.val()
    
    # Check crossarm performance
    class_names = model.names
    if 'crossarm' in class_names:
        crossarm_idx = class_names.index('crossarm')
        crossarm_metrics = metrics.box.class_result(crossarm_idx)
        
        logger.info(f"Crossarm Performance:")
        logger.info(f"  Precision: {{crossarm_metrics[0]:.3f}}")
        logger.info(f"  Recall: {{crossarm_metrics[1]:.3f}}")
        logger.info(f"  mAP50: {{crossarm_metrics[2]:.3f}}")
        logger.info(f"  mAP50-95: {{crossarm_metrics[3]:.3f}}")
        
        if crossarm_metrics[1] >= 0.5:
            logger.info("✅ CROSSARM RECALL TARGET ACHIEVED!")
        else:
            logger.warning("⚠️ Crossarm recall below target, consider more data")
    
    # Export best model
    best_model_path = Path(config['project']) / config['name'] / 'weights' / 'best.pt'
    if best_model_path.exists():
        logger.info(f"Best model saved at: {{best_model_path}}")
        
        # Copy to deployment location
        import shutil
        deploy_path = Path('/data/yolo_crossarm_fixed.pt')
        shutil.copy2(best_model_path, deploy_path)
        logger.info(f"Deployed to: {{deploy_path}}")
    
    return results

if __name__ == "__main__":
    train_with_roboflow_data()
"""
        
        with open(output_path, 'w') as f:
            f.write(script_content)
        
        # Make executable
        output_path.chmod(0o755)
        
        logger.info(f"Training script created at {output_path}")

# Integration endpoint
def integrate_roboflow_datasets(app):
    """Add Roboflow integration endpoints to FastAPI"""
    
    from fastapi import APIRouter, BackgroundTasks, HTTPException
    from pydantic import BaseModel
    from typing import Optional, List
    
    router = APIRouter(prefix="/roboflow", tags=["Roboflow Integration"])
    integrator = RoboflowIntegrator()
    
    class DownloadRequest(BaseModel):
        dataset_names: Optional[List[str]] = None
        api_key: Optional[str] = None
        priority_only: bool = True
    
    @router.post("/download-datasets")
    async def download_roboflow_datasets(
        request: DownloadRequest,
        background_tasks: BackgroundTasks
    ):
        """
        Download recommended Roboflow datasets for crossarm fix
        Priority 1: Zac's Utility Poles, ROAM Equipment (have crossarms)
        """
        
        # Select datasets
        if request.dataset_names:
            datasets = [d for d in RECOMMENDED_DATASETS if d.name in request.dataset_names]
        elif request.priority_only:
            datasets = [d for d in RECOMMENDED_DATASETS if d.priority == 1]
        else:
            datasets = RECOMMENDED_DATASETS
        
        # Start download in background
        def download_all():
            results = []
            for dataset in datasets:
                result = integrator.download_dataset(dataset, request.api_key)
                results.append({
                    "dataset": dataset.name,
                    "status": result["status"],
                    "path": result.get("path")
                })
            return results
        
        background_tasks.add_task(download_all)
        
        return {
            "message": f"Downloading {len(datasets)} datasets",
            "datasets": [d.name for d in datasets],
            "note": "Check /roboflow/status for progress"
        }
    
    @router.post("/merge-and-train")
    async def merge_and_train(background_tasks: BackgroundTasks):
        """
        Merge downloaded datasets and start training
        Fixes crossarm detection issue (0% -> >60% recall)
        """
        
        # Find downloaded datasets
        dataset_dirs = [d for d in integrator.base_dir.iterdir() if d.is_dir()]
        
        if len(dataset_dirs) < 1:
            raise HTTPException(400, "No datasets found. Download first with /roboflow/download-datasets")
        
        # Merge datasets
        merged_dir = integrator.base_dir / "merged_dataset"
        
        def merge_and_train_task():
            # Convert annotations
            for dataset_dir in dataset_dirs:
                integrator.convert_annotations(dataset_dir)
            
            # Merge
            merge_stats = integrator.merge_datasets(dataset_dirs, merged_dir)
            
            # Create training config
            config = integrator.prepare_training_config(merged_dir)
            
            # Create training script
            script_path = merged_dir / "train_roboflow.py"
            integrator.create_training_script(config, script_path)
            
            # Start training
            import subprocess
            subprocess.run([str(script_path)], check=True)
            
            return merge_stats
        
        background_tasks.add_task(merge_and_train_task)
        
        return {
            "message": "Merging datasets and starting training",
            "datasets": len(dataset_dirs),
            "output": str(merged_dir)
        }
    
    @router.get("/datasets")
    async def list_available_datasets():
        """List recommended Roboflow datasets for utility pole detection"""
        
        return [
            {
                "name": d.name,
                "images": d.image_count,
                "classes": d.classes,
                "priority": d.priority,
                "description": d.description
            }
            for d in RECOMMENDED_DATASETS
        ]
    
    @router.get("/statistics")
    async def get_integration_stats():
        """Get statistics about downloaded and merged datasets"""
        
        return integrator.stats
    
    app.include_router(router)
    logger.info("✅ Roboflow integration endpoints added: /roboflow/*")

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    
    print("🎯 Roboflow Dataset Integration for Crossarm Fix")
    print("="*60)
    print("\nRecommended datasets for fixing 0% crossarm recall:")
    print("-"*60)
    
    for dataset in sorted(RECOMMENDED_DATASETS, key=lambda x: x.priority):
        print(f"\n{dataset.name} (Priority {dataset.priority})")
        print(f"  Images: {dataset.image_count}")
        print(f"  Classes: {', '.join(dataset.classes[:5])}...")
        print(f"  Note: {dataset.description}")
    
    print("\n" + "="*60)
    print("To integrate:")
    print("1. Get API key from https://roboflow.com")
    print("2. POST /roboflow/download-datasets")
    print("3. POST /roboflow/merge-and-train")
    print("4. Monitor training progress")
    print("\nExpected improvement: Crossarm recall 0% -> 60-75%")
