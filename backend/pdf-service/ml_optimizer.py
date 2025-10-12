#!/usr/bin/env python3
"""
ML Optimization and Performance Monitoring for Production
Handles batching, caching, and resource management
"""

import os
import time
import psutil
import logging
from typing import List, Dict, Any, Optional
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor, TimeoutError
import asyncio
import numpy as np
from pathlib import Path
import pickle
import json

from fastapi import HTTPException
from sentence_transformers import SentenceTransformer
import torch

logger = logging.getLogger(__name__)

class MLOptimizer:
    """
    Optimizations for ML inference under load
    """
    
    def __init__(self,
                 batch_size: int = 32,
                 max_workers: int = 4,
                 cache_size: int = 1000,
                 timeout: int = 30):
        
        self.batch_size = int(os.getenv("BATCH_SIZE", batch_size))
        self.max_workers = int(os.getenv("MAX_WORKERS", max_workers))
        self.timeout = int(os.getenv("INFERENCE_TIMEOUT", timeout))
        
        # Thread pool for concurrent processing
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        
        # Cache for embeddings (LRU)
        self.cache_size = cache_size
        
        # Initialize models lazily
        self._embedder = None
        self._ner_model = None
        
        # Performance metrics
        self.metrics = {
            "total_requests": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "avg_inference_time": 0,
            "batch_count": 0,
            "memory_usage_mb": 0
        }
        
        # Request queue for batching
        self.request_queue = []
        self.batch_lock = asyncio.Lock()
        
        logger.info(f"ML Optimizer initialized: batch_size={self.batch_size}, workers={self.max_workers}")
    
    @property
    def embedder(self):
        """Lazy load embedder model"""
        if self._embedder is None:
            logger.info("Loading sentence transformer...")
            self._embedder = SentenceTransformer('all-MiniLM-L6-v2')
            # Set to eval mode and optimize
            self._embedder.eval()
            if torch.cuda.is_available():
                self._embedder = self._embedder.cuda()
        return self._embedder
    
    @lru_cache(maxsize=1000)
    def cached_embedding(self, text: str) -> np.ndarray:
        """Cache embeddings for frequently accessed texts"""
        self.metrics["cache_hits"] += 1
        return self.embedder.encode(text)
    
    def batch_encode(self, texts: List[str]) -> np.ndarray:
        """
        Batch encoding with resource management
        """
        
        start_time = time.time()
        self.metrics["total_requests"] += len(texts)
        
        # Check memory before processing
        memory_usage = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        self.metrics["memory_usage_mb"] = memory_usage
        
        if memory_usage > 3500:  # 3.5GB threshold
            logger.warning(f"High memory usage: {memory_usage:.0f}MB")
            # Clear caches to free memory
            self.cached_embedding.cache_clear()
            torch.cuda.empty_cache() if torch.cuda.is_available() else None
        
        try:
            # Process in batches
            all_embeddings = []
            
            for i in range(0, len(texts), self.batch_size):
                batch = texts[i:i + self.batch_size]
                
                # Try cache first
                embeddings = []
                uncached = []
                uncached_indices = []
                
                for j, text in enumerate(batch):
                    try:
                        # Check if in cache
                        emb = self.cached_embedding.__wrapped__(self, text)
                        embeddings.append(emb)
                        self.metrics["cache_hits"] += 1
                    except:
                        uncached.append(text)
                        uncached_indices.append(j)
                        self.metrics["cache_misses"] += 1
                
                # Encode uncached texts
                if uncached:
                    new_embeddings = self.embedder.encode(
                        uncached,
                        batch_size=min(self.batch_size, len(uncached)),
                        show_progress_bar=False,
                        convert_to_numpy=True
                    )
                    
                    # Insert new embeddings at correct positions
                    for idx, emb in zip(uncached_indices, new_embeddings):
                        embeddings.insert(idx, emb)
                
                all_embeddings.extend(embeddings)
                self.metrics["batch_count"] += 1
            
            # Update metrics
            inference_time = time.time() - start_time
            self.metrics["avg_inference_time"] = (
                self.metrics["avg_inference_time"] * 0.9 + inference_time * 0.1
            )
            
            logger.info(f"Batch encoded {len(texts)} texts in {inference_time:.2f}s")
            
            return np.array(all_embeddings)
            
        except Exception as e:
            logger.error(f"Batch encoding failed: {e}")
            raise HTTPException(status_code=500, detail="Encoding failed")
    
    async def queue_for_batch(self, text: str, timeout: Optional[int] = None) -> np.ndarray:
        """
        Queue requests for batch processing (async)
        """
        
        timeout = timeout or self.timeout
        
        async with self.batch_lock:
            self.request_queue.append(text)
            
            # Process batch if full or after timeout
            if len(self.request_queue) >= self.batch_size:
                return await self._process_batch()
        
        # Wait for batch to fill or timeout
        await asyncio.sleep(0.1)  # Small delay for batching
        
        async with self.batch_lock:
            if text in self.request_queue:
                return await self._process_batch()
    
    async def _process_batch(self) -> np.ndarray:
        """Process queued batch"""
        
        if not self.request_queue:
            return np.array([])
        
        batch = self.request_queue[:self.batch_size]
        self.request_queue = self.request_queue[self.batch_size:]
        
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(
            self.executor,
            self.batch_encode,
            batch
        )
        
        return embeddings
    
    def optimize_model_memory(self):
        """
        Optimize model memory usage for production
        """
        
        if self._embedder:
            # Convert to half precision if supported
            if torch.cuda.is_available():
                self._embedder = self._embedder.half()
            
            # Enable gradient checkpointing
            self._embedder.eval()
            
            # Clear gradients
            for param in self._embedder.parameters():
                param.grad = None
        
        # Force garbage collection
        import gc
        gc.collect()
        
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        
        cache_hit_rate = (
            self.metrics["cache_hits"] / 
            max(self.metrics["cache_hits"] + self.metrics["cache_misses"], 1)
        ) * 100
        
        return {
            **self.metrics,
            "cache_hit_rate": f"{cache_hit_rate:.1f}%",
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "thread_count": self.executor._threads.__len__() if hasattr(self.executor, '_threads') else 0
        }

