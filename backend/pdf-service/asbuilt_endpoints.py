"""
API Endpoints for PG&E As-Built Processing
Add these to app_oct2025_enhanced.py
"""
from fastapi import APIRouter, File, UploadFile, HTTPException, Form
from typing import List, Optional, Dict
import json
import base64
from celery.result import AsyncResult
from asbuilt_tasks import (
    fill_asbuilt_async,
    batch_asbuilt_async,
    extract_procedure_rules_async,
    update_mat_prices_async
)

# Create router for as-built endpoints
asbuilt_router = APIRouter(prefix="/asbuilt", tags=["PG&E As-Built"])

@asbuilt_router.post("/fill-async")
async def fill_asbuilt_endpoint(
    file: UploadFile = File(..., description="As-built PDF to fill"),
    pm_number: str = Form(..., description="PM Number"),
    notification_number: str = Form(..., description="Notification Number"),
    work_type: Optional[str] = Form(None, description="Work type (optional)"),
    photos: Optional[List[UploadFile]] = File(None, description="Field photos")
):
    """
    Fill a single as-built according to PG&E procedures
    Returns job_id for async processing
    """
    try:
        # Validate PDF
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(400, "Only PDF files allowed")
        
        # Read PDF content
        pdf_content = await file.read()
        if len(pdf_content) > 50 * 1024 * 1024:  # 50MB limit
            raise HTTPException(413, "File too large (max 50MB)")
        
        # Process photos if provided
        photo_paths = []
        if photos:
            for photo in photos:
                if photo.filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                    photo_paths.append(photo.filename)
        
        # Prepare job data
        job_data = {
            'pm_number': pm_number,
            'notification_number': notification_number,
            'work_type': work_type,
            'filename': file.filename
        }
        
        # Queue async task
        task = fill_asbuilt_async.delay(pdf_content, job_data, photo_paths)
        
        return {
            'job_id': task.id,
            'status': 'queued',
            'message': f'As-built processing queued for PM {pm_number}',
            'poll_url': f'/asbuilt/result/{task.id}'
        }
        
    except Exception as e:
        raise HTTPException(500, f"Failed to queue as-built: {str(e)}")


@asbuilt_router.post("/batch-fill")
async def batch_fill_asbuilts(
    files: List[UploadFile] = File(..., description="Multiple as-built PDFs"),
    job_data_json: str = Form(..., description="JSON array of job data")
):
    """
    Process multiple as-builts in batch
    job_data_json should be array matching files order
    """
    try:
        # Parse job data
        job_data_list = json.loads(job_data_json)
        
        if len(files) != len(job_data_list):
            raise HTTPException(400, "Number of files must match job data entries")
        
        if len(files) > 20:
            raise HTTPException(400, "Maximum 20 files per batch")
        
        # Prepare batch data
        batch_data = []
        for idx, file in enumerate(files):
            if not file.filename.lower().endswith('.pdf'):
                continue
            
            pdf_content = await file.read()
            
            batch_data.append({
                'pdf_content': base64.b64encode(pdf_content).decode('utf-8'),
                'job_data': job_data_list[idx],
                'photos': []  # TODO: Handle photos in batch
            })
        
        # Queue batch task
        task = batch_asbuilt_async.delay(batch_data)
        
        return {
            'batch_id': task.id,
            'status': 'queued',
            'total_files': len(batch_data),
            'message': f'Batch processing queued for {len(batch_data)} as-builts',
            'poll_url': f'/asbuilt/batch-result/{task.id}'
        }
        
    except json.JSONDecodeError:
        raise HTTPException(400, "Invalid job_data_json format")
    except Exception as e:
        raise HTTPException(500, f"Failed to queue batch: {str(e)}")


