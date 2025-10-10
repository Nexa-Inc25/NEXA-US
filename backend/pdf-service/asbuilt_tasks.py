"""
Celery tasks for async as-built processing
Integrates with PG&E procedure rules for intelligent filling
"""
from celery import Task
from celery_worker import app as celery_app
from asbuilt_processor import PGEAsBuiltProcessor
import json
import logging
from typing import Dict, List, Optional
import base64
import io

logger = logging.getLogger(__name__)

# Initialize processor
processor = PGEAsBuiltProcessor()

@celery_app.task(bind=True, name='asbuilt.fill_single')
def fill_asbuilt_async(self: Task, pdf_content: bytes, job_data: Dict, 
                       photo_paths: Optional[List[str]] = None) -> Dict:
    """
    Async task to fill a single as-built according to PG&E procedures
    
    Args:
        pdf_content: Raw PDF bytes
        job_data: Job information including PM/Notification numbers
        photo_paths: Optional list of photo file paths
    
    Returns:
        Dict with annotated PDF, suggestions, pricing, etc.
    """
    try:
        # Update progress
        self.update_state(
            state='PROCESSING',
            meta={
                'progress': 10,
                'status': 'Extracting text from PDF...',
                'job': job_data.get('pm_number', 'Unknown')
            }
        )
        
        # Process the as-built
        self.update_state(
            state='ANALYZING',
            meta={'progress': 30, 'status': 'Analyzing content...'}
        )
        
        result = processor.fill_asbuilt(pdf_content, job_data, photo_paths)
        
        self.update_state(
            state='ANNOTATING',
            meta={'progress': 60, 'status': 'Adding annotations...'}
        )
        
        # Convert PDF bytes to base64 for JSON serialization
        result['annotated_pdf'] = base64.b64encode(
            result['annotated_pdf']
        ).decode('utf-8')
        
        self.update_state(
            state='FINALIZING',
            meta={'progress': 90, 'status': 'Finalizing documents...'}
        )
        
        # Add summary
        result['summary'] = {
            'pm_number': job_data.get('pm_number'),
            'notification': job_data.get('notification_number'),
            'work_type': result['work_type'],
            'total_price': result['pricing']['total'],
            'compliance_score': result['compliance_score'],
            'documents_required': len(result['required_docs']),
            'materials_found': len(result['mat_codes']),
            'suggestions_count': (
                len(result['fill_suggestions'].get('red_line', [])) +
                len(result['fill_suggestions'].get('blue_line', []))
            )
        }
        
        logger.info(f"Completed as-built processing for PM {job_data.get('pm_number')}")
        return result
        
    except Exception as e:
        logger.error(f"Error processing as-built: {e}")
        self.update_state(
            state='FAILURE',
            meta={'error': str(e)}
        )
        raise


@celery_app.task(bind=True, name='asbuilt.batch_process')
def batch_asbuilt_async(self: Task, batch_data: List[Dict]) -> Dict:
    """
    Process multiple as-builts in batch
    
    Args:
        batch_data: List of dicts with pdf_content, job_data, photos
    
    Returns:
        Dict with results for each processed as-built
    """
    try:
        total = len(batch_data)
        results = []
        errors = []
        
        for idx, item in enumerate(batch_data):
            # Update progress
            self.update_state(
                state='BATCH_PROCESSING',
                meta={
                    'progress': int((idx / total) * 100),
                    'status': f'Processing {idx + 1} of {total}',
                    'current': item.get('job_data', {}).get('pm_number', 'Unknown')
                }
            )
            
            try:
                # Process individual as-built
                pdf_content = base64.b64decode(item['pdf_content'])
                result = processor.fill_asbuilt(
                    pdf_content,
                    item['job_data'],
                    item.get('photos')
                )
                
                # Convert for serialization
                result['annotated_pdf'] = base64.b64encode(
                    result['annotated_pdf']
                ).decode('utf-8')
                
                results.append({
                    'job_id': item['job_data'].get('pm_number'),
                    'status': 'success',
                    'result': result
                })
                
            except Exception as e:
                logger.error(f"Error in batch item {idx}: {e}")
                errors.append({
                    'job_id': item.get('job_data', {}).get('pm_number', 'Unknown'),
                    'status': 'error',
                    'error': str(e)
                })
        
        return {
            'total': total,
            'successful': len(results),
            'failed': len(errors),
            'results': results,
            'errors': errors,
            'batch_summary': {
                'total_pricing': sum(
                    r['result']['pricing']['total'] 
                    for r in results 
                    if 'result' in r and 'pricing' in r['result']
                ),
                'avg_compliance': sum(
                    r['result']['compliance_score'] 
                    for r in results 
                    if 'result' in r and 'compliance_score' in r['result']
                ) / len(results) if results else 0
            }
        }
        
    except Exception as e:
        logger.error(f"Batch processing error: {e}")
        self.update_state(
            state='FAILURE',
            meta={'error': str(e)}
        )
        raise


@celery_app.task(name='asbuilt.extract_procedure_rules')
def extract_procedure_rules_async(pdf_text: str, filename: Optional[str] = None) -> Dict:
    """
    Extract and save PG&E procedure rules from uploaded PDF
    This runs once when procedure PDF is uploaded
    Handles: Main procedure, Document ordering, Pole types PDFs
    """
    try:
        rules = processor.extract_asbuilt_rules(pdf_text, filename)
        
        # Count extracted elements based on PDF type
        summary = {
            'red_line_rules': len(rules.get('red_line', {}).get('actions', [])),
            'blue_line_rules': len(rules.get('blue_line', {}).get('actions', [])),
            'work_types': len(rules.get('pairing_table', {})),
            'fda_requirements': bool(rules.get('fda')),
            'cert_template': bool(rules.get('cert_sheet')),
            'document_order': len(rules.get('document_order', [])),
            'pole_types': len(rules.get('pole_types', {}))
        }
        
        # Identify PDF type
        pdf_type = 'general'
        if filename:
            if 'document order' in filename.lower():
                pdf_type = 'document_order'
            elif 'pole type' in filename.lower():
                pdf_type = 'pole_types'
        
        logger.info(f"Extracted {pdf_type} rules from {filename}: {summary}")
        
        return {
            'status': 'success',
            'pdf_type': pdf_type,
            'filename': filename,
            'rules_extracted': rules,
            'summary': summary
        }
        
    except Exception as e:
        logger.error(f"Error extracting procedure rules: {e}")
        return {
            'status': 'error',
            'error': str(e)
        }


@celery_app.task(name='asbuilt.update_prices')
def update_mat_prices_async(prices_data: Dict) -> Dict:
    """
    Update material prices asynchronously
    """
    try:
        success = processor.update_mat_prices(prices_data)
        
        if success:
            return {
                'status': 'success',
                'updated': len(prices_data),
                'message': f'Updated {len(prices_data)} material prices'
            }
        else:
            return {
                'status': 'error',
                'message': 'Failed to update prices'
            }
            
    except Exception as e:
        logger.error(f"Error updating prices: {e}")
        return {
            'status': 'error',
            'error': str(e)
        }
