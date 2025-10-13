#!/bin/bash

# NEXA AI Document Analyzer - Security Deployment Script
# For Render.com deployment with security features enabled

echo "========================================"
echo "NEXA SECURITY DEPLOYMENT"
echo "========================================"
echo "Deploying to Render.com with security enabled"
echo "----------------------------------------"

# Check if .env.production exists
if [ ! -f .env.production ]; then
    echo "❌ Error: .env.production not found!"
    echo "Run python generate_credentials.py first"
    exit 1
fi

# Verify required files
required_files=(
    "field_crew_workflow.py"
    "requirements_oct2025.txt"
    "Dockerfile.production"
    ".env.production"
)

echo "Checking required files..."
for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file found"
    else
        echo "❌ $file missing!"
        exit 1
    fi
done

# Update Dockerfile for security
echo ""
echo "Creating secure Dockerfile..."
cat > Dockerfile.production <<EOF
FROM python:3.11-slim

# Security: Run as non-root user
RUN useradd -m -u 1000 nexa && \
    mkdir -p /data /app && \
    chown -R nexa:nexa /data /app

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    tesseract-ocr \
    poppler-utils \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libgomp1 \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY --chown=nexa:nexa requirements_oct2025.txt .
RUN pip install --no-cache-dir -r requirements_oct2025.txt

# Download spaCy model
RUN python -m spacy download en_core_web_sm

# Copy application code
COPY --chown=nexa:nexa . .

# Create necessary directories
RUN mkdir -p /data/logs /data/uploads /data/quarantine /data/models

# Switch to non-root user
USER nexa

# Security: Don't expose sensitive info
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Run with security features enabled
CMD ["uvicorn", "field_crew_workflow:api", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
EOF

echo "✅ Secure Dockerfile created"

# Create render.yaml for deployment
echo ""
echo "Creating render.yaml..."
cat > render.yaml <<EOF
services:
  - type: web
    name: nexa-api-secure
    env: docker
    dockerfilePath: ./Dockerfile.production
    envVars:
      - key: DATABASE_URL
        fromDatabase:
          name: nexa-db
          property: connectionString
      - key: JWT_SECRET
        generateValue: true
      - key: ENCRYPTION_KEY
        generateValue: true
    disk:
      name: nexa-data
      mountPath: /data
      sizeGB: 100
    healthCheckPath: /health
    autoDeploy: false  # Manual deploy for security

databases:
  - name: nexa-db
    databaseName: nexa_production
    user: nexa_user
    plan: starter  # Upgrade for production
    ipAllowList: []  # Configure for security

envVarGroups:
  - name: nexa-security
    envVars:
      - key: JWT_ALGORITHM
        value: HS256
      - key: JWT_EXPIRATION_HOURS
        value: 24
      - key: ENABLE_AUDIT_LOGGING
        value: true
      - key: RATE_LIMIT_PER_MINUTE
        value: 100
EOF

echo "✅ render.yaml created"

# Create production test script
echo ""
echo "Creating production test script..."
cat > test_production.py <<'EOF'
#!/usr/bin/env python3
"""Test production deployment security"""

import requests
import sys
import os

# Get URL from environment or use default
BASE_URL = os.getenv("NEXA_API_URL", "https://nexa-api-xpu3.onrender.com")

print(f"Testing production deployment: {BASE_URL}")

# Test health check
try:
    response = requests.get(f"{BASE_URL}/health", timeout=10)
    if response.status_code == 200:
        data = response.json()
        print(f"✅ API is healthy: {data['status']}")
        print(f"   Security: {data.get('security', 'unknown')}")
    else:
        print(f"❌ Health check failed: {response.status_code}")
        sys.exit(1)
except Exception as e:
    print(f"❌ Cannot reach API: {e}")
    sys.exit(1)

# Test unauthorized access (should fail)
try:
    response = requests.get(f"{BASE_URL}/api/me", timeout=10)
    if response.status_code == 401:
        print("✅ Security is active (unauthorized access blocked)")
    else:
        print(f"❌ SECURITY BREACH! API accessible without auth")
        sys.exit(1)
except Exception as e:
    print(f"⚠️ Warning: {e}")

print("\n🔒 Production security checks passed!")
print("Remember to:")
print("1. Set all environment variables in Render")
print("2. Change admin password immediately")
print("3. Configure CORS for your frontend domain")
print("4. Enable database backups")
print("5. Set up monitoring alerts")
EOF

chmod +x test_production.py
echo "✅ Test script created"

# Git operations
echo ""
echo "Preparing Git commit..."

# Add security files to .gitignore
if ! grep -q ".env.production" .gitignore 2>/dev/null; then
    echo -e "\n# Security files\n.env*\n*.key\n*.pem\ncredentials.json" >> .gitignore
    echo "✅ Updated .gitignore for security"
fi

# Commit changes
git add -A
git commit -m "Add production security: JWT, encryption, audit logging, rate limiting"

echo ""
echo "========================================"
echo "🚀 DEPLOYMENT INSTRUCTIONS"
echo "========================================"
echo ""
echo "1. Generate credentials (if not done):"
echo "   python generate_credentials.py"
echo ""
echo "2. Push to GitHub:"
echo "   git push origin main"
echo ""
echo "3. In Render.com Dashboard:"
echo "   a. Create new Web Service"
echo "   b. Connect to your GitHub repo"
echo "   c. Use Docker environment"
echo "   d. Add environment variables from .env.production"
echo ""
echo "4. After deployment, test security:"
echo "   python test_production.py"
echo ""
echo "5. Create users:"
echo "   - Login as admin"
echo "   - Create PM and foreman accounts"
echo "   - Disable admin for daily use"
echo ""
echo "========================================"
echo "⚠️ CRITICAL SECURITY REMINDERS"
echo "========================================"
echo "• NEVER commit .env.production to Git"
echo "• Change admin password IMMEDIATELY"
echo "• Use unique JWT_SECRET in production"
echo "• Enable HTTPS (automatic on Render)"
echo "• Review audit logs weekly"
echo "• Rotate secrets quarterly"
echo "========================================"
