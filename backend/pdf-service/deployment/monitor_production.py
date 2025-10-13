#!/usr/bin/env python3
"""Production monitoring for infrastructure detection"""

import requests
import json
import time
from datetime import datetime

API_URL = "https://nexa-infrastructure-detector.onrender.com"

def check_health():
    """Check API health"""
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        if response.status_code == 200:
            return True, response.json()
        return False, None
    except Exception as e:
        return False, str(e)

def monitor_metrics():
    """Monitor key metrics"""
    metrics = {
        "timestamp": datetime.now().isoformat(),
        "health": False,
        "response_time": 0,
        "model_loaded": False
    }
    
    # Check health
    start = time.time()
    health_ok, health_data = check_health()
    metrics["response_time"] = time.time() - start
    metrics["health"] = health_ok
    
    if health_ok and health_data:
        metrics["model_loaded"] = health_data.get("models_loaded", False)
    
    # Check model info
    try:
        response = requests.get(f"{API_URL}/api/model-info", timeout=5)
        if response.status_code == 200:
            model_info = response.json()
            metrics["classes"] = model_info.get("yolo_model", {}).get("classes", [])
            metrics["spec_rules"] = model_info.get("spec_book", {}).get("rules_indexed", 0)
    except:
        pass
    
    return metrics

def alert_if_needed(metrics):
    """Send alerts if issues detected"""
    alerts = []
    
    if not metrics["health"]:
        alerts.append("🚨 API is down!")
    
    if metrics["response_time"] > 2.0:
        alerts.append(f"⚠️ Slow response: {metrics['response_time']:.2f}s")
    
    if not metrics["model_loaded"]:
        alerts.append("❌ Model not loaded")
    
    if alerts:
        print(f"\n[{metrics['timestamp']}] ALERTS:")
        for alert in alerts:
            print(f"  {alert}")
    else:
        print(f"[{metrics['timestamp']}] ✅ All systems operational")

def main():
    """Main monitoring loop"""
    print("🔍 Starting infrastructure detection monitoring...")
    print(f"   API: {API_URL}")
    print("-" * 60)
    
    while True:
        metrics = monitor_metrics()
        alert_if_needed(metrics)
        time.sleep(30)  # Check every 30 seconds

if __name__ == "__main__":
    main()
