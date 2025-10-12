#!/bin/bash
# NEXA Live Deployment Test Script
# Tests the production system at https://nexa-us-pro.onrender.com

URL="https://nexa-us-pro.onrender.com"
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}   NEXA LIVE DEPLOYMENT TEST${NC}"
echo -e "${YELLOW}   URL: $URL${NC}"
echo -e "${YELLOW}========================================${NC}"
echo ""

# Test 1: Health Check
echo -e "${GREEN}Test 1: Health Check${NC}"
curl -s "$URL/health" | python -m json.tool
echo ""

# Test 2: Root Endpoint
echo -e "${GREEN}Test 2: System Info${NC}"
curl -s "$URL/" | python -m json.tool
echo ""

# Test 3: Get Auth Token
echo -e "${GREEN}Test 3: Authentication${NC}"
TOKEN=$(curl -s -X POST "$URL/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=Test@Pass123!" | python -c "import sys, json; print(json.load(sys.stdin).get('access_token', ''))")

if [ -z "$TOKEN" ]; then
    echo -e "${RED}Failed to get auth token!${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Token obtained successfully${NC}"
echo "Token (first 20 chars): ${TOKEN:0:20}..."
echo ""

# Test 4: Check Spec Library
echo -e "${GREEN}Test 4: Spec Library Status${NC}"
curl -s -H "Authorization: Bearer $TOKEN" "$URL/spec-library" | python -m json.tool
echo ""

# Test 5: ML Status
echo -e "${GREEN}Test 5: ML System Status${NC}"
curl -s -H "Authorization: Bearer $TOKEN" "$URL/ml-status" | python -m json.tool
echo ""

echo -e "${YELLOW}========================================${NC}"
echo -e "${GREEN}✓ Basic tests complete!${NC}"
echo -e "${YELLOW}========================================${NC}"
echo ""
echo "Next steps:"
echo "1. Upload a spec PDF using:"
echo "   curl -X POST $URL/upload-specs \\"
echo "     -H \"Authorization: Bearer \$TOKEN\" \\"
echo "     -F \"files=@your_spec.pdf\""
echo ""
echo "2. Analyze an audit PDF using:"
echo "   curl -X POST $URL/analyze-audit \\"
echo "     -H \"Authorization: Bearer \$TOKEN\" \\"
echo "     -F \"file=@your_audit.pdf\""
