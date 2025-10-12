"""
PostgreSQL RLS Integration for NEXA Platform
Provides secure database access with Row-Level Security policies
"""

import os
import logging
from typing import Optional, Dict, Any, List
from contextlib import contextmanager
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import sql
import hashlib
import secrets
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class RLSConnection:
    """
    Manages PostgreSQL connections with Row-Level Security
    Automatically sets user context for RLS policies
    """
    
    def __init__(self, database_url: str = None):
        self.database_url = database_url or os.getenv("DATABASE_URL")
        if self.database_url and self.database_url.startswith("postgres://"):
            self.database_url = self.database_url.replace("postgres://", "postgresql://", 1)
        
        self.connection = None
        self.cursor = None
        
    @contextmanager
    def get_connection(self, user_id: str, role: str, crew_id: Optional[str] = None):
        """
        Get a database connection with RLS context set
        
        Args:
            user_id: Current user ID
            role: User role (pm, gf, foreman, qa)
            crew_id: Crew ID for foreman role
            
        Yields:
            Database cursor with RLS context
        """
        conn = None
        cursor = None
        
        try:
            # Connect to database
            conn = psycopg2.connect(self.database_url)
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Set session variables for RLS
            cursor.execute("SET app.current_user_id = %s", (user_id,))
            cursor.execute("SET app.current_role = %s", (role,))
            if crew_id:
                cursor.execute("SET app.current_crew = %s", (crew_id,))
            
            # Set PostgreSQL role
            role_name = f"{role}_role"
            cursor.execute(sql.SQL("SET ROLE {}").format(sql.Identifier(role_name)))
            
            logger.info(f"RLS context set: user={user_id}, role={role}, crew={crew_id}")
            
            yield cursor
            
            # Commit transaction
            conn.commit()
            
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database error with RLS: {e}")
            raise
            
        finally:
            # Reset role and close
            if cursor:
                try:
                    cursor.execute("RESET ROLE")
                except:
                    pass
                cursor.close()
            if conn:
                conn.close()

