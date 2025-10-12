#!/usr/bin/env python3
"""
Training Data Generator for NEXA Models
Creates synthetic and augmented training data for NER, embeddings, and YOLO
"""

import json
import random
import re
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

class TrainingDataGenerator:
    """Generates training data for model fine-tuning"""
    
    def __init__(self, output_dir: str = "/data/training"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Domain-specific templates
        self.spec_templates = [
            "Minimum clearance shall be {clearance} {unit} per {standard}",
            "Poles must be installed with {clearance} {unit} vertical clearance",
            "{equipment} requires {clearance} {unit} separation from {location}",
            "Install {equipment} at height of {clearance} {unit} above {location}",
            "Maintain {clearance} {unit} horizontal clearance for {equipment}",
            "{standard} requires {clearance} {unit} for {equipment} installations",
            "Underground {equipment} depth: minimum {clearance} {unit}",
            "Exemption {exemption_num} allows reduction to {clearance} {unit}",
            "Per {standard}, {equipment} spacing is {clearance} {unit}",
            "Emergency repairs may use {clearance} {unit} temporary clearance"
        ]
        
        self.equipment_types = [
            "pole", "crossarm", "guy wire", "anchor", "transformer",
            "conductor", "neutral", "ground wire", "insulator", "switch",
            "capacitor", "recloser", "fuse", "lightning arrester",
            "underground cable", "conduit", "vault", "pad-mount equipment"
        ]
        
        self.locations = [
            "ground level", "roadway", "sidewalk", "building", "fence",
            "water crossing", "railway", "parking area", "residential area",
            "commercial zone", "industrial facility", "agricultural land"
        ]
        
        self.standards = [
            "G.O. 95", "G.O. 128", "Rule 37", "Rule 38.2", "Section 4.1",
            "CPUC Rule 20", "IEEE C2", "NESC", "PG&E Greenbook Section 3.2"
        ]
        
        self.exemptions = [
            "A-12", "B-7", "C-3.4", "D-9", "E-15.2", "F-4", "G-8.1"
        ]
    
    def generate_ner_examples(self, num_examples: int = 500) -> List[Dict]:
        """
        Generate NER training examples with labeled entities
        
        Returns:
            List of examples with text and BIO tags
        """
        
        examples = []
        
        for i in range(num_examples):
            # Generate random spec text
            template = random.choice(self.spec_templates)
            
            # Fill in values
            clearance = random.choice([6, 8, 10, 12, 15, 18, 20, 25, 30])
            unit = random.choice(["feet", "ft", "inches", "in", "meters", "m"])
            equipment = random.choice(self.equipment_types)
            location = random.choice(self.locations)
            standard = random.choice(self.standards)
            exemption = random.choice(self.exemptions)
            
            text = template.format(
                clearance=clearance,
                unit=unit,
                equipment=equipment,
                location=location,
                standard=standard,
                exemption_num=exemption
            )
            
            # Generate BIO tags
            tokens = text.split()
            labels = []
            
            for j, token in enumerate(tokens):
                # Label standards
                if token in self.standards or token.startswith("G.O.") or token.startswith("Rule"):
                    if j > 0 and labels[j-1].startswith("I-STANDARD"):
                        labels.append("I-STANDARD")
                    else:
                        labels.append("B-STANDARD")
                
                # Label measurements
                elif token.isdigit() or re.match(r'\d+\.?\d*', token):
                    labels.append("B-MEASURE")
                elif token in ["feet", "ft", "inches", "in", "meters", "m", "'"]:
                    labels.append("I-MEASURE")
                
                # Label equipment
                elif token.lower() in self.equipment_types:
                    labels.append("B-EQUIPMENT")
                
                # Label locations
                elif token.lower() in ["ground", "roadway", "sidewalk", "building"]:
                    labels.append("B-LOCATION")
                elif j > 0 and labels[j-1] == "B-LOCATION" and token in ["level", "area", "zone"]:
                    labels.append("I-LOCATION")
                
                # Label exemptions
                elif "Exemption" in token or token in self.exemptions:
                    labels.append("B-EXEMPTION")
                elif j > 0 and labels[j-1] == "B-EXEMPTION":
                    labels.append("I-EXEMPTION")
                
                # Default: not an entity
                else:
                    labels.append("O")
            
            examples.append({
                "text": text,
                "tokens": tokens,
                "labels": labels,
                "id": f"synthetic_{i}"
            })
        
        # Add some complex examples
        complex_examples = [
            {
                "text": "Per G.O. 95 Rule 37, distribution poles require 18 feet minimum clearance above ground level with Exemption A-12 allowing 15 feet in constrained areas",
                "tokens": ["Per", "G.O.", "95", "Rule", "37,", "distribution", "poles", "require", "18", "feet", "minimum", "clearance", "above", "ground", "level", "with", "Exemption", "A-12", "allowing", "15", "feet", "in", "constrained", "areas"],
                "labels": ["O", "B-STANDARD", "I-STANDARD", "I-STANDARD", "I-STANDARD", "O", "B-EQUIPMENT", "O", "B-MEASURE", "I-MEASURE", "O", "O", "O", "B-LOCATION", "I-LOCATION", "O", "B-EXEMPTION", "I-EXEMPTION", "O", "B-MEASURE", "I-MEASURE", "O", "O", "O"]
            },
            {
                "text": "Install crossarms at 25 ft height per CPUC requirements with 12 inches horizontal offset from pole centerline",
                "tokens": ["Install", "crossarms", "at", "25", "ft", "height", "per", "CPUC", "requirements", "with", "12", "inches", "horizontal", "offset", "from", "pole", "centerline"],
                "labels": ["O", "B-EQUIPMENT", "O", "B-MEASURE", "I-MEASURE", "O", "O", "B-STANDARD", "O", "O", "B-MEASURE", "I-MEASURE", "O", "O", "O", "B-EQUIPMENT", "O"]
            }
        ]
        
        examples.extend(complex_examples)
        
        logger.info(f"Generated {len(examples)} NER training examples")
        return examples
    
    def generate_embedding_pairs(self, num_pairs: int = 300) -> List[Dict]:
        """
        Generate similarity pairs for embedding fine-tuning
        
        Returns:
            List of (text1, text2, similarity) pairs
        """
        
        pairs = []
        
        # Generate similar pairs (high similarity)
        for i in range(num_pairs // 3):
            base = f"Install {random.choice(self.equipment_types)} with"
            clearance = random.choice([12, 15, 18, 20, 25])
            
            text1 = f"{base} {clearance} feet clearance per G.O. 95"
            text2 = f"{base} {clearance} ft spacing according to G.O. 95"
            
            pairs.append({
                "text1": text1,
                "text2": text2,
                "similarity": 0.9 + random.uniform(0, 0.1)  # 0.9-1.0
            })
        
        # Generate somewhat similar pairs (medium similarity)
        for i in range(num_pairs // 3):
            equip1 = random.choice(self.equipment_types)
            equip2 = random.choice(self.equipment_types)
            clearance1 = random.choice([12, 15, 18, 20, 25])
            clearance2 = clearance1 + random.choice([-3, -2, 2, 3])
            
            text1 = f"Install {equip1} at {clearance1} feet height"
            text2 = f"Mount {equip2} at {clearance2} feet elevation"
            
            pairs.append({
                "text1": text1,
                "text2": text2,
                "similarity": 0.5 + random.uniform(0, 0.3)  # 0.5-0.8
            })
        
        # Generate dissimilar pairs (low similarity)
        for i in range(num_pairs // 3):
            text1 = f"{random.choice(self.equipment_types)} requires {random.choice([6, 8, 10])} feet underground"
            text2 = f"{random.choice(self.equipment_types)} needs {random.choice([30, 35, 40])} feet overhead clearance"
            
            pairs.append({
                "text1": text1,
                "text2": text2,
                "similarity": random.uniform(0, 0.3)  # 0.0-0.3
            })
        
        # Add some exact technical spec pairs
        technical_pairs = [
            {
                "text1": "G.O. 95 Rule 37 requires 18 feet vertical clearance",
                "text2": "General Order 95 Rule 37 mandates 18 ft vertical spacing",
                "similarity": 0.95
            },
            {
                "text1": "Crossarm offset shall not exceed 12 inches",
                "text2": "Maximum crossarm displacement is 12 in",
                "similarity": 0.92
            },
            {
                "text1": "Underground conduit depth minimum 36 inches",
                "text2": "Overhead conductor height minimum 25 feet",
                "similarity": 0.15
            }
        ]
        
        pairs.extend(technical_pairs)
        
        logger.info(f"Generated {len(pairs)} embedding training pairs")
        return pairs
    
    def generate_yolo_augmentation_config(self) -> Dict:
        """
        Generate YOLO augmentation configuration for crossarm improvement
        
        Returns:
            Augmentation config dict
        """
        
        config = {
            "augmentation": {
                # Geometric transforms
                "rotation": {
                    "degrees": 15,
                    "probability": 0.5
                },
                "shear": {
                    "x": 0.1,
                    "y": 0.1,
                    "probability": 0.3
                },
                "scale": {
                    "min": 0.5,
                    "max": 1.5,
                    "probability": 0.7  # Important for varying distances
                },
                "translate": {
                    "x": 0.2,
                    "y": 0.2,
                    "probability": 0.5
                },
                "flip": {
                    "horizontal": 0.5,
                    "vertical": 0.0  # Don't flip poles upside down
                },
                
                # Color transforms
                "hsv": {
                    "hue": 0.015,
                    "saturation": 0.7,
                    "value": 0.4,
                    "probability": 0.5
                },
                "brightness": {
                    "min": 0.7,
                    "max": 1.3,
                    "probability": 0.5
                },
                "contrast": {
                    "min": 0.7,
                    "max": 1.3,
                    "probability": 0.3
                },
                
                # Advanced augmentations
                "mosaic": {
                    "probability": 1.0  # Always use for small objects
                },
                "mixup": {
                    "probability": 0.2,
                    "alpha": 0.2
                },
                "copy_paste": {
                    "probability": 0.3,  # Copy crossarms to increase samples
                    "max_objects": 3
                },
                "blur": {
                    "probability": 0.1,
                    "kernel_size": 3
                },
                "noise": {
                    "probability": 0.1,
                    "variance": 10
                }
            },
            
            # Class weights for imbalanced dataset
            "class_weights": {
                "pole": 1.0,
                "crossarm": 3.0,  # Triple weight for rare class
                "underground_marker": 1.5
            },
            
            # Training hyperparameters
            "hyperparameters": {
                "focal_loss_gamma": 2.0,  # Focus on hard examples
                "anchor_threshold": 4.0,  # Better for elongated objects
                "obj_loss_weight": 1.0,
                "cls_loss_weight": 0.5,
                "box_loss_weight": 7.5,
                "label_smoothing": 0.1,
                "warmup_epochs": 3,
                "patience": 30  # Extended patience
            }
        }
        
        logger.info("Generated YOLO augmentation config for crossarm improvement")
        return config
    
    def save_training_data(self):
        """Save all generated training data to disk"""
        
        # Generate NER examples
        ner_examples = self.generate_ner_examples(500)
        ner_path = self.output_dir / "ner_examples.json"
        with open(ner_path, 'w') as f:
            json.dump(ner_examples, f, indent=2)
        logger.info(f"Saved {len(ner_examples)} NER examples to {ner_path}")
        
        # Generate embedding pairs
        embedding_pairs = self.generate_embedding_pairs(300)
        pairs_path = self.output_dir / "similarity_pairs.json"
        with open(pairs_path, 'w') as f:
            json.dump(embedding_pairs, f, indent=2)
        logger.info(f"Saved {len(embedding_pairs)} embedding pairs to {pairs_path}")
        
        # Generate YOLO config
        yolo_config = self.generate_yolo_augmentation_config()
        yolo_path = self.output_dir / "yolo_augmentation.json"
        with open(yolo_path, 'w') as f:
            json.dump(yolo_config, f, indent=2)
        logger.info(f"Saved YOLO augmentation config to {yolo_path}")
        
        # Create download script for additional data
        self._create_data_download_scripts()
        
        return {
            "ner_examples": len(ner_examples),
            "embedding_pairs": len(embedding_pairs),
            "yolo_config": "saved",
            "output_dir": str(self.output_dir)
        }
    
    def _create_data_download_scripts(self):
        """Create scripts to download additional training data"""
        
        # PowerShell script for downloading crossarm datasets
        ps_script = """
# Download additional crossarm training data
# Addresses zero recall issue for crossarm detection

Write-Host "Downloading utility pole datasets with crossarms..." -ForegroundColor Green

# Create dataset directory
$dataDir = "C:\\Users\\mikev\\CascadeProjects\\nexa-inc-mvp\\backend\\pdf-service\\data\\training\\yolo_dataset"
New-Item -ItemType Directory -Force -Path $dataDir

# 1. Roboflow Utility Poles Dataset (380 images)
Write-Host "Downloading Roboflow dataset..." -ForegroundColor Yellow
$roboflowUrl = "https://universe.roboflow.com/api/dataset/utility-poles-2ejhi/1/download/yolov8"
# Note: Requires API key - get from https://roboflow.com/

# 2. Dataset Ninja Electric Poles
Write-Host "Dataset Ninja Electric Poles - visit: https://datasetninja.com/electric-poles" -ForegroundColor Yellow

# 3. EPRI Transmission Dataset
Write-Host "EPRI dataset - contact EPRI for access" -ForegroundColor Yellow

# Alternative: Generate synthetic data
Write-Host "Generating synthetic crossarm annotations..." -ForegroundColor Green

# Create sample annotations for augmentation
$sampleAnnotation = @"
# YOLO format: class x_center y_center width height
1 0.5 0.3 0.4 0.05
1 0.5 0.35 0.35 0.04
1 0.5 0.4 0.45 0.06
"@

$sampleAnnotation | Out-File "$dataDir\\sample_crossarm.txt"

Write-Host "✅ Data preparation complete!" -ForegroundColor Green
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Download Roboflow dataset with API key"
Write-Host "2. Place images in $dataDir\\images"
Write-Host "3. Place labels in $dataDir\\labels"
Write-Host "4. Run fine-tuning: POST /fine-tune/start"
"""
        
        script_path = self.output_dir / "download_crossarm_data.ps1"
        with open(script_path, 'w') as f:
            f.write(ps_script)
        
        logger.info(f"Created data download script at {script_path}")

# Integration function
def prepare_training_data():
    """Prepare all training data for fine-tuning"""
    
    generator = TrainingDataGenerator()
    results = generator.save_training_data()
    
    print("\n✅ Training Data Generated!")
    print("="*50)
    print(f"NER Examples: {results['ner_examples']}")
    print(f"Embedding Pairs: {results['embedding_pairs']}")
    print(f"YOLO Config: {results['yolo_config']}")
    print(f"Output Directory: {results['output_dir']}")
    print("\nNext steps:")
    print("1. Run download_crossarm_data.ps1 for YOLO data")
    print("2. Start fine-tuning: POST /fine-tune/start")
    print("3. Monitor progress: GET /fine-tune/progress")
    
    return results

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    
    prepare_training_data()
