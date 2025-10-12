# THE ACTUAL FUCKING WORKFLOW - GET IT RIGHT!

## 📋 STEP BY STEP - NO MORE CONFUSION

### 1️⃣ **PM UPLOADS JOB PACKAGE** 
```
PM → Uploads job package PDF
NEXA → Verifies:
  - ✅ Permits included
  - ✅ All required documents present
  - ✅ Compliance check
```

### 2️⃣ **PM ASSIGNS TO GF**
```
PM → Assigns job to General Foreman
GF → Receives job for pre-fielding
```

### 3️⃣ **GF PRE-FIELDS & SCHEDULES**
```
GF → Pre-fields the job:
  - Checks site conditions
  - Identifies dependencies
  - Schedules on crew calendar
  - Assigns to specific Foreman
```

### 4️⃣ **FOREMAN DOES THE WORK**
```
Foreman → Goes on-site
  - Pole replacement OR
  - Crossarm replacement OR
  - Other utility work
Foreman → Completes physical work
```

### 5️⃣ **FOREMAN TAKES PHOTOS**
```
Foreman → Takes completion photos
  - Before/after shots
  - Close-ups of work
  - Overall site photos
```

### 6️⃣ **NEXA CHECKS FOR INFRACTIONS**
```
NEXA → Analyzes photos with YOLO:
  - ✅ No infractions = PROCEED
  - ❌ Infractions found = FIX & RETAKE
```

### 7️⃣ **JOB GOES TO QA**
```
If photos clear:
  Job → Moves to QA queue
  NEXA → Auto-fills package to PG&E spec
```

### 8️⃣ **QA REVIEWS**
```
QA → Reviews NEXA-filled package:
  - Accuracy check
  - Spec compliance
  - Documentation complete
```

### 9️⃣ **QA SUBMITS TO PG&E**
```
QA → Final approval
NEXA → Submits to PG&E portal
Status → COMPLETE
```

---

## 🔥 THIS IS THE FLOW - NOTHING ELSE!

No spec learning bullshit during job flow. The specs are ALREADY LEARNED. This is about:
1. **Job packages** (not spec books)
2. **Permit verification** (not learning)
3. **Photo infractions** (not audit analysis)
4. **PG&E submission** (the end goal)

---

## API ENDPOINTS FOR THIS WORKFLOW:

```bash
# 1. PM uploads job package
POST /upload-job-package
Body: { file: job_package.pdf }
Returns: { job_id, permits_valid, documents_complete }

# 2. PM assigns to GF
POST /assign-job
Body: { job_id, gf_id }

# 3. GF pre-fields and schedules
POST /prefield-job
Body: { job_id, site_conditions, dependencies, scheduled_date, foreman_id }

# 4-5. Foreman completes and uploads photos
POST /complete-job
Body: { job_id, photos: [photo1.jpg, photo2.jpg] }

# 6. NEXA checks infractions
Response: { infractions_found, infraction_details, status: "clear" or "needs_fix" }

# 7-8. QA reviews
POST /qa-review
Body: { job_id, approved: true }

# 9. Submit to PG&E
POST /submit-to-pge
Body: { job_id }
```

---

## THIS IS IT. THIS IS THE WORKFLOW. PERIOD.
