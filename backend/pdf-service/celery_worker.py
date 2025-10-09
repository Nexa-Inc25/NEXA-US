"""
Celery Worker for Async Audit Processing
Handles background PDF analysis without blocking the API
"""
from celery import Celery
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get Redis URL from environment
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# Create Celery app
app = Celery('nexa_worker', broker=REDIS_URL, backend=REDIS_URL)

# Configure Celery
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 min max
    task_soft_time_limit=240,  # 4 min soft limit
)

@app.task(bind=True)
def analyze_audit_async(self, pdf_content, filename):
    """
    Async task to analyze PDF audit
    """
    try:
        # Update progress
        self.update_state(
            state='PROCESSING',
            meta={'progress': 10, 'status': 'Starting analysis...'}
        )
        
        # Import here to avoid loading model in main process
        import pickle
        import json
        from sentence_transformers import SentenceTransformer, util
        
        logger.info(f"Processing {filename}")
        
        # Simulate processing (replace with actual logic)
        import time
        time.sleep(2)
        
        # Update progress
        self.update_state(
            state='ANALYZING',
            meta={'progress': 50, 'status': 'Analyzing document...'}
        )
        
        # Mock result (replace with actual analysis)
        result = {
            'status': 'success',
            'filename': filename,
            'infractions': [
                {
                    'item': 1,
                    'text': 'Sample infraction',
                    'confidence': 85.5,
                    'repealable': True,
                    'reason': 'Matches spec requirement',
                    'source': 'spec.pdf'
                }
            ]
        }
        
        logger.info(f"Completed analysis of {filename}")
        return result
        
    except Exception as e:
        logger.error(f"Task failed: {str(e)}")
        return {
            'status': 'failed',
            'error': str(e),
            'filename': filename
        }

if __name__ == '__main__':
    # For testing locally
    app.worker_main(['worker', '--loglevel=info'])
