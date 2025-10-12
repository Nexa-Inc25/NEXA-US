# 🧪 NEXA Complete Testing Suite
## Test Every Component Until It's Bulletproof

---

## 📋 Workflow Overview
```
PM Upload → GF Schedule → Foreman Field → YOLO Check → AI Fill → QA Review → PG&E Submit
```

---

## PART 1: GF Dashboard (Web) Testing

### 🖥️ Local Setup & Test
```bash
# Navigate to web app
cd c:\Users\mikev\CascadeProjects\nexa-inc-mvp\nexa-core\apps\web

# Install dependencies
npm install

# Start local server
npm start
```

### Expected Results:
- Browser opens at `http://localhost:3000`
- Login screen appears
- Use credentials: `general_foreman` / `password`

### Test Checklist:
- [ ] Login works
- [ ] Dashboard shows total audits count
- [ ] Savings summary displays correctly
- [ ] Job list populates (even with mock data)
- [ ] Assign job to crew works
- [ ] Schedule date picker functions
- [ ] Filters work (pending/assigned/completed)

### Common Issues & Fixes:
```bash
# If TypeScript errors
npm update @types/react @types/react-dom

# If port 3000 busy
PORT=3001 npm start

# If module not found
rm -rf node_modules package-lock.json
npm install
```

---

## PART 2: Foreman Mobile Dashboard Testing

### 📱 Local Setup & Test
```bash
# Navigate to mobile app
cd c:\Users\mikev\CascadeProjects\nexa-inc-mvp\nexa-core\apps\mobile

# Install dependencies
npm install

# Start Expo
npx expo start
```

### Test Methods:
1. **Physical Device**: Scan QR with Expo Go app
2. **Android Emulator**: Press 'a' 
3. **iOS Simulator**: Press 'i' (Mac only)
4. **Web Browser**: Press 'w' (limited features)

### Login Credentials:
- Username: `foreman`
- Password: `password`

### Test Each Tab:
#### Dashboard Tab ✓
- [ ] Total savings displays
- [ ] Repealable count shows
- [ ] Recent jobs list loads
- [ ] Pull-to-refresh works

#### Upload Tab ✓
- [ ] QR scanner opens camera
- [ ] Can scan job QR code
- [ ] Photo capture works
- [ ] YOLO detection shows results
- [ ] "Go-back detected" warning appears
- [ ] Submit button uploads to backend

#### Results Tab ✓
- [ ] Infractions list loads
- [ ] Repealable items show green
- [ ] True infractions show red
- [ ] Confidence percentages display
- [ ] Cost savings calculate correctly
- [ ] Tap for detail view works

#### Sync Tab ✓
- [ ] Shows offline queue count
- [ ] Manual sync button works
- [ ] Auto-sync on reconnect works

### Offline Testing:
```bash
# Test offline capability
1. Enable airplane mode
2. Take photos and submit
3. Check sync queue shows pending
4. Disable airplane mode
5. Verify auto-sync completes
```

---

## PART 3: End-to-End Backend Testing

### 🚀 Live API Tests (https://nexa-doc-analyzer-oct2025.onrender.com)

### Test 1: Upload Spec Book
```bash
# Upload PG&E Greenbook for learning
curl -X POST https://nexa-doc-analyzer-oct2025.onrender.com/upload-specs \
  -F "files=@greenbook.pdf" \
  -F "mode=append"

# Verify spec library
curl https://nexa-doc-analyzer-oct2025.onrender.com/spec-library
```

**Expected Response:**
```json
{
  "total_files": 1,
  "total_chunks": 10000,
  "files": ["greenbook.pdf"]
}
```

### Test 2: PM Upload Job Package
```bash
# Create test job
curl -X POST https://nexa-doc-analyzer-oct2025.onrender.com/analyze-audit \
  -F "file=@test_package.pdf"
```

**Expected Response:**
```json
{
  "job_id": "abc-123",
  "pm_number": "PM-2024-001",
  "initial_analysis": {
    "total_infractions": 5,
    "repealable": 2,
    "confidence_avg": 0.85,
    "estimated_savings": 14000
  }
}
```

### Test 3: Foreman Field Submission
```bash
# Submit field photos with YOLO
curl -X POST https://nexa-doc-analyzer-oct2025.onrender.com/vision/detect-pole \
  -F "file=@pole_photo.jpg"
```

**Expected YOLO Response:**
```json
{
  "detections": [
    {
      "type": "pole",
      "confidence": 0.92,
      "classification": "Type 3",
      "go_back_detected": true,
      "reason": "Crossarm angle violation"
    }
  ]
}
```

### Test 4: Cross-Reference Analysis
```bash
# Analyze against learned specs
curl -X POST https://nexa-doc-analyzer-oct2025.onrender.com/analyze-audit \
  -F "file=@field_photos.zip" \
  -H "X-Job-ID: abc-123"
```

