-- NEXA PostgreSQL Schema with Row-Level Security (RLS)
-- Implements role-based access control for job workflow
-- Compatible with Render PostgreSQL service

-- =====================================================
-- CLEANUP (if rebuilding)
-- =====================================================
-- DROP POLICY IF EXISTS pm_jobs_policy ON jobs;
-- DROP POLICY IF EXISTS gf_jobs_policy ON jobs;
-- DROP POLICY IF EXISTS foreman_jobs_policy ON jobs;
-- DROP POLICY IF EXISTS qa_jobs_policy ON jobs;
-- DROP TABLE IF EXISTS jobs CASCADE;
-- DROP ROLE IF EXISTS pm_role;
-- DROP ROLE IF EXISTS gf_role;
-- DROP ROLE IF EXISTS foreman_role;
-- DROP ROLE IF EXISTS qa_role;

-- =====================================================
-- ROLES SETUP
-- =====================================================
-- Create application roles (not login roles, used via SET ROLE)
CREATE ROLE pm_role;         -- Project Manager
CREATE ROLE gf_role;         -- General Foreman
CREATE ROLE foreman_role;    -- Field Foreman
CREATE ROLE qa_role;         -- QA Reviewer
CREATE ROLE admin_role;      -- System Admin (bypass RLS)

-- Grant schema access
GRANT USAGE ON SCHEMA public TO pm_role, gf_role, foreman_role, qa_role, admin_role;

-- =====================================================
-- JOBS TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS jobs (
    -- Primary identifiers
    id VARCHAR(50) PRIMARY KEY,
    pm_number VARCHAR(50) NOT NULL,
    notification_number VARCHAR(50),
    
    -- Job details
    package_url TEXT,
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN (
        'pending', 'assigned', 'in_progress', 'ready_for_qa', 
        'approved', 'rejected', 'submitted'
    )),
    location VARCHAR(255),
    scheduled_date TIMESTAMPTZ,
    
    -- Assignments
    assigned_crew VARCHAR(100),
    assigned_foreman VARCHAR(100),
    
    -- User tracking (for RLS)
    uploaded_by VARCHAR(100),      -- PM user ID
    assigned_by VARCHAR(100),      -- GF user ID
    submitted_by VARCHAR(100),     -- Foreman user ID
    reviewed_by VARCHAR(100),      -- QA user ID
    
    -- Analysis data
    initial_analysis JSONB,
    field_photos JSONB,
    vision_analysis JSONB,
    final_analysis JSONB,
    filled_pdf_url TEXT,
    
    -- Metrics
    has_go_backs BOOLEAN DEFAULT FALSE,
    repealable_count INTEGER DEFAULT 0,
    total_savings INTEGER DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    submission_date TIMESTAMPTZ,
    qa_date TIMESTAMPTZ,
    pge_submission_date TIMESTAMPTZ,
    
    -- Indexes for performance
    INDEX idx_pm_number ON jobs(pm_number),
    INDEX idx_status ON jobs(status),
    INDEX idx_crew ON jobs(assigned_crew),
    INDEX idx_foreman ON jobs(assigned_foreman),
    INDEX idx_uploaded_by ON jobs(uploaded_by)
);

-- =====================================================
-- ENABLE ROW LEVEL SECURITY
-- =====================================================
ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;

-- =====================================================
-- CREATE SESSION SETTINGS TABLE
-- =====================================================
-- This table stores current user context for RLS
CREATE TABLE IF NOT EXISTS session_context (
    session_id VARCHAR(100) PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    user_role VARCHAR(50) NOT NULL,
    user_crew VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ DEFAULT NOW() + INTERVAL '24 hours'
);

-- Function to get current user context
CREATE OR REPLACE FUNCTION current_app_user() 
RETURNS VARCHAR AS $$
BEGIN
    RETURN current_setting('app.current_user_id', TRUE);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE FUNCTION current_app_role() 
RETURNS VARCHAR AS $$
BEGIN
    RETURN current_setting('app.current_role', TRUE);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE FUNCTION current_app_crew() 
RETURNS VARCHAR AS $$
BEGIN
    RETURN current_setting('app.current_crew', TRUE);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- =====================================================
-- RLS POLICIES FOR JOBS TABLE
-- =====================================================

-- Policy 1: Project Manager (PM)
-- Can see and manage their uploaded jobs
CREATE POLICY pm_jobs_policy ON jobs
    FOR ALL
    TO pm_role
    USING (
        uploaded_by = current_app_user()  -- Own uploads
        OR status = 'pending'              -- Can see all pending for assignment overview
    )
    WITH CHECK (
        uploaded_by = current_app_user()  -- Can only create as themselves
    );

-- Policy 2: General Foreman (GF)
-- Can see all jobs, assign crews, view schedules
CREATE POLICY gf_jobs_policy ON jobs
    FOR ALL
    TO gf_role
    USING (
        TRUE  -- GF can see all jobs for scheduling
    )
    WITH CHECK (
        status IN ('pending', 'assigned', 'in_progress')  -- Can only modify active jobs
        OR assigned_by = current_app_user()               -- Or jobs they assigned
    );

-- Policy 3: Field Foreman
-- Can only see and submit jobs assigned to their crew
CREATE POLICY foreman_jobs_policy ON jobs
    FOR ALL
    TO foreman_role
    USING (
        assigned_crew = current_app_crew()                -- Jobs for their crew
        AND status IN ('assigned', 'in_progress')         -- Only active jobs
        OR submitted_by = current_app_user()              -- Or jobs they submitted
    )
    WITH CHECK (
        assigned_crew = current_app_crew()                -- Can only update their crew's jobs
        AND assigned_foreman = current_app_user()         -- And they are the assigned foreman
    );

