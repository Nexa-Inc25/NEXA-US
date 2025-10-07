#!/bin/bash
# NEXA AI Document Analyzer - Render.com Deployment Script
# October 07, 2025 Version

echo "================================================"
echo "🚀 NEXA Document Analyzer - Deployment Script"
echo "   October 07, 2025 Enhanced Version"
echo "================================================"

# Configuration
RENDER_SERVICE_NAME="nexa-doc-analyzer-oct2025"
GITHUB_REPO="nexa-inc-mvp"  # Update with your repo name
DOCKERFILE="Dockerfile.oct2025"
APP_FILE="app_oct2025_enhanced.py"
REQUIREMENTS="requirements_oct2025.txt"

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

# Start server in background
uvicorn app_oct2025_enhanced:app --port 8000 &
SERVER_PID=$!
echo "Server PID: $SERVER_PID"

# Wait for server to start
sleep 5

# Run tests
echo "Running test suite..."
python test_oct07_full.py

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

git add $APP_FILE $REQUIREMENTS $DOCKERFILE test_oct07_full.py render.yaml
git commit -m "Deploy October 07, 2025 Enhanced Version - FuseSaver/Recloser improvements"
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
echo "6. Environment Variables (optional):"
echo "   • LOG_LEVEL: INFO"
echo ""
echo "7. Click 'Create Web Service'"
echo ""
echo "8. Wait for build to complete (~5-10 minutes)"
echo ""
echo "9. Test your deployment:"
echo "   curl https://${RENDER_SERVICE_NAME}.onrender.com/health"
echo ""
echo "================================================"
echo "✨ Deployment preparation complete!"
echo "================================================"
