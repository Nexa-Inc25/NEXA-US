"""
Integration endpoints for app_oct2025_enhanced.py
Add these imports and endpoints to your main app
"""

# Add these imports to app_oct2025_enhanced.py
# PDF manipulation
from PyPDF2 import PdfReader
import pytesseract
from PIL import Image

# Computer Vision for pole detection (if available)
try:
    from vision_endpoints import vision_router
    VISION_ENABLED = True
except ImportError:
    VISION_ENABLED = False
    logger.warning("Vision endpoints not available - install ultralytics and roboflow")

import app as celery_app, analyze_audit_async
import uuid
async def analyze_audit_async_endpoint(
    file: UploadFile = File(..., description="QA audit PDF to analyze")
):
    """
    Queue audit for async analysis with full infraction detection and repeal recommendations
    Returns job_id immediately for polling
    """
    try:
        # Validate file
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(400, "Only PDF files are allowed")
        
        # Read content
        content = await file.read()
        
        if len(content) > 100 * 1024 * 1024:  # 100MB limit
            raise HTTPException(413, "File too large (max 100MB)")
        
        # Check cache first
        import hashlib
        file_hash = hashlib.sha256(content).hexdigest()[:16]
        
        # Queue async task
        from celery_worker import analyze_audit_async
        task = analyze_audit_async.delay(content, file.filename)
        
        logger.info(f"Queued async audit analysis: {task.id}")
        
        return {
            "job_id": task.id,
            "status": "queued",
            "message": f"Analysis queued for {file.filename}",
            "poll_url": f"/job-result/{task.id}"
        }
        
    except Exception as e:
        logger.error(f"Failed to queue audit: {e}")
        raise HTTPException(500, f"Failed to start analysis: {str(e)}")

@app.get("/job-result/{job_id}")
async def get_job_result(job_id: str):
    """
    Get async job results with infraction analysis and repeal recommendations
    """
    try:
        result = AsyncResult(job_id, app=celery_app)
        
        if result.state == 'PENDING':
            return {
                "job_id": job_id,
                "status": "pending",
                "message": "Job is queued, waiting for worker..."
            }
        
        elif result.state == 'FAILURE':
            return {
                "job_id": job_id,
                "status": "failed",
                "error": str(result.info) if result.info else "Unknown error"
            }
        
        elif result.state in ['EXTRACTING', 'LOADING', 'ANALYZING', 'FINALIZING']:
            # Progress updates from worker
            meta = result.info or {}
            return {
                "job_id": job_id,
                "status": "processing",
                "state": result.state.lower(),
                "progress": meta.get('progress', 0),
                "message": meta.get('status', 'Processing...')
            }
        
        elif result.state == 'SUCCESS':
            # Complete with results
            analysis = result.result
            
            # Format for easy consumption
            if analysis.get('status') == 'success':
                infractions = analysis.get('infractions', [])
                
                # Separate by confidence
                high_confidence = [i for i in infractions if i.get('confidence', 0) > 80]
                needs_review = [i for i in infractions if i.get('confidence', 0) <= 80]
                
                return {
                    "job_id": job_id,
                    "status": "complete",
                    "summary": {
                        "total_infractions": len(infractions),
                        "auto_repealable": len(high_confidence),
                        "needs_review": len(needs_review),
                        "avg_confidence": sum(i.get('confidence', 0) for i in infractions) / max(1, len(infractions))
                    },
                    "repeals": [
                        {
                            "infraction_id": i['item'],
                            "confidence": i['confidence'],
                            "reasons": [i['reason']],
                            "spec_reference": i.get('source', 'Unknown'),
                            "recommendation": "AUTO_REPEAL" if i['confidence'] > 90 else "REVIEW_RECOMMENDED"
                        }
                        for i in high_confidence
                    ],
                    "review_items": needs_review,
                    "raw_result": analysis
                }
            else:
                return {
                    "job_id": job_id,
                    "status": "failed",
                    "error": analysis.get('error', 'Analysis failed')
                }
        
        else:
            return {
                "job_id": job_id,
                "status": "unknown",
                "state": result.state
            }
            
    except Exception as e:
        logger.error(f"Error checking job {job_id}: {e}")
        return {
            "job_id": job_id,
            "status": "error",
            "error": str(e)
        }

@app.get("/queue-status")
async def get_queue_status():
    """
    Check Celery worker status and queue health
    """
    try:
        inspect = celery_app.control.inspect()
        
        # Ping workers
        active_workers = inspect.ping()
        
        # Get active tasks
        active_tasks = inspect.active()
        active_count = sum(len(tasks) for tasks in active_tasks.values()) if active_tasks else 0
        
        # Get queue stats
        stats = inspect.stats()
        
        return {
            "workers": {
                "available": bool(active_workers),
                "count": len(active_workers) if active_workers else 0,
                "ping": active_workers
            },
            "queue": {
                "active_tasks": active_count
            },
            "stats": stats if stats else {},
            "status": "healthy" if active_workers else "no_workers"
        }
        
    except Exception as e:
        logger.error(f"Queue status error: {e}")
        return {
            "workers": {"available": False, "error": str(e)},
            "status": "error"
        }

@app.post("/batch-analyze")
async def batch_analyze_audits(
    files: List[UploadFile] = File(..., description="Multiple audit PDFs")
):
    """
    Queue multiple audits for parallel processing
    """
    if len(files) > 20:
        raise HTTPException(400, "Maximum 20 files per batch")
    
    jobs = []
    
    for file in files:
        if not file.filename.lower().endswith('.pdf'):
            jobs.append({
                "filename": file.filename,
                "status": "skipped",
                "error": "Not a PDF"
            })
            continue
        
        try:
            content = await file.read()
            
            # Queue task
            from celery_worker import analyze_audit_async
            task = analyze_audit_async.delay(content, file.filename)
            
            jobs.append({
                "filename": file.filename,
                "job_id": task.id,
                "status": "queued",
                "poll_url": f"/job-result/{task.id}"
            })
            
        except Exception as e:
            jobs.append({
                "filename": file.filename,
                "status": "failed",
                "error": str(e)
            })
    
    return {
        "batch_id": str(uuid.uuid4())[:8],
        "total": len(files),
        "queued": sum(1 for j in jobs if j['status'] == 'queued'),
        "jobs": jobs
    }
