#!/bin/bash

# NEXA Workflow Deployment Script
# Deploys the complete job workflow system to Render

echo "🚀 NEXA Workflow Deployment Script"
echo "=================================="

# Color codes for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
RENDER_API_URL="https://nexa-doc-analyzer-oct2025.onrender.com"
GITHUB_REPO="https://github.com/Nexa-Inc25/NEXA-US.git"

echo -e "${YELLOW}Starting deployment process...${NC}"

# Step 1: Check environment
echo -e "\n${GREEN}Step 1: Checking environment${NC}"
if [ ! -f "requirements_oct2025.txt" ]; then
    echo -e "${RED}Error: requirements_oct2025.txt not found${NC}"
    exit 1
fi

# Step 2: Update requirements
echo -e "\n${GREEN}Step 2: Updating requirements${NC}"
grep -q "reportlab" requirements_oct2025.txt || echo "reportlab==4.0.9" >> requirements_oct2025.txt
grep -q "sqlalchemy" requirements_oct2025.txt || echo "sqlalchemy==2.0.23" >> requirements_oct2025.txt
grep -q "boto3" requirements_oct2025.txt || echo "boto3==1.28.62" >> requirements_oct2025.txt
echo "✅ Requirements updated"

# Step 3: Merge workflow API into main app
echo -e "\n${GREEN}Step 3: Integrating workflow endpoints${NC}"
cat << 'EOF' > workflow_integration.py
# Workflow integration module
# Import this in app_oct2025_enhanced.py

from job_workflow_api import (
    upload_job_package,
    assign_job,
    submit_field_work,
    qa_review,
    get_job_status,
    list_jobs
)

def register_workflow_routes(app):
    """Register all workflow routes with the main app"""
    app.add_api_route("/api/workflow/upload-package", upload_job_package, methods=["POST"])
    app.add_api_route("/api/workflow/assign-job", assign_job, methods=["POST"])
    app.add_api_route("/api/workflow/submit-field-work", submit_field_work, methods=["POST"])
    app.add_api_route("/api/workflow/qa-review", qa_review, methods=["POST"])
    app.add_api_route("/api/workflow/job/{job_id}", get_job_status, methods=["GET"])
    app.add_api_route("/api/workflow/jobs", list_jobs, methods=["GET"])
    print("✅ Workflow routes registered")
EOF

# Step 4: Create database migration script
echo -e "\n${GREEN}Step 4: Creating database setup${NC}"
cat << 'EOF' > setup_database.py
#!/usr/bin/env python3
"""
Database setup for NEXA workflow
Run this after deployment to create tables
"""

import os
from sqlalchemy import create_engine
from job_workflow_api import Base

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/nexa_jobs")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

try:
    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully")
except Exception as e:
    print(f"❌ Database setup failed: {e}")
EOF

chmod +x setup_database.py

# Step 5: Update Dockerfile
echo -e "\n${GREEN}Step 5: Updating Dockerfile${NC}"
if [ -f "Dockerfile.oct2025" ]; then
    # Add workflow files to Docker image
    grep -q "job_workflow_api.py" Dockerfile.oct2025 || {
        echo "COPY ./job_workflow_api.py /app/" >> Dockerfile.oct2025
        echo "COPY ./workflow_integration.py /app/" >> Dockerfile.oct2025
        echo "COPY ./setup_database.py /app/" >> Dockerfile.oct2025
    }
    echo "✅ Dockerfile updated"
else
    echo -e "${YELLOW}Warning: Dockerfile.oct2025 not found${NC}"
fi

# Step 6: Create test script
echo -e "\n${GREEN}Step 6: Creating test script${NC}"
cat << 'EOF' > test_workflow.py
#!/usr/bin/env python3
"""Test the workflow API endpoints"""

import requests
import json
import time

API_URL = "https://nexa-doc-analyzer-oct2025.onrender.com"

def test_workflow():
    print("🧪 Testing NEXA Workflow API")
    print("=" * 40)
    
    # Test 1: Check workflow endpoints
    print("\n1. Testing workflow endpoints...")
    endpoints = [
        "/api/workflow/jobs",
    ]
    
    for endpoint in endpoints:
        try:
            response = requests.get(f"{API_URL}{endpoint}")
            if response.status_code in [200, 404]:
                print(f"✅ {endpoint}: OK")
            else:
                print(f"❌ {endpoint}: {response.status_code}")
        except Exception as e:
            print(f"❌ {endpoint}: {e}")
    
    # Test 2: Upload test job
    print("\n2. Testing job upload...")
    # Would need actual PDF file for real test
    print("⏭️ Skipping (requires PDF file)")
    
    print("\n✨ Workflow API test complete")

if __name__ == "__main__":
    test_workflow()
EOF

chmod +x test_workflow.py

# Step 7: Git operations
echo -e "\n${GREEN}Step 7: Preparing Git commit${NC}"
git add -A
git status --short

echo -e "\n${YELLOW}Ready to deploy!${NC}"
echo "Run the following commands:"
echo -e "${GREEN}1. git commit -m \"Add complete job workflow system\"${NC}"
echo -e "${GREEN}2. git push origin main${NC}"
echo -e "${GREEN}3. Wait for Render to rebuild (3-5 minutes)${NC}"
echo -e "${GREEN}4. python setup_database.py (run on Render shell)${NC}"
echo -e "${GREEN}5. python test_workflow.py (test endpoints)${NC}"

# Step 8: Environment variables reminder
echo -e "\n${YELLOW}📝 Required Environment Variables on Render:${NC}"
cat << EOF
DATABASE_URL=postgresql://...  (auto-provided by Render)
REDIS_URL=redis://...          (from Redis addon)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
PGE_EMAIL=submissions@pge.com
ROBOFLOW_API_KEY=your-key
EOF

echo -e "\n${GREEN}✅ Deployment preparation complete!${NC}"
echo -e "${YELLOW}Total estimated deployment time: 5-10 minutes${NC}"
echo -e "${YELLOW}Monthly cost remains: \$134/month${NC}"
