"""
NEXA User Roles and Permissions System
"""
from enum import Enum
from typing import List, Dict, Optional
from pydantic import BaseModel
from datetime import datetime

class UserRole(str, Enum):
    """User role definitions"""
    ADMIN = "admin"
    GENERAL_FOREMAN = "general_foreman"  # GF - Oversees multiple crews
    FOREMAN = "foreman"  # Manages single crew
    CREW_MEMBER = "crew_member"  # Field worker
    INSPECTOR = "inspector"  # Quality control
    CLIENT = "client"  # PG&E representatives

class Permission(str, Enum):
    """System permissions"""
    # Document permissions
    VIEW_ALL_DOCUMENTS = "view_all_documents"
    VIEW_CREW_DOCUMENTS = "view_crew_documents"
    UPLOAD_DOCUMENTS = "upload_documents"
    APPROVE_DOCUMENTS = "approve_documents"
    
    # Crew management
    MANAGE_ALL_CREWS = "manage_all_crews"
    MANAGE_OWN_CREW = "manage_own_crew"
    VIEW_ALL_CREWS = "view_all_crews"
    VIEW_OWN_CREW = "view_own_crew"
    
    # Job package permissions
    CREATE_JOB_PACKAGE = "create_job_package"
    ASSIGN_JOB_PACKAGE = "assign_job_package"
    UPDATE_JOB_STATUS = "update_job_status"
    APPROVE_COMPLETION = "approve_completion"
    
    # Financial permissions
    VIEW_ALL_COSTS = "view_all_costs"
    VIEW_CREW_COSTS = "view_crew_costs"
    APPROVE_COSTS = "approve_costs"
    
    # System permissions
    MANAGE_USERS = "manage_users"
    VIEW_ANALYTICS = "view_analytics"
    CONFIGURE_SYSTEM = "configure_system"

# Role-Permission Mapping
ROLE_PERMISSIONS: Dict[UserRole, List[Permission]] = {
    UserRole.ADMIN: [p for p in Permission],  # All permissions
    
    UserRole.GENERAL_FOREMAN: [
        Permission.VIEW_ALL_DOCUMENTS,
        Permission.UPLOAD_DOCUMENTS,
        Permission.APPROVE_DOCUMENTS,
        Permission.MANAGE_ALL_CREWS,
        Permission.VIEW_ALL_CREWS,
        Permission.CREATE_JOB_PACKAGE,
        Permission.ASSIGN_JOB_PACKAGE,
        Permission.UPDATE_JOB_STATUS,
        Permission.APPROVE_COMPLETION,
        Permission.VIEW_ALL_COSTS,
        Permission.APPROVE_COSTS,
        Permission.VIEW_ANALYTICS,
    ],
    
    UserRole.FOREMAN: [
        Permission.VIEW_CREW_DOCUMENTS,
        Permission.UPLOAD_DOCUMENTS,
        Permission.MANAGE_OWN_CREW,
        Permission.VIEW_OWN_CREW,
        Permission.UPDATE_JOB_STATUS,
        Permission.VIEW_CREW_COSTS,
        Permission.VIEW_ANALYTICS,
    ],
    
    UserRole.CREW_MEMBER: [
        Permission.VIEW_CREW_DOCUMENTS,
        Permission.VIEW_OWN_CREW,
        Permission.UPDATE_JOB_STATUS,
    ],
    
    UserRole.INSPECTOR: [
        Permission.VIEW_ALL_DOCUMENTS,
        Permission.UPLOAD_DOCUMENTS,
        Permission.VIEW_ALL_CREWS,
        Permission.APPROVE_COMPLETION,
        Permission.VIEW_ANALYTICS,
    ],
    
    UserRole.CLIENT: [
        Permission.VIEW_ALL_DOCUMENTS,
        Permission.VIEW_ALL_CREWS,
        Permission.VIEW_ALL_COSTS,
        Permission.VIEW_ANALYTICS,
    ],
}

class User(BaseModel):
    """User model"""
    id: str
    email: str
    name: str
    role: UserRole
    crew_id: Optional[str] = None  # For Foreman and Crew Members
    phone: Optional[str] = None
    created_at: datetime
    last_login: Optional[datetime] = None
    is_active: bool = True
    
    def has_permission(self, permission: Permission) -> bool:
        """Check if user has specific permission"""
        return permission in ROLE_PERMISSIONS.get(self.role, [])
    
    def can_manage_crew(self, crew_id: str) -> bool:
        """Check if user can manage specific crew"""
        if self.role == UserRole.GENERAL_FOREMAN:
            return True
        elif self.role == UserRole.FOREMAN:
            return self.crew_id == crew_id
        return False
    
    def can_view_document(self, document_crew_id: Optional[str]) -> bool:
        """Check if user can view document"""
        if self.has_permission(Permission.VIEW_ALL_DOCUMENTS):
            return True
        elif self.has_permission(Permission.VIEW_CREW_DOCUMENTS):
            return document_crew_id == self.crew_id
        return False

class Crew(BaseModel):
    """Crew model"""
    id: str
    name: str
    foreman_id: str
    general_foreman_id: str
    members: List[str]  # List of user IDs
    classification: str  # IBEW classification
    location: str
    status: str  # active, on_break, completed
    current_job_id: Optional[str] = None
    created_at: datetime
    
class JobAssignment(BaseModel):
    """Job package assignment"""
    id: str
    job_package_id: str
    crew_id: str
    assigned_by: str  # GF user ID
    assigned_to: str  # Foreman user ID
    assigned_at: datetime
    due_date: datetime
    status: str  # pending, in_progress, completed, rejected
    completion_time: Optional[datetime] = None
    notes: Optional[str] = None
    cost_estimate: Optional[float] = None
    actual_cost: Optional[float] = None
    infractions_count: int = 0
    
class CrewStatusUpdate(BaseModel):
    """Real-time crew status update"""
    crew_id: str
    updated_by: str
    timestamp: datetime
    status: str
    location: Optional[str] = None
    progress_percentage: Optional[int] = None
    issues: Optional[List[str]] = None
    photos: Optional[List[str]] = None  # URLs to photos
    weather_conditions: Optional[str] = None
    safety_incidents: int = 0
    
class DashboardMetrics(BaseModel):
    """Dashboard metrics for GF/Foreman"""
    total_crews: int
    active_crews: int
    jobs_assigned: int
    jobs_completed: int
    jobs_pending: int
    infractions_today: int
    safety_incidents: int
    completion_rate: float
    average_completion_time: float
    total_cost_today: float
    cost_vs_budget: float
    crews_performance: Dict[str, float]  # crew_id -> performance_score
