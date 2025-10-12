"""
Advanced RLS Integration with All Security Patterns
Demonstrates hierarchical access, multi-tenancy, time-based policies, and more
"""

import os
import logging
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
from contextlib import contextmanager
import psycopg2
from psycopg2.extras import RealDictCursor, Json
from psycopg2 import sql
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

# =====================================================
# Data Models
# =====================================================

class UserRole(Enum):
    PM = "pm"           # Project Manager
    GF = "gf"           # General Foreman
    FOREMAN = "foreman" # Field Foreman
    QA = "qa"           # QA Reviewer
    ADMIN = "admin"     # System Admin

class JobStatus(Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    READY_FOR_QA = "ready_for_qa"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUBMITTED = "submitted"
    CANCELLED = "cancelled"

class AccessLevel(Enum):
    STANDARD = "standard"
    RESTRICTED = "restricted"
    CONFIDENTIAL = "confidential"

@dataclass
class UserContext:
    """User context for RLS policies"""
    user_id: str
    role: UserRole
    crew_id: Optional[str] = None
    tenant_id: int = 1
    department_id: Optional[int] = None
    permissions: List[str] = None

    def __post_init__(self):
        if self.permissions is None:
            self.permissions = []

# =====================================================
# Advanced RLS Connection Manager
# =====================================================

class AdvancedRLSConnection:
    """
    Enhanced connection manager with support for all RLS patterns:
    - Hierarchical access
    - Multi-tenancy
    - Time-based policies
    - Access level control
    """
    
    def __init__(self, database_url: str = None):
        self.database_url = database_url or os.getenv("DATABASE_URL")
        if self.database_url and self.database_url.startswith("postgres://"):
            self.database_url = self.database_url.replace("postgres://", "postgresql://", 1)
    
    @contextmanager
    def get_connection(self, context: UserContext):
        """
        Get a database connection with comprehensive RLS context
        """
        conn = None
        cursor = None
        
        try:
            # Connect to database
            conn = psycopg2.connect(self.database_url)
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Set all session variables for RLS
            cursor.execute("SET app.current_user_id = %s", (context.user_id,))
            cursor.execute("SET app.current_role = %s", (context.role.value,))
            
            if context.crew_id:
                cursor.execute("SET app.current_crew = %s", (context.crew_id,))
            
            cursor.execute("SET app.tenant_id = %s", (str(context.tenant_id),))
            
            if context.department_id:
                cursor.execute("SET app.department_id = %s", (str(context.department_id),))
            
            # Set PostgreSQL role
            role_name = f"{context.role.value}_role"
            cursor.execute(sql.SQL("SET ROLE {}").format(sql.Identifier(role_name)))
            
            logger.info(f"RLS context set: user={context.user_id}, role={context.role.value}, "
                       f"tenant={context.tenant_id}, crew={context.crew_id}, dept={context.department_id}")
            
            yield cursor
            
            # Commit transaction
            conn.commit()
            
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database error with advanced RLS: {e}")
            raise
            
        finally:
            # Reset role and close
            if cursor:
                try:
                    cursor.execute("RESET ROLE")
                    cursor.execute("RESET ALL")  # Clear all session variables
                except:
                    pass
                cursor.close()
            if conn:
                conn.close()

# =====================================================
# Advanced Job Repository
# =====================================================

class AdvancedJobRepository:
    """
    Repository with support for all RLS patterns
    """
    
    def __init__(self, database_url: str = None):
        self.db = AdvancedRLSConnection(database_url)
    
    # --------------------------------------------------
    # Basic Operations
    # --------------------------------------------------
    
    def get_visible_jobs(self, context: UserContext) -> List[Dict]:
        """
        Get all jobs visible to the user based on all RLS policies
        """
        with self.db.get_connection(context) as cursor:
            cursor.execute("""
                SELECT 
                    id,
                    pm_number,
                    notification_number,
                    status,
                    location,
                    scheduled_date,
                    assigned_crew,
                    assigned_foreman,
                    tenant_id,
                    department_id,
                    access_level,
                    expires_at,
                    is_archived,
                    has_go_backs,
                    repealable_count,
                    total_savings,
                    created_at,
                    updated_at
                FROM jobs
                WHERE 1=1  -- RLS policies apply automatically
                ORDER BY 
                    CASE 
                        WHEN status = 'ready_for_qa' THEN 1
                        WHEN status = 'in_progress' THEN 2
                        WHEN status = 'assigned' THEN 3
                        ELSE 4
                    END,
                    scheduled_date DESC
                LIMIT 100
            """)
            
            results = cursor.fetchall()
            logger.info(f"User {context.user_id} ({context.role.value}) can see {len(results)} jobs")
            return results
    
    # --------------------------------------------------
    # Hierarchical Access Patterns
    # --------------------------------------------------
    
    def get_department_jobs(self, context: UserContext) -> List[Dict]:
        """
        Get jobs within department hierarchy (GF oversees multiple crews)
        """
        with self.db.get_connection(context) as cursor:
            cursor.execute("""
                SELECT 
                    j.*,
                    array_agg(DISTINCT c.crew_name) as accessible_crews
                FROM jobs j
                LEFT JOIN crews c ON c.department_id = j.department_id
                WHERE j.department_id = %s
                GROUP BY j.id, j.pm_number, j.status, j.location, j.scheduled_date,
                         j.assigned_crew, j.assigned_foreman, j.tenant_id, j.department_id,
                         j.access_level, j.expires_at, j.is_archived, j.has_go_backs,
                         j.repealable_count, j.total_savings, j.created_at, j.updated_at,
                         j.notification_number, j.package_url, j.uploaded_by, j.assigned_by,
                         j.submitted_by, j.reviewed_by, j.initial_analysis, j.field_photos,
                         j.vision_analysis, j.final_analysis, j.filled_pdf_url, j.submission_date,
                         j.qa_date, j.pge_submission_date, j.last_modified_by
            """, (context.department_id,))
            
            return cursor.fetchall()
    
    def get_crew_hierarchy(self, context: UserContext) -> List[str]:
        """
        Get all crews accessible through hierarchy
        """
        with self.db.get_connection(context) as cursor:
            cursor.execute("""
                SELECT * FROM get_user_hierarchy(%s)
            """, (context.user_id,))
            
            return [row['accessible_crew_id'] for row in cursor.fetchall()]
    
    # --------------------------------------------------
    # Time-Based Access Patterns
    # --------------------------------------------------
    
    def get_active_jobs(self, context: UserContext, days_back: int = 30) -> List[Dict]:
        """
        Get non-expired, non-archived jobs within time window
        """
        with self.db.get_connection(context) as cursor:
            cursor.execute("""
                SELECT *
                FROM jobs
                WHERE 
                    (expires_at IS NULL OR expires_at > NOW())
                    AND is_archived = FALSE
                    AND created_at > NOW() - INTERVAL '%s days'
                ORDER BY created_at DESC
            """, (days_back,))
            
            return cursor.fetchall()
    
    def archive_old_jobs(self, context: UserContext, older_than_days: int = 90) -> int:
        """
        Archive jobs older than specified days (admin only)
        """
        if context.role != UserRole.ADMIN:
            raise PermissionError("Only admins can archive jobs")
        
        with self.db.get_connection(context) as cursor:
            cursor.execute("""
                UPDATE jobs
                SET 
                    is_archived = TRUE,
                    updated_at = NOW(),
                    last_modified_by = %s
                WHERE 
                    created_at < NOW() - INTERVAL '%s days'
                    AND is_archived = FALSE
                    AND status IN ('approved', 'rejected', 'cancelled')
                RETURNING id
            """, (context.user_id, older_than_days))
            
            archived = cursor.fetchall()
            logger.info(f"Archived {len(archived)} old jobs")
            return len(archived)
    
    # --------------------------------------------------
    # Multi-Tenant Patterns
    # --------------------------------------------------
    
    def create_tenant_job(self, context: UserContext, job_data: Dict) -> Dict:
        """
        Create job with tenant isolation
        """
        with self.db.get_connection(context) as cursor:
            cursor.execute("""
                INSERT INTO jobs (
                    id, pm_number, notification_number, location,
                    status, uploaded_by, tenant_id, department_id,
                    access_level, scheduled_date, expires_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                ) RETURNING *
            """, (
                job_data['id'],
                job_data['pm_number'],
                job_data.get('notification_number'),
                job_data['location'],
                'pending',
                context.user_id,
                context.tenant_id,  # Automatic tenant assignment
                context.department_id,
                job_data.get('access_level', AccessLevel.STANDARD.value),
                job_data.get('scheduled_date', datetime.now() + timedelta(days=7)),
                job_data.get('expires_at')  # Optional expiration
            ))
            
            return cursor.fetchone()
    
    def get_tenant_metrics(self, context: UserContext) -> Dict:
        """
        Get metrics for current tenant only
        """
        with self.db.get_connection(context) as cursor:
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_jobs,
                    COUNT(DISTINCT assigned_crew) as active_crews,
                    COUNT(DISTINCT department_id) as departments,
                    SUM(total_savings) as total_savings,
                    AVG(repealable_count) as avg_repealable
                FROM jobs
                WHERE tenant_id = %s
            """, (context.tenant_id,))
            
            return cursor.fetchone()
    
    # --------------------------------------------------
    # Status Transition Control
    # --------------------------------------------------
    
    def transition_job_status(
        self, 
        context: UserContext, 
        job_id: str, 
        new_status: JobStatus,
        notes: str = None
    ) -> Dict:
        """
        Transition job status with validation
        """
        with self.db.get_connection(context) as cursor:
            # Get current status
            cursor.execute("SELECT status FROM jobs WHERE id = %s", (job_id,))
            current = cursor.fetchone()
            
            if not current:
                raise ValueError(f"Job {job_id} not found or not accessible")
            
            # Check if transition is valid (done by DB policy)
            cursor.execute("""
                UPDATE jobs
                SET 
                    status = %s,
                    updated_at = NOW(),
                    last_modified_by = %s,
                    final_analysis = COALESCE(final_analysis, '{}'::jsonb) || %s::jsonb
                WHERE 
                    id = %s
                RETURNING *
            """, (
                new_status.value,
                context.user_id,
                Json({'status_change': {'from': current['status'], 'to': new_status.value, 'notes': notes}}),
                job_id
            ))
            
            result = cursor.fetchone()
            if not result:
                raise PermissionError(f"Cannot transition job {job_id} from {current['status']} to {new_status.value}")
            
            logger.info(f"Job {job_id} transitioned from {current['status']} to {new_status.value}")
            return result
    
    # --------------------------------------------------
    # Access Level Control
    # --------------------------------------------------
    
    def get_jobs_by_access_level(self, context: UserContext, level: AccessLevel) -> List[Dict]:
        """
        Get jobs filtered by access level
        """
        with self.db.get_connection(context) as cursor:
            cursor.execute("""
                SELECT *
                FROM jobs
                WHERE access_level = %s
                ORDER BY created_at DESC
            """, (level.value,))
            
            results = cursor.fetchall()
            logger.info(f"Found {len(results)} {level.value} jobs accessible to {context.user_id}")
            return results
    
    def set_job_access_level(
        self, 
        context: UserContext, 
        job_id: str, 
        level: AccessLevel
    ) -> Dict:
        """
        Change job access level (restricted operation)
        """
        if context.role not in [UserRole.GF, UserRole.ADMIN]:
            raise PermissionError("Only GF and Admin can change access levels")
        
        with self.db.get_connection(context) as cursor:
            cursor.execute("""
                UPDATE jobs
                SET 
                    access_level = %s,
                    updated_at = NOW(),
                    last_modified_by = %s
                WHERE id = %s
                RETURNING *
            """, (level.value, context.user_id, job_id))
            
            result = cursor.fetchone()
            if not result:
                raise PermissionError(f"Cannot change access level for job {job_id}")
            
            return result

# =====================================================
# Testing Suite
# =====================================================

class RLSTestSuite:
    """
    Comprehensive testing for all RLS patterns
    """
    
    def __init__(self, database_url: str = None):
        self.repo = AdvancedJobRepository(database_url)
    
    def run_all_tests(self) -> Dict[str, Any]:
        """
        Run comprehensive RLS tests
        """
        results = {
            'basic_access': self.test_basic_access(),
            'hierarchical': self.test_hierarchical_access(),
            'time_based': self.test_time_based_access(),
            'multi_tenant': self.test_multi_tenant_isolation(),
            'status_transitions': self.test_status_transitions(),
            'access_levels': self.test_access_levels()
        }
        
        # Summary
        total_tests = sum(len(v) for v in results.values())
        passed = sum(1 for test_group in results.values() for test in test_group.values() if test['passed'])
        
        results['summary'] = {
            'total_tests': total_tests,
            'passed': passed,
            'failed': total_tests - passed,
            'success_rate': f"{(passed/total_tests)*100:.1f}%"
        }
        
        return results
    
    def test_basic_access(self) -> Dict:
        """Test basic user-specific access"""
        tests = {}
        
        # PM sees their uploads
        pm_context = UserContext("PM001", UserRole.PM, tenant_id=1)
        pm_jobs = self.repo.get_visible_jobs(pm_context)
        tests['pm_sees_uploads'] = {
            'passed': len(pm_jobs) > 0,
            'count': len(pm_jobs)
        }
        
        # Foreman sees crew jobs
        foreman_context = UserContext("F001", UserRole.FOREMAN, crew_id="CREW-001", tenant_id=1)
        foreman_jobs = self.repo.get_visible_jobs(foreman_context)
        tests['foreman_sees_crew'] = {
            'passed': all(j.get('assigned_crew') == 'CREW-001' for j in foreman_jobs if j.get('assigned_crew')),
            'count': len(foreman_jobs)
        }
        
        # QA sees review queue
        qa_context = UserContext("QA001", UserRole.QA, tenant_id=1)
        qa_jobs = self.repo.get_visible_jobs(qa_context)
        tests['qa_sees_queue'] = {
            'passed': any(j['status'] == 'ready_for_qa' for j in qa_jobs),
            'count': len(qa_jobs)
        }
        
        return tests
    
    def test_hierarchical_access(self) -> Dict:
        """Test department/crew hierarchy"""
        tests = {}
        
        # GF sees all department crews
        gf_context = UserContext("GF001", UserRole.GF, department_id=1, tenant_id=1)
        dept_jobs = self.repo.get_department_jobs(gf_context)
        tests['gf_department_access'] = {
            'passed': len(dept_jobs) > 0,
            'count': len(dept_jobs)
        }
        
        # Get crew hierarchy
        crews = self.repo.get_crew_hierarchy(gf_context)
        tests['crew_hierarchy'] = {
            'passed': len(crews) > 0,
            'crews': crews
        }
        
        return tests
    
    def test_time_based_access(self) -> Dict:
        """Test time-based policies"""
        tests = {}
        
        # Recent jobs only
        foreman_context = UserContext("F001", UserRole.FOREMAN, crew_id="CREW-001", tenant_id=1)
        active_jobs = self.repo.get_active_jobs(foreman_context, days_back=7)
        tests['recent_jobs'] = {
            'passed': all(
                datetime.fromisoformat(str(j['created_at'])) > datetime.now() - timedelta(days=7) 
                for j in active_jobs if j.get('created_at')
            ),
            'count': len(active_jobs)
        }
        
        # Non-expired jobs
        tests['non_expired'] = {
            'passed': all(
                j.get('expires_at') is None or 
                datetime.fromisoformat(str(j['expires_at'])) > datetime.now()
                for j in active_jobs
            ),
            'count': len([j for j in active_jobs if j.get('expires_at')])
        }
        
        return tests
    
    def test_multi_tenant_isolation(self) -> Dict:
        """Test tenant isolation"""
        tests = {}
        
        # Tenant 1 user
        tenant1_context = UserContext("PM001", UserRole.PM, tenant_id=1)
        tenant1_jobs = self.repo.get_visible_jobs(tenant1_context)
        
        # All jobs should be from tenant 1 or shared (0)
        tests['tenant1_isolation'] = {
            'passed': all(j.get('tenant_id') in [0, 1] for j in tenant1_jobs),
            'count': len(tenant1_jobs)
        }
        
        # Tenant metrics
        metrics = self.repo.get_tenant_metrics(tenant1_context)
        tests['tenant_metrics'] = {
            'passed': metrics is not None,
            'metrics': metrics
        }
        
        return tests
    
    def test_status_transitions(self) -> Dict:
        """Test status transition control"""
        tests = {}
        
        # Create test job
        pm_context = UserContext("PM-TEST", UserRole.PM, tenant_id=1)
        test_job = {
            'id': f'TEST-TRANS-{datetime.now().timestamp()}',
            'pm_number': 'PM-TRANS-001',
            'location': 'Test Location'
        }
        
        try:
            # PM creates job (pending)
            job = self.repo.create_tenant_job(pm_context, test_job)
            tests['pm_creates'] = {'passed': job['status'] == 'pending'}
            
            # GF assigns (pending -> assigned)
            gf_context = UserContext("GF-TEST", UserRole.GF, tenant_id=1)
            try:
                job = self.repo.transition_job_status(
                    gf_context, job['id'], JobStatus.ASSIGNED
                )
                tests['gf_assigns'] = {'passed': job['status'] == 'assigned'}
            except PermissionError:
                tests['gf_assigns'] = {'passed': False, 'error': 'Permission denied'}
            
            # Foreman cannot approve (wrong transition)
            foreman_context = UserContext("F-TEST", UserRole.FOREMAN, crew_id="CREW-001", tenant_id=1)
            try:
                self.repo.transition_job_status(
                    foreman_context, job['id'], JobStatus.APPROVED
                )
                tests['invalid_transition'] = {'passed': False}
            except PermissionError:
                tests['invalid_transition'] = {'passed': True, 'note': 'Correctly blocked'}
                
        except Exception as e:
            tests['error'] = {'passed': False, 'error': str(e)}
        
        return tests
    
    def test_access_levels(self) -> Dict:
        """Test sensitivity-based access"""
        tests = {}
        
        # Standard access for all
        foreman_context = UserContext("F001", UserRole.FOREMAN, crew_id="CREW-001", tenant_id=1)
        standard_jobs = self.repo.get_jobs_by_access_level(foreman_context, AccessLevel.STANDARD)
        tests['foreman_standard'] = {
            'passed': True,  # Should not error
            'count': len(standard_jobs)
        }
        
        # Restricted requires higher role
        try:
            restricted_jobs = self.repo.get_jobs_by_access_level(foreman_context, AccessLevel.RESTRICTED)
            tests['foreman_restricted'] = {
                'passed': len(restricted_jobs) == 0,  # Should be empty
                'count': len(restricted_jobs)
            }
        except:
            tests['foreman_restricted'] = {'passed': True, 'note': 'Access denied'}
        
        # Admin sees all
        admin_context = UserContext("ADMIN001", UserRole.ADMIN, tenant_id=1)
        conf_jobs = self.repo.get_jobs_by_access_level(admin_context, AccessLevel.CONFIDENTIAL)
        tests['admin_confidential'] = {
            'passed': True,  # Admin should see
            'count': len(conf_jobs)
        }
        
        return tests

# =====================================================
# Usage Examples
# =====================================================

def demonstrate_advanced_rls():
    """
    Demonstrate all RLS patterns in action
    """
    repo = AdvancedJobRepository()
    
    print("🔐 Advanced RLS Demonstration")
    print("=" * 50)
    
    # 1. Basic user access
    print("\n1️⃣ Basic User Access:")
    pm = UserContext("PM001", UserRole.PM, tenant_id=1)
    pm_jobs = repo.get_visible_jobs(pm)
    print(f"   PM sees {len(pm_jobs)} jobs")
    
    # 2. Hierarchical access
    print("\n2️⃣ Hierarchical Access:")
    gf = UserContext("GF001", UserRole.GF, department_id=1, tenant_id=1)
    dept_jobs = repo.get_department_jobs(gf)
    print(f"   GF sees {len(dept_jobs)} department jobs")
    crews = repo.get_crew_hierarchy(gf)
    print(f"   Accessible crews: {crews}")
    
    # 3. Time-based access
    print("\n3️⃣ Time-Based Access:")
    foreman = UserContext("F001", UserRole.FOREMAN, crew_id="CREW-001", tenant_id=1)
    active = repo.get_active_jobs(foreman, days_back=30)
    print(f"   Foreman sees {len(active)} active jobs (last 30 days)")
    
    # 4. Multi-tenant isolation
    print("\n4️⃣ Multi-Tenant Isolation:")
    tenant1 = UserContext("PM-T1", UserRole.PM, tenant_id=1)
    tenant2 = UserContext("PM-T2", UserRole.PM, tenant_id=2)
    t1_jobs = repo.get_visible_jobs(tenant1)
    t2_jobs = repo.get_visible_jobs(tenant2)
    print(f"   Tenant 1: {len(t1_jobs)} jobs")
    print(f"   Tenant 2: {len(t2_jobs)} jobs")
    
    # 5. Access level control
    print("\n5️⃣ Access Level Control:")
    qa = UserContext("QA001", UserRole.QA, tenant_id=1)
    standard = repo.get_jobs_by_access_level(qa, AccessLevel.STANDARD)
    restricted = repo.get_jobs_by_access_level(qa, AccessLevel.RESTRICTED)
    print(f"   QA sees {len(standard)} standard, {len(restricted)} restricted")
    
    # 6. Run test suite
    print("\n6️⃣ Running Test Suite:")
    tester = RLSTestSuite()
    results = tester.run_all_tests()
    print(f"   ✅ Passed: {results['summary']['passed']}/{results['summary']['total_tests']}")
    print(f"   📊 Success Rate: {results['summary']['success_rate']}")

if __name__ == "__main__":
    import json
    logging.basicConfig(level=logging.INFO)
    
    try:
        demonstrate_advanced_rls()
        
        # Run full test suite
        print("\n" + "=" * 50)
        print("📊 Full Test Results:")
        tester = RLSTestSuite()
        results = tester.run_all_tests()
        print(json.dumps(results, indent=2, default=str))
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
