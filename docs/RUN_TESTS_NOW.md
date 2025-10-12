# 🚀 RUN THESE TESTS RIGHT NOW

## Quick Test #1: Is Backend Alive?
```bash
curl https://nexa-doc-analyzer-oct2025.onrender.com/health
```

✅ **Should return**: `{"status":"healthy"}`

---

## Quick Test #2: Start GF Dashboard
```bash
cd c:\Users\mikev\CascadeProjects\nexa-inc-mvp\nexa-core\apps\web
npm start
```

Then open browser to `http://localhost:3000`
- Login: `general_foreman` / `password`
- ✅ **Should see**: Job list dashboard

---

## Quick Test #3: Start Foreman Mobile
```bash
cd c:\Users\mikev\CascadeProjects\nexa-inc-mvp\nexa-core\apps\mobile
npx expo start
```

Press `w` for web browser
- Login: `foreman` / `password`  
- ✅ **Should see**: 4 tabs (Dashboard, Upload, Results, Sync)

---

## Quick Test #4: Upload Test Spec
```bash
# Create a test PDF first
echo "Test spec content" > test.txt
# Convert to PDF (or use any PDF you have)

# Upload it
curl -X POST https://nexa-doc-analyzer-oct2025.onrender.com/upload-specs \
  -F "files=@any_pdf_you_have.pdf"
```

✅ **Should return**: Spec upload confirmation

---

## Quick Test #5: Full Workflow Test
Run the PowerShell test script:
```powershell
.\test_workflow.ps1
```

✅ **Should show**: All green checkmarks

---

## 🔴 IF ANYTHING FAILS:

### Backend Down (502 error)?
```bash
# Check Render logs
# https://dashboard.render.com

# Quick fix - restart service:
# Click "Manual Deploy" > "Deploy latest commit"
```

### Dashboard Won't Start?
```bash
# Clear and reinstall
rm -rf node_modules package-lock.json
npm install
npm start
```

### Mobile App Errors?
```bash
# Clear Expo cache
npx expo start -c
```

---

## 🎯 THE CONCRETE TEST

### Upload Real PG&E Spec:
```bash
curl -X POST https://nexa-doc-analyzer-oct2025.onrender.com/upload-specs \
  -F "files=@PGE_greenbook.pdf"
```

### Analyze Real Audit:
```bash
curl -X POST https://nexa-doc-analyzer-oct2025.onrender.com/analyze-audit \
  -F "file=@real_audit.pdf"
```

### Expected Result:
```json
{
  "infractions": [
    {
      "type": "crossarm_violation",
      "repealable": true,
      "confidence": 0.85,
      "reason": "Per Section 3.2 Grade B variance allowed",
      "savings": 14000
    }
  ]
}
```

---

## ✅ WHEN ALL TESTS PASS:

You have a **rock-solid system** ready for:
- PM uploads ✓
- GF scheduling ✓
- Foreman field photos ✓
- YOLO go-back detection ✓
- AI spec cross-reference ✓
- Repeal analysis with savings ✓
- QA approval ✓
- PG&E submission ✓

**Start charging $200/month!** 💰
