#!/usr/bin/env python3
"""
Health monitoring script for NEXA Document Analyzer
Tracks system status, error rates, and performance metrics
"""
import requests
import time
import json
from datetime import datetime
from typing import Dict, Any
import sys

# Configuration
BASE_URL = "https://nexa-doc-analyzer-oct2025.onrender.com"
CHECK_INTERVAL = 30  # seconds
ERROR_THRESHOLD = 5  # consecutive failures before alert

def check_endpoint(endpoint: str, timeout: int = 10) -> Dict[str, Any]:
    """Check a single endpoint and return status"""
    url = f"{BASE_URL}{endpoint}"
    try:
        start = time.time()
        response = requests.get(url, timeout=timeout)
        elapsed = (time.time() - start) * 1000  # ms
        
        return {
            "url": url,
            "status_code": response.status_code,
            "response_time_ms": round(elapsed, 2),
            "success": response.status_code == 200,
            "data": response.json() if response.headers.get('content-type', '').startswith('application/json') else None
        }
    except requests.exceptions.Timeout:
        return {
            "url": url,
            "error": "Timeout",
            "success": False
        }
    except Exception as e:
        return {
            "url": url,
            "error": str(e),
            "success": False
        }

def monitor_health():
    """Main monitoring loop"""
    print("🔍 NEXA Document Analyzer - Health Monitor")
    print("=" * 50)
    print(f"Target: {BASE_URL}")
    print(f"Check interval: {CHECK_INTERVAL} seconds")
    print("=" * 50)
    print()
    
    consecutive_failures = 0
    check_count = 0
    
    endpoints = [
        "/health",
        "/status",
        "/"
    ]
    
    while True:
        check_count += 1
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n[{timestamp}] Check #{check_count}")
        print("-" * 40)
        
        all_success = True
        
        for endpoint in endpoints:
            result = check_endpoint(endpoint)
            
            if result["success"]:
                print(f"✅ {endpoint:15} - {result['response_time_ms']}ms")
                
                # Special handling for /status endpoint
                if endpoint == "/status" and result.get("data"):
                    data = result["data"]
                    spec_info = data.get("spec_book", {})
                    if spec_info.get("ready"):
                        print(f"   📚 Spec book: {spec_info['chunks_loaded']} chunks loaded")
                    else:
                        print(f"   ⚠️  Spec book: Not loaded")
                    
                    print(f"   🔧 CPU threads: {data.get('cpu_threads', 'N/A')}")
                    
            else:
                all_success = False
                error_msg = result.get("error", f"HTTP {result.get('status_code', 'Unknown')}")
                print(f"❌ {endpoint:15} - {error_msg}")
        
        # Track consecutive failures
        if all_success:
            if consecutive_failures > 0:
                print(f"\n✅ Service recovered after {consecutive_failures} failure(s)")
            consecutive_failures = 0
        else:
            consecutive_failures += 1
            
            if consecutive_failures >= ERROR_THRESHOLD:
                print(f"\n🚨 ALERT: Service has failed {consecutive_failures} consecutive checks!")
                print("   Consider checking:")
                print("   - Render.com dashboard for deployment status")
                print("   - Application logs for errors")
                print("   - Network connectivity")
        
        # Performance summary
        if check_count % 10 == 0:
            print(f"\n📊 Summary after {check_count} checks:")
            print(f"   Consecutive failures: {consecutive_failures}")
            print(f"   Status: {'🟢 Healthy' if consecutive_failures == 0 else '🔴 Issues detected'}")
        
        # Wait for next check
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    try:
        monitor_health()
    except KeyboardInterrupt:
        print("\n\n👋 Monitoring stopped")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Monitor error: {e}")
        sys.exit(1)