class InferenceScaler:
    """
    Handles scaling decisions based on load
    """
    
    def __init__(self, optimizer: MLOptimizer):
        self.optimizer = optimizer
        self.scaling_history = []
        self.last_scale_time = time.time()
        self.scale_cooldown = 60  # seconds
    
    def should_scale_up(self) -> bool:
        """Determine if should scale up based on metrics"""
        
        metrics = self.optimizer.get_metrics()
        
        # Scale up conditions
        scale_up = any([
            metrics["cpu_percent"] > 70,
            metrics["memory_percent"] > 80,
            metrics["avg_inference_time"] > 5,  # seconds
            metrics["batch_count"] > 100  # High throughput
        ])
        
        # Check cooldown
        if scale_up and (time.time() - self.last_scale_time) > self.scale_cooldown:
            self.last_scale_time = time.time()
            self.scaling_history.append({
                "action": "scale_up",
                "metrics": metrics,
                "timestamp": time.time()
            })
            return True
        
        return False
    
    def should_scale_down(self) -> bool:
        """Determine if should scale down based on metrics"""
        
        metrics = self.optimizer.get_metrics()
        
        # Scale down conditions
        scale_down = all([
            metrics["cpu_percent"] < 30,
            metrics["memory_percent"] < 50,
            metrics["avg_inference_time"] < 1,
            metrics["batch_count"] < 10
        ])
        
        # Check cooldown
        if scale_down and (time.time() - self.last_scale_time) > self.scale_cooldown * 2:
            self.last_scale_time = time.time()
            self.scaling_history.append({
                "action": "scale_down",
                "metrics": metrics,
                "timestamp": time.time()
            })
            return True
        
        return False
    
    def get_recommendations(self) -> Dict[str, Any]:
        """Get scaling recommendations"""
        
        metrics = self.optimizer.get_metrics()
        
        recommendations = {
            "current_metrics": metrics,
            "scale_up": self.should_scale_up(),
            "scale_down": self.should_scale_down(),
            "recommendations": []
        }
        
        # Specific recommendations
        if metrics["cpu_percent"] > 70:
            recommendations["recommendations"].append(
                "High CPU usage - consider upgrading to 'pro' instance or adding workers"
            )
        
        if metrics["memory_percent"] > 80:
            recommendations["recommendations"].append(
                "High memory usage - consider upgrading instance or optimizing batch size"
            )
        
        if metrics.get("cache_hit_rate", "0%").replace("%", "") < "50":
            recommendations["recommendations"].append(
                "Low cache hit rate - consider increasing cache size"
            )
        
        if metrics["avg_inference_time"] > 3:
            recommendations["recommendations"].append(
                f"Slow inference ({metrics['avg_inference_time']:.1f}s) - reduce batch size or add GPU"
            )
        
        return recommendations

# FastAPI integration
def integrate_ml_optimizer(app):
    """Add ML optimization endpoints to FastAPI app"""
    
    from fastapi import APIRouter
    
    router = APIRouter(prefix="/ml", tags=["ML Optimization"])
    optimizer = MLOptimizer()
    scaler = InferenceScaler(optimizer)
    
    @router.get("/metrics")
    async def get_metrics():
        """Get ML performance metrics"""
        return optimizer.get_metrics()
    
    @router.get("/scaling-recommendations")
    async def get_scaling_recommendations():
        """Get scaling recommendations based on current load"""
        return scaler.get_recommendations()
    
    @router.post("/optimize-memory")
    async def optimize_memory():
        """Trigger memory optimization"""
        optimizer.optimize_model_memory()
        return {"status": "optimized", "memory_mb": psutil.Process().memory_info().rss / 1024 / 1024}
    
    @router.post("/batch-encode")
    async def batch_encode_endpoint(texts: List[str]):
        """Batch encode texts with optimization"""
        embeddings = optimizer.batch_encode(texts)
        return {
            "count": len(texts),
            "shape": embeddings.shape,
            "metrics": optimizer.get_metrics()
        }
    
    app.include_router(router)
    logger.info("✅ ML optimization endpoints added: /ml/*")

if __name__ == "__main__":
    # Test the optimizer
    optimizer = MLOptimizer()
    
    # Test batch encoding
    test_texts = [
        "This is a test specification",
        "Minimum clearance is 18 feet",
        "Conduit depth requirements"
    ] * 10  # 30 texts
    
    print("Testing batch encoding...")
    embeddings = optimizer.batch_encode(test_texts)
    print(f"Encoded {len(test_texts)} texts -> shape: {embeddings.shape}")
    
    # Show metrics
    metrics = optimizer.get_metrics()
    print("\nPerformance Metrics:")
    for key, value in metrics.items():
        print(f"  {key}: {value}")
    
    # Test scaler
    scaler = InferenceScaler(optimizer)
    recommendations = scaler.get_recommendations()
    print("\nScaling Recommendations:")
    for rec in recommendations["recommendations"]:
        print(f"  - {rec}")
