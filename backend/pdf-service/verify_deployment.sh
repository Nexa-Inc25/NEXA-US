#!/bin/bash

# NEXA Document Analyzer - Post-Deployment Verification Script
# Tests all endpoints after YOLO DFLoss fix (ultralytics 8.0.196)

echo "=========================================="
echo "  NEXA Deployment Verification Suite"
echo "  Testing YOLO Fix (93.2% mAP restored)"
echo "=========================================="
echo ""

# Configuration
BASE_URL="${BASE_URL:-https://nexa-us-pro.onrender.com}"
TOKEN="${AUTH_TOKEN:-your_token_here}"
TEST_IMAGE="${TEST_IMAGE:-test_pole.jpg}"
TEST_SPEC="${TEST_SPEC:-pg&e_greenbook_2025.pdf}"
TEST_AUDIT="${TEST_AUDIT:-qa_audit_2025.pdf}"

# Color codes for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "Using endpoint: $BASE_URL"
echo ""

# Function to check test result
check_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ $2 PASSED${NC}"
    else
        echo -e "${RED}❌ $2 FAILED${NC}"
        echo "Response: $3"
    fi
    echo ""
}

# Test 1: Health Check
echo "======================================"
echo "Test 1: Health Check - Verify YOLO Loaded"
echo "======================================"
HEALTH_RESPONSE=$(curl -s "$BASE_URL/health")
echo "Response: $HEALTH_RESPONSE"

# Check for YOLO in response
if echo "$HEALTH_RESPONSE" | grep -q '"yolo":true' || echo "$HEALTH_RESPONSE" | grep -q '"yolo": true'; then
    check_result 0 "YOLO Model Check"
    
    # Check for mAP
    if echo "$HEALTH_RESPONSE" | grep -q '"model_mAP":0.932' || echo "$HEALTH_RESPONSE" | grep -q '"mAP": 0.932'; then
        echo -e "${GREEN}✅ Custom model loaded (93.2% mAP)${NC}"
    elif echo "$HEALTH_RESPONSE" | grep -q '"model_mAP":0.7' || echo "$HEALTH_RESPONSE" | grep -q '"mAP": 0.70'; then
        echo -e "${YELLOW}⚠️ Using fallback model (70% mAP)${NC}"
    fi
else
    check_result 1 "YOLO Model Check" "$HEALTH_RESPONSE"
fi

# Test 2: Vision Detection (if image exists)
if [ -f "$TEST_IMAGE" ]; then
    echo ""
    echo "======================================"
    echo "Test 2: Vision Detection Endpoint"
    echo "======================================"
    
    VISION_RESPONSE=$(curl -s -X POST "$BASE_URL/vision/detect" \
        -H "Authorization: Bearer $TOKEN" \
        -F "image=@$TEST_IMAGE")
    
    echo "Response: $VISION_RESPONSE"
    
    # Check for detections
    if echo "$VISION_RESPONSE" | grep -q '"num_detections"'; then
        # Extract mAP value
        if echo "$VISION_RESPONSE" | grep -q '"mAP":0.932' || echo "$VISION_RESPONSE" | grep -q '"mAP": 0.932'; then
            echo -e "${GREEN}✅ Custom YOLO model active (93.2% mAP)${NC}"
        else
            echo -e "${YELLOW}⚠️ Fallback model active (check logs)${NC}"
        fi
        
        # Count detections
        NUM_DETECTIONS=$(echo "$VISION_RESPONSE" | grep -oP '"num_detections":\s*\K\d+' | head -1)
        echo "Detected $NUM_DETECTIONS objects in image"
        check_result 0 "Vision Detection"
    else
        check_result 1 "Vision Detection" "$VISION_RESPONSE"
    fi
else
    echo ""
    echo -e "${YELLOW}Skipping Test 2: No test image found at $TEST_IMAGE${NC}"
fi

# Test 3: Spec Upload (if file exists)
if [ -f "$TEST_SPEC" ]; then
    echo ""
    echo "======================================"
    echo "Test 3: Spec Book Upload & Learning"
    echo "======================================"
    
    SPEC_RESPONSE=$(curl -s -X POST "$BASE_URL/upload-specs" \
        -H "Authorization: Bearer $TOKEN" \
        -F "files=@$TEST_SPEC")
    
    echo "Response: ${SPEC_RESPONSE:0:200}..." # First 200 chars
    
    if echo "$SPEC_RESPONSE" | grep -q 'success\|processed\|learned'; then
        check_result 0 "Spec Upload"
    else
        check_result 1 "Spec Upload" "$SPEC_RESPONSE"
    fi
else
    echo ""
    echo -e "${YELLOW}Skipping Test 3: No spec file found at $TEST_SPEC${NC}"
fi

# Test 4: Audit Analysis (if file exists)
if [ -f "$TEST_AUDIT" ]; then
    echo ""
    echo "======================================"
    echo "Test 4: QA Audit Analysis"
    echo "======================================"
    
    AUDIT_RESPONSE=$(curl -s -X POST "$BASE_URL/analyze-audit" \
        -H "Authorization: Bearer $TOKEN" \
        -F "file=@$TEST_AUDIT")
    
    echo "Response: ${AUDIT_RESPONSE:0:300}..." # First 300 chars
    
    # Check for job_id or infractions
    if echo "$AUDIT_RESPONSE" | grep -q 'job_id\|infractions'; then
        check_result 0 "Audit Analysis"
        
        # If async, get job_id for polling
        JOB_ID=$(echo "$AUDIT_RESPONSE" | grep -oP '"job_id":\s*"[^"]+' | cut -d'"' -f4)
        if [ ! -z "$JOB_ID" ]; then
            echo "Job ID: $JOB_ID"
            echo "Poll status at: GET $BASE_URL/job-result/$JOB_ID"
        fi
        
        # Check if vision contributed
        if echo "$AUDIT_RESPONSE" | grep -q 'YOLO\|vision\|detected'; then
            echo -e "${GREEN}✅ Vision integration active in audit analysis${NC}"
        fi
    else
        check_result 1 "Audit Analysis" "$AUDIT_RESPONSE"
    fi
else
    echo ""
    echo -e "${YELLOW}Skipping Test 4: No audit file found at $TEST_AUDIT${NC}"
fi

# Test 5: Queue Status
echo ""
echo "======================================"
echo "Test 5: Queue Status Check"
echo "======================================"

QUEUE_RESPONSE=$(curl -s "$BASE_URL/queue-status" -H "Authorization: Bearer $TOKEN")
echo "Response: $QUEUE_RESPONSE"

if echo "$QUEUE_RESPONSE" | grep -q 'pending\|active\|completed' || [ "$?" -eq 0 ]; then
    check_result 0 "Queue Status"
else
    check_result 1 "Queue Status" "$QUEUE_RESPONSE"
fi

# Summary
echo ""
echo "======================================"
echo "  Deployment Verification Complete"
echo "======================================"
echo ""
echo "Expected Log Outputs on Render:"
echo "  ✅ DFLoss patched for compatibility"
echo "  ✅ Loaded custom YOLO model from /data/yolo_pole.pt (93.2% mAP)"
echo ""
echo "Next Steps:"
echo "  1. Add ROBOFLOW_API_KEY to Render environment"
echo "  2. Monitor logs at https://dashboard.render.com/"
echo "  3. Test with real PG&E specs and audit PDFs"
echo "  4. Consider GPU upgrade for faster embeddings"
echo ""
echo "If any tests failed, check:"
echo "  - Render build logs for errors"
echo "  - Environment variables (AUTH_TOKEN, ROBOFLOW_API_KEY)"
echo "  - File paths for test documents"
echo ""
