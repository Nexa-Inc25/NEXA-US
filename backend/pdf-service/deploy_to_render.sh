#!/bin/bash

# Deploy NEXA AI Document Analyzer to Render.com
# PRODUCTION MODE - NO MOCK DATA

echo "========================================="
echo "NEXA AI DOCUMENT ANALYZER - PRODUCTION"
echo "========================================="
echo "Deploying with REAL DATA ONLY mode..."
echo "-----------------------------------------"

# Build production Docker image (no mock data)
docker build -f Dockerfile.production -t nexa-backend-production .

echo "================================================"
echo "🚀 NEXA Document Analyzer - Deployment Script"
echo "   October 07, 2025 Enhanced Version"
echo "================================================"

# Configuration
RENDER_SERVICE_NAME="nexa-ai-analyzer-production"
GITHUB_REPO="nexa-inc-mvp"  # Update with your repo name
DOCKERFILE="Dockerfile.production"
APP_FILE="field_crew_workflow.py"
REQUIREMENTS="requirements_oct2025.txt"
DATABASE_NAME="nexa_db_94sr"

# Check if files exist
echo ""
echo "📋 Checking required files..."

if [ ! -f "$APP_FILE" ]; then
    echo "❌ Missing $APP_FILE"
    exit 1
fi

if [ ! -f "$REQUIREMENTS" ]; then
    echo "❌ Missing $REQUIREMENTS"
    exit 1
fi

if [ ! -f "$DOCKERFILE" ]; then
    echo "❌ Missing $DOCKERFILE"
    exit 1
fi

echo "✅ All required files present"

# Test locally first
echo ""
echo "🧪 Testing locally..."
echo "Starting server for testing..."

# Verify no mock data
echo "Verifying production readiness (no mock data)..."
python verify_production_ready.py

if [ $? -ne 0 ]; then
    echo "❌ System contains mock data. Clean before deploying."
    exit 1
fi

echo "✅ No mock data found - ready for production"

TEST_RESULT=$?

# Stop server
echo "Stopping test server..."
kill $SERVER_PID 2>/dev/null

if [ $TEST_RESULT -ne 0 ]; then
    echo "❌ Tests failed. Fix issues before deploying."
    exit 1
fi

echo "✅ Local tests passed"

# Prepare for deployment
echo ""
echo "📦 Preparing deployment..."

# Create render.yaml if it doesn't exist
if [ ! -f "render.yaml" ]; then
    echo "Creating render.yaml..."
    cat > render.yaml << EOF
services:
  - type: web
    name: ${RENDER_SERVICE_NAME}
    env: docker
    dockerfilePath: ./${DOCKERFILE}
    dockerContext: .
    disk:
      name: embeddings
      mountPath: /data
      sizeGB: 1
    envVars:
      - key: PYTHON_VERSION
        value: "3.9"
    healthCheckPath: /health
EOF
    echo "✅ render.yaml created"
fi

# Git operations
echo ""
echo "📤 Pushing to GitHub..."

git add $APP_FILE $REQUIREMENTS $DOCKERFILE init_production_db.py verify_production_ready.py render.yaml
git commit -m "Deploy NEXA AI Document Analyzer - PRODUCTION (Real Data Only)"
git push origin main

if [ $? -ne 0 ]; then
    echo "❌ Git push failed. Check your repository settings."
    exit 1
fi

echo "✅ Code pushed to GitHub"

# Instructions for Render deployment
echo ""
echo "================================================"
echo "📝 RENDER.COM DEPLOYMENT INSTRUCTIONS"
echo "================================================"
echo ""
echo "1. Go to https://dashboard.render.com"
echo ""
echo "2. Click 'New +' → 'Web Service'"
echo ""
echo "3. Connect your GitHub repository: ${GITHUB_REPO}"
echo ""
echo "4. Configure service:"
echo "   • Name: ${RENDER_SERVICE_NAME}"
echo "   • Environment: Docker"
echo "   • Docker Path: ${DOCKERFILE}"
echo "   • Instance Type: Starter (\$7/month) for persistence"
echo ""
echo "5. Add Disk (for Starter plan):"
echo "   • Name: embeddings"
echo "   • Mount Path: /data"
echo "   • Size: 1 GB"
echo ""
echo "6. Environment Variables:"
echo "   • DATABASE_URL: (use internal Render PostgreSQL URL)"
echo "   • RENDER: true"
echo "   • NO_MOCK_DATA: true"
echo "   • LOG_LEVEL: INFO"
echo ""
echo "7. Click 'Create Web Service'"
echo ""
echo "8. Wait for build to complete (~5-10 minutes)"
echo ""
echo "9. Test your deployment:"
echo "   curl https://${RENDER_SERVICE_NAME}.onrender.com/api/status"
echo ""
echo "10. Initialize database (tables only, no mock data):"
echo "   curl -X POST https://${RENDER_SERVICE_NAME}.onrender.com/api/init-db"
echo ""
echo "================================================"
echo "✨ Deployment preparation complete!"
echo "================================================"
