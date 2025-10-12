#!/bin/bash

echo "🚀 DEPLOYING NEXA UNIVERSAL STANDARDS PLATFORM"
echo "=============================================="
echo ""

# Configuration
RENDER_SERVICE="nexa-us-pro"
DATABASE_URL=${DATABASE_URL:-"postgresql://postgres:password@localhost/nexa"}

echo "📦 Step 1: Update requirements"
echo "------------------------------"

# Add new requirements to existing file
cat >> backend/pdf-service/requirements_oct2025_fixed.txt << EOF

# Universal Standards Platform
asyncpg==0.27.0
EOF

echo "✅ Requirements updated"
echo ""

echo "🗄️ Step 2: Setup Database (Local Testing)"
echo "-----------------------------------------"
echo "Running database setup script..."

cd backend/pdf-service
python setup_universal_db.py

cd ../..
echo "✅ Database configured"
echo ""

echo "📝 Step 3: Update Application"
echo "-----------------------------"
echo "Copying universal app as main app..."

# Backup existing app
cp backend/pdf-service/app_oct2025_enhanced.py backend/pdf-service/app_oct2025_backup.py

# Update imports in existing app
cat >> backend/pdf-service/app_oct2025_enhanced.py << 'EOF'

# ==================== UNIVERSAL STANDARDS INTEGRATION ====================
try:
    from universal_engine import engine
    
    @app.on_event("startup")
    async def init_universal():
        await engine.initialize()
        logger.info("Universal Standards Engine initialized")
    
    # Add universal endpoints
    @app.get("/api/utilities")
    async def list_utilities():
        return {"utilities": list(engine.utility_cache.keys())}
    
    @app.post("/api/jobs/create")
    async def create_universal_job(
        job_number: str = Form(...),
        lat: float = Form(...),
        lng: float = Form(...),
        address: Optional[str] = Form(None)
    ):
        utility_code = await engine.detect_utility_for_job(lat, lng, address)
        return {
            "job_number": job_number,
            "detected_utility": utility_code,
            "location": {"lat": lat, "lng": lng}
        }
    
except ImportError:
    logger.warning("Universal engine not available")
EOF

echo "✅ Application updated"
echo ""

echo "🌍 Step 4: Environment Variables for Render"
echo "-------------------------------------------"
echo "Add these to Render dashboard:"
echo ""
echo "DATABASE_URL=<your-postgres-url>"
echo "DATA_PATH=/data"
echo ""

echo "📤 Step 5: Deploy to Render"
echo "---------------------------"

# Git operations
git add -A
git commit -m "Add Universal Standards Platform - Multi-utility support with auto-detection"
git push origin main

echo ""
echo "✅ DEPLOYMENT INITIATED!"
echo ""
echo "========================================="
echo "📊 NEXT STEPS:"
echo "========================================="
echo ""
echo "1. Wait for Render to rebuild (~5-10 min)"
echo ""
echo "2. Run database migration on Render:"
echo "   ssh into Render service and run:"
echo "   python backend/pdf-service/setup_universal_db.py"
echo ""
echo "3. Test the endpoints:"
echo ""
echo "   # List utilities"
echo "   curl https://nexa-us-pro.onrender.com/api/utilities"
echo ""
echo "   # Create job with auto-detection"
echo "   curl -X POST https://nexa-us-pro.onrender.com/api/jobs/create \\"
echo "     -F 'job_number=TEST-001' \\"
echo "     -F 'lat=37.7749' \\"
echo "     -F 'lng=-122.4194' \\"
echo "     -F 'address=San Francisco, CA'"
echo ""
echo "   # Ingest PG&E spec"
echo "   curl -X POST https://nexa-us-pro.onrender.com/api/utilities/PGE/ingest \\"
echo "     -F 'file=@greenbook.pdf'"
echo ""
echo "4. Setup demo data:"
echo "   curl -X POST https://nexa-us-pro.onrender.com/api/demo/setup"
echo ""
echo "🎉 Universal Standards Platform Ready!"