@asbuilt_router.get("/result/{job_id}")
async def get_asbuilt_result(job_id: str):
    """
    Get async as-built processing result
    """
    try:
        from celery_worker import app as celery_app
        result = AsyncResult(job_id, app=celery_app)
        
        if result.state == 'PENDING':
            return {
                'job_id': job_id,
                'status': 'pending',
                'message': 'Job queued, waiting for worker...'
            }
        
        elif result.state in ['PROCESSING', 'ANALYZING', 'ANNOTATING', 'FINALIZING']:
            meta = result.info or {}
            return {
                'job_id': job_id,
                'status': 'processing',
                'state': result.state.lower(),
                'progress': meta.get('progress', 0),
                'message': meta.get('status', 'Processing...')
            }
        
        elif result.state == 'SUCCESS':
            data = result.result
            
            # Don't return the full PDF in status check
            if 'annotated_pdf' in data:
                pdf_size = len(data['annotated_pdf'])
                data['annotated_pdf_size'] = pdf_size
                data['download_url'] = f'/asbuilt/download/{job_id}'
                del data['annotated_pdf']  # Remove from response
            
            return {
                'job_id': job_id,
                'status': 'complete',
                'result': data
            }
        
        elif result.state == 'FAILURE':
            return {
                'job_id': job_id,
                'status': 'failed',
                'error': str(result.info) if result.info else 'Unknown error'
            }
        
        else:
            return {
                'job_id': job_id,
                'status': 'unknown',
                'state': result.state
            }
            
    except Exception as e:
        return {
            'job_id': job_id,
            'status': 'error',
            'error': str(e)
        }


@asbuilt_router.get("/batch-result/{batch_id}")
async def get_batch_result(batch_id: str):
    """
    Get batch processing result
    """
    try:
        from celery_worker import app as celery_app
        result = AsyncResult(batch_id, app=celery_app)
        
        if result.state == 'PENDING':
            return {
                'batch_id': batch_id,
                'status': 'pending'
            }
        
        elif result.state == 'BATCH_PROCESSING':
            meta = result.info or {}
            return {
                'batch_id': batch_id,
                'status': 'processing',
                'progress': meta.get('progress', 0),
                'current': meta.get('current', 'Unknown')
            }
        
        elif result.state == 'SUCCESS':
            data = result.result
            
            # Prepare download links
            for r in data.get('results', []):
                if 'result' in r and 'annotated_pdf' in r['result']:
                    r['result']['download_url'] = f'/asbuilt/download-batch/{batch_id}/{r["job_id"]}'
                    del r['result']['annotated_pdf']
            
            return {
                'batch_id': batch_id,
                'status': 'complete',
                'summary': data.get('batch_summary', {}),
                'results': data.get('results', []),
                'errors': data.get('errors', [])
            }
        
        elif result.state == 'FAILURE':
            return {
                'batch_id': batch_id,
                'status': 'failed',
                'error': str(result.info)
            }
        
        else:
            return {
                'batch_id': batch_id,
                'status': result.state.lower()
            }
            
    except Exception as e:
        return {
            'batch_id': batch_id,
            'status': 'error',
            'error': str(e)
        }


@asbuilt_router.get("/download/{job_id}")
async def download_asbuilt(job_id: str):
    """
    Download the annotated as-built PDF
    """
    try:
        from fastapi.responses import Response
        from celery_worker import app as celery_app
        
        result = AsyncResult(job_id, app=celery_app)
        
        if result.state != 'SUCCESS':
            raise HTTPException(404, "Result not ready or failed")
        
        data = result.result
        if 'annotated_pdf' not in data:
            raise HTTPException(404, "Annotated PDF not found")
        
        # Decode base64 PDF
        pdf_bytes = base64.b64decode(data['annotated_pdf'])
        
        return Response(
            content=pdf_bytes,
            media_type='application/pdf',
            headers={
                'Content-Disposition': f'attachment; filename="asbuilt_{job_id}.pdf"'
            }
        )
        
    except Exception as e:
        raise HTTPException(500, f"Download error: {str(e)}")


