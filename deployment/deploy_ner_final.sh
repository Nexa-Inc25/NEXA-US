#!/bin/bash
# Deploy NER-enhanced analyzer to Render.com
# Linux/Mac version

echo "🚀 DEPLOYING NER-ENHANCED ANALYZER TO RENDER"
echo "============================================="
echo ""

# Check if we're in the right directory
if [ ! -f "backend/pdf-service/test_full_flow_simple.py" ]; then
    echo "❌ Error: Must run from project root directory"
    exit 1
fi

echo "📦 Preparing deployment..."
echo "--------------------------"

# Ensure data directory exists
mkdir -p data

# Copy model if it exists (optional - can train on Render)
if [ -d "backend/pdf-service/data/fine_tuned_ner" ]; then
    echo "📋 Found trained model, copying to repo..."
    cp -r backend/pdf-service/data/fine_tuned_ner data/
fi

# Copy embeddings if they exist
if [ -f "backend/pdf-service/data/spec_embeddings.pkl" ]; then
    echo "📋 Found spec embeddings, copying to repo..."
    cp backend/pdf-service/data/spec_embeddings.pkl data/
fi

# Stage all changes
echo ""
echo "📝 Staging changes..."
git add backend/pdf-service/*.py
git add backend/pdf-service/data/training/*.json 2>/dev/null
git add data/* 2>/dev/null
git add requirements*.txt
git add Dockerfile* 2>/dev/null
git add render*.yaml 2>/dev/null
git add *.md

# Commit changes
echo ""
echo "💾 Committing changes..."
git commit -m "Deploy NER-enhanced analyzer with full flow testing

- Simplified test flow for Python 3.13 compatibility
- Mock embeddings for testing without dependencies
- Pattern-based NER extraction fallback
- Confidence scoring with spec matching
- Ready for Render.com deployment"

# Push to GitHub
echo ""
echo "📤 Pushing to GitHub..."
git push origin main

echo ""
echo "============================================="
echo "✅ DEPLOYMENT INITIATED"
echo "============================================="
echo ""
echo "Next Steps on Render.com:"
echo "-------------------------"
echo "1. Check Render dashboard for auto-deploy"
echo "2. Ensure /data disk is mounted (10GB)"
echo "3. Set environment variables if needed:"
echo "   - CONFIDENCE_THRESHOLD=0.85"
echo "   - MODEL_PATH=/data/fine_tuned_ner"
echo ""
echo "Test endpoints after deployment:"
echo "---------------------------------"
echo "# Health check"
echo "curl https://your-app.onrender.com/health"
echo ""
echo "# Upload spec"
echo "curl -X POST https://your-app.onrender.com/upload-specs \\"
echo "  -F 'files=@spec.pdf'"
echo ""
echo "# Analyze go-backs"
echo "curl -X POST https://your-app.onrender.com/analyze-go-back \\"
echo "  -d '{\"infraction_text\": \"16 ft clearance over street\"}'"
echo ""
echo "============================================="
echo "📊 Expected Performance:"
echo "- Confidence: 85-95% for matches"
echo "- Response time: <100ms"
echo "- Repeal rate: 30-50%"
echo "============================================="
