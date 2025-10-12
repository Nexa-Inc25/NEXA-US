#!/bin/bash

# Script to diagnose and fix 502 Bad Gateway on Render

echo "🔍 Diagnosing 502 Bad Gateway Error"
echo "===================================="

# Common causes and fixes for 502 on Render:

echo ""
echo "1️⃣ CHECK: Application Memory Usage"
echo "-----------------------------------"
echo "The app might be running out of memory (Render kills apps >512MB on free tier)"
echo ""
echo "FIX: Add memory optimization to app_oct2025_enhanced.py:"
echo "- Reduce model batch size"
echo "- Clear cache periodically"
echo "- Use lazy loading for models"

echo ""
echo "2️⃣ CHECK: Port Binding"
echo "----------------------"
echo "Ensure the app binds to the correct port"
echo ""
echo "FIX: In app_oct2025_enhanced.py, ensure:"
echo "port = int(os.environ.get('PORT', 8000))"
echo "uvicorn.run(app, host='0.0.0.0', port=port)"

echo ""
echo "3️⃣ CHECK: Startup Time"
echo "----------------------"
echo "Render has a 10-minute startup timeout"
echo ""
echo "FIX: Move heavy initialization to background:"
echo "- Load models after startup"
echo "- Use async initialization"

echo ""
echo "4️⃣ CHECK: Environment Variables"
echo "--------------------------------"
echo "Missing env vars can cause crashes"
echo ""
echo "Required variables on Render:"
echo "- PORT (auto-set by Render)"
echo "- DATABASE_URL (if using PostgreSQL)"
echo "- REDIS_URL (if using Redis)"
echo "- ROBOFLOW_API_KEY (for vision model)"

echo ""
echo "5️⃣ CHECK: Application Logs"
echo "--------------------------"
echo "Check Render dashboard for crash logs"
echo ""
echo "Common error patterns:"
echo "- 'Killed' = Out of memory"
echo "- 'Address already in use' = Port conflict"
echo "- 'ModuleNotFoundError' = Missing dependency"

echo ""
echo "📝 IMMEDIATE FIXES TO TRY:"
echo "========================="

echo ""
echo "Fix #1: Reduce Memory Usage"
cat << 'EOF'

# Add to app_oct2025_enhanced.py at the top:
import gc
import resource

# Limit memory usage (for 512MB limit)
def limit_memory():
    soft, hard = resource.getrlimit(resource.RLIMIT_AS)
    resource.setrlimit(resource.RLIMIT_AS, (480 * 1024 * 1024, hard))

# Add periodic garbage collection
@app.on_event("startup")
async def startup_event():
    # Run garbage collection every 60 seconds
    import asyncio
    async def gc_task():
        while True:
            await asyncio.sleep(60)
            gc.collect()
    asyncio.create_task(gc_task())
EOF

echo ""
echo "Fix #2: Optimize Model Loading"
cat << 'EOF'

# Lazy load the sentence transformer
_model = None

def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer('all-MiniLM-L6-v2')
        # Reduce batch size for lower memory
        _model.max_seq_length = 256
    return _model

# Use get_model() instead of direct model reference
EOF

echo ""
echo "Fix #3: Add Health Check Endpoint"
cat << 'EOF'

@app.get("/")
def root():
    return {"status": "healthy", "service": "NEXA Document Analyzer"}

@app.head("/")
def head_root():
    return Response(status_code=200)
EOF

echo ""
echo "🚀 DEPLOYMENT COMMANDS:"
echo "======================"
echo ""
echo "1. Apply fixes to app_oct2025_enhanced.py"
echo "2. Test locally:"
echo "   python app_oct2025_enhanced.py"
echo ""
echo "3. Deploy to Render:"
echo "   git add -A"
echo "   git commit -m 'Fix 502 error - optimize memory'"
echo "   git push origin main"
echo ""
echo "4. Monitor deployment:"
echo "   - Check Render dashboard logs"
echo "   - Wait for 'Your service is live'"
echo ""
echo "5. Test after deployment:"
echo "   curl https://nexa-doc-analyzer-oct2025.onrender.com/health"

echo ""
echo "✅ These fixes should resolve the 502 error!"