class JobRepository:
    """
    Repository for job operations with RLS enforcement
    All queries automatically respect row-level security
    """
    
    def __init__(self, database_url: str = None):
        self.db = RLSConnection(database_url)
        
    def get_jobs_for_user(self, user_id: str, role: str, crew_id: Optional[str] = None) -> List[Dict]:
        """
        Get all jobs visible to the user based on their role
        RLS automatically filters results
        """
        with self.db.get_connection(user_id, role, crew_id) as cursor:
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
                    has_go_backs,
                    repealable_count,
                    total_savings
                FROM jobs
                ORDER BY scheduled_date DESC
                LIMIT 100
            """)
            
            results = cursor.fetchall()
            logger.info(f"User {user_id} ({role}) can see {len(results)} jobs")
            return results
    
    def create_job(self, user_id: str, job_data: Dict) -> Dict:
        """
        Create a new job (PM role only)
        """
        with self.db.get_connection(user_id, "pm") as cursor:
            cursor.execute("""
                INSERT INTO jobs (
                    id, pm_number, notification_number, location,
                    status, uploaded_by, scheduled_date
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s
                ) RETURNING *
            """, (
                job_data['id'],
                job_data['pm_number'],
                job_data.get('notification_number'),
                job_data['location'],
                'pending',
                user_id,
                job_data.get('scheduled_date', datetime.now() + timedelta(days=7))
            ))
            
            return cursor.fetchone()
    
    def assign_job(self, user_id: str, job_id: str, crew_id: str, foreman_id: str) -> Dict:
        """
        Assign job to crew (GF role only)
        """
        with self.db.get_connection(user_id, "gf") as cursor:
            cursor.execute("""
                UPDATE jobs 
                SET 
                    assigned_crew = %s,
                    assigned_foreman = %s,
                    assigned_by = %s,
                    status = 'assigned',
                    updated_at = NOW()
                WHERE id = %s
                RETURNING *
            """, (crew_id, foreman_id, user_id, job_id))
            
            result = cursor.fetchone()
            if not result:
                raise PermissionError(f"Cannot assign job {job_id} - check permissions")
            
            return result
    
    def submit_field_work(self, user_id: str, crew_id: str, job_id: str, data: Dict) -> Dict:
        """
        Submit field work (Foreman role only)
        """
        with self.db.get_connection(user_id, "foreman", crew_id) as cursor:
            cursor.execute("""
                UPDATE jobs 
                SET 
                    field_photos = %s,
                    vision_analysis = %s,
                    status = 'ready_for_qa',
                    submitted_by = %s,
                    submission_date = NOW(),
                    updated_at = NOW()
                WHERE id = %s
                RETURNING *
            """, (
                psycopg2.extras.Json(data.get('photos', [])),
                psycopg2.extras.Json(data.get('vision_analysis', {})),
                user_id,
                job_id
            ))
            
            result = cursor.fetchone()
            if not result:
                raise PermissionError(f"Cannot submit job {job_id} - not assigned to your crew")
            
            return result
    
    def review_job(self, user_id: str, job_id: str, approved: bool, comments: str = None) -> Dict:
        """
        Review job (QA role only)
        """
        with self.db.get_connection(user_id, "qa") as cursor:
            new_status = 'approved' if approved else 'rejected'
            
            cursor.execute("""
                UPDATE jobs 
                SET 
                    status = %s,
                    reviewed_by = %s,
                    qa_date = NOW(),
                    final_analysis = final_analysis || %s,
                    updated_at = NOW()
                WHERE id = %s AND status = 'ready_for_qa'
                RETURNING *
            """, (
                new_status,
                user_id,
                psycopg2.extras.Json({'qa_comments': comments} if comments else {}),
                job_id
            ))
            
            result = cursor.fetchone()
            if not result:
                raise PermissionError(f"Cannot review job {job_id} - not in QA queue or no permission")
            
            return result
    
    def get_metrics_by_role(self, user_id: str, role: str, crew_id: Optional[str] = None) -> Dict:
        """
        Get role-specific metrics respecting RLS
        """
        with self.db.get_connection(user_id, role, crew_id) as cursor:
            # Base metrics visible to all
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_jobs,
                    COUNT(*) FILTER (WHERE status = 'pending') as pending,
                    COUNT(*) FILTER (WHERE status = 'assigned') as assigned,
                    COUNT(*) FILTER (WHERE status = 'ready_for_qa') as in_qa,
                    COUNT(*) FILTER (WHERE status = 'approved') as approved,
                    COUNT(*) FILTER (WHERE has_go_backs) as with_go_backs,
                    SUM(repealable_count) as total_repealable,
                    SUM(total_savings) as total_savings
                FROM jobs
            """)
            
            metrics = cursor.fetchone()
            
            # Add role-specific metrics
            if role == "pm":
                cursor.execute("""
                    SELECT COUNT(*) as my_uploads
                    FROM jobs 
                    WHERE uploaded_by = %s
                """, (user_id,))
                metrics.update(cursor.fetchone())
                
            elif role == "gf":
                cursor.execute("""
                    SELECT 
                        COUNT(DISTINCT assigned_crew) as crews_active,
                        COUNT(*) FILTER (WHERE scheduled_date = CURRENT_DATE) as today_jobs
                    FROM jobs
                    WHERE status IN ('assigned', 'in_progress')
                """)
                metrics.update(cursor.fetchone())
                
            elif role == "foreman":
                cursor.execute("""
                    SELECT 
                        COUNT(*) as crew_jobs,
                        COUNT(*) FILTER (WHERE submitted_by = %s) as my_submissions
                    FROM jobs
                    WHERE assigned_crew = %s
                """, (user_id, crew_id))
                metrics.update(cursor.fetchone())
                
            elif role == "qa":
                cursor.execute("""
                    SELECT 
                        COUNT(*) as queue_size,
                        COUNT(*) FILTER (WHERE reviewed_by = %s) as my_reviews,
                        AVG(EXTRACT(EPOCH FROM (NOW() - submission_date))/3600) as avg_wait_hours
                    FROM jobs
                    WHERE status IN ('ready_for_qa', 'approved', 'rejected')
                """, (user_id,))
                metrics.update(cursor.fetchone())
            
            return metrics

