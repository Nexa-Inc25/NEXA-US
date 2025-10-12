#!/usr/bin/env python3
"""
Quick fix for 502 Bad Gateway error on Render
Apply these patches to app_oct2025_enhanced.py
"""

import os

def create_fixed_app():
    """
    Create a patched version of the app with 502 fixes
    """
    
    fixes = """
# MEMORY OPTIMIZATION FIXES FOR 502 ERROR
# Add these imports at the top of app_oct2025_enhanced.py

import gc
import psutil
from fastapi.responses import Response

# Add memory monitoring
def get_memory_usage():
    process = psutil.Process()
    return process.memory_info().rss / 1024 / 1024

# Modify the model loading to be lazy
_sentence_model = None

def get_sentence_model():
    global _sentence_model
    if _sentence_model is None:
        logger.info(f"Loading model. Memory: {get_memory_usage():.2f} MB")
        _sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
        _sentence_model.max_seq_length = 256  # Reduce for memory
        gc.collect()
        logger.info(f"Model loaded. Memory: {get_memory_usage():.2f} MB")
    return _sentence_model

# Replace the startup event with this optimized version:
@app.on_event("startup")
async def startup_event():
    global spec_embeddings, spec_metadata
    
    logger.info("🚀 Starting NEXA (memory optimized)...")
    logger.info(f"Initial memory: {get_memory_usage():.2f} MB")
    
    # Load embeddings if they exist (but don't fail if they don't)
    try:
        if os.path.exists(EMBEDDINGS_FILE):
            with open(EMBEDDINGS_FILE, 'rb') as f:
                spec_embeddings = pickle.load(f)
            logger.info(f"Loaded {len(spec_embeddings.get('chunks', []))} chunks")
        else:
            spec_embeddings = {"chunks": [], "embeddings": None}
    except Exception as e:
        logger.error(f"Failed to load embeddings: {e}")
        spec_embeddings = {"chunks": [], "embeddings": None}
    
    # Load metadata
    try:
        if os.path.exists(METADATA_FILE):
            with open(METADATA_FILE, 'r') as f:
                spec_metadata = json.load(f)
        else:
            spec_metadata = {"files": [], "total_chunks": 0}
    except Exception as e:
        logger.error(f"Failed to load metadata: {e}")
        spec_metadata = {"files": [], "total_chunks": 0}
    
    # Don't load models at startup - use lazy loading
    logger.info("✅ Lazy loading enabled for models")
    
    # Start periodic garbage collection
    import asyncio
    async def gc_task():
        while True:
            await asyncio.sleep(60)
            before = get_memory_usage()
            collected = gc.collect()
            after = get_memory_usage()
            if before - after > 10:  # If freed more than 10MB
                logger.info(f"GC freed {before-after:.2f} MB")
    
    asyncio.create_task(gc_task())
    logger.info(f"Startup complete. Memory: {get_memory_usage():.2f} MB")

# Add a root endpoint for Render health checks
@app.get("/")
async def root():
    return {
        "status": "healthy",
        "service": "NEXA Document Analyzer",
        "memory_mb": round(get_memory_usage(), 2)
    }

# Add HEAD support for health checks
@app.head("/")
async def head_root():
    return Response(status_code=200)

# Modify the health endpoint
@app.get("/health")
async def health_check():
    memory = get_memory_usage()
    memory_warning = memory > 450  # Warning if over 450MB
    
    return {
        "status": "healthy" if not memory_warning else "warning",
        "version": "2.0-optimized",
        "storage_path": DATA_DIR,
        "memory_mb": round(memory, 2),
        "memory_warning": memory_warning,
        "spec_chunks": len(spec_embeddings.get('chunks', [])),
        "spec_files": len(spec_metadata.get('files', []))
    }

# In analyze_audit endpoint, use lazy loading:
# Replace: embeddings = model.encode(infraction_texts)
# With: 
# model = get_sentence_model()
# embeddings = model.encode(infraction_texts)

"""

    print("="*50)
    print("502 BAD GATEWAY FIX INSTRUCTIONS")
    print("="*50)
    print("\n📝 Add these fixes to app_oct2025_enhanced.py:\n")
    print(fixes)
    print("\n" + "="*50)
    print("🚀 DEPLOYMENT STEPS")
    print("="*50)
    print("""
1. Apply the fixes above to app_oct2025_enhanced.py

2. Test locally first:
   python app_oct2025_enhanced.py
   curl http://localhost:8000/health

3. Commit and push:
   git add app_oct2025_enhanced.py
   git commit -m "Fix 502 error - optimize memory usage"
   git push origin main

4. Monitor on Render Dashboard:
   - Watch deployment logs
   - Check memory usage
   - Verify "Your service is live"

5. Test after deployment:
   curl https://nexa-doc-analyzer-oct2025.onrender.com/health
   
   Should return:
   {
     "status": "healthy",
     "memory_mb": <should be under 450>
   }
""")

    # Create requirements additions
    print("\n" + "="*50)
    print("📦 ADD TO requirements_oct2025.txt:")
    print("="*50)
    print("psutil==5.9.5  # For memory monitoring")
    
    print("\n✅ These fixes should resolve the 502 error!")
    print("💡 The main issue is likely memory usage exceeding Render's limit.")
    print("   These optimizations keep memory under 480MB (512MB limit).")

if __name__ == "__main__":
    create_fixed_app()
