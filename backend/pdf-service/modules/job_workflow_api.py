"""
Job Workflow API - Complete PG&E Job Package Management
Handles the full lifecycle: Upload → Assign → Build → Submit → QA → PG&E
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import os
import json
import hashlib
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import logging
from sqlalchemy import create_engine, Column, String, Integer, DateTime, JSON, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import boto3  # For S3 storage if needed
from io import BytesIO

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database setup - Use Render's PostgreSQL
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/nexa_jobs")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Database Models
class Job(Base):
    __tablename__ = "jobs"
    
    id = Column(String, primary_key=True)
    pm_number = Column(String, index=True)
    notification_number = Column(String, index=True)
    package_url = Column(String)  # S3 or local path
    status = Column(String, default="pending")  # pending, assigned, in_progress, ready_for_qa, approved, submitted
    assigned_crew = Column(String)
    assigned_foreman = Column(String)
    location = Column(String)
    scheduled_date = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Analysis data
    initial_analysis = Column(JSON)  # From PDF upload
    field_photos = Column(JSON)  # URLs to photos
    vision_analysis = Column(JSON)  # YOLO results
    final_analysis = Column(JSON)  # Combined analysis
    filled_pdf_url = Column(String)  # Generated PDF
    
    # Workflow metadata
    uploaded_by = Column(String)  # PM user ID
    assigned_by = Column(String)  # GF user ID
    submitted_by = Column(String)  # Foreman user ID
    reviewed_by = Column(String)  # QA user ID
    
    # Tracking
    submission_date = Column(DateTime)
    qa_date = Column(DateTime)
    pge_submission_date = Column(DateTime)
    
    # Flags
    has_go_backs = Column(Boolean, default=False)
    repealable_count = Column(Integer, default=0)
    total_savings = Column(Integer, default=0)

# Create tables
Base.metadata.create_all(bind=engine)

# Pydantic models for API
class JobUpload(BaseModel):
    pm_number: str
    notification_number: Optional[str] = None
    location: str
    scheduled_date: Optional[datetime] = None

class JobAssignment(BaseModel):
    job_id: str
    crew_id: str
    foreman_id: str
    scheduled_date: datetime

class JobSubmission(BaseModel):
    job_id: str
    photos: List[str]  # URLs or base64
    notes: Optional[str] = None

class QAReview(BaseModel):
    job_id: str
    approved: bool
    comments: Optional[str] = None
    corrections: Optional[List[Dict]] = None

# Dependency for DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Workflow API endpoints
app = FastAPI(title="NEXA Job Workflow API")

@app.post("/api/workflow/upload-package")
async def upload_job_package(
    file: UploadFile = File(...),
    pm_number: str = None,
    notification_number: str = None,
    location: str = None,
    user_id: str = None,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db)
):
    """
    PM uploads job package PDF - triggers initial analysis
    """
    try:
        # Generate job ID
        job_id = f"JOB-{datetime.utcnow().strftime('%Y%m%d')}-{hashlib.md5(file.filename.encode()).hexdigest()[:8]}"
        
        # Save file (to S3 in production, local for now)
        file_path = f"/data/job_packages/{job_id}/{file.filename}"
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        # Create job record
        job = Job(
            id=job_id,
            pm_number=pm_number or f"PM-{job_id[:8]}",
            notification_number=notification_number,
            package_url=file_path,
            status="pending",
            location=location or "Unspecified",
            uploaded_by=user_id,
            scheduled_date=datetime.utcnow() + timedelta(days=7)  # Default 1 week out
        )
        
        db.add(job)
        db.commit()
        
        # Trigger background analysis
        background_tasks.add_task(analyze_package_background, job_id)
        
        return {
            "job_id": job_id,
            "pm_number": job.pm_number,
            "status": "Package uploaded, analysis in progress",
            "scheduled_date": job.scheduled_date.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error uploading package: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/workflow/assign-job")
async def assign_job(
    assignment: JobAssignment,
    user_id: str = None,
    db: Session = Depends(get_db)
):
    """
    GF assigns job to crew and foreman
    """
    job = db.query(Job).filter(Job.id == assignment.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job.assigned_crew = assignment.crew_id
    job.assigned_foreman = assignment.foreman_id
    job.scheduled_date = assignment.scheduled_date
    job.assigned_by = user_id
    job.status = "assigned"
    
    db.commit()
    
    # Send notification to foreman (implement push notification)
    # notify_foreman(assignment.foreman_id, job)
    
    return {
        "status": "Job assigned",
        "job_id": job.id,
        "crew": job.assigned_crew,
        "foreman": job.assigned_foreman,
        "scheduled": job.scheduled_date.isoformat()
    }

@app.post("/api/workflow/submit-field-work")
async def submit_field_work(
    submission: JobSubmission,
    user_id: str = None,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db)
):
    """
    Foreman submits completed field work with photos
    """
    job = db.query(Job).filter(Job.id == submission.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Save photos
    photo_paths = []
    for i, photo_data in enumerate(submission.photos):
        photo_path = f"/data/job_photos/{job.id}/photo_{i}.jpg"
        os.makedirs(os.path.dirname(photo_path), exist_ok=True)
        # Decode base64 or download URL
        # ... photo saving logic ...
        photo_paths.append(photo_path)
    
    job.field_photos = photo_paths
    job.status = "in_progress"
    job.submitted_by = user_id
    job.submission_date = datetime.utcnow()
    
    db.commit()
    
    # Trigger vision analysis and PDF generation
    background_tasks.add_task(process_submission_background, job.id)
    
    return {
        "status": "Field work submitted, processing",
        "job_id": job.id,
        "photos": len(photo_paths),
        "expected_completion": (datetime.utcnow() + timedelta(minutes=5)).isoformat()
    }

@app.post("/api/workflow/qa-review")
async def qa_review(
    review: QAReview,
    user_id: str = None,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db)
):
    """
    QA reviews and approves/rejects completed job
    """
    job = db.query(Job).filter(Job.id == review.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job.reviewed_by = user_id
    job.qa_date = datetime.utcnow()
    
    if review.approved:
        job.status = "approved"
        # Submit to PG&E
        background_tasks.add_task(submit_to_pge, job.id)
    else:
        job.status = "rejected"
        # Send back to foreman with corrections
        if review.corrections:
            job.final_analysis["qa_corrections"] = review.corrections
    
    db.commit()
    
    return {
        "status": "approved" if review.approved else "rejected",
        "job_id": job.id,
        "next_action": "Submitting to PG&E" if review.approved else "Returned to foreman"
    }

@app.get("/api/workflow/job/{job_id}")
async def get_job_status(job_id: str, db: Session = Depends(get_db)):
    """
    Get current job status and details
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {
        "job_id": job.id,
        "pm_number": job.pm_number,
        "notification_number": job.notification_number,
        "status": job.status,
        "location": job.location,
        "scheduled_date": job.scheduled_date.isoformat() if job.scheduled_date else None,
        "crew": job.assigned_crew,
        "foreman": job.assigned_foreman,
        "has_go_backs": job.has_go_backs,
        "repealable_count": job.repealable_count,
        "total_savings": job.total_savings,
        "analysis": job.final_analysis,
        "filled_pdf": job.filled_pdf_url,
        "timeline": {
            "uploaded": job.created_at.isoformat(),
            "submitted": job.submission_date.isoformat() if job.submission_date else None,
            "reviewed": job.qa_date.isoformat() if job.qa_date else None,
            "sent_to_pge": job.pge_submission_date.isoformat() if job.pge_submission_date else None
        }
    }

