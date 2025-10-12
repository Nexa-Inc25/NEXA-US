"""
Memory-optimized startup configuration for Render deployment
Fixes 502 Bad Gateway errors caused by memory issues
"""

import os
import gc
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class OptimizedModelLoader:
    """
    Lazy loading and memory-optimized model management
    """
    def __init__(self):
        self._model = None
        self._vision_model = None
        self._embeddings = None
        self.max_memory_mb = 480  # Stay under 512MB limit
        
    def get_sentence_model(self):
        """Load sentence transformer with memory optimization"""
        if self._model is None:
            logger.info("Loading sentence transformer (optimized)...")
            
            # Clear memory before loading
            gc.collect()
            
            # Import only when needed
            from sentence_transformers import SentenceTransformer
            
            # Use smaller model for lower memory
            self._model = SentenceTransformer('all-MiniLM-L6-v2')
            
            # Reduce batch size to save memory
            self._model.max_seq_length = 256
            
            # Set to eval mode (saves memory)
            self._model.eval()
            
            logger.info("✅ Sentence transformer loaded (optimized)")
            
        return self._model
    
    def get_vision_model(self):
        """Load YOLO model only when needed"""
        if self._vision_model is None:
            logger.info("Loading vision model (lazy)...")
            
            try:
                from ultralytics import YOLO
                
                # Clear memory first
                gc.collect()
                
                # Try to load trained model, fall back to base
                model_path = "/data/yolo_pole.pt"
                if os.path.exists(model_path):
                    self._vision_model = YOLO(model_path)
                else:
                    # Use nano model for lower memory
                    self._vision_model = YOLO("yolov8n.pt")
                    
                logger.info("✅ Vision model loaded")
                
            except Exception as e:
                logger.warning(f"Vision model not loaded: {e}")
                self._vision_model = None
                
        return self._vision_model
    
    def load_embeddings(self):
        """Load embeddings with memory management"""
        if self._embeddings is None:
            import pickle
            
            embeddings_path = "/data/spec_embeddings.pkl"
            if os.path.exists(embeddings_path):
                try:
                    # Clear memory before loading
                    gc.collect()
                    
                    with open(embeddings_path, 'rb') as f:
                        self._embeddings = pickle.load(f)
                        
                    logger.info(f"✅ Loaded {len(self._embeddings.get('chunks', []))} embeddings")
                    
                except Exception as e:
                    logger.error(f"Failed to load embeddings: {e}")
                    self._embeddings = {'chunks': [], 'embeddings': None}
            else:
                self._embeddings = {'chunks': [], 'embeddings': None}
                
        return self._embeddings
    
    def clear_cache(self):
        """Clear unused models from memory"""
        if self._vision_model is not None:
            del self._vision_model
            self._vision_model = None
            
        gc.collect()
        logger.info("♻️ Memory cache cleared")

# Global instance
model_manager = OptimizedModelLoader()

def setup_memory_monitoring():
    """
    Setup memory monitoring and limits
    """
    import resource
    import psutil
    
    # Log current memory usage
    process = psutil.Process()
    memory_mb = process.memory_info().rss / 1024 / 1024
    logger.info(f"💾 Current memory usage: {memory_mb:.2f} MB")
    
    # Set memory limit (Linux only)
    if hasattr(resource, 'RLIMIT_AS'):
        try:
            soft, hard = resource.getrlimit(resource.RLIMIT_AS)
            # Set to 480MB (under 512MB Render limit)
            resource.setrlimit(resource.RLIMIT_AS, (480 * 1024 * 1024, hard))
            logger.info("✅ Memory limit set to 480 MB")
        except Exception as e:
            logger.warning(f"Could not set memory limit: {e}")

async def periodic_gc(interval_seconds: int = 60):
    """
    Run garbage collection periodically
    """
    import asyncio
    
    while True:
        await asyncio.sleep(interval_seconds)
        
        # Log memory before GC
        import psutil
        process = psutil.Process()
        before_mb = process.memory_info().rss / 1024 / 1024
        
        # Run garbage collection
        collected = gc.collect()
        
        # Log memory after GC
        after_mb = process.memory_info().rss / 1024 / 1024
        freed_mb = before_mb - after_mb
        
        if freed_mb > 0:
            logger.info(f"♻️ GC freed {freed_mb:.2f} MB (collected {collected} objects)")

def get_optimized_app_config():
    """
    Returns optimized FastAPI configuration for low memory
    """
    return {
        "title": "NEXA Document Analyzer (Optimized)",
        "version": "2.0-optimized",
        "docs_url": "/docs",
        "redoc_url": None,  # Disable redoc to save memory
        "openapi_url": "/openapi.json",
    }

# Startup function to add to FastAPI app
async def optimized_startup(app):
    """
    Optimized startup sequence for FastAPI app
    """
    logger.info("🚀 Starting NEXA with memory optimization...")
    
    # Setup memory monitoring
    setup_memory_monitoring()
    
    # Start periodic garbage collection
    import asyncio
    asyncio.create_task(periodic_gc(60))
    
    # Don't load models at startup - use lazy loading
    logger.info("✅ Lazy loading enabled - models load on first use")
    
    # Log startup complete
    logger.info("✅ Optimized startup complete")

# Health check endpoint that doesn't load models
async def lightweight_health_check():
    """
    Lightweight health check that doesn't trigger model loading
    """
    import psutil
    
    process = psutil.Process()
    memory_mb = process.memory_info().rss / 1024 / 1024
    memory_percent = (memory_mb / 512) * 100
    
    return {
        "status": "healthy",
        "memory_mb": round(memory_mb, 2),
        "memory_percent": round(memory_percent, 2),
        "memory_warning": memory_percent > 90,
        "models_loaded": {
            "sentence": model_manager._model is not None,
            "vision": model_manager._vision_model is not None,
            "embeddings": model_manager._embeddings is not None
        }
    }

# Example usage in FastAPI app:
"""
from fastapi import FastAPI
from memory_optimized_startup import (
    model_manager, 
    optimized_startup,
    lightweight_health_check,
    get_optimized_app_config
)

# Create app with optimized config
app = FastAPI(**get_optimized_app_config())

# Add startup event
@app.on_event("startup")
async def startup_event():
    await optimized_startup(app)

# Add lightweight health check
@app.get("/health")
async def health():
    return await lightweight_health_check()

# Use lazy loading in endpoints
@app.post("/analyze")
async def analyze(text: str):
    # Model loads only when needed
    model = model_manager.get_sentence_model()
    # ... rest of analysis
    
# Add HEAD support for Render health checks
@app.head("/")
async def head_root():
    return Response(status_code=200)
"""

if __name__ == "__main__":
    # Test memory optimization
    setup_memory_monitoring()
    print("✅ Memory optimization module ready")
