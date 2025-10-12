#!/usr/bin/env python3
"""
Real-time Monitoring Dashboard for ML Document Analyzer
Tracks performance metrics and provides scaling insights
"""

import os
import time
import asyncio
import psutil
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import deque
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import numpy as np

logger = logging.getLogger(__name__)

class PerformanceMonitor:
    """
    Tracks and analyzes performance metrics for ML workloads
    """
    
    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        
        # Metrics tracking with sliding windows
        self.metrics_history = {
            "cpu_percent": deque(maxlen=window_size),
            "memory_percent": deque(maxlen=window_size),
            "inference_times": deque(maxlen=window_size),
            "request_counts": deque(maxlen=window_size),
            "cache_hits": deque(maxlen=window_size),
            "error_counts": deque(maxlen=window_size),
            "batch_sizes": deque(maxlen=window_size),
            "queue_lengths": deque(maxlen=window_size)
        }
        
        # Aggregated metrics
        self.hourly_stats = []
        self.daily_stats = []
        
        # Alert thresholds
        self.thresholds = {
            "cpu_critical": 80,
            "cpu_warning": 60,
            "memory_critical": 85,
            "memory_warning": 70,
            "inference_slow": 5.0,  # seconds
            "error_rate_high": 0.05,  # 5%
            "queue_backlog": 100
        }
        
        # Active alerts
        self.active_alerts = []
        
        # Start time
        self.start_time = time.time()
    
    def record_metric(self, metric_type: str, value: float):
        """Record a metric value"""
        if metric_type in self.metrics_history:
            self.metrics_history[metric_type].append({
                "value": value,
                "timestamp": time.time()
            })
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current system metrics"""
        
        # System metrics
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Process-specific metrics
        process = psutil.Process()
        process_memory = process.memory_info().rss / 1024 / 1024  # MB
        process_cpu = process.cpu_percent(interval=0.1)
        
        # Network metrics
        net = psutil.net_io_counters()
        
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "uptime_hours": (time.time() - self.start_time) / 3600,
            "system": {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available_gb": memory.available / (1024**3),
                "disk_percent": disk.percent,
                "disk_free_gb": disk.free / (1024**3)
            },
            "process": {
                "cpu_percent": process_cpu,
                "memory_mb": process_memory,
                "thread_count": process.num_threads(),
                "open_files": len(process.open_files())
            },
            "network": {
                "bytes_sent_mb": net.bytes_sent / (1024**2),
                "bytes_recv_mb": net.bytes_recv / (1024**2),
                "packets_dropped": net.dropin + net.dropout
            }
        }
        
        # Record metrics
        self.record_metric("cpu_percent", cpu_percent)
        self.record_metric("memory_percent", memory.percent)
        
        return metrics
    
    def calculate_statistics(self) -> Dict[str, Any]:
        """Calculate statistics from metric history"""
        
        stats = {}
        
        for metric_name, history in self.metrics_history.items():
            if history:
                values = [item["value"] for item in history]
                stats[metric_name] = {
                    "current": values[-1] if values else 0,
                    "average": np.mean(values),
                    "min": np.min(values),
                    "max": np.max(values),
                    "std": np.std(values),
                    "p50": np.percentile(values, 50),
                    "p95": np.percentile(values, 95),
                    "p99": np.percentile(values, 99)
                }
        
        return stats
    
    def check_alerts(self) -> List[Dict[str, Any]]:
        """Check for alert conditions"""
        
        new_alerts = []
        metrics = self.get_current_metrics()
        
        # CPU alerts
        cpu = metrics["system"]["cpu_percent"]
        if cpu > self.thresholds["cpu_critical"]:
            new_alerts.append({
                "level": "critical",
                "type": "cpu",
                "message": f"CPU usage critical: {cpu:.1f}%",
                "value": cpu,
                "threshold": self.thresholds["cpu_critical"],
                "recommendation": "Scale up immediately or add instances"
            })
        elif cpu > self.thresholds["cpu_warning"]:
            new_alerts.append({
                "level": "warning",
                "type": "cpu",
                "message": f"CPU usage high: {cpu:.1f}%",
                "value": cpu,
                "threshold": self.thresholds["cpu_warning"],
                "recommendation": "Monitor closely, prepare to scale"
            })
        
        # Memory alerts
        mem = metrics["system"]["memory_percent"]
        if mem > self.thresholds["memory_critical"]:
            new_alerts.append({
                "level": "critical",
                "type": "memory",
                "message": f"Memory usage critical: {mem:.1f}%",
                "value": mem,
                "threshold": self.thresholds["memory_critical"],
                "recommendation": "Upgrade instance or optimize memory usage"
            })
        elif mem > self.thresholds["memory_warning"]:
            new_alerts.append({
                "level": "warning",
                "type": "memory",
                "message": f"Memory usage high: {mem:.1f}%",
                "value": mem,
                "threshold": self.thresholds["memory_warning"],
                "recommendation": "Clear caches, consider upgrading"
            })
        
        # Inference time alerts
        if self.metrics_history["inference_times"]:
            recent_times = [item["value"] for item in list(self.metrics_history["inference_times"])[-10:]]
            avg_time = np.mean(recent_times)
            if avg_time > self.thresholds["inference_slow"]:
                new_alerts.append({
                    "level": "warning",
                    "type": "performance",
                    "message": f"Slow inference: {avg_time:.1f}s average",
                    "value": avg_time,
                    "threshold": self.thresholds["inference_slow"],
                    "recommendation": "Reduce batch size or add GPU"
                })
        
        # Update active alerts
        self.active_alerts = new_alerts
        
        return new_alerts
    
    def get_scaling_recommendation(self) -> Dict[str, Any]:
        """Generate scaling recommendations based on metrics"""
        
        stats = self.calculate_statistics()
        metrics = self.get_current_metrics()
        alerts = self.check_alerts()
        
        recommendation = {
            "timestamp": datetime.now().isoformat(),
            "current_state": {
                "cpu": metrics["system"]["cpu_percent"],
                "memory": metrics["system"]["memory_percent"],
                "alerts": len(alerts)
            },
            "recommendation": "maintain",
            "confidence": 0.0,
            "reasons": [],
            "actions": []
        }
        
        # Analyze trends
        if "cpu_percent" in stats:
            cpu_stats = stats["cpu_percent"]
            
            # Scale up conditions
            if cpu_stats["p95"] > 70:
                recommendation["recommendation"] = "scale_up"
                recommendation["confidence"] = 0.9
                recommendation["reasons"].append(f"95th percentile CPU at {cpu_stats['p95']:.1f}%")
                recommendation["actions"].append("Increase instance size or add workers")
            
            # Scale down conditions
            elif cpu_stats["p95"] < 30 and stats.get("memory_percent", {}).get("p95", 100) < 50:
                recommendation["recommendation"] = "scale_down"
                recommendation["confidence"] = 0.7
                recommendation["reasons"].append("Low resource utilization")
                recommendation["actions"].append("Consider smaller instance or fewer workers")
        
        # Check for critical alerts
        critical_alerts = [a for a in alerts if a["level"] == "critical"]
        if critical_alerts:
            recommendation["recommendation"] = "scale_up"
            recommendation["confidence"] = 1.0
            recommendation["reasons"].append(f"{len(critical_alerts)} critical alerts")
            recommendation["actions"].extend([a["recommendation"] for a in critical_alerts])
        
        return recommendation

class MetricsAggregator:
    """
    Aggregates metrics for reporting
    """
    
    def __init__(self, monitor: PerformanceMonitor):
        self.monitor = monitor
        self.last_hour_aggregate = None
        self.last_day_aggregate = None
    
    def aggregate_hourly(self) -> Dict[str, Any]:
        """Aggregate metrics for the last hour"""
        
        stats = self.monitor.calculate_statistics()
        
        aggregate = {
            "period": "hourly",
            "timestamp": datetime.now().isoformat(),
            "metrics": stats,
            "alerts_count": len(self.monitor.active_alerts),
            "recommendation": self.monitor.get_scaling_recommendation()
        }
        
        self.last_hour_aggregate = aggregate
        return aggregate
    
    def aggregate_daily(self) -> Dict[str, Any]:
        """Aggregate metrics for the last day"""
        
        stats = self.monitor.calculate_statistics()
        
        aggregate = {
            "period": "daily",
            "timestamp": datetime.now().isoformat(),
            "metrics": stats,
            "peak_cpu": max([m["value"] for m in self.monitor.metrics_history["cpu_percent"]], default=0),
            "peak_memory": max([m["value"] for m in self.monitor.metrics_history["memory_percent"]], default=0),
            "total_requests": sum([m["value"] for m in self.monitor.metrics_history["request_counts"]], default=0),
            "error_rate": self._calculate_error_rate(),
            "cache_hit_rate": self._calculate_cache_hit_rate()
        }
        
        self.last_day_aggregate = aggregate
        return aggregate
    
    def _calculate_error_rate(self) -> float:
        """Calculate error rate"""
        
        total_requests = sum([m["value"] for m in self.monitor.metrics_history["request_counts"]], default=1)
        total_errors = sum([m["value"] for m in self.monitor.metrics_history["error_counts"]], default=0)
        
        return (total_errors / max(total_requests, 1)) * 100
    
    def _calculate_cache_hit_rate(self) -> float:
        """Calculate cache hit rate"""
        
        cache_hits = self.monitor.metrics_history["cache_hits"]
        if not cache_hits:
            return 0.0
        
        hits = sum([m["value"] for m in cache_hits])
        total = len(cache_hits)
        
        return (hits / max(total, 1)) * 100

# FastAPI Integration
def create_monitoring_router() -> APIRouter:
    """Create monitoring dashboard router"""
    
    router = APIRouter(prefix="/monitoring", tags=["Monitoring"])
    monitor = PerformanceMonitor()
    aggregator = MetricsAggregator(monitor)
    
    @router.get("/metrics")
    async def get_metrics():
        """Get current performance metrics"""
        return monitor.get_current_metrics()
    
    @router.get("/statistics")
    async def get_statistics():
        """Get aggregated statistics"""
        return monitor.calculate_statistics()
    
    @router.get("/alerts")
    async def get_alerts():
        """Get active alerts"""
        alerts = monitor.check_alerts()
        return {
            "active_alerts": alerts,
            "count": len(alerts),
            "critical_count": len([a for a in alerts if a["level"] == "critical"]),
            "warning_count": len([a for a in alerts if a["level"] == "warning"])
        }
    
    @router.get("/scaling-recommendation")
    async def get_scaling_recommendation():
        """Get scaling recommendations"""
        return monitor.get_scaling_recommendation()
    
    @router.get("/aggregates/hourly")
    async def get_hourly_aggregate():
        """Get hourly aggregated metrics"""
        return aggregator.aggregate_hourly()
    
    @router.get("/aggregates/daily")
    async def get_daily_aggregate():
        """Get daily aggregated metrics"""
        return aggregator.aggregate_daily()
    
    @router.post("/record-inference")
    async def record_inference(duration: float, batch_size: int = 1):
        """Record an inference operation"""
        monitor.record_metric("inference_times", duration)
        monitor.record_metric("batch_sizes", batch_size)
        monitor.record_metric("request_counts", 1)
        return {"recorded": True}
    
    @router.websocket("/live")
    async def websocket_metrics(websocket: WebSocket):
        """WebSocket endpoint for live metrics"""
        
        await websocket.accept()
        
        try:
            while True:
                # Send metrics every second
                metrics = monitor.get_current_metrics()
                alerts = monitor.active_alerts
                
                await websocket.send_json({
                    "metrics": metrics,
                    "alerts": alerts,
                    "timestamp": time.time()
                })
                
                await asyncio.sleep(1)
                
        except WebSocketDisconnect:
            logger.info("WebSocket client disconnected")
    
    @router.get("/dashboard")
    async def dashboard():
        """Simple HTML dashboard"""
        
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>ML Analyzer Monitoring</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
                .metric { 
                    background: white; 
                    padding: 15px; 
                    margin: 10px; 
                    border-radius: 5px; 
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    display: inline-block;
                    min-width: 200px;
                }
                .metric-label { color: #666; font-size: 12px; }
                .metric-value { font-size: 24px; font-weight: bold; color: #333; }
                .alert { 
                    padding: 10px; 
                    margin: 10px 0; 
                    border-radius: 5px; 
                }
                .alert-warning { background: #fff3cd; border: 1px solid #ffc107; }
                .alert-critical { background: #f8d7da; border: 1px solid #dc3545; }
                h1 { color: #333; }
                .chart { background: white; padding: 20px; margin: 20px 0; border-radius: 5px; }
            </style>
        </head>
        <body>
            <h1>🔍 ML Document Analyzer - Monitoring Dashboard</h1>
            
            <div id="alerts"></div>
            
            <div id="metrics">
                <div class="metric">
                    <div class="metric-label">CPU Usage</div>
                    <div class="metric-value" id="cpu">--%</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Memory Usage</div>
                    <div class="metric-value" id="memory">--%</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Uptime</div>
                    <div class="metric-value" id="uptime">--h</div>
                </div>
            </div>
            
            <div class="chart">
                <h3>Real-time Metrics</h3>
                <canvas id="chart" width="800" height="200"></canvas>
            </div>
            
            <script>
                const ws = new WebSocket('ws://localhost:8001/monitoring/live');
                const cpuData = [];
                const memoryData = [];
                const maxDataPoints = 60;
                
                ws.onmessage = function(event) {
                    const data = JSON.parse(event.data);
                    
                    // Update metrics
                    document.getElementById('cpu').textContent = 
                        data.metrics.system.cpu_percent.toFixed(1) + '%';
                    document.getElementById('memory').textContent = 
                        data.metrics.system.memory_percent.toFixed(1) + '%';
                    document.getElementById('uptime').textContent = 
                        data.metrics.uptime_hours.toFixed(1) + 'h';
                    
                    // Update alerts
                    const alertsDiv = document.getElementById('alerts');
                    alertsDiv.innerHTML = '';
                    data.alerts.forEach(alert => {
                        const div = document.createElement('div');
                        div.className = 'alert alert-' + alert.level;
                        div.textContent = alert.message + ' - ' + alert.recommendation;
                        alertsDiv.appendChild(div);
                    });
                    
                    // Update chart data
                    cpuData.push(data.metrics.system.cpu_percent);
                    memoryData.push(data.metrics.system.memory_percent);
                    
                    if (cpuData.length > maxDataPoints) {
                        cpuData.shift();
                        memoryData.shift();
                    }
                    
                    drawChart();
                };
                
                function drawChart() {
                    const canvas = document.getElementById('chart');
                    const ctx = canvas.getContext('2d');
                    const width = canvas.width;
                    const height = canvas.height;
                    
                    ctx.clearRect(0, 0, width, height);
                    
                    // Draw CPU line (blue)
                    ctx.strokeStyle = '#007bff';
                    ctx.beginPath();
                    cpuData.forEach((value, index) => {
                        const x = (index / maxDataPoints) * width;
                        const y = height - (value / 100) * height;
                        if (index === 0) ctx.moveTo(x, y);
                        else ctx.lineTo(x, y);
                    });
                    ctx.stroke();
                    
                    // Draw Memory line (green)
                    ctx.strokeStyle = '#28a745';
                    ctx.beginPath();
                    memoryData.forEach((value, index) => {
                        const x = (index / maxDataPoints) * width;
                        const y = height - (value / 100) * height;
                        if (index === 0) ctx.moveTo(x, y);
                        else ctx.lineTo(x, y);
                    });
                    ctx.stroke();
                }
            </script>
        </body>
        </html>
        """
        
        return HTMLResponse(content=html)
    
    return router

if __name__ == "__main__":
    # Test monitoring
    monitor = PerformanceMonitor()
    
    # Simulate some metrics
    for i in range(10):
        monitor.record_metric("cpu_percent", 50 + i * 3)
        monitor.record_metric("memory_percent", 60 + i * 2)
        monitor.record_metric("inference_times", 1.5 + i * 0.1)
        monitor.record_metric("request_counts", 10 + i)
        monitor.record_metric("cache_hits", 8 + i)
    
    # Get statistics
    stats = monitor.calculate_statistics()
    print("Statistics:")
    for metric, values in stats.items():
        print(f"  {metric}:")
        for stat, value in values.items():
            print(f"    {stat}: {value:.2f}")
    
    # Check alerts
    alerts = monitor.check_alerts()
    print(f"\nAlerts ({len(alerts)}):")
    for alert in alerts:
        print(f"  [{alert['level']}] {alert['message']}")
        print(f"    Recommendation: {alert['recommendation']}")
    
    # Get scaling recommendation
    rec = monitor.get_scaling_recommendation()
    print(f"\nScaling Recommendation: {rec['recommendation']}")
    print(f"Confidence: {rec['confidence']:.1%}")
    for reason in rec['reasons']:
        print(f"  - {reason}")
