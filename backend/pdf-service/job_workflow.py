"""
Job Workflow Management System
Handles GF → Foreman → Submittal complete workflow
"""
from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime, date
from enum import Enum
import uuid
import json
import os

# Job Status Workflow
class JobStatus(str, Enum):
    CREATED = "created"
    ASSIGNED = "assigned"
    PRE_FIELD = "pre_field"
    IN_PROGRESS = "in_progress"
    QC_REVIEW = "qc_review"
    CLOSEOUT = "closeout"
    SUBMITTED = "submitted"
    COMPLETED = "completed"

class JobType(str, Enum):
    INSTALL = "install"
    MAINTENANCE = "maintenance"
    REPAIR = "repair"
    INSPECTION = "inspection"

# Data Models
class Job(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    job_number: str
    type: JobType
    location: str
    customer: str
    scheduled_date: date
    status: JobStatus = JobStatus.CREATED
    
    # Assignments
    gf_id: Optional[str] = None
    foreman_id: Optional[str] = None
    crew_ids: List[str] = []
    
    # Documents
    spec_files: List[str] = []
    permit_files: List[str] = []
    pre_field_docs: List[str] = []
    field_photos: List[str] = []
    closeout_docs: List[str] = []
    
    # Analysis Results
    pre_field_status: Optional[Dict] = None
    qc_audit_results: Optional[Dict] = None
    infractions: List[Dict] = []
    repeals: List[Dict] = []
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    assigned_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

class JobAssignment(BaseModel):
    foreman_id: str
    crew_ids: List[str]
    notes: Optional[str] = None

class PreFieldSubmission(BaseModel):
    job_id: str
    documents_complete: bool
    permits_verified: bool
    specs_reviewed: bool
    safety_briefing: bool
    notes: Optional[str] = None

# In-memory storage (replace with database in production)
JOBS_DB: Dict[str, Job] = {}

# API Endpoints for Complete Workflow

@app.post("/jobs/create")
async def create_job(job: Job) -> Dict[str, Any]:
    """
    GF creates a new job
    """
    JOBS_DB[job.id] = job
    
    return {
        "job_id": job.id,
        "status": job.status,
        "message": f"Job {job.job_number} created successfully"
    }

@app.get("/jobs/today")
async def get_todays_jobs(
    role: str,  # 'gf', 'foreman', 'crew'
    user_id: str
) -> Dict[str, Any]:
    """
    Get today's jobs for user based on role
    """
    today = date.today()
    jobs = []
    
    for job in JOBS_DB.values():
        # Filter by role and date
        if job.scheduled_date == today:
            if role == "gf" and job.gf_id == user_id:
                jobs.append(job)
            elif role == "foreman" and job.foreman_id == user_id:
                jobs.append(job)
            elif role == "crew" and user_id in job.crew_ids:
                jobs.append(job)
    
    # Categorize by status
    return {
        "date": today.isoformat(),
        "total": len(jobs),
        "needs_assignment": [j for j in jobs if j.status == JobStatus.CREATED],
        "pre_field": [j for j in jobs if j.status == JobStatus.ASSIGNED],
        "in_progress": [j for j in jobs if j.status == JobStatus.IN_PROGRESS],
        "needs_closeout": [j for j in jobs if j.status == JobStatus.QC_REVIEW],
        "jobs": jobs
    }

@app.post("/jobs/{job_id}/assign")
async def assign_job(
    job_id: str,
    assignment: JobAssignment
) -> Dict[str, Any]:
    """
    GF assigns job to foreman and crew
    """
    if job_id not in JOBS_DB:
        raise HTTPException(404, "Job not found")
    
    job = JOBS_DB[job_id]
    job.foreman_id = assignment.foreman_id
    job.crew_ids = assignment.crew_ids
    job.status = JobStatus.ASSIGNED
    job.assigned_at = datetime.utcnow()
    
    return {
        "job_id": job_id,
        "status": job.status,
        "foreman_id": job.foreman_id,
        "message": "Job assigned successfully"
    }

@app.post("/jobs/{job_id}/pre-field")
async def submit_pre_field(
    job_id: str,
    submission: PreFieldSubmission,
    files: List[UploadFile] = File(None)
) -> Dict[str, Any]:
    """
    Foreman submits pre-field verification
    """
    if job_id not in JOBS_DB:
        raise HTTPException(404, "Job not found")
    
    job = JOBS_DB[job_id]
    
    # Store uploaded documents
    if files:
        for file in files:
            # Save file (implement actual storage)
            filename = f"pre_field_{job_id}_{file.filename}"
            job.pre_field_docs.append(filename)
    
    # Verify all requirements met
    if not all([
        submission.documents_complete,
        submission.permits_verified,
        submission.specs_reviewed,
        submission.safety_briefing
    ]):
        return {
            "job_id": job_id,
            "status": "incomplete",
            "message": "Pre-field requirements not met",
            "missing": []  # List what's missing
        }
    
    # Auto-analyze documents using existing analyzer
    from app_oct2025_enhanced import analyze_audit
    
    analysis_results = []
    for doc in job.pre_field_docs:
        # Analyze each document
        # result = await analyze_audit(doc)
        # analysis_results.append(result)
        pass
    
    job.pre_field_status = {
        "submitted_at": datetime.utcnow().isoformat(),
        "submitted_by": job.foreman_id,
        "verification": submission.dict(),
        "analysis": analysis_results
    }
    job.status = JobStatus.PRE_FIELD
    
    return {
        "job_id": job_id,
        "status": job.status,
        "message": "Pre-field submitted successfully",
        "can_proceed": True
    }

@app.post("/jobs/{job_id}/start")
async def start_fieldwork(job_id: str) -> Dict[str, Any]:
    """
    Foreman starts field work
    """
    if job_id not in JOBS_DB:
        raise HTTPException(404, "Job not found")
    
    job = JOBS_DB[job_id]
    
    if job.status != JobStatus.PRE_FIELD:
        raise HTTPException(400, "Pre-field must be completed first")
    
    job.status = JobStatus.IN_PROGRESS
    job.started_at = datetime.utcnow()
    
    return {
        "job_id": job_id,
        "status": job.status,
        "started_at": job.started_at.isoformat()
    }

@app.post("/jobs/{job_id}/qc-audit")
async def submit_qc_audit(
    job_id: str,
    audit_file: UploadFile = File(...)
) -> Dict[str, Any]:
    """
    Submit QC audit for analysis
    """
    if job_id not in JOBS_DB:
        raise HTTPException(404, "Job not found")
    
    job = JOBS_DB[job_id]
    
    # Use existing async analyzer
    from celery_worker import analyze_audit_async
    
    content = await audit_file.read()
    task = analyze_audit_async.delay(content, audit_file.filename)
    
    return {
        "job_id": job_id,
        "audit_job_id": task.id,
        "status": "analyzing",
        "message": "QC audit submitted for analysis",
        "poll_url": f"/job-status/{task.id}"
    }

@app.get("/jobs/{job_id}/qc-results")
async def get_qc_results(job_id: str) -> Dict[str, Any]:
    """
    Get QC audit analysis results with repeal recommendations
    """
    if job_id not in JOBS_DB:
        raise HTTPException(404, "Job not found")
    
    job = JOBS_DB[job_id]
    
    if not job.qc_audit_results:
        return {"status": "pending", "message": "QC audit not analyzed yet"}
    
    # Format results for easy review
    infractions = job.qc_audit_results.get("infractions", [])
    
    repealable = [i for i in infractions if i.get("confidence", 0) > 80]
    needs_review = [i for i in infractions if i.get("confidence", 0) <= 80]
    
    return {
        "job_id": job_id,
        "summary": {
            "total_infractions": len(infractions),
            "repealable": len(repealable),
            "needs_review": len(needs_review),
            "confidence_avg": sum(i.get("confidence", 0) for i in infractions) / max(1, len(infractions))
        },
        "repeal_recommendations": [
            {
                "item": i["item"],
                "confidence": i["confidence"],
                "reason": i["reason"],
                "spec_reference": i.get("source", ""),
                "action": "AUTO_REPEAL" if i["confidence"] > 90 else "REVIEW_RECOMMENDED"
            }
            for i in repealable
        ],
        "requires_attention": needs_review,
        "next_step": "proceed_to_closeout" if len(needs_review) == 0 else "address_infractions"
    }

@app.post("/jobs/{job_id}/closeout")
async def submit_closeout(
    job_id: str,
    files: List[UploadFile] = File(...)
) -> Dict[str, Any]:
    """
    Foreman submits closeout package
    """
    if job_id not in JOBS_DB:
        raise HTTPException(404, "Job not found")
    
    job = JOBS_DB[job_id]
    
    # Store closeout documents
    for file in files:
        filename = f"closeout_{job_id}_{file.filename}"
        job.closeout_docs.append(filename)
    
    job.status = JobStatus.CLOSEOUT
    
    # Auto-generate submittal package
    submittal = await generate_submittal_package(job)
    
    return {
        "job_id": job_id,
        "status": job.status,
        "closeout_docs": len(job.closeout_docs),
        "submittal_ready": submittal is not None,
        "message": "Closeout submitted, submittal package being generated"
    }

@app.post("/jobs/{job_id}/generate-submittal")
async def generate_submittal(job_id: str) -> Dict[str, Any]:
    """
    Generate final submittal package for customer
    """
    if job_id not in JOBS_DB:
        raise HTTPException(404, "Job not found")
    
    job = JOBS_DB[job_id]
    
    # Compile all documents
    submittal_package = await generate_submittal_package(job)
    
    job.status = JobStatus.SUBMITTED
    job.completed_at = datetime.utcnow()
    
    return {
        "job_id": job_id,
        "status": job.status,
        "submittal_url": f"/download/submittal_{job_id}.pdf",
        "included_documents": {
            "pre_field": len(job.pre_field_docs),
            "field_photos": len(job.field_photos),
            "closeout": len(job.closeout_docs),
            "qc_audit": "included" if job.qc_audit_results else "missing"
        },
        "message": "Submittal package generated successfully"
    }

async def generate_submittal_package(job: Job) -> Optional[bytes]:
    """
    Helper to create submittal PDF package
    """
    # TODO: Implement actual PDF generation
    # 1. Create cover sheet with job info
    # 2. Append pre-field docs
    # 3. Append field photos
    # 4. Append QC audit with repeal annotations
    # 5. Append closeout docs
    # 6. Generate single PDF
    
    return b"PDF_CONTENT"  # Placeholder

@app.get("/workflow/status/{job_id}")
async def get_workflow_status(job_id: str) -> Dict[str, Any]:
    """
    Get complete workflow status for a job
    """
    if job_id not in JOBS_DB:
        raise HTTPException(404, "Job not found")
    
    job = JOBS_DB[job_id]
    
    # Calculate completion percentage
    stages = {
        JobStatus.CREATED: 10,
        JobStatus.ASSIGNED: 20,
        JobStatus.PRE_FIELD: 40,
        JobStatus.IN_PROGRESS: 60,
        JobStatus.QC_REVIEW: 80,
        JobStatus.CLOSEOUT: 90,
        JobStatus.SUBMITTED: 95,
        JobStatus.COMPLETED: 100
    }
    
    return {
        "job_id": job_id,
        "current_stage": job.status,
        "completion": stages.get(job.status, 0),
        "timeline": {
            "created": job.created_at.isoformat() if job.created_at else None,
            "assigned": job.assigned_at.isoformat() if job.assigned_at else None,
            "started": job.started_at.isoformat() if job.started_at else None,
            "completed": job.completed_at.isoformat() if job.completed_at else None
        },
        "assignments": {
            "gf": job.gf_id,
            "foreman": job.foreman_id,
            "crew": job.crew_ids
        },
        "documents": {
            "specs": len(job.spec_files),
            "permits": len(job.permit_files),
            "pre_field": len(job.pre_field_docs),
            "photos": len(job.field_photos),
            "closeout": len(job.closeout_docs)
        },
        "issues": {
            "infractions": len(job.infractions),
            "repeals": len(job.repeals)
        },
        "next_action": get_next_action(job)
    }

def get_next_action(job: Job) -> str:
    """
    Determine next action in workflow
    """
    actions = {
        JobStatus.CREATED: "Assign to foreman",
        JobStatus.ASSIGNED: "Complete pre-field verification",
        JobStatus.PRE_FIELD: "Start field work",
        JobStatus.IN_PROGRESS: "Submit QC audit",
        JobStatus.QC_REVIEW: "Address infractions or proceed to closeout",
        JobStatus.CLOSEOUT: "Generate submittal",
        JobStatus.SUBMITTED: "Await customer approval",
        JobStatus.COMPLETED: "Job complete"
    }
    return actions.get(job.status, "Unknown")
