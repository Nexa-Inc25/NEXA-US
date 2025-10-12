#!/usr/bin/env python3
"""
Monitor Crossarm Detection Performance
Track improvements in recall and precision for crossarm class
"""

import os
import torch
from ultralytics import YOLO
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from datetime import datetime
import json

class CrossarmPerformanceMonitor:
    """Monitor and visualize crossarm detection improvements"""
    
    def __init__(self, model_paths: list, test_images_dir: str = "datasets/test_crossarms"):
        """
        Initialize monitor
        
        Args:
            model_paths: List of model paths to compare (e.g., before/after)
            test_images_dir: Directory with test images
        """
        self.model_paths = model_paths
        self.test_images_dir = Path(test_images_dir)
        self.results = {}
        
    def evaluate_model(self, model_path: str, name: str):
        """
        Evaluate a model's performance on crossarm detection
        
        Args:
            model_path: Path to YOLO model
            name: Name for this model (e.g., "baseline", "enhanced")
        """
        print(f"\n📊 Evaluating {name}: {model_path}")
        print("-" * 50)
        
        model = YOLO(model_path)
        
        # Get test images
        test_images = list(self.test_images_dir.glob("*.jpg")) + \
                     list(self.test_images_dir.glob("*.png"))
        
        if not test_images:
            print(f"⚠️ No test images found in {self.test_images_dir}")
            return None
        
        # Run inference
        detections = {
            'crossarm': [],
            'pole': [],
            'other': []
        }
        
        confidence_scores = []
        
        for img_path in test_images:
            results = model(img_path, verbose=False)
            
            for r in results:
                if r.boxes is not None:
                    for box in r.boxes:
                        cls_id = int(box.cls)
                        conf = float(box.conf)
                        cls_name = model.names[cls_id]
                        
                        # Track crossarm detections specifically
                        if 'crossarm' in cls_name.lower():
                            detections['crossarm'].append({
                                'image': img_path.name,
                                'confidence': conf,
                                'bbox': box.xyxy[0].tolist()
                            })
                            confidence_scores.append(conf)
                        elif 'pole' in cls_name.lower():
                            detections['pole'].append({
                                'image': img_path.name,
                                'confidence': conf
                            })
                        else:
                            detections['other'].append({
                                'class': cls_name,
                                'confidence': conf
                            })
        
        # Calculate metrics
        metrics = {
            'model_name': name,
            'model_path': model_path,
            'total_images': len(test_images),
            'crossarm_detections': len(detections['crossarm']),
            'pole_detections': len(detections['pole']),
            'other_detections': len(detections['other']),
            'avg_crossarm_confidence': np.mean(confidence_scores) if confidence_scores else 0,
            'min_crossarm_confidence': np.min(confidence_scores) if confidence_scores else 0,
            'max_crossarm_confidence': np.max(confidence_scores) if confidence_scores else 0,
            'detection_rate': len(detections['crossarm']) / len(test_images) if test_images else 0
        }
        
        self.results[name] = {
            'metrics': metrics,
            'detections': detections,
            'confidence_scores': confidence_scores
        }
        
        # Print metrics
        print(f"✅ Crossarm Detections: {metrics['crossarm_detections']}")
        print(f"📈 Detection Rate: {metrics['detection_rate']*100:.1f}%")
        print(f"🎯 Avg Confidence: {metrics['avg_crossarm_confidence']:.3f}")
        print(f"📊 Confidence Range: [{metrics['min_crossarm_confidence']:.3f}, {metrics['max_crossarm_confidence']:.3f}]")
        
        return metrics
    
    def compare_models(self):
        """Compare performance across models"""
        
        print("\n" + "="*60)
        print("🔍 MODEL COMPARISON - CROSSARM DETECTION")
        print("="*60)
        
        # Evaluate each model
        for i, model_path in enumerate(self.model_paths):
            name = f"Model_{i+1}" if i > 0 else "Baseline"
            if os.path.exists(model_path):
                self.evaluate_model(model_path, name)
            else:
                print(f"⚠️ Model not found: {model_path}")
        
        # Create comparison table
        if self.results:
            df = pd.DataFrame([r['metrics'] for r in self.results.values()])
            
            print("\n📊 Performance Comparison Table:")
            print(df[['model_name', 'crossarm_detections', 'detection_rate', 
                     'avg_crossarm_confidence']].to_string(index=False))
            
            # Calculate improvement
            if len(self.results) >= 2:
                baseline = list(self.results.values())[0]['metrics']
                enhanced = list(self.results.values())[-1]['metrics']
                
                detection_improvement = (
                    (enhanced['crossarm_detections'] - baseline['crossarm_detections']) / 
                    max(baseline['crossarm_detections'], 1) * 100
                )
                
                confidence_improvement = (
                    (enhanced['avg_crossarm_confidence'] - baseline['avg_crossarm_confidence']) / 
                    max(baseline['avg_crossarm_confidence'], 0.01) * 100
                )
                
                print("\n📈 IMPROVEMENTS:")
                print(f"  Detection Count: {detection_improvement:+.1f}%")
                print(f"  Confidence Score: {confidence_improvement:+.1f}%")
                
                if detection_improvement > 50:
                    print("  ✅ SIGNIFICANT IMPROVEMENT in crossarm detection!")
                elif detection_improvement > 0:
                    print("  ✅ Positive improvement in crossarm detection")
                else:
                    print("  ⚠️ No improvement - needs more training data")
    
    def visualize_improvements(self):
        """Create visualization of improvements"""
        
        if len(self.results) < 2:
            print("Need at least 2 models to visualize improvements")
            return
        
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        fig.suptitle('Crossarm Detection Performance Analysis', fontsize=16)
        
        # 1. Detection counts comparison
        models = list(self.results.keys())
        detections = [self.results[m]['metrics']['crossarm_detections'] for m in models]
        
        axes[0, 0].bar(models, detections, color=['red', 'green'])
        axes[0, 0].set_title('Crossarm Detection Count')
        axes[0, 0].set_ylabel('Number of Detections')
        
        # 2. Confidence distribution
        for name, result in self.results.items():
            if result['confidence_scores']:
                axes[0, 1].hist(result['confidence_scores'], alpha=0.5, label=name, bins=20)
        axes[0, 1].set_title('Confidence Score Distribution')
        axes[0, 1].set_xlabel('Confidence')
        axes[0, 1].set_ylabel('Frequency')
        axes[0, 1].legend()
        
        # 3. Detection rate
        rates = [self.results[m]['metrics']['detection_rate']*100 for m in models]
        axes[1, 0].plot(models, rates, 'o-', markersize=10, linewidth=2)
        axes[1, 0].set_title('Detection Rate Progress')
        axes[1, 0].set_ylabel('Detection Rate (%)')
        axes[1, 0].axhline(y=50, color='r', linestyle='--', label='Target (50%)')
        axes[1, 0].legend()
        
        # 4. Performance summary
        summary_text = "Performance Summary:\n\n"
        for name, result in self.results.items():
            m = result['metrics']
            summary_text += f"{name}:\n"
            summary_text += f"  • Detections: {m['crossarm_detections']}\n"
            summary_text += f"  • Rate: {m['detection_rate']*100:.1f}%\n"
            summary_text += f"  • Avg Conf: {m['avg_crossarm_confidence']:.3f}\n\n"
        
        axes[1, 1].text(0.1, 0.5, summary_text, fontsize=10, verticalalignment='center')
        axes[1, 1].set_title('Summary Statistics')
        axes[1, 1].axis('off')
        
        plt.tight_layout()
        output_path = 'crossarm_performance_analysis.png'
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"\n📊 Visualization saved to {output_path}")
        
        return fig
    
    def generate_report(self):
        """Generate detailed performance report"""
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'test_directory': str(self.test_images_dir),
            'models_evaluated': len(self.results),
            'results': self.results
        }
        
        # Save JSON report
        report_path = f'crossarm_performance_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"\n📄 Detailed report saved to {report_path}")
        
        # Generate recommendations
        print("\n💡 RECOMMENDATIONS:")
        
        if self.results:
            latest = list(self.results.values())[-1]['metrics']
            
            if latest['detection_rate'] < 0.5:
                print("  1. Add more crossarm training images (need 200-500 more)")
                print("  2. Focus on images with:")
                print("     • Crossarms at various angles")
                print("     • Different lighting conditions")
                print("     • Partial occlusions")
            
            if latest['avg_crossarm_confidence'] < 0.7:
                print("  3. Increase training epochs (try 300)")
                print("  4. Use larger model (YOLOv8l or YOLOv8x)")
                print("  5. Fine-tune anchor boxes for crossarm aspect ratio")
            
            if latest['crossarm_detections'] == 0:
                print("  ⚠️ CRITICAL: Zero detections - check class index mapping")
                print("  ⚠️ Verify crossarm class is index 1 in data.yaml")
                print("  ⚠️ Ensure training data has crossarm annotations")

def main():
    """Main monitoring pipeline"""
    
    print("🔍 CROSSARM DETECTION PERFORMANCE MONITOR")
    print("="*50)
    
    # Models to compare
    model_paths = [
        "backend/pdf-service/yolo_pole_trained.pt",  # Original (zero recall)
        "yolo_crossarm_enhanced.pt"  # New enhanced model
    ]
    
    # Initialize monitor
    monitor = CrossarmPerformanceMonitor(
        model_paths=model_paths,
        test_images_dir="datasets/test_crossarms"
    )
    
    # Run comparison
    monitor.compare_models()
    
    # Visualize improvements
    monitor.visualize_improvements()
    
    # Generate report
    monitor.generate_report()
    
    print("\n✅ Monitoring complete!")

if __name__ == "__main__":
    main()