-- Policy 4: QA Reviewer
-- Can see and review jobs ready for QA
CREATE POLICY qa_jobs_policy ON jobs
    FOR ALL
    TO qa_role
    USING (
        status IN ('ready_for_qa', 'approved', 'rejected', 'submitted')  -- QA pipeline jobs
        OR reviewed_by = current_app_user()                              -- Jobs they reviewed
    )
    WITH CHECK (
        status IN ('ready_for_qa', 'approved', 'rejected')               -- Can only modify QA states
    );

-- Policy 5: Admin (bypass RLS for system operations)
CREATE POLICY admin_bypass_policy ON jobs
    FOR ALL
    TO admin_role
    USING (TRUE)
    WITH CHECK (TRUE);

-- =====================================================
-- GRANT PERMISSIONS
-- =====================================================
-- Grant table permissions to roles
GRANT SELECT, INSERT, UPDATE ON jobs TO pm_role, gf_role, foreman_role, qa_role;
GRANT ALL ON jobs TO admin_role;

-- Grant sequence permissions if using auto-increment
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO pm_role, gf_role, foreman_role, qa_role;

-- =====================================================
-- AUDIT LOG TABLE (Optional but recommended)
-- =====================================================
CREATE TABLE IF NOT EXISTS audit_log (
    id SERIAL PRIMARY KEY,
    table_name VARCHAR(50),
    operation VARCHAR(10),
    user_id VARCHAR(100),
    user_role VARCHAR(50),
    job_id VARCHAR(50),
    old_data JSONB,
    new_data JSONB,
    query_text TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Audit trigger function
CREATE OR REPLACE FUNCTION audit_trigger_function()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO audit_log (
        table_name,
        operation,
        user_id,
        user_role,
        job_id,
        old_data,
        new_data,
        query_text
    ) VALUES (
        TG_TABLE_NAME,
        TG_OP,
        current_app_user(),
        current_app_role(),
        COALESCE(NEW.id, OLD.id),
        to_jsonb(OLD),
        to_jsonb(NEW),
        current_query()
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Attach audit trigger to jobs table
CREATE TRIGGER jobs_audit_trigger
    AFTER INSERT OR UPDATE OR DELETE ON jobs
    FOR EACH ROW
    EXECUTE FUNCTION audit_trigger_function();

-- =====================================================
-- HELPER VIEWS (Read-only, respects RLS)
-- =====================================================

-- View for PM Dashboard
CREATE OR REPLACE VIEW pm_dashboard AS
SELECT 
    j.*,
    COUNT(*) FILTER (WHERE status = 'pending') OVER () as pending_count,
    COUNT(*) FILTER (WHERE status = 'submitted') OVER () as submitted_count,
    SUM(total_savings) OVER () as total_savings_all
FROM jobs j;

-- View for GF Scheduling
CREATE OR REPLACE VIEW gf_schedule AS
SELECT 
    j.*,
    COUNT(*) OVER (PARTITION BY assigned_crew) as crew_job_count,
    COUNT(*) FILTER (WHERE has_go_backs) OVER () as go_back_count
FROM jobs j
WHERE scheduled_date >= CURRENT_DATE;

-- View for QA Queue
CREATE OR REPLACE VIEW qa_queue AS
SELECT 
    j.*,
    EXTRACT(EPOCH FROM (NOW() - submission_date))/3600 as hours_waiting
FROM jobs j
WHERE status = 'ready_for_qa'
ORDER BY submission_date ASC;

-- =====================================================
-- TEST DATA FUNCTIONS (Remove in production)
-- =====================================================
CREATE OR REPLACE FUNCTION test_rls_as_role(
    test_role VARCHAR,
    test_user VARCHAR,
    test_crew VARCHAR DEFAULT NULL
) RETURNS TABLE (
    visible_jobs_count INTEGER,
    job_ids TEXT[]
) AS $$
BEGIN
    -- Set session variables
    PERFORM set_config('app.current_user_id', test_user, TRUE);
    PERFORM set_config('app.current_role', test_role, TRUE);
    IF test_crew IS NOT NULL THEN
        PERFORM set_config('app.current_crew', test_crew, TRUE);
    END IF;
    
    -- Set role
    EXECUTE format('SET ROLE %I', test_role || '_role');
    
    -- Count visible jobs
    RETURN QUERY
    SELECT 
        COUNT(*)::INTEGER,
        ARRAY_AGG(id)
    FROM jobs;
    
    -- Reset role
    RESET ROLE;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- MAINTENANCE FUNCTIONS
-- =====================================================

-- Function to clean expired sessions
CREATE OR REPLACE FUNCTION cleanup_expired_sessions()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM session_context 
    WHERE expires_at < NOW();
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Schedule cleanup (requires pg_cron extension on Render)
-- SELECT cron.schedule('cleanup-sessions', '0 */6 * * *', 'SELECT cleanup_expired_sessions();');

-- =====================================================
-- MIGRATION NOTES
-- =====================================================
-- To apply this schema:
-- 1. Connect to Render PostgreSQL: psql $DATABASE_URL
-- 2. Run this entire file: \i schema_with_rls.sql
-- 3. Test with: SELECT test_rls_as_role('foreman', 'F001', 'CREW-001');
-- 4. Verify policies: SELECT * FROM pg_policies WHERE tablename = 'jobs';

-- To rollback:
-- ALTER TABLE jobs DISABLE ROW LEVEL SECURITY;
-- DROP POLICY ALL ON jobs;

COMMENT ON TABLE jobs IS 'Main job tracking table with RLS for role-based access control';
COMMENT ON COLUMN jobs.pm_number IS 'PG&E PM Number - primary identifier';
COMMENT ON COLUMN jobs.notification_number IS 'PG&E Notification Number - secondary identifier';
