# 🚀 Deploy AI Document Analyzer to Render.com

## Quick Deployment Guide

### Step 1: Prepare Your Repository

1. **Create a GitHub repository:**
```bash
cd backend/pdf-service
git init
git add app_final.py utils.py requirements_final.txt .gitignore
git commit -m "Initial commit - AI Document Analyzer"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/ai-doc-analyzer.git
git push -u origin main
```

2. **Project structure should be:**
```
ai-doc-analyzer/
├── app_final.py           # Main Streamlit app
├── utils.py               # Helper functions
├── requirements_final.txt # Dependencies
├── .gitignore            # Ignore patterns
└── README.md             # Documentation
```

### Step 2: Set Up Render.com

1. **Sign up at [render.com](https://render.com)** (free tier works)

2. **Create New Web Service:**
   - Click "New +" → "Web Service"
   - Connect your GitHub account
   - Select your repository: `ai-doc-analyzer`

3. **Configure Build Settings:**
   - **Name**: `nexa-doc-analyzer` (or your choice)
   - **Region**: Oregon (US West) or nearest to you
   - **Branch**: `main`
   - **Root Directory**: (leave blank if app is in root)
   - **Runtime**: Python 3
   - **Build Command**:
     ```bash
     pip install -r requirements_final.txt
     ```
   - **Start Command**:
     ```bash
     streamlit run app_final.py --server.port $PORT --server.address 0.0.0.0
     ```

4. **Set Environment Variables:**
   - Click "Environment" → "Add Environment Variable"
   - Add:
     ```
     XAI_API_KEY = your-xai-api-key-here
     ```
   - Or use `GROK_API_KEY` if you prefer

5. **Choose Instance Type:**
   - **Free**: Good for testing (512 MB RAM, spins down after 15 min)
   - **Starter**: $7/month (better for production)

6. **Click "Create Web Service"**

### Step 3: Wait for Deployment

1. Render will:
   - Clone your repo
   - Install dependencies
   - Start your app
   - Provide URL: `https://nexa-doc-analyzer.onrender.com`

2. **First deployment takes 5-10 minutes**

3. **Monitor logs** in the Render dashboard

### Step 4: Test Your Deployment

1. **Access your app** at the provided URL

2. **Test workflow:**
   - Upload PG&E spec PDFs (transformer docs)
   - Click "Learn Spec Book"
   - Upload audit document
   - Click "Analyze Audit"
   - View results

### Troubleshooting

#### Memory Issues (Free Tier)
If you get memory errors with large PDFs:
```python
# In utils.py, reduce chunk size:
chunk_size=1000  # instead of 1500
```

#### Timeout Issues
Free tier spins down after 15 min. Solutions:
- Upgrade to Starter ($7/month)
- Use external service to ping every 10 min
- Accept the spin-down (takes 30s to restart)

#### Missing Dependencies
If you get import errors:
```bash
# Update requirements_final.txt to include:
langchain==0.1.0
langchain-community==0.0.10
faiss-cpu==1.7.4
```

#### API Key Issues
- Double-check XAI_API_KEY in environment variables
- No quotes needed in Render env vars
- Get key from [x.ai/api](https://x.ai/api)

### Alternative: Docker Deployment

Create `Dockerfile`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y build-essential

# Copy and install requirements
COPY requirements_final.txt .
RUN pip install --no-cache-dir -r requirements_final.txt

# Copy app files
COPY app_final.py utils.py ./

# Create data directory
RUN mkdir -p data

EXPOSE 8501

CMD ["streamlit", "run", "app_final.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

Then on Render:
- Choose "Docker" runtime instead of Python
- Render will build and deploy automatically

### Production Considerations

1. **Scaling:**
   - Upgrade to Starter/Standard for more RAM
   - Use Redis for caching (Render Redis addon)
   - Implement async processing for large files

2. **Security:**
   - Add authentication (Streamlit-Authenticator)
   - Use secrets manager for API keys
   - Enable HTTPS (automatic on Render)

3. **Performance:**
   - Pre-build spec index locally, upload to S3
   - Use CDN for static assets
   - Implement progress bars for long operations

4. **Monitoring:**
   - Set up alerts in Render dashboard
   - Use logging service (Papertrail, Logtail)
   - Track API usage and costs

### Cost Optimization

**Free Tier Limits:**
- 750 hours/month
- 512 MB RAM
- Spins down after 15 min
- Good for: demos, testing

**Paid Options:**
- Starter: $7/month (always on, 512 MB)
- Standard: $25/month (2 GB RAM)
- Pro: $85/month (4 GB RAM)

**xAI API Costs:**
- ~$0.05 per analysis
- 500 analyses = $25/month
- Implement caching to reduce

### Example GitHub Actions for Auto-Deploy

Create `.github/workflows/deploy.yml`:
```yaml
name: Deploy to Render

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Deploy to Render
        env:
          deploy_url: ${{ secrets.RENDER_DEPLOY_HOOK_URL }}
        run: |
          curl "$deploy_url"
```

Get deploy hook URL from Render dashboard → Settings → Deploy Hook

### Support

- **Render Docs**: [render.com/docs](https://render.com/docs)
- **Streamlit Deployment**: [docs.streamlit.io/deploy](https://docs.streamlit.io/deploy)
- **xAI API**: [x.ai/api](https://x.ai/api)

### Next Steps

1. **Deploy to production**
2. **Add custom domain** (Render settings)
3. **Set up monitoring**
4. **Implement user authentication**
5. **Add more utilities** (SCE, SDG&E)
6. **Create landing page**

---

**Ready to deploy?** Your app is tested locally and ready for Render.com!

Access locally at: http://localhost:8506
Will be available at: https://your-app.onrender.com