**Expected Repeal Analysis:**
```json
{
  "infractions": [
    {
      "id": "INF-001",
      "type": "crossarm_angle",
      "status": "REPEALABLE",
      "confidence": 0.85,
      "reasons": [
        "Per SECTION 3.2: Grade B construction allows variance",
        "Greenbook Table 4-1: Acceptable for pre-2020 installation"
      ],
      "cost_impact": {
        "labor_saved": 8000,
        "equipment_saved": 6000,
        "total_savings": 14000
      }
    }
  ]
}
```

### Test 5: QA Review & Submit
```bash
# QA approval
curl -X POST https://nexa-doc-analyzer-oct2025.onrender.com/qa-review \
  -d '{"job_id": "abc-123", "approved": true}' \
  -H "Content-Type: application/json"
```

**Expected:**
```json
{
  "status": "approved",
  "pge_submission": "queued",
  "email_sent": true
}
```

---

## 🔄 Reliability Test Loop

### Automated Test Script
```bash
#!/bin/bash
# test_reliability.sh

echo "🧪 Running reliability tests..."

# Test 30 iterations
for i in {1..30}
do
  echo "Test iteration $i/30"
  
  # Upload different test files
  TEST_FILE="test_package_$((i % 5)).pdf"
  
  # Time the analysis
  START=$(date +%s)
  
  # Run full workflow
  RESPONSE=$(curl -s -X POST https://nexa-doc-analyzer-oct2025.onrender.com/analyze-audit \
    -F "file=@$TEST_FILE")
  
  END=$(date +%s)
  DURATION=$((END - START))
  
  # Check response
  if echo "$RESPONSE" | grep -q "error"; then
    echo "❌ Test $i FAILED"
    echo "$RESPONSE"
  else
    echo "✅ Test $i passed in ${DURATION}s"
  fi
  
  # Random delay to simulate real usage
  sleep $((RANDOM % 3))
done

echo "✅ Reliability test complete!"
```

---

## 📊 Performance Benchmarks

| Operation | Target Time | Acceptable | Failed |
|-----------|------------|------------|--------|
| Spec Upload | <30s | <60s | >60s |
| Job Analysis | <1s | <2s | >2s |
| YOLO Detection | <500ms | <1s | >1s |
| PDF Generation | <2s | <5s | >5s |
| Full Workflow | <10s | <20s | >20s |

---

## 🐛 Debug Checklist

### If GF Dashboard Not Showing:
```bash
# Check backend connection
curl https://nexa-doc-analyzer-oct2025.onrender.com/health

# Check CORS settings
# In app_oct2025_enhanced.py, ensure:
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Check API endpoint
curl http://localhost:8000/get-audits
```

### If Mobile App Crashes:
```bash
# Clear cache
npx expo start -c

# Check dependencies
npm list expo-camera expo-barcode-scanner

# Rebuild
npx expo run:android
```

### If YOLO Not Detecting:
```python
# Test vision endpoint directly
import requests

with open("test_pole.jpg", "rb") as f:
    response = requests.post(
        "https://nexa-doc-analyzer-oct2025.onrender.com/vision/detect-pole",
        files={"file": f}
    )
    print(response.json())
```

---

## ✅ Validation Criteria

Before declaring "rock-solid":

1. **Reliability**: 30 consecutive tests pass
2. **Performance**: All operations under target time
3. **Offline**: Mobile works without connection
4. **Concurrency**: 5 simultaneous uploads work
5. **Error Handling**: Graceful failures with clear messages
6. **Data Integrity**: No data loss across workflow

---

## 📈 Load Testing

```python
# load_test.py
import concurrent.futures
import requests
import time

def test_upload(i):
    """Test single upload"""
    start = time.time()
    response = requests.post(
        "https://nexa-doc-analyzer-oct2025.onrender.com/analyze-audit",
        files={"file": open(f"test_{i%3}.pdf", "rb")}
    )
    duration = time.time() - start
    return response.status_code == 200, duration

# Run 20 concurrent uploads
with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
    futures = [executor.submit(test_upload, i) for i in range(20)]
    results = [f.result() for f in concurrent.futures.as_completed(futures)]
    
    successes = sum(1 for success, _ in results if success)
    avg_time = sum(duration for _, duration in results) / len(results)
    
    print(f"✅ Success rate: {successes}/20")
    print(f"⏱️ Average time: {avg_time:.2f}s")
```

---

## 🎯 Next Steps After Testing

Once all tests pass:

1. **Add SendGrid** for PG&E email submission
2. **Deploy dashboards** to production
3. **Set up monitoring** (UptimeRobot)
4. **Create user accounts** for first customers
5. **Start billing** at $200/month!

---

**LET'S TEST THE SHIT OUT OF THIS!** 🚀
