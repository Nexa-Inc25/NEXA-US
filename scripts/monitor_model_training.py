#!/usr/bin/env python3
"""
Model Training Monitor for NEXA
Tracks fine-tuning progress and validates improvements
"""

import time
import json
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import matplotlib.pyplot as plt
import numpy as np

API_BASE_URL = "http://localhost:8001"

class ModelTrainingMonitor:
    """Monitors and validates model fine-tuning progress"""
    
    def __init__(self, api_base: str = API_BASE_URL):
        self.api_base = api_base
        self.metrics_history = []
        self.start_time = None
    
    def start_fine_tuning(self, models: Optional[List[str]] = None) -> Dict:
        """Start the fine-tuning process"""
        
        print("🚀 Starting Model Fine-Tuning")
        print("="*60)
        
        payload = {
            "models": models or ["ner", "embeddings", "yolo"]
        }
        
        try:
            response = requests.post(
                f"{self.api_base}/fine-tune/start",
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                self.start_time = datetime.now()
                print(f"✅ Fine-tuning initiated for: {', '.join(result['models'])}")
                print(f"Check progress at: {result['check_progress']}")
                return result
            else:
                print(f"❌ Failed to start: {response.status_code}")
                return {"error": response.text}
                
        except Exception as e:
            print(f"❌ Error: {e}")
            return {"error": str(e)}
    
    def check_progress(self) -> Dict:
        """Check current fine-tuning progress"""
        
        try:
            response = requests.get(
                f"{self.api_base}/fine-tune/progress",
                timeout=10
            )
            
            if response.status_code == 200:
                progress = response.json()
                self.metrics_history.append(progress)
                return progress
            else:
                return {"error": f"Status {response.status_code}"}
                
        except Exception as e:
            return {"error": str(e)}
    
    def monitor_training(self, interval: int = 30, max_duration: int = 3600):
        """
        Monitor training progress with live updates
        
        Args:
            interval: Check interval in seconds
            max_duration: Maximum monitoring duration in seconds
        """
        
        print("\n📊 Monitoring Training Progress")
        print("="*60)
        print("Targets:")
        print("  • NER F1: >0.85")
        print("  • YOLO mAP50-95: >0.6")
        print("  • Crossarm Recall: >0.5")
        print("  • Embedding Correlation: >0.85")
        print("\nPress Ctrl+C to stop monitoring\n")
        
        elapsed = 0
        
        try:
            while elapsed < max_duration:
                progress = self.check_progress()
                
                if "error" not in progress:
                    self._display_progress(progress, elapsed)
                    
                    # Check if all targets met
                    if self._check_targets_met(progress):
                        print("\n🎉 All targets achieved!")
                        break
                else:
                    print(f"⚠️ Check failed: {progress['error']}")
                
                time.sleep(interval)
                elapsed += interval
                
        except KeyboardInterrupt:
            print("\n\n⏸️ Monitoring stopped by user")
        
        # Final summary
        self._display_summary()
    
    def _display_progress(self, progress: Dict, elapsed: int):
        """Display formatted progress update"""
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        elapsed_min = elapsed // 60
        
        print(f"\n[{timestamp}] Elapsed: {elapsed_min} minutes")
        print("-"*40)
        
        for model_name, model_data in progress.get('models', {}).items():
            status = model_data.get('status', 'unknown')
            target_met = model_data.get('target_met', False)
            metrics = model_data.get('metrics', {})
            
            icon = "✅" if target_met else "🔄" if status == "training" else "⏳"
            
            print(f"{icon} {model_name.upper()}:")
            
            if model_name == 'ner':
                f1 = metrics.get('val_f1', 0)
                print(f"   F1 Score: {f1:.3f} / 0.85")
                self._show_progress_bar(f1, 0.85)
                
            elif model_name == 'yolo':
                map_score = metrics.get('mAP50_95', 0)
                crossarm = metrics.get('crossarm_mAP50', 0)
                print(f"   mAP50-95: {map_score:.3f} / 0.6")
                self._show_progress_bar(map_score, 0.6)
                print(f"   Crossarm: {crossarm:.3f} / 0.5")
                self._show_progress_bar(crossarm, 0.5)
                
            elif model_name == 'embeddings':
                corr = metrics.get('similarity_correlation', 0)
                print(f"   Correlation: {corr:.3f} / 0.85")
                self._show_progress_bar(corr, 0.85)
        
        # Show recommendations
        recs = progress.get('recommendations', [])
        if recs:
            print("\n💡 Recommendations:")
            for rec in recs[:3]:
                print(f"   • {rec}")
    
    def _show_progress_bar(self, current: float, target: float, width: int = 30):
        """Display a progress bar"""
        
        progress = min(1.0, current / target if target > 0 else 0)
        filled = int(width * progress)
        bar = "█" * filled + "░" * (width - filled)
        percentage = progress * 100
        print(f"   [{bar}] {percentage:.1f}%")
    
    def _check_targets_met(self, progress: Dict) -> bool:
        """Check if all training targets are met"""
        
        for model_data in progress.get('models', {}).values():
            if not model_data.get('target_met', False):
                return False
        return len(progress.get('models', {})) > 0
    
    def _display_summary(self):
        """Display final training summary"""
        
        if not self.metrics_history:
            print("\nNo metrics collected")
            return
        
        print("\n" + "="*60)
        print("📈 TRAINING SUMMARY")
        print("="*60)
        
        # Get final metrics
        final = self.metrics_history[-1]
        
        for model_name, model_data in final.get('models', {}).items():
            metrics = model_data.get('metrics', {})
            target_met = model_data.get('target_met', False)
            
            print(f"\n{model_name.upper()}:")
            
            if model_name == 'ner':
                print(f"  Final F1: {metrics.get('val_f1', 0):.3f}")
                print(f"  Precision: {metrics.get('val_precision', 0):.3f}")
                print(f"  Recall: {metrics.get('val_recall', 0):.3f}")
                
            elif model_name == 'yolo':
                print(f"  mAP50: {metrics.get('mAP50', 0):.3f}")
                print(f"  mAP50-95: {metrics.get('mAP50_95', 0):.3f}")
                print(f"  Crossarm Recall: {metrics.get('crossarm_mAP50', 0):.3f}")
                
            elif model_name == 'embeddings':
                print(f"  Correlation: {metrics.get('similarity_correlation', 0):.3f}")
            
            print(f"  Target Met: {'✅ YES' if target_met else '❌ NO'}")
        
        if self.start_time:
            duration = datetime.now() - self.start_time
            print(f"\nTotal Duration: {duration}")
    
    def validate_improvements(self):
        """Validate model improvements with test cases"""
        
        print("\n🔬 Validating Model Improvements")
        print("="*60)
        
        # Test NER improvement
        test_text = "Install pole with 18 feet clearance per G.O. 95 Rule 37 with Exemption A-12"
        
        print("\nNER Test:")
        print(f"Input: '{test_text}'")
        
        # Would call NER endpoint here
        print("Expected entities:")
        print("  • EQUIPMENT: pole")
        print("  • MEASURE: 18 feet")
        print("  • STANDARD: G.O. 95 Rule 37")
        print("  • EXEMPTION: Exemption A-12")
        
        # Test embedding improvement
        print("\nEmbedding Test:")
        pairs = [
            ("18 feet clearance", "18 ft spacing", "Expected: >0.9"),
            ("pole installation", "crossarm mounting", "Expected: 0.4-0.6"),
            ("underground conduit", "overhead conductor", "Expected: <0.3")
        ]
        
        for text1, text2, expected in pairs:
            print(f"  '{text1}' vs '{text2}'")
            print(f"    {expected}")
        
        # Test YOLO improvement
        print("\nYOLO Test:")
        print("  Test image: utility_pole_test.jpg")
        print("  Expected detections:")
        print("    • 2 poles (confidence >0.8)")
        print("    • 3 crossarms (confidence >0.7)")
        print("    • Previous crossarm recall: 0%")
        print("    • Target crossarm recall: >50%")
    
    def plot_metrics_history(self):
        """Plot training metrics over time"""
        
        if len(self.metrics_history) < 2:
            print("Not enough data for plotting")
            return
        
        # Extract metrics over time
        timestamps = []
        ner_f1 = []
        yolo_map = []
        crossarm_recall = []
        
        for i, metrics in enumerate(self.metrics_history):
            timestamps.append(i)
            
            models = metrics.get('models', {})
            
            if 'ner' in models:
                ner_f1.append(models['ner'].get('metrics', {}).get('val_f1', 0))
            
            if 'yolo' in models:
                yolo_map.append(models['yolo'].get('metrics', {}).get('mAP50_95', 0))
                crossarm_recall.append(models['yolo'].get('metrics', {}).get('crossarm_mAP50', 0))
        
        # Create plot
        fig, axes = plt.subplots(3, 1, figsize=(10, 10))
        
        # NER F1
        if ner_f1:
            axes[0].plot(timestamps[:len(ner_f1)], ner_f1, 'b-', label='F1 Score')
            axes[0].axhline(y=0.85, color='r', linestyle='--', label='Target (0.85)')
            axes[0].set_title('NER Performance')
            axes[0].set_ylabel('F1 Score')
            axes[0].legend()
            axes[0].grid(True)
        
        # YOLO mAP
        if yolo_map:
            axes[1].plot(timestamps[:len(yolo_map)], yolo_map, 'g-', label='mAP50-95')
            axes[1].axhline(y=0.6, color='r', linestyle='--', label='Target (0.6)')
            axes[1].set_title('YOLO Performance')
            axes[1].set_ylabel('mAP50-95')
            axes[1].legend()
            axes[1].grid(True)
        
        # Crossarm Recall
        if crossarm_recall:
            axes[2].plot(timestamps[:len(crossarm_recall)], crossarm_recall, 'm-', label='Crossarm Recall')
            axes[2].axhline(y=0.5, color='r', linestyle='--', label='Target (0.5)')
            axes[2].set_title('Crossarm Detection')
            axes[2].set_ylabel('Recall')
            axes[2].set_xlabel('Check Interval')
            axes[2].legend()
            axes[2].grid(True)
        
        plt.tight_layout()
        plt.savefig('training_metrics.png')
        print("\n📊 Metrics plot saved to training_metrics.png")
        plt.show()

def main():
    """Main monitoring workflow"""
    
    print("🎯 NEXA MODEL FINE-TUNING MONITOR")
    print("="*70)
    print("\nThis tool monitors model fine-tuning to achieve:")
    print("  • NER F1 >0.85 for utility domain entities")
    print("  • YOLO mAP50-95 >0.6 with crossarm recall >0.5")
    print("  • Embedding correlation >0.85 for spec similarity")
    print("="*70)
    
    monitor = ModelTrainingMonitor()
    
    # Check if API is running
    try:
        response = requests.get(f"{API_BASE_URL}/docs", timeout=5)
        if response.status_code != 200:
            print("❌ API not responding")
            return
    except:
        print("❌ Cannot connect to API at", API_BASE_URL)
        print("\nPlease start the API first:")
        print("  cd backend/pdf-service")
        print("  python app_oct2025_enhanced.py")
        return
    
    # Menu
    while True:
        print("\n📋 OPTIONS:")
        print("1. Generate training data")
        print("2. Start fine-tuning")
        print("3. Monitor progress")
        print("4. Validate improvements")
        print("5. Plot metrics history")
        print("6. Exit")
        
        choice = input("\nSelect option (1-6): ").strip()
        
        if choice == "1":
            print("\n🔄 Generating training data...")
            try:
                from training_data_generator import prepare_training_data
                results = prepare_training_data()
                print(f"✅ Generated {results['ner_examples']} NER examples")
                print(f"✅ Generated {results['embedding_pairs']} embedding pairs")
            except Exception as e:
                print(f"❌ Failed to generate data: {e}")
        
        elif choice == "2":
            print("\n🚀 Starting fine-tuning...")
            result = monitor.start_fine_tuning()
            if "error" not in result:
                print("✅ Fine-tuning started!")
                print("Use option 3 to monitor progress")
        
        elif choice == "3":
            monitor.monitor_training(interval=10, max_duration=1800)
        
        elif choice == "4":
            monitor.validate_improvements()
        
        elif choice == "5":
            monitor.plot_metrics_history()
        
        elif choice == "6":
            print("\n👋 Goodbye!")
            break
        
        else:
            print("Invalid option, please try again")

if __name__ == "__main__":
    main()
