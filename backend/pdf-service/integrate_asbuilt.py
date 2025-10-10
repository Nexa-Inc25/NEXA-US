"""
Integration code to add PG&E as-built processing to app_oct2025_enhanced.py

INSTRUCTIONS:
1. Copy the imports to the top of app_oct2025_enhanced.py
2. Add the router inclusion after creating the FastAPI app
3. Ensure celery_worker.py imports the tasks
"""

# ============================================
# ADD THESE IMPORTS TO app_oct2025_enhanced.py
# ============================================
"""
from fastapi import APIRouter
from asbuilt_endpoints import asbuilt_router
import PyPDF2  # Already in requirements_oct2025.txt
"""

# ============================================
# ADD THIS AFTER CREATING FASTAPI APP
# ============================================
"""
# In app_oct2025_enhanced.py, after:
# app = FastAPI(title="NEXA Document Analyzer", version="2.0")

# Add this line:
app.include_router(asbuilt_router)
"""

# ============================================
# UPDATE celery_worker.py
# ============================================
"""
# At the top of celery_worker.py, add:
from asbuilt_tasks import (
    fill_asbuilt_async,
    batch_asbuilt_async,
    extract_procedure_rules_async,
    update_mat_prices_async
)
"""

# ============================================
# ALTERNATIVE: Direct Integration
# ============================================
# If you prefer to add endpoints directly to app_oct2025_enhanced.py
# instead of using a router, copy this code:

def add_asbuilt_endpoints_directly(app):
    """
    Add this function to app_oct2025_enhanced.py and call it after creating app
    """
    from fastapi import File, UploadFile, HTTPException, Form
    from typing import List, Optional
    import json
    import base64
    from celery.result import AsyncResult
    
    @app.post("/asbuilt/fill-async")
    async def fill_asbuilt(
        file: UploadFile = File(...),
        pm_number: str = Form(...),
        notification_number: str = Form(...),
        work_type: Optional[str] = Form(None),
        photos: Optional[List[UploadFile]] = File(None)
    ):
        """Fill as-built per PG&E procedures"""
        try:
            if not file.filename.lower().endswith('.pdf'):
                raise HTTPException(400, "Only PDF files allowed")
            
            pdf_content = await file.read()
            
            job_data = {
                'pm_number': pm_number,
                'notification_number': notification_number,
                'work_type': work_type,
                'filename': file.filename
            }
            
            # Import task
            from asbuilt_tasks import fill_asbuilt_async
            task = fill_asbuilt_async.delay(pdf_content, job_data, [])
            
            return {
                'job_id': task.id,
                'status': 'queued',
                'message': f'Processing PM {pm_number}',
                'poll_url': f'/asbuilt/result/{task.id}'
            }
            
        except Exception as e:
            raise HTTPException(500, str(e))
    
    @app.get("/asbuilt/result/{job_id}")
    async def get_asbuilt_result(job_id: str):
        """Get processing result"""
        try:
            result = AsyncResult(job_id, app=celery_app)
            
            if result.state == 'PENDING':
                return {'status': 'pending'}
            elif result.state == 'SUCCESS':
                return {'status': 'complete', 'result': result.result}
            elif result.state == 'FAILURE':
                return {'status': 'failed', 'error': str(result.info)}
            else:
                return {'status': result.state.lower()}
                
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    # Add more endpoints as needed...

# ============================================
# DEPLOYMENT COMMANDS
# ============================================
"""
# After making changes:
git add .
git commit -m "Add PG&E as-built intelligent processing"
git push origin main

# Render will auto-deploy in 3-5 minutes
# Monitor at: https://dashboard.render.com
"""

# ============================================
# TESTING COMMANDS
# ============================================
"""
# Test locally first:
cd backend/pdf-service
python -m pytest test_asbuilt.py

# Test on production:
curl -X POST https://nexa-doc-analyzer-oct2025.onrender.com/asbuilt/fill-async \
  -F "file=@sample_asbuilt.pdf" \
  -F "pm_number=07D" \
  -F "notification_number=12345"

# Check result:
curl https://nexa-doc-analyzer-oct2025.onrender.com/asbuilt/result/{job_id}
"""
