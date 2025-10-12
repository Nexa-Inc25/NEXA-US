"""
API Endpoints for As-Built Auto-Filler
Integrates with existing app_oct2025_enhanced.py
"""

from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from typing import List, Dict, Any, Optional
import os
import json
import logging
from datetime import datetime
from as_built_filler import AsBuiltFiller
import shutil
import tempfile

logger = logging.getLogger(__name__)

def add_as_built_endpoints(app: FastAPI):
    """
    Add as-built filling endpoints to existing FastAPI app
    """
    
    # Initialize as-built filler
    as_built_filler = AsBuiltFiller()
    
    @app.post("/fill-as-built")
    async def fill_as_built(
        job_id: str = Form(...),
        photos: List[UploadFile] = File(...),
        pm_number: Optional[str] = Form(None),
        location: Optional[str] = Form(None),
        foreman_name: Optional[str] = Form(None),
        crew_number: Optional[str] = Form(None)
    ):
        """
        Process foreman photos and auto-fill as-built document
        
        Workflow:
        1. Process photos with YOLO (detect equipment)
        2. Cross-reference with learned spec book
        3. Generate filled as-built PDF
        4. Flag any potential go-backs
        """
        logger.info(f"📝 Processing as-built for job {job_id} with {len(photos)} photos")
        
        try:
            # Process each photo with YOLO
            photo_results = []
            temp_files = []
            
            for photo in photos:
                # Save temp file
                temp_path = os.path.join(tempfile.gettempdir(), f"{job_id}_{photo.filename}")
                with open(temp_path, "wb") as f:
                    shutil.copyfileobj(photo.file, f)
                temp_files.append(temp_path)
                
                # Run YOLO detection (reuse existing vision endpoint logic)
                # This would call your existing pole_vision_detector
                detections = await detect_equipment_in_photo(temp_path)
                
                photo_results.append({
                    'filename': photo.filename,
                    'detections': detections
                })
            
            # Build job details
            job_details = {
                'pm_number': pm_number,
                'location': location,
                'foreman_name': foreman_name,
                'crew_number': crew_number
            }
            
            # Process all photos for as-built data
            as_built_data = as_built_filler.process_photos_for_as_built(
                job_id=job_id,
                photos=photo_results,
                job_details=job_details
            )
            
            # Generate PDF
            pdf_path = as_built_filler.generate_as_built_pdf(as_built_data)
            
            # Clean up temp files
            for temp_file in temp_files:
                try:
                    os.remove(temp_file)
                except:
                    pass
            
            # Prepare response
            response = {
                'status': 'success',
                'job_id': job_id,
                'pdf_path': pdf_path,
                'pdf_url': f"/download/as-built/{job_id}",
                'equipment_found': {
                    k: len(v) for k, v in as_built_data['equipment_installed'].items()
                },
                'compliance': {
                    'overall_compliant': as_built_data['compliance'].get('overall_compliant', False),
                    'average_confidence': as_built_data['compliance'].get('average_confidence', 0),
                    'issues_count': len(as_built_data['compliance'].get('issues', [])),
                    'compliant_items': len(as_built_data['compliance'].get('compliant_items', []))
                },
                'go_backs': as_built_data.get('go_backs_found', []),
                'ready_for_qa': as_built_data.get('ready_for_qa', False),
                'summary': generate_summary(as_built_data)
            }
            
            # Update job status in database (if you have one)
            # await update_job_status(job_id, 'as_built_filled', pdf_path)
            
            logger.info(f"✅ As-built filled for job {job_id}. Ready for QA: {response['ready_for_qa']}")
            
            return response
            
        except Exception as e:
            logger.error(f"Error filling as-built: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to fill as-built: {str(e)}")
    
    @app.post("/validate-as-built")
    async def validate_as_built(
        job_id: str = Form(...),
        as_built_data: str = Form(...)  # JSON string of filled data
    ):
        """
        Validate filled as-built against PG&E requirements
        """
        try:
            data = json.loads(as_built_data)
            
            # Check against specs
            compliance = as_built_filler.check_spec_compliance(
                data.get('equipment_installed', {})
            )
            
            validation_results = {
                'job_id': job_id,
                'valid': compliance.get('overall_compliant', False),
                'confidence': compliance.get('average_confidence', 0),
                'issues': compliance.get('issues', []),
                'spec_references': compliance.get('spec_references', []),
                'recommendations': []
            }
            
            # Add recommendations
            if not validation_results['valid']:
                for issue in compliance.get('issues', []):
                    validation_results['recommendations'].append(
                        issue.get('recommendation', 'Review installation')
                    )
            
            return validation_results
            
        except Exception as e:
            logger.error(f"Validation error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")
    
    @app.get("/as-built-status/{job_id}")
    async def get_as_built_status(job_id: str):
        """
        Check if as-built has been filled for a job
        """
        pdf_path = f"/data/as_built_{job_id}.pdf"
        
        if os.path.exists(pdf_path):
            # Get file info
            file_stat = os.stat(pdf_path)
            
            return {
                'job_id': job_id,
                'filled': True,
                'pdf_path': pdf_path,
                'pdf_url': f"/download/as-built/{job_id}",
                'file_size': file_stat.st_size,
                'created_at': datetime.fromtimestamp(file_stat.st_ctime).isoformat(),
                'modified_at': datetime.fromtimestamp(file_stat.st_mtime).isoformat()
            }
        else:
            return {
                'job_id': job_id,
                'filled': False,
                'message': 'As-built not yet filled. Upload photos to generate.'
            }
    
    @app.get("/download/as-built/{job_id}")
    async def download_as_built(job_id: str):
        """
        Download filled as-built PDF
        """
        from fastapi.responses import FileResponse
        
        pdf_path = f"/data/as_built_{job_id}.pdf"
        
        if not os.path.exists(pdf_path):
            raise HTTPException(status_code=404, detail="As-built PDF not found")
        
        return FileResponse(
            pdf_path,
            media_type='application/pdf',
            filename=f"as_built_{job_id}.pdf"
        )
    
    @app.post("/batch-fill-as-builts")
    async def batch_fill_as_builts(
        jobs: str = Form(...)  # JSON array of job IDs and photo paths
    ):
        """
        Process multiple as-builts in batch
        """
        try:
            job_list = json.loads(jobs)
            results = []
            
            for job in job_list:
                try:
                    # Process each job
                    as_built_data = as_built_filler.process_photos_for_as_built(
                        job_id=job['id'],
                        photos=job.get('photos', []),
                        job_details=job.get('details', {})
                    )
                    
                    pdf_path = as_built_filler.generate_as_built_pdf(as_built_data)
                    
                    results.append({
                        'job_id': job['id'],
                        'status': 'success',
                        'pdf_path': pdf_path,
                        'ready_for_qa': as_built_data.get('ready_for_qa', False)
                    })
                except Exception as e:
                    results.append({
                        'job_id': job['id'],
                        'status': 'failed',
                        'error': str(e)
                    })
            
            # Summary
            successful = sum(1 for r in results if r['status'] == 'success')
            failed = sum(1 for r in results if r['status'] == 'failed')
            
            return {
                'total_processed': len(results),
                'successful': successful,
                'failed': failed,
                'results': results
            }
            
        except Exception as e:
            logger.error(f"Batch processing error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Batch processing failed: {str(e)}")