@app.get("/api/workflow/jobs")
async def list_jobs(
    status: Optional[str] = None,
    crew_id: Optional[str] = None,
    foreman_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    List jobs with filters
    """
    query = db.query(Job)
    
    if status:
        query = query.filter(Job.status == status)
    if crew_id:
        query = query.filter(Job.assigned_crew == crew_id)
    if foreman_id:
        query = query.filter(Job.assigned_foreman == foreman_id)
    
    jobs = query.order_by(Job.scheduled_date.desc()).limit(100).all()
    
    return [{
        "job_id": job.id,
        "pm_number": job.pm_number,
        "status": job.status,
        "location": job.location,
        "scheduled_date": job.scheduled_date.isoformat() if job.scheduled_date else None,
        "crew": job.assigned_crew,
        "has_go_backs": job.has_go_backs,
        "savings": job.total_savings
    } for job in jobs]

# Background tasks
async def analyze_package_background(job_id: str):
    """
    Analyze uploaded PDF package for initial go-backs
    """
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return
        
        # Call existing analyze_audit endpoint
        # analysis = await analyze_audit(job.package_url)
        # For now, mock analysis
        analysis = {
            "infractions": 12,
            "repealable": 8,
            "total_savings": 45000,
            "go_backs": [
                {"description": "Crossarm spacing", "repealable": True, "confidence": 0.92},
                {"description": "Grounding wire gauge", "repealable": False, "confidence": 0.98}
            ]
        }
        
        job.initial_analysis = analysis
        job.has_go_backs = len(analysis.get("go_backs", [])) > 0
        job.repealable_count = analysis.get("repealable", 0)
        job.total_savings = analysis.get("total_savings", 0)
        
        db.commit()
        logger.info(f"Package analysis complete for {job_id}")
        
    except Exception as e:
        logger.error(f"Error analyzing package {job_id}: {e}")
    finally:
        db.close()

async def process_submission_background(job_id: str):
    """
    Process field submission - run YOLO, generate filled PDF
    """
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return
        
        # Run YOLO on photos (mock for now)
        vision_results = {
            "poles_detected": 3,
            "issues": [],
            "compliant": True
        }
        job.vision_analysis = vision_results
        
        # Combine analyses
        final_analysis = {
            **job.initial_analysis,
            "field_verified": True,
            "vision_check": vision_results,
            "final_repealable": job.repealable_count,
            "final_savings": job.total_savings
        }
        job.final_analysis = final_analysis
        
        # Generate filled PDF
        pdf_path = generate_filled_pdf(job)
        job.filled_pdf_url = pdf_path
        job.status = "ready_for_qa"
        
        db.commit()
        logger.info(f"Submission processed for {job_id}")
        
    except Exception as e:
        logger.error(f"Error processing submission {job_id}: {e}")
    finally:
        db.close()

def generate_filled_pdf(job: Job) -> str:
    """
    Generate filled PDF with all analysis data
    """
    pdf_path = f"/data/filled_pdfs/{job.id}_filled.pdf"
    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
    
    doc = SimpleDocTemplate(pdf_path, pagesize=letter)
    story = []
    styles = getSampleStyleSheet()
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=24,
        textColor=colors.HexColor('#1e3a8a'),
        alignment=TA_CENTER
    )
    story.append(Paragraph(f"Job Package: {job.pm_number}", title_style))
    story.append(Spacer(1, 0.5*inch))
    
    # Job details
    details = [
        ["PM Number:", job.pm_number],
        ["Notification:", job.notification_number or "N/A"],
        ["Location:", job.location],
        ["Crew:", job.assigned_crew],
        ["Foreman:", job.assigned_foreman],
        ["Status:", job.status.upper()]
    ]
    
    detail_table = Table(details, colWidths=[2*inch, 4*inch])
    detail_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(detail_table)
    story.append(Spacer(1, 0.5*inch))
    
    # Analysis summary
    story.append(Paragraph("Analysis Summary", styles['Heading1']))
    if job.final_analysis:
        summary = [
            ["Total Infractions:", str(job.final_analysis.get("infractions", 0))],
            ["Repealable:", str(job.repealable_count)],
            ["Valid Go-Backs:", str(job.final_analysis.get("infractions", 0) - job.repealable_count)],
            ["Total Savings:", f"${job.total_savings:,}"],
            ["Field Verified:", "Yes" if job.final_analysis.get("field_verified") else "No"]
        ]
        
        summary_table = Table(summary, colWidths=[2*inch, 2*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e5e7eb')),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('PADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(summary_table)
    
    story.append(PageBreak())
    
    # Detailed infractions
    story.append(Paragraph("Detailed Infractions", styles['Heading1']))
    if job.initial_analysis and "go_backs" in job.initial_analysis:
        for i, infraction in enumerate(job.initial_analysis["go_backs"], 1):
            story.append(Paragraph(f"{i}. {infraction['description']}", styles['Heading3']))
            status = "REPEALABLE" if infraction.get("repealable") else "VALID GO-BACK"
            confidence = infraction.get("confidence", 0) * 100
            story.append(Paragraph(f"Status: {status} (Confidence: {confidence:.1f}%)", styles['Normal']))
            story.append(Spacer(1, 0.25*inch))
    
    # Build PDF
    doc.build(story)
    logger.info(f"Generated filled PDF: {pdf_path}")
    return pdf_path

async def submit_to_pge(job_id: str):
    """
    Submit approved job to PG&E
    """
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job or not job.filled_pdf_url:
            return
        
        # Email configuration (use environment variables)
        smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USER", "nexa-system@example.com")
        smtp_pass = os.getenv("SMTP_PASSWORD", "")
        pge_email = os.getenv("PGE_EMAIL", "submissions@pge.com")
        
        # Create email
        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = pge_email
        msg['Subject'] = f"Job Package Submission - {job.pm_number}"
        
        body = f"""
        Job Package Submission
        
        PM Number: {job.pm_number}
        Notification: {job.notification_number or 'N/A'}
        Location: {job.location}
        
        Analysis Summary:
        - Total Infractions: {job.final_analysis.get('infractions', 0)}
        - Repealable: {job.repealable_count}
        - Cost Savings: ${job.total_savings:,}
        
        Please find the completed job package attached.
        
        This submission was generated by the NEXA Field Management System.
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Attach PDF
        with open(job.filled_pdf_url, 'rb') as f:
            attach = MIMEBase('application', 'pdf')
            attach.set_payload(f.read())
            encoders.encode_base64(attach)
            attach.add_header('Content-Disposition', f'attachment; filename={job.pm_number}_filled.pdf')
            msg.attach(attach)
        
        # Send email
        if smtp_pass:  # Only send if configured
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.send_message(msg)
        
        job.pge_submission_date = datetime.utcnow()
        job.status = "submitted"
        db.commit()
        
        logger.info(f"Submitted {job_id} to PG&E")
        
    except Exception as e:
        logger.error(f"Error submitting {job_id} to PG&E: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
