# 📈 ML Document Analyzer - Production Scaling Guide

## Overview
Complete scaling configuration for handling production ML workloads on Render.com, optimized for NER/embedding inference with cost-effective scaling from $7/mo to enterprise.

## 🚀 Quick Start Deployment

### 1. Deploy with Scaling Configuration
```bash
# Use the scaling-optimized configuration
cp render-scaling.yaml render.yaml
git add -A
git commit -m "Deploy with ML scaling configuration"
git push origin main
```

### 2. Initial Configuration
- **Start**: Starter plan ($7/mo) for testing
- **Production**: Standard plan ($25/mo) for real workloads
- **Heavy ML**: Pro plan ($85/mo) for large PDFs/concurrent users

## 📊 Scaling Tiers & Recommendations

### Tier 1: Development/Testing ($7-15/mo)
```yaml
plan: starter  # 0.5 CPU, 512MB RAM
scaling:
  minInstances: 1
  maxInstances: 1
```
**Handles**: 
- 1-5 concurrent users
- PDFs up to 50 pages
- <100 requests/day

### Tier 2: Small Production ($25-50/mo)
```yaml
plan: standard  # 1 CPU, 1GB RAM
scaling:
  minInstances: 1
  maxInstances: 3
```
**Handles**:
- 5-20 concurrent users
- PDFs up to 200 pages
- 100-1000 requests/day

### Tier 3: Standard Production ($85-250/mo)
```yaml
plan: pro  # 2 CPU, 4GB RAM
scaling:
  minInstances: 2
  maxInstances: 10
  targetCPUPercent: 60
```
**Handles**:
- 20-100 concurrent users
- PDFs up to 1000 pages
- 1000-10,000 requests/day

### Tier 4: Enterprise ($500+/mo)
```yaml
plan: pro-plus  # 4 CPU, 8GB RAM
scaling:
  minInstances: 5
  maxInstances: 50
  targetCPUPercent: 50
```
**Handles**:
- 100+ concurrent users
- Any PDF size
- 10,000+ requests/day

## 🎯 ML-Specific Optimizations

### 1. Batch Processing Configuration
```python
# In ml_optimizer.py
BATCH_SIZE = 32  # Optimal for CPU inference
MAX_WORKERS = 4  # Thread pool size
CACHE_SIZE = 1000  # LRU cache for embeddings
```

### 2. Memory Management
```python
# Triggers at 3.5GB usage
if memory_usage > 3500:
    clear_caches()
    gc.collect()
```

### 3. Request Batching
```python
# Queue requests for batch processing
async def queue_for_batch(text):
    # Waits up to 100ms to fill batch
    # Processes when batch_size reached
    return await process_batch()
```

## 📈 Monitoring & Metrics

### Key Metrics to Watch
| Metric | Healthy | Warning | Critical | Action |
|--------|---------|---------|----------|--------|
| CPU % | <60% | 60-80% | >80% | Scale up/out |
| Memory % | <70% | 70-85% | >85% | Upgrade instance |
| Inference Time | <2s | 2-5s | >5s | Add workers/GPU |
| Cache Hit Rate | >60% | 40-60% | <40% | Increase cache |
| Queue Size | <50 | 50-100 | >100 | Add instances |

### Dashboard Monitoring
```bash
# Check metrics endpoint
curl https://your-app.onrender.com/ml/metrics

# Response:
{
  "total_requests": 1523,
  "cache_hit_rate": "67.3%",
  "avg_inference_time": 1.8,
  "cpu_percent": 55,
  "memory_percent": 62
}
```

### Scaling Recommendations API
```bash
curl https://your-app.onrender.com/ml/scaling-recommendations

# Response:
{
  "scale_up": false,
  "scale_down": false,
  "recommendations": [
    "Cache hit rate good",
    "Consider adding instance if load increases"
  ]
}
```

## ⚡ Performance Optimizations

### 1. Cold Start Reduction
```dockerfile
# Pre-download models in Docker
RUN python -c "from sentence_transformers import SentenceTransformer; \
    SentenceTransformer('all-MiniLM-L6-v2')"
```

### 2. Gunicorn Workers
```dockerfile
CMD ["gunicorn", "app:app", \
     "--workers", "4", \
     "--threads", "2", \
     "--worker-class", "uvicorn.workers.UvicornWorker"]
```

### 3. Connection Pooling
```yaml
# For concurrent requests
--worker-connections 1000
--max-requests 1000
--max-requests-jitter 50
```

## 🔄 Auto-Scaling Configuration

### CPU-Based Scaling (ML Workloads)
```yaml
scaling:
  targetCPUPercent: 60  # Lower threshold for ML
  minInstances: 1
  maxInstances: 10
```

