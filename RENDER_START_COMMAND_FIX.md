# 🚨 Fix "File does not exist: ui_enhanced.py" Error

## The Problem
Render is running a **custom start command** from the dashboard that's looking for `ui_enhanced.py` in the wrong directory.

Error:
```
Error: Invalid value: File does not exist: ui_enhanced.py
```

## ✅ Good News
The `StreamlitAPIException` is **GONE**! This is a simpler path issue.

## 🔧 The Fix (Choose One)

### Option 1: Use render.yaml (RECOMMENDED)
I've updated `render.yaml` to use `Dockerfile.streamlit` which has the correct paths built-in.

**Action:** Just push the changes and Render will auto-deploy with the correct configuration.

### Option 2: Fix Start Command in Dashboard

If you need to manually fix it in Render Dashboard:

1. **Go to:** https://dashboard.render.com
2. **Click:** `nexa-ui` service (or `nexa-ai-analyzer-python`)
3. **Settings Tab** → **Build & Deploy**
4. **Start Command:** Update to:
   ```bash
   cd /app/backend/pdf-service && streamlit run ui_enhanced.py --server.port $PORT --server.address 0.0.0.0 --server.headless true --server.fileWatcherType none
   ```
   
   OR leave it **blank** to use the Dockerfile CMD (recommended)

5. **Docker File Path:** Ensure it's set to `./Dockerfile.streamlit`
6. **Save Changes**

## 📦 What I Fixed

1. **render.yaml** - Changed from `./Dockerfile` to `./Dockerfile.streamlit` ✅
2. **PostgreSQL version** - Fixed lint error (string instead of number) ✅

## 🎯 Current File Structure

```
/app/                           ← Docker WORKDIR
└── backend/
    └── pdf-service/
        ├── ui_enhanced.py      ← Your Streamlit app
        ├── ui.py
        ├── api.py
        └── requirements.txt
```

The Dockerfile sets `WORKDIR /app/backend/pdf-service` so the command `streamlit run ui_enhanced.py` works correctly.

## 🚀 Next Steps

1. **Push this commit** (render.yaml updated)
2. **Render auto-deploys** with correct Dockerfile
3. **Service should start successfully**

## 📊 Expected Success Log

After fix, you should see:
```
==> Running CMD from Dockerfile.streamlit
  You can now view your Streamlit app in your browser.
  Network URL: http://0.0.0.0:8501
==> Your service is live 🎉
```

---

**The Streamlit error is FIXED! This is just a path issue that render.yaml will resolve! 🎉**