@asbuilt_router.post("/update-mat-prices")
async def update_material_prices(
    file: UploadFile = File(..., description="CSV or JSON file with material prices")
):
    """
    Update material prices database
    Expected format: {"code": price, ...} or CSV with code,price columns
    """
    try:
        content = await file.read()
        
        # Parse based on file type
        if file.filename.lower().endswith('.json'):
            prices_data = json.loads(content)
        elif file.filename.lower().endswith('.csv'):
            # Simple CSV parsing
            import csv
            import io
            prices_data = {}
            reader = csv.reader(io.StringIO(content.decode('utf-8')))
            next(reader)  # Skip header
            for row in reader:
                if len(row) >= 2:
                    prices_data[row[0]] = float(row[1])
        else:
            raise HTTPException(400, "Only JSON or CSV files accepted")
        
        # Queue update task
        task = update_mat_prices_async.delay(prices_data)
        
        return {
            'status': 'queued',
            'task_id': task.id,
            'prices_count': len(prices_data),
            'message': f'Updating {len(prices_data)} material prices'
        }
        
    except json.JSONDecodeError:
        raise HTTPException(400, "Invalid JSON format")
    except ValueError as e:
        raise HTTPException(400, f"Invalid price data: {str(e)}")
    except Exception as e:
        raise HTTPException(500, f"Failed to update prices: {str(e)}")


@asbuilt_router.post("/learn-procedure")
async def learn_from_procedure(
    file: UploadFile = File(..., description="PG&E procedure PDF to learn from")
):
    """
    Extract and learn rules from PG&E procedure PDF
    This should be done once when uploading the procedure document
    Handles: Main procedure, Document ordering, Pole types PDFs
    """
    try:
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(400, "Only PDF files allowed")
        
        # Extract text from PDF
        import PyPDF2
        import io
        
        content = await file.read()
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(content))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        
        # Detect PDF type from filename
        pdf_type = "general"
        if "document order" in file.filename.lower():
            pdf_type = "document_order"
        elif "pole type" in file.filename.lower():
            pdf_type = "pole_types"
        
        # Queue extraction task with filename for type detection
        task = extract_procedure_rules_async.delay(text, file.filename)
        
        return {
            'status': 'queued',
            'task_id': task.id,
            'message': f'Extracting {pdf_type} rules from {file.filename}',
            'filename': file.filename,
            'pdf_type': pdf_type
        }
        
    except Exception as e:
        raise HTTPException(500, f"Failed to process procedure: {str(e)}")


@asbuilt_router.get("/compliance-check/{job_id}")
async def check_compliance(job_id: str):
    """
    Quick compliance check for a processed as-built
    """
    try:
        from celery_worker import app as celery_app
        result = AsyncResult(job_id, app=celery_app)
        
        if result.state != 'SUCCESS':
            raise HTTPException(404, "Result not ready")
        
        data = result.result
        
        compliance = {
            'job_id': job_id,
            'pm_number': data.get('summary', {}).get('pm_number'),
            'compliance_score': data.get('compliance_score', 0),
            'work_type': data.get('work_type'),
            'required_docs': data.get('required_docs', []),
            'missing_docs': [],  # TODO: Calculate from actual vs required
            'suggestions': {
                'red_line': len(data.get('fill_suggestions', {}).get('red_line', [])),
                'blue_line': len(data.get('fill_suggestions', {}).get('blue_line', []))
            },
            'pricing': data.get('pricing', {}).get('total', 0)
        }
        
        # Determine compliance level
        score = compliance['compliance_score']
        if score >= 95:
            compliance['level'] = 'EXCELLENT'
        elif score >= 80:
            compliance['level'] = 'GOOD'
        elif score >= 60:
            compliance['level'] = 'NEEDS_REVIEW'
        else:
            compliance['level'] = 'NON_COMPLIANT'
        
        return compliance
        
    except Exception as e:
        raise HTTPException(500, f"Compliance check error: {str(e)}")