### Memory-Based Scaling (Embeddings)
```yaml
scaling:
  targetMemoryPercent: 70
  minInstances: 2
  maxInstances: 20
```

### Time-Based Scaling (Business Hours)
```yaml
# Via Render Workflows
workflows:
  - name: business-hours
    schedule: "0 8 * * 1-5"  # 8 AM weekdays
    action: scale-up
    instances: 5
    
  - name: after-hours
    schedule: "0 18 * * 1-5"  # 6 PM weekdays
    action: scale-down
    instances: 1
```

## 💰 Cost Optimization

### 1. Scale to Zero (Dev/Test)
```yaml
scaling:
  minInstances: 0  # Only for non-production
```

### 2. Spot Instances (Coming Soon)
```yaml
# When available on Render
spotInstances: true
spotMaxPrice: 0.05  # $/hour
```

### 3. Reserved Instances
- Commit to 1-year for 20% discount
- Best for baseline capacity

## 🚨 Alerts & Monitoring

### Configure Alerts
```yaml
notifications:
  - type: email
    events:
      - highCPU          # >80% for 5 min
      - highMemory       # >85% for 5 min
      - outOfMemory      # OOM errors
      - slowResponse     # >5s p95 latency
      - instanceScaleUp
      - instanceScaleDown
```

### Custom Metrics
```python
# Log to Render metrics
import logging
logger.info(f"ml_inference_time:{inference_time}")
logger.info(f"batch_size:{len(batch)}")
logger.info(f"cache_hit_rate:{cache_hit_rate}")
```

## 📝 Deployment Checklist

### Before Production
- [ ] Test with expected load (use locust/k6)
- [ ] Configure auto-scaling thresholds
- [ ] Set up monitoring alerts
- [ ] Test failover/recovery
- [ ] Document runbooks

### Initial Deployment
```bash
# 1. Deploy with starter plan
render create --name ml-analyzer --plan starter

# 2. Test with sample workload
python test_load.py --users 10 --duration 60

# 3. Monitor metrics
watch curl https://your-app.onrender.com/ml/metrics

# 4. Adjust scaling based on results
render scale --min 1 --max 5
```

### Production Deployment
```bash
# 1. Upgrade to standard/pro
render plan --set standard

# 2. Enable auto-scaling
render scaling --min 2 --max 10 --cpu 60

# 3. Configure alerts
render alerts --add cpu>80 memory>85

# 4. Deploy with zero-downtime
render deploy --strategy blue-green
```

## 🔧 Troubleshooting

### High CPU Usage
```bash
# Check which endpoints are slow
curl /ml/metrics | jq '.avg_inference_time'

# Optimize batch size
export BATCH_SIZE=16  # Reduce from 32

# Add more workers
render scale --min 3
```

### Memory Issues
```bash
# Trigger cleanup
curl -X POST /ml/optimize-memory

# Check memory usage
curl /ml/metrics | jq '.memory_usage_mb'

# Upgrade instance
render plan --set pro
```

### Slow Inference
```bash
# Check cache performance
curl /ml/metrics | jq '.cache_hit_rate'

# Increase cache size
export CACHE_SIZE=2000

# Consider GPU for >1000 req/hour
render gpu --enable  # When available
```

## 📊 Load Testing

### Test Script
```python
# test_load.py
import asyncio
import aiohttp
import time

async def test_inference(session, text):
    async with session.post('/analyze-go-back', 
                           json={'infraction_text': text}) as resp:
        return await resp.json()

async def load_test(users=10, duration=60):
    async with aiohttp.ClientSession() as session:
        start = time.time()
        tasks = []
        
        while time.time() - start < duration:
            for _ in range(users):
                tasks.append(test_inference(session, "test text"))
            
            if len(tasks) >= 100:
                await asyncio.gather(*tasks)
                tasks = []
        
        print(f"Completed {len(tasks)} requests")

# Run test
asyncio.run(load_test(users=50, duration=300))
```

## 🎯 Performance Targets

### Response Times (p95)
- **/learn-spec**: <10s for 100-page PDF
- **/analyze-go-back**: <2s per infraction
- **/batch-analyze**: <5s for 10 infractions
- **/ml/metrics**: <100ms

### Throughput
- **Starter**: 10 req/min
- **Standard**: 60 req/min
- **Pro**: 200 req/min
- **Pro+**: 1000 req/min

## 🚀 Next Steps

1. **Deploy**: `git push` with scaling config
2. **Monitor**: Watch metrics for 24 hours
3. **Tune**: Adjust thresholds based on actual load
4. **Optimize**: Enable caching, batching
5. **Scale**: Upgrade plan as needed

---

*Your ML analyzer is now configured for production scaling from $7/mo to enterprise!*
