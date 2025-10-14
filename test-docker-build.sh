#!/bin/bash
# Test script to verify files are present for Docker build

echo "Checking files in backend/pdf-service/..."

if [ -f "backend/pdf-service/field_crew_workflow.py" ]; then
    echo "✓ field_crew_workflow.py exists"
else
    echo "✗ field_crew_workflow.py NOT FOUND"
fi

if [ -f "backend/pdf-service/app_oct2025_enhanced.py" ]; then
    echo "✓ app_oct2025_enhanced.py exists"
else
    echo "✗ app_oct2025_enhanced.py NOT FOUND"
fi

if [ -f "backend/pdf-service/middleware.py" ]; then
    echo "✓ middleware.py exists"
else
    echo "✗ middleware.py NOT FOUND"
fi

if [ -d "backend/pdf-service/modules" ]; then
    echo "✓ modules/ directory exists"
    echo "  Contains $(ls backend/pdf-service/modules | wc -l) files"
else
    echo "✗ modules/ directory NOT FOUND"
fi

if [ -f "requirements_security.txt" ]; then
    echo "✓ requirements_security.txt exists"
else
    echo "✗ requirements_security.txt NOT FOUND"
fi

echo ""
echo "Git status of these files:"
git ls-files backend/pdf-service/field_crew_workflow.py backend/pdf-service/app_oct2025_enhanced.py backend/pdf-service/middleware.py requirements_security.txt | head -5
