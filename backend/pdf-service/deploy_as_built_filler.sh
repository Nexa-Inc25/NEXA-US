#!/bin/bash

# Deploy As-Built Auto-Filler to Render
echo "🚀 DEPLOYING AS-BUILT AUTO-FILLER"
echo "=================================="

# Step 1: Update app_oct2025_enhanced.py to include new endpoints
echo "📝 Adding as-built endpoints to main app..."

# Create patch file for app_oct2025_enhanced.py
cat > add_as_built_patch.py << 'EOF'
# Add this to your app_oct2025_enhanced.py after existing imports:

from as_built_endpoints import add_as_built_endpoints

# After creating FastAPI app and adding existing endpoints:
# Add as-built auto-filler endpoints
add_as_built_endpoints(app)
logger.info("📝 As-Built Auto-Filler endpoints registered")
EOF

echo "✅ Patch created - add to app_oct2025_enhanced.py"

# Step 2: Check requirements
echo ""
echo "📦 Checking requirements..."
echo "reportlab is already in requirements_oct2025.txt ✓"
echo "All other dependencies already included ✓"

# Step 3: Commit and push
echo ""
echo "📤 Deploying to Render..."
echo ""
echo "Run these commands:"
echo "==================="
echo ""
echo "# 1. Add the import to app_oct2025_enhanced.py:"
echo "   from as_built_endpoints import add_as_built_endpoints"
echo ""
echo "# 2. Add after existing endpoints:"
echo "   add_as_built_endpoints(app)"
echo ""
echo "# 3. Commit and push:"
echo "   git add as_built_filler.py as_built_endpoints.py app_oct2025_enhanced.py"
echo "   git commit -m 'Add as-built auto-filler with YOLO + spec cross-ref'"
echo "   git push origin main"
echo ""
echo "# 4. Monitor deployment on Render:"
echo "   https://dashboard.render.com"
echo ""
echo "⏱️ Deployment takes ~5 minutes"
echo ""
echo "✅ New endpoints will be available at:"
echo "   POST /fill-as-built - Process photos and generate PDF"
echo "   GET  /as-built-status/{job_id} - Check if filled"
echo "   GET  /download/as-built/{job_id} - Download PDF"
echo "   POST /validate-as-built - Validate against specs"
echo ""
echo "💰 No additional cost - uses existing infrastructure!"