class RLSMiddleware:
    """
    FastAPI/Flask middleware to automatically set RLS context
    """
    
    def __init__(self, app, database_url: str = None):
        self.app = app
        self.db = RLSConnection(database_url)
        
    def __call__(self, environ, start_response):
        # Extract user context from JWT or session
        user_id = environ.get('HTTP_X_USER_ID')
        user_role = environ.get('HTTP_X_USER_ROLE')
        user_crew = environ.get('HTTP_X_USER_CREW')
        
        # Store in request context for later use
        environ['rls.user_id'] = user_id
        environ['rls.role'] = user_role
        environ['rls.crew'] = user_crew
        
        return self.app(environ, start_response)

# FastAPI integration example
def setup_rls_fastapi(app):
    """
    Setup RLS for FastAPI application
    """
    from fastapi import Request, Depends, HTTPException
    from typing import Optional
    
    async def get_rls_context(request: Request) -> Dict:
        """
        Extract RLS context from request headers or JWT
        """
        # Get from JWT claims or headers
        user_id = request.headers.get('X-User-Id')
        user_role = request.headers.get('X-User-Role')
        user_crew = request.headers.get('X-User-Crew')
        
        if not user_id or not user_role:
            raise HTTPException(status_code=401, detail="Missing user context")
        
        # Validate role
        valid_roles = ['pm', 'gf', 'foreman', 'qa', 'admin']
        if user_role not in valid_roles:
            raise HTTPException(status_code=403, detail=f"Invalid role: {user_role}")
        
        return {
            'user_id': user_id,
            'role': user_role,
            'crew_id': user_crew
        }
    
    # Add to app state
    app.state.get_rls_context = get_rls_context
    
    # Example endpoint using RLS
    @app.get("/api/secure/jobs")
    async def get_jobs(rls: Dict = Depends(get_rls_context)):
        """
        Get jobs with RLS enforcement
        """
        repo = JobRepository()
        jobs = repo.get_jobs_for_user(
            user_id=rls['user_id'],
            role=rls['role'],
            crew_id=rls.get('crew_id')
        )
        return {"jobs": jobs, "count": len(jobs)}
    
    @app.get("/api/secure/metrics")
    async def get_metrics(rls: Dict = Depends(get_rls_context)):
        """
        Get role-specific metrics
        """
        repo = JobRepository()
        metrics = repo.get_metrics_by_role(
            user_id=rls['user_id'],
            role=rls['role'],
            crew_id=rls.get('crew_id')
        )
        return metrics
    
    return app

# Testing utilities
def test_rls_policies():
    """
    Test RLS policies with different roles
    """
    repo = JobRepository()
    
    test_cases = [
        ("PM001", "pm", None, "Project Manager"),
        ("GF001", "gf", None, "General Foreman"),
        ("F001", "foreman", "CREW-001", "Foreman for Crew 001"),
        ("QA001", "qa", None, "QA Reviewer"),
    ]
    
    results = {}
    
    for user_id, role, crew_id, description in test_cases:
        try:
            jobs = repo.get_jobs_for_user(user_id, role, crew_id)
            metrics = repo.get_metrics_by_role(user_id, role, crew_id)
            
            results[role] = {
                'description': description,
                'visible_jobs': len(jobs),
                'metrics': metrics,
                'sample_jobs': [j['id'] for j in jobs[:3]] if jobs else []
            }
            
            logger.info(f"✅ {description}: Can see {len(jobs)} jobs")
            
        except Exception as e:
            results[role] = {
                'description': description,
                'error': str(e)
            }
            logger.error(f"❌ {description}: {e}")
    
    return results

if __name__ == "__main__":
    # Test RLS implementation
    import json
    
    logging.basicConfig(level=logging.INFO)
    
    print("🔐 Testing PostgreSQL RLS Implementation")
    print("=" * 50)
    
    try:
        results = test_rls_policies()
        print(json.dumps(results, indent=2, default=str))
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
