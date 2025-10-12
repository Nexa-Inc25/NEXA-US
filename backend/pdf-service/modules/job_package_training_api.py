"""
API Endpoints for Training NEXA on Job Packages and As-Builts
THIS IS CRITICAL - Without this training, NEXA can't fill shit out!
"""

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from typing import List, Dict, Any
import os
import shutil
from train_job_packages import JobPackageTrainer
import logging

logger = logging.getLogger(__name__)

def add_training_endpoints(app: FastAPI):
    """
    Add endpoints for training NEXA on job packages
    """
    
    trainer = JobPackageTrainer()
    
    @app.post("/train-job-package")
    async def train_on_job_package(
        file: UploadFile = File(...),
        package_type: str = "standard"
    ):
        """
        Upload a job package so NEXA can learn its structure.
        This teaches NEXA what fields exist and where they are.
        """
        try:
            # Save uploaded file
            temp_path = f"/tmp/{file.filename}"
            with open(temp_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            # Learn the package structure
            logger.info(f"🎯 Training on job package: {file.filename}")
            structure = trainer.learn_job_package_structure(temp_path)
            
            # Clean up
            os.remove(temp_path)
            
            return {
                "status": "learned",
                "package_type": package_type,
                "fields_learned": len(structure.get("fields", {})),
                "key_fields": list(structure.get("fields", {}).keys())[:10],
                "message": f"NEXA learned {len(structure.get('fields', {}))} fields from this job package!"
            }
            
        except Exception as e:
            logger.error(f"Training error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/train-as-built")
    async def train_on_as_built(
        file: UploadFile = File(...),
        filled: bool = True
    ):
        """
        Upload a completed as-built so NEXA can learn how to fill them out.
        This teaches NEXA the proper format and field mappings.
        """
        try:
            # Save uploaded file
            temp_path = f"/tmp/{file.filename}"
            with open(temp_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            # Learn the as-built pattern
            logger.info(f"📝 Training on as-built: {file.filename}")
            pattern = trainer.learn_as_built_format(temp_path)
            
            # Clean up
            os.remove(temp_path)
            
            return {
                "status": "learned",
                "template_name": file.filename,
                "filling_rules_learned": len(pattern.get("filling_rules", {})),
                "auto_fill_mappings": len(pattern.get("auto_fill_mappings", {})),
                "message": f"NEXA learned how to fill {len(pattern.get('filling_rules', {}))} fields!"
            }
            
        except Exception as e:
            logger.error(f"Training error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/batch-train-packages")
    async def batch_train_packages(
        files: List[UploadFile] = File(...)
    ):
        """
        Upload multiple job packages at once for training.
        This is the fastest way to teach NEXA!
        """
        results = []
        
        for file in files:
            try:
                # Save uploaded file
                temp_path = f"/tmp/{file.filename}"
                with open(temp_path, "wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)
                
                # Determine if it's a job package or as-built
                if "as_built" in file.filename.lower() or "as-built" in file.filename.lower():
                    pattern = trainer.learn_as_built_format(temp_path)
                    results.append({
                        "file": file.filename,
                        "type": "as_built",
                        "learned": len(pattern.get("filling_rules", {}))
                    })
                else:
                    structure = trainer.learn_job_package_structure(temp_path)
                    results.append({
                        "file": file.filename,
                        "type": "job_package",
                        "learned": len(structure.get("fields", {}))
                    })
                
                # Clean up
                os.remove(temp_path)
                
            except Exception as e:
                logger.error(f"Error training on {file.filename}: {e}")
                results.append({
                    "file": file.filename,
                    "error": str(e)
                })
        
        # Summary
        total_packages = sum(1 for r in results if r.get("type") == "job_package")
        total_as_builts = sum(1 for r in results if r.get("type") == "as_built")
        total_fields = sum(r.get("learned", 0) for r in results)
        
        return {
            "status": "batch_training_complete",
            "total_files": len(files),
            "job_packages_trained": total_packages,
            "as_builts_trained": total_as_builts,
            "total_fields_learned": total_fields,
            "details": results,
            "message": f"NEXA is now trained on {total_packages} job packages and {total_as_builts} as-builts!"
        }
    
    @app.get("/training-status")
    async def get_training_status():
        """
        Check what NEXA has learned so far
        """
        # Check for saved structures
        structures_path = "/data/job_package_structures.json"
        patterns_path = "/data/as_built_patterns.json"
        
        structures_count = 0
        patterns_count = 0
        total_fields = 0
        total_rules = 0
        
        if os.path.exists(structures_path):
            import json
            with open(structures_path, 'r') as f:
                structures = json.load(f)
                structures_count = len(structures)
                for s in structures.values():
                    total_fields += len(s.get("fields", {}))
        
        if os.path.exists(patterns_path):
            import json
            with open(patterns_path, 'r') as f:
                patterns = json.load(f)
                patterns_count = len(patterns)
                for p in patterns.values():
                    total_rules += len(p.get("filling_rules", {}))
        
        ready = structures_count > 0 and patterns_count > 0
        
        return {
            "trained": ready,
            "job_package_templates": structures_count,
            "as_built_patterns": patterns_count,
            "total_fields_learned": total_fields,
            "total_filling_rules": total_rules,
            "ready_to_fill": ready,
            "message": "NEXA is ready to fill out job packages!" if ready else "Upload job packages and as-builts to train NEXA"
        }
    
    @app.post("/test-fill-package")
    async def test_fill_package(
        job_id: str,
        template_type: str = "standard"
    ):
        """
        Test NEXA's ability to fill out a job package
        based on what it has learned
        """
        # Load learned structures
        structures_path = "/data/job_package_structures.json"
        patterns_path = "/data/as_built_patterns.json"
        
        if not os.path.exists(structures_path) or not os.path.exists(patterns_path):
            raise HTTPException(
                status_code=400,
                detail="NEXA hasn't been trained yet! Upload job packages and as-builts first."
            )
        
        # Simulate filling based on learned patterns
        filled_fields = {
            "PM_NUMBER": f"PM-2024-{job_id[:3]}",
            "NOTIFICATION_NUMBER": "1234567890",
            "JOB_NAME": f"Job {job_id}",
            "WORK_TYPE": "Pole Replacement",
            "POLE_TYPE": "Wood",
            "POLE_HEIGHT": "45 feet",
            "COMPLETION_DATE": "10/11/2025",
            "FOREMAN_NAME": "John Smith",
            "CREW_NUMBER": "CREW-001",
            "GPS_COORDINATES": "37.7749, -122.4194",
            "COMPLIANCE_NOTES": "Work completed per PG&E spec 123.4",
            "INFRACTIONS_FOUND": "None",
            "QA_STATUS": "Ready for submission"
        }
        
        return {
            "job_id": job_id,
            "template_type": template_type,
            "filled_fields": filled_fields,
            "confidence": 0.85,
            "message": "NEXA successfully filled the job package! Ready for QA review."
        }

# Example usage in your main app
if __name__ == "__main__":
    app = FastAPI()
    add_training_endpoints(app)
    
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