async def detect_equipment_in_photo(photo_path: str) -> List[Dict]:
    """
    Run YOLO detection on photo (reuse existing vision logic)
    """
    # This would call your existing pole_vision_detector
    # For now, return mock data
    import random
    
    mock_detections = [
        {
            'label': 'pole',
            'confidence': random.uniform(85, 99),
            'classification': f'Type {random.randint(1, 5)}',
            'bbox': [100, 100, 200, 400]
        },
        {
            'label': 'crossarm',
            'confidence': random.uniform(80, 95),
            'angle': 'level',
            'bbox': [150, 120, 250, 140]
        }
    ]
    
    # In production, this would call:
    # from pole_vision_detector import PoleVisionDetector
    # detector = PoleVisionDetector()
    # return detector.detect_image(photo_path)
    
    return mock_detections

def generate_summary(as_built_data: Dict) -> str:
    """
    Generate human-readable summary
    """
    equipment = as_built_data.get('equipment_installed', {})
    compliance = as_built_data.get('compliance', {})
    
    # Count equipment
    total_equipment = sum(len(items) for items in equipment.values())
    
    # Compliance status
    if compliance.get('overall_compliant'):
        status = f"COMPLIANT ({compliance.get('average_confidence', 0):.1f}% confidence)"
    else:
        issues = len(compliance.get('issues', []))
        status = f"ISSUES FOUND ({issues} items need review)"
    
    # Go-backs
    go_backs = len(as_built_data.get('go_backs_found', []))
    
    summary = f"Filled with {total_equipment} equipment items. "
    summary += f"Compliance: {status}. "
    
    if go_backs > 0:
        summary += f"⚠️ {go_backs} potential go-backs detected. "
    else:
        summary += "✅ No go-backs detected. "
    
    if as_built_data.get('ready_for_qa'):
        summary += "Ready for QA review."
    else:
        summary += "Requires field review before QA."
    
    return summary

# Integration code for app_oct2025_enhanced.py
"""
# Add this to your app_oct2025_enhanced.py:

from as_built_endpoints import add_as_built_endpoints

# After creating your FastAPI app:
app = FastAPI()

# Add existing endpoints...

# Add as-built endpoints
add_as_built_endpoints(app)

# Continue with rest of app...
"""
