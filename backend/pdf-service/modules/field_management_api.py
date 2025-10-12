"""
NEXA Field Management API Endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, File, UploadFile, Form
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from pydantic import BaseModel
import asyncio
import json
from user_roles import (
    User, Crew, JobAssignment, CrewStatusUpdate, 
    DashboardMetrics, UserRole, Permission
)

router = APIRouter(prefix="/api/field", tags=["Field Management"])

# In-memory storage (replace with database in production)
users_db: Dict[str, User] = {}
crews_db: Dict[str, Crew] = {}
job_assignments_db: Dict[str, JobAssignment] = {}
status_updates_db: List[CrewStatusUpdate] = []

# WebSocket connections for real-time updates
active_connections: Dict[str, Any] = {}

class LoginRequest(BaseModel):
    email: str
    password: str

class CrewUpdateRequest(BaseModel):
    crew_id: str
    status: str
    location: Optional[str] = None
    progress: Optional[int] = None
    notes: Optional[str] = None

class JobAssignmentRequest(BaseModel):
    job_package_id: str
    crew_id: str
    foreman_id: str
    due_date: datetime
    notes: Optional[str] = None
    estimated_cost: float

class TimeEntryRequest(BaseModel):
    crew_id: str
    member_id: str
    hours: float
    date: datetime
    job_id: str

class SafetyReportRequest(BaseModel):
    crew_id: str
    incident_type: Optional[str] = None
    severity: Optional[str] = None
    description: str
    photos: Optional[List[str]] = None

# Authentication helper (simplified for demo)
async def get_current_user(user_id: str) -> User:
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail="User not found")
    return users_db[user_id]

@router.post("/login")
async def login(request: LoginRequest):
    """Authenticate user and return token"""
    # Simplified authentication - in production use JWT
    # Demo users
    if request.email == "gf@nexa.com":
        user = User(
            id="gf_001",
            email=request.email,
            name="General Foreman",
            role=UserRole.GENERAL_FOREMAN,
            created_at=datetime.now()
        )
    elif request.email == "foreman@nexa.com":
        user = User(
            id="f_001",
            email=request.email,
            name="Field Foreman",
            role=UserRole.FOREMAN,
            crew_id="crew_001",
            created_at=datetime.now()
        )
    else:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    users_db[user.id] = user
    
    return {
        "user": user.dict(),
        "token": f"token_{user.id}",  # Simplified token
        "permissions": [p.value for p in Permission if user.has_permission(p)]
    }

@router.get("/dashboard/{user_id}")
async def get_dashboard(user_id: str):
    """Get dashboard metrics based on user role"""
    user = await get_current_user(user_id)
    
    # Calculate metrics based on role
    if user.role == UserRole.GENERAL_FOREMAN:
        # GF sees all crews
        total_crews = len(crews_db)
        active_crews = sum(1 for c in crews_db.values() if c.status == "active")
        jobs_assigned = len(job_assignments_db)
        jobs_completed = sum(1 for j in job_assignments_db.values() if j.status == "completed")
        
        metrics = DashboardMetrics(
            total_crews=total_crews,
            active_crews=active_crews,
            jobs_assigned=jobs_assigned,
            jobs_completed=jobs_completed,
            jobs_pending=jobs_assigned - jobs_completed,
            infractions_today=2,  # Demo data
            safety_incidents=0,
            completion_rate=0.92,
            average_completion_time=4.5,
            total_cost_today=28500,
            cost_vs_budget=0.78,
            crews_performance={"crew_001": 0.95, "crew_002": 0.88}
        )
        
        return {
            "metrics": metrics.dict(),
            "crews": list(crews_db.values()),
            "recent_jobs": list(job_assignments_db.values())[:10],
            "alerts": [
                {"type": "warning", "message": "Crew Bravo running behind schedule"},
                {"type": "info", "message": "Weather alert: High winds expected"}
            ]
        }
    
    elif user.role == UserRole.FOREMAN:
        # Foreman sees only their crew
        crew = crews_db.get(user.crew_id)
        if not crew:
            raise HTTPException(status_code=404, detail="Crew not found")
        
        crew_jobs = [j for j in job_assignments_db.values() if j.crew_id == user.crew_id]
        
        return {
            "crew": crew.dict(),
            "current_job": next((j for j in crew_jobs if j.status == "in_progress"), None),
            "pending_jobs": [j for j in crew_jobs if j.status == "pending"],
            "completed_today": sum(1 for j in crew_jobs if j.status == "completed" and j.completion_time and j.completion_time.date() == datetime.now().date()),
            "safety_checks": {
                "ppe": True,
                "equipment": True,
                "site_secured": True,
                "weather_clear": True
            },
            "crew_hours_today": 28.5
        }

@router.post("/crews")
async def create_crew(
    name: str = Form(...),
    foreman_id: str = Form(...),
    general_foreman_id: str = Form(...),
    classification: str = Form(...),
    location: str = Form(...),
    members: str = Form(...)  # JSON string of member IDs
):
    """Create a new crew (GF only)"""
    crew = Crew(
        id=f"crew_{len(crews_db) + 1:03d}",
        name=name,
        foreman_id=foreman_id,
        general_foreman_id=general_foreman_id,
        members=json.loads(members),
        classification=classification,
        location=location,
        status="active",
        created_at=datetime.now()
    )
    
    crews_db[crew.id] = crew
    
    # Notify connected clients
    await notify_clients("crew_created", crew.dict())
    
    return crew

@router.get("/crews")
async def get_crews(user_id: str):
    """Get crews based on user permissions"""
    user = await get_current_user(user_id)
    
    if user.has_permission(Permission.VIEW_ALL_CREWS):
        return list(crews_db.values())
    elif user.has_permission(Permission.VIEW_OWN_CREW):
        crew = crews_db.get(user.crew_id)
        return [crew] if crew else []
    
    raise HTTPException(status_code=403, detail="Insufficient permissions")

@router.put("/crews/{crew_id}/status")
async def update_crew_status(crew_id: str, request: CrewUpdateRequest, user_id: str = Form(...)):
    """Update crew status (Foreman/GF)"""
    user = await get_current_user(user_id)
    
    if not user.can_manage_crew(crew_id):
        raise HTTPException(status_code=403, detail="Cannot manage this crew")
    
    crew = crews_db.get(crew_id)
    if not crew:
        raise HTTPException(status_code=404, detail="Crew not found")
    
    # Update crew status
    crew.status = request.status
    if request.location:
        crew.location = request.location
    
    # Create status update record
    status_update = CrewStatusUpdate(
        crew_id=crew_id,
        updated_by=user_id,
        timestamp=datetime.now(),
        status=request.status,
        location=request.location,
        progress_percentage=request.progress,
        notes=request.notes
    )
    
    status_updates_db.append(status_update)
    
    # Notify GF and other connected clients
    await notify_clients("crew_status_updated", {
        "crew": crew.dict(),
        "update": status_update.dict()
    })
    
    return {"success": True, "crew": crew, "update": status_update}

@router.post("/jobs/assign")
async def assign_job(request: JobAssignmentRequest, user_id: str = Form(...)):
    """Assign job package to crew (GF only)"""
    user = await get_current_user(user_id)
    
    if not user.has_permission(Permission.ASSIGN_JOB_PACKAGE):
        raise HTTPException(status_code=403, detail="Cannot assign jobs")
    
    assignment = JobAssignment(
        id=f"ja_{len(job_assignments_db) + 1:03d}",
        job_package_id=request.job_package_id,
        crew_id=request.crew_id,
        assigned_by=user_id,
        assigned_to=request.foreman_id,
        assigned_at=datetime.now(),
        due_date=request.due_date,
        status="pending",
        notes=request.notes,
        cost_estimate=request.estimated_cost,
        infractions_count=0
    )
    
    job_assignments_db[assignment.id] = assignment
    
    # Update crew's current job
    crew = crews_db.get(request.crew_id)
    if crew:
        crew.current_job_id = assignment.id
    
    # Notify foreman
    await notify_clients("job_assigned", assignment.dict())
    
    return assignment

@router.put("/jobs/{job_id}/status")
async def update_job_status(
    job_id: str, 
    status: str = Form(...),
    progress: Optional[int] = Form(None),
    notes: Optional[str] = Form(None),
    user_id: str = Form(...)
):
    """Update job status (Foreman/GF)"""
    user = await get_current_user(user_id)
    
    if not user.has_permission(Permission.UPDATE_JOB_STATUS):
        raise HTTPException(status_code=403, detail="Cannot update job status")
    
    job = job_assignments_db.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Update job
    job.status = status
    if status == "completed":
        job.completion_time = datetime.now()
    
    if notes:
        job.notes = (job.notes or "") + f"\n[{datetime.now().isoformat()}] {notes}"
    
    # Notify GF
    await notify_clients("job_status_updated", {
        "job": job.dict(),
        "updated_by": user_id,
        "progress": progress
    })
    
    return job

@router.post("/time-entry")
async def submit_time_entry(request: TimeEntryRequest, user_id: str = Form(...)):
    """Submit time entry for crew member"""
    user = await get_current_user(user_id)
    
    if not user.can_manage_crew(request.crew_id):
        raise HTTPException(status_code=403, detail="Cannot submit time for this crew")
    
    # In production, save to database
    time_entry = {
        "id": f"te_{datetime.now().timestamp()}",
        "crew_id": request.crew_id,
        "member_id": request.member_id,
        "hours": request.hours,
        "date": request.date.isoformat(),
        "job_id": request.job_id,
        "submitted_by": user_id,
        "submitted_at": datetime.now().isoformat()
    }
    
    # Calculate cost
    hourly_rate = 85  # Example rate
    cost = request.hours * hourly_rate
    
    # Update job actual cost
    job = job_assignments_db.get(request.job_id)
    if job:
        job.actual_cost = (job.actual_cost or 0) + cost
    
    return {"success": True, "time_entry": time_entry, "cost": cost}

@router.post("/safety/report")
async def submit_safety_report(request: SafetyReportRequest, user_id: str = Form(...)):
    """Submit safety incident report"""
    user = await get_current_user(user_id)
    
    safety_report = {
        "id": f"sr_{datetime.now().timestamp()}",
        "crew_id": request.crew_id,
        "reported_by": user_id,
        "timestamp": datetime.now().isoformat(),
        "incident_type": request.incident_type,
        "severity": request.severity,
        "description": request.description,
        "photos": request.photos
    }
    
    # Notify GF immediately
    await notify_clients("safety_incident", safety_report, priority="high")
    
    return {"success": True, "report": safety_report}

@router.post("/photos/upload")
async def upload_photo(file: UploadFile = File(...), job_id: str = Form(...), user_id: str = Form(...)):
    """Upload photo for job documentation"""
    user = await get_current_user(user_id)
    
    # In production, save to cloud storage
    file_content = await file.read()
    file_url = f"https://storage.nexa.com/photos/{job_id}/{file.filename}"
    
    photo_record = {
        "id": f"photo_{datetime.now().timestamp()}",
        "job_id": job_id,
        "url": file_url,
        "uploaded_by": user_id,
        "timestamp": datetime.now().isoformat(),
        "filename": file.filename,
        "size": len(file_content)
    }
    
    return {"success": True, "photo": photo_record}

@router.get("/notifications/{user_id}")
async def get_notifications(user_id: str, limit: int = 20):
    """Get user notifications"""
    user = await get_current_user(user_id)
    
    # Demo notifications based on role
    if user.role == UserRole.GENERAL_FOREMAN:
        notifications = [
            {"type": "job_completed", "message": "Crew Alpha completed TAG-2 replacement", "timestamp": datetime.now() - timedelta(minutes=15)},
            {"type": "safety", "message": "All crews passed morning safety check", "timestamp": datetime.now() - timedelta(hours=2)},
            {"type": "alert", "message": "Crew Bravo requesting additional equipment", "timestamp": datetime.now() - timedelta(hours=3)},
        ]
    else:
        notifications = [
            {"type": "job_assigned", "message": "New job assigned: 07D Cable Replacement", "timestamp": datetime.now() - timedelta(hours=1)},
            {"type": "reminder", "message": "Submit daily report by 5 PM", "timestamp": datetime.now() - timedelta(hours=2)},
        ]
    
    return notifications[:limit]

# WebSocket helper for real-time updates
async def notify_clients(event_type: str, data: Any, priority: str = "normal"):
    """Send real-time notification to connected clients"""
    message = {
        "event": event_type,
        "data": data,
        "timestamp": datetime.now().isoformat(),
        "priority": priority
    }
    
    # In production, use WebSocket connections
    # For now, just log
    print(f"Notification: {event_type} - {priority}")
    
    # Broadcast to all connected clients
    for connection in active_connections.values():
        try:
            await connection.send_json(message)
        except:
            pass  # Handle disconnected clients

# Initialize demo data
def init_demo_data():
    """Initialize demo data for testing"""
    # Create demo crews
    crews_db["crew_001"] = Crew(
        id="crew_001",
        name="Crew Alpha",
        foreman_id="f_001",
        general_foreman_id="gf_001",
        members=["m_001", "m_002", "m_003"],
        classification="IBEW Journeyman",
        location="Stockton North",
        status="active",
        created_at=datetime.now()
    )
    
    crews_db["crew_002"] = Crew(
        id="crew_002",
        name="Crew Bravo",
        foreman_id="f_002",
        general_foreman_id="gf_001",
        members=["m_004", "m_005", "m_006"],
        classification="IBEW Apprentice",
        location="Stockton South",
        status="active",
        created_at=datetime.now()
    )
    
    # Create demo job assignments
    job_assignments_db["ja_001"] = JobAssignment(
        id="ja_001",
        job_package_id="JP-2025-001",
        crew_id="crew_001",
        assigned_by="gf_001",
        assigned_to="f_001",
        assigned_at=datetime.now() - timedelta(hours=3),
        due_date=datetime.now() + timedelta(days=1),
        status="in_progress",
        cost_estimate=12500,
        infractions_count=0
    )

# Initialize on module load
init_demo_data()
