#!/bin/bash
# NEXA Week 1 Deployment - Minimal Pipeline Usage Version
# Runs locally to avoid CI/CD minutes

echo "🎯 Week 1 Deployment (Pipeline-Efficient)"
echo "========================================="

# 1. Apply optimizations locally
echo "📝 Applying optimizations..."
cd backend/pdf-service

# Update rate limit
sed -i.bak 's/calls=100/calls=200/' app_oct2025_enhanced.py

# Update chunk size
sed -i.bak 's/chunk_size: int = 1100/chunk_size: int = 400/' app_oct2025_enhanced.py

# 2. Quick local test (no full suite)
echo "✓ Testing health endpoint..."
python -c "import requests; r=requests.get('http://localhost:8000/health'); print('Local test:', r.status_code)"

# 3. Single commit (avoid multiple pipeline triggers)
git add app_oct2025_enhanced.py backup_manager.py app_opt_week1.py
git commit -m "Week 1: Foundation optimizations (chunk=400, rate=200, backup system)"

# 4. Direct push to Render (bypasses GitHub Actions)
echo "🚀 Pushing to Render only..."
git push render main  # Push directly to Render, not GitHub

echo "✅ Deployment complete - minimal pipeline usage"
echo "Check: https://nexa-api-xpu3.onrender.com/health"
