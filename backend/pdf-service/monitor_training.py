#!/usr/bin/env python3
"""
Monitor YOLO training progress in real-time
"""

import os
import time
from pathlib import Path
import re
import yaml

def get_latest_training_run():
    """Find the latest training run directory"""
    runs_dir = Path("runs/production")
    if not runs_dir.exists():
        return None
    
    # Get all infrastructure training directories
    dirs = [d for d in runs_dir.iterdir() if d.is_dir() and 'infrastructure' in d.name]
    if not dirs:
        return None
    
    # Return the most recent one
    return max(dirs, key=lambda d: d.stat().st_mtime)

def parse_results_file(results_file):
    """Parse the results.csv file for metrics"""
    if not results_file.exists():
        return None
    
    metrics = {}
    with open(results_file, 'r') as f:
        lines = f.readlines()
        if len(lines) < 2:
            return None
        
        # Parse header
        header = lines[0].strip().split(',')
        header = [h.strip() for h in header]
        
        # Get latest epoch data
        latest_line = lines[-1].strip().split(',')
        latest_line = [v.strip() for v in latest_line]
        
        # Create metrics dict
        for i, h in enumerate(header):
            if i < len(latest_line):
                try:
                    metrics[h] = float(latest_line[i])
                except:
                    metrics[h] = latest_line[i]
    
    return metrics

def monitor_training():
    """Monitor training progress"""
    print("="*60)
    print("🔍 NEXA TRAINING MONITOR")
    print("="*60)
    
    # Find latest training run
    run_dir = get_latest_training_run()
    if not run_dir:
        print("❌ No training runs found")
        return
    
    print(f"📂 Monitoring: {run_dir.name}")
    print("   Press Ctrl+C to stop monitoring\n")
    
    results_file = run_dir / "results.csv"
    
    # Monitor loop
    last_epoch = -1
    while True:
        try:
            # Parse results
            metrics = parse_results_file(results_file)
            
            if metrics and 'epoch' in metrics:
                current_epoch = int(metrics.get('epoch', 0))
                
                if current_epoch > last_epoch:
                    last_epoch = current_epoch
                    
                    # Display key metrics
                    print(f"\n📊 Epoch {current_epoch}/100")
                    print("-" * 40)
                    
                    # Training losses
                    box_loss = metrics.get('train/box_loss', 0)
                    cls_loss = metrics.get('train/cls_loss', 0)
                    dfl_loss = metrics.get('train/dfl_loss', 0)
                    print(f"   Training Losses:")
                    print(f"      Box: {box_loss:.4f}")
                    print(f"      Cls: {cls_loss:.4f}")
                    print(f"      DFL: {dfl_loss:.4f}")
                    
                    # Validation metrics
                    map50 = metrics.get('metrics/mAP50(B)', 0)
                    map50_95 = metrics.get('metrics/mAP50-95(B)', 0)
                    precision = metrics.get('metrics/precision(B)', 0)
                    recall = metrics.get('metrics/recall(B)', 0)
                    
                    print(f"\n   Validation Metrics:")
                    print(f"      mAP@0.5: {map50:.3f}")
                    print(f"      mAP@0.5:0.95: {map50_95:.3f}")
                    print(f"      Precision: {precision:.3f}")
                    print(f"      Recall: {recall:.3f}")
                    
                    # Progress bar
                    progress = current_epoch / 100
                    bar_length = 40
                    filled = int(bar_length * progress)
                    bar = '█' * filled + '░' * (bar_length - filled)
                    print(f"\n   Progress: [{bar}] {progress*100:.1f}%")
                    
                    # Target status
                    if map50 >= 0.95:
                        print(f"\n   ✅ TARGET ACHIEVED! mAP@0.5 = {map50:.3f} ≥ 0.95")
                    else:
                        print(f"\n   📈 Target: mAP@0.5 ≥ 0.95 (current: {map50:.3f})")
                    
                    # Estimated time
                    if current_epoch > 0:
                        # Read training time from log if available
                        remaining = 100 - current_epoch
                        print(f"\n   ⏱️ Epochs remaining: {remaining}")
            
            time.sleep(5)  # Check every 5 seconds
            
        except KeyboardInterrupt:
            print("\n\n✋ Monitoring stopped")
            break
        except Exception as e:
            # Silently continue on errors
            time.sleep(5)
            continue

def get_final_results():
    """Get final training results"""
    run_dir = get_latest_training_run()
    if not run_dir:
        return None
    
    results_file = run_dir / "results.csv"
    metrics = parse_results_file(results_file)
    
    if metrics:
        print("\n" + "="*60)
        print("📊 FINAL TRAINING RESULTS")
        print("="*60)
        
        epoch = int(metrics.get('epoch', 0))
        map50 = metrics.get('metrics/mAP50(B)', 0)
        map50_95 = metrics.get('metrics/mAP50-95(B)', 0)
        precision = metrics.get('metrics/precision(B)', 0)
        recall = metrics.get('metrics/recall(B)', 0)
        
        print(f"\n   Epochs Completed: {epoch}")
        print(f"   mAP@0.5: {map50:.3f}")
        print(f"   mAP@0.5:0.95: {map50_95:.3f}")
        print(f"   Precision: {precision:.3f}")
        print(f"   Recall: {recall:.3f}")
        
        if map50 >= 0.95:
            print(f"\n   🏆 SUCCESS! Target mAP@0.5 ≥ 0.95 achieved!")
        else:
            print(f"\n   ⚠️ Target not met. Consider more epochs or data.")
        
        # Model location
        best_model = run_dir / "weights" / "best.pt"
        if best_model.exists():
            print(f"\n   📦 Best model: {best_model}")
            print(f"   💾 Size: {best_model.stat().st_size / 1024 / 1024:.1f} MB")

if __name__ == "__main__":
    import sys
    
    if '--final' in sys.argv:
        get_final_results()
    else:
        monitor_training()
