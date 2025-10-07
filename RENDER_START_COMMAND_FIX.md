# 🚨 Fix "cd: /app/backend/pdf-service: No such file or directory" Error

## The Problem
Render is running a **custom start command** from the dashboard that's trying to cd to a directory that doesn't exist.

Error:
```
bash: line 1: cd: /app/backend/pdf-service: No such file or directory
```

## Root Cause
The **Start Command field in Render Dashboard is set** and overriding the Dockerfile's CMD. This custom command includes `cd /app/backend/pdf-service` but this path doesn't match the actual container structure.

## ✅ THE FIX - USE CORRECT START COMMAND

**Update the Start Command in Render Dashboard (without the cd):**

1. **Go to:** https://dashboard.render.com
2. **Click:** `nexa-ui` service
3. **Settings Tab** → **Build & Deploy** section
4. **Start Command:** Replace with this exact command (NO cd):
   
   **WRONG** (Current):
   ```bash
   cd /app/backend/pdf-service && streamlit run ui_enhanced.py --server.port $PORT --server.address 0.0.0.0 --server.headless true --server.fileWatcherType none
   ```
   
   **CORRECT** (Use this):
   ```bash
   streamlit run ui_enhanced.py --server.port $PORT --server.address 0.0.0.0 --server.headless true --server.fileWatcherType none --server.runOnSave false
   ```

5. **Docker File Path:** Ensure it's set to `./Dockerfile.streamlit`
6. **Click "Save Changes"**
7. **Manually trigger a redeploy** (Deploy button)

## Why This Happens

When you manually set a Start Command in Render's dashboard, it **completely overrides** the Dockerfile's CMD. The custom command was trying to navigate to a path before the container's working directory was properly set.

## Why Removing `cd` Works

The `Dockerfile.streamlit` already sets the working directory correctly:

```dockerfile
WORKDIR /app                              # Sets initial directory
COPY backend/pdf-service ...              # Copies files to /app/backend/pdf-service
WORKDIR /app/backend/pdf-service          # Changes to the service directory
CMD ["sh", "-c", "streamlit run ..."]     # Runs from correct directory
```

The Dockerfile's `WORKDIR /app/backend/pdf-service` (line 38) means the container **already starts** in the correct directory. Adding `cd /app/backend/pdf-service` tries to navigate to a path that doesn't exist yet.

## 🚀 Next Steps

### Step 1: Update the Start Command (NOW)
1. Go to Render Dashboard → nexa-ui service
2. Settings → Build & Deploy
3. Replace Start Command with:
   ```bash
   streamlit run ui_enhanced.py --server.port $PORT --server.address 0.0.0.0 --server.headless true --server.fileWatcherType none --server.runOnSave false
   ```
4. Save Changes
5. Click "Manual Deploy" → "Deploy latest commit"

### Step 2: Monitor Logs
After redeploying, you should see:
```
==> Running: sh -c streamlit run ui_enhanced.py --server.port $PORT ...
  You can now view your Streamlit app in your browser.
  Network URL: http://0.0.0.0:10000
==> Your service is live 🎉
```

## 📦 Files Updated

1. **render.yaml** - Uses `./Dockerfile.streamlit` ✅
2. **Dockerfile.streamlit** - Has correct CMD and WORKDIR ✅

---

**ACTION REQUIRED: Update the Start Command in Render Dashboard - remove the `cd` part and use only the streamlit command!**
