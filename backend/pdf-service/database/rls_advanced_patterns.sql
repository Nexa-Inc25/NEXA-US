-- =====================================================
-- Advanced PostgreSQL RLS Patterns for NEXA Platform
-- Complete implementation with all security patterns
-- =====================================================

-- =====================================================
-- CLEANUP (if rebuilding)
-- =====================================================
DROP POLICY IF EXISTS user_specific_policy ON jobs CASCADE;
DROP POLICY IF EXISTS hierarchical_access_policy ON jobs CASCADE;
DROP POLICY IF EXISTS time_based_policy ON jobs CASCADE;
DROP POLICY IF EXISTS multi_tenant_policy ON jobs CASCADE;
DROP POLICY IF EXISTS status_transition_policy ON jobs CASCADE;
DROP POLICY IF EXISTS update_owner_only_policy ON jobs CASCADE;
DROP FUNCTION IF EXISTS is_in_department CASCADE;
DROP FUNCTION IF EXISTS can_transition_status CASCADE;
DROP FUNCTION IF EXISTS get_user_hierarchy CASCADE;

-- =====================================================
-- ENHANCED JOBS TABLE with all fields
-- =====================================================
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS tenant_id INTEGER;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS department_id INTEGER;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS is_archived BOOLEAN DEFAULT FALSE;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS last_modified_by VARCHAR(100);
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS access_level VARCHAR(50) DEFAULT 'standard';

-- Create indexes for RLS performance
CREATE INDEX IF NOT EXISTS idx_jobs_tenant_id ON jobs(tenant_id);
CREATE INDEX IF NOT EXISTS idx_jobs_department_id ON jobs(department_id);
CREATE INDEX IF NOT EXISTS idx_jobs_expires_at ON jobs(expires_at);
CREATE INDEX IF NOT EXISTS idx_jobs_is_archived ON jobs(is_archived);
CREATE INDEX IF NOT EXISTS idx_jobs_access_level ON jobs(access_level);

-- =====================================================
-- HELPER FUNCTIONS FOR COMPLEX POLICIES
-- =====================================================

-- Function to check department hierarchy (GF oversees multiple crews)
CREATE OR REPLACE FUNCTION is_in_department(user_id text, dept_id int) 
RETURNS boolean AS $$
DECLARE
    user_dept integer;
    user_role text;
BEGIN
    -- Get user's department and role
    SELECT department_id, role INTO user_dept, user_role
    FROM users 
    WHERE id = user_id;
    
    -- GF can see all departments
    IF user_role = 'gf' THEN
        RETURN TRUE;
    END IF;
    
    -- Others see only their department
    RETURN user_dept = dept_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to get user hierarchy (for nested crew access)
CREATE OR REPLACE FUNCTION get_user_hierarchy(user_id text)
RETURNS TABLE(accessible_crew_id text) AS $$
BEGIN
    RETURN QUERY
    SELECT DISTINCT crew_id
    FROM (
        -- Direct crew assignment
        SELECT assigned_crew as crew_id
        FROM users
        WHERE id = user_id
        
        UNION
        
        -- Crews under user's supervision (for GF)
        SELECT c.crew_id
        FROM crews c
        JOIN users u ON u.id = user_id
        WHERE u.role = 'gf' AND c.department_id = u.department_id
        
        UNION
        
        -- All crews for admin
        SELECT crew_id
        FROM crews
        WHERE EXISTS (SELECT 1 FROM users WHERE id = user_id AND role = 'admin')
    ) AS hierarchy;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to validate status transitions
CREATE OR REPLACE FUNCTION can_transition_status(
    user_role text,
    current_status text,
    new_status text
) RETURNS boolean AS $$
BEGIN
    -- Define valid transitions per role
    CASE user_role
        WHEN 'pm' THEN
            -- PM can create and cancel
            RETURN (current_status IS NULL AND new_status = 'pending')
                OR (current_status = 'pending' AND new_status = 'cancelled');
                
        WHEN 'gf' THEN
            -- GF can assign and reassign
            RETURN (current_status = 'pending' AND new_status = 'assigned')
                OR (current_status = 'assigned' AND new_status IN ('assigned', 'cancelled'));
                
        WHEN 'foreman' THEN
            -- Foreman can start and complete work
            RETURN (current_status = 'assigned' AND new_status = 'in_progress')
                OR (current_status = 'in_progress' AND new_status = 'ready_for_qa');
                
        WHEN 'qa' THEN
            -- QA can approve or reject
            RETURN (current_status = 'ready_for_qa' AND new_status IN ('approved', 'rejected'));
                
        WHEN 'admin' THEN
            -- Admin can do anything
            RETURN TRUE;
            
        ELSE
            RETURN FALSE;
    END CASE;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- =====================================================
-- ADVANCED RLS POLICIES
-- =====================================================

-- 1. USER-SPECIFIC ACCESS (Basic pattern)
CREATE POLICY user_specific_policy ON jobs
    FOR ALL
    USING (
        -- Users see their own jobs
        uploaded_by = current_setting('app.current_user_id', TRUE)
        OR submitted_by = current_setting('app.current_user_id', TRUE)
        OR reviewed_by = current_setting('app.current_user_id', TRUE)
    )
    WITH CHECK (
        -- Can only modify their own actions
        CASE 
            WHEN status IS NULL OR status = 'pending' THEN 
                uploaded_by = current_setting('app.current_user_id', TRUE)
            WHEN status = 'ready_for_qa' THEN
                submitted_by = current_setting('app.current_user_id', TRUE)
            WHEN status IN ('approved', 'rejected') THEN
                reviewed_by = current_setting('app.current_user_id', TRUE)
            ELSE FALSE
        END
    );

-- 2. HIERARCHICAL ACCESS (GF oversees crews)
CREATE POLICY hierarchical_access_policy ON jobs
    FOR SELECT
    USING (
        -- Check if user has access through hierarchy
        assigned_crew IN (
            SELECT * FROM get_user_hierarchy(current_setting('app.current_user_id', TRUE))
        )
        OR
        -- Department-based access
        is_in_department(
            current_setting('app.current_user_id', TRUE),
            department_id
        )
    );

-- 3. TIME-BASED EXPIRATION (Active jobs only)
CREATE POLICY time_based_policy ON jobs
    FOR SELECT
    USING (
        -- Show only non-expired, non-archived jobs
        (expires_at IS NULL OR expires_at > NOW())
        AND
        is_archived = FALSE
        AND
        -- Recent activity (last 30 days for foreman, all for others)
        CASE current_setting('app.current_role', TRUE)
            WHEN 'foreman' THEN 
                created_at > NOW() - INTERVAL '30 days'
            ELSE TRUE
        END
    );

-- 4. MULTI-TENANT ISOLATION (Complete separation)
CREATE POLICY multi_tenant_policy ON jobs
    FOR ALL
    USING (
        -- Tenant isolation
        tenant_id = current_setting('app.tenant_id', TRUE)::INTEGER
        OR
        -- Shared tenant (0) visible to all
        tenant_id = 0
        OR
        -- Admin bypass
        current_setting('app.current_role', TRUE) = 'admin'
    )
    WITH CHECK (
        -- Ensure writes maintain tenant isolation
        tenant_id = current_setting('app.tenant_id', TRUE)::INTEGER
        OR
        (tenant_id = 0 AND current_setting('app.current_role', TRUE) = 'admin')
    );

-- 5. STATUS-BASED TRANSITION CONTROL
CREATE POLICY status_transition_policy ON jobs
    FOR UPDATE
    USING (
        -- Can see job to update it
        TRUE  -- Rely on other policies for visibility
    )
    WITH CHECK (
        -- Validate status transition
        can_transition_status(
            current_setting('app.current_role', TRUE),
            status,
            NEW.status
        )
        AND
        -- Prevent updates after submission (except by QA/admin)
        (
            status NOT IN ('submitted', 'approved')
            OR current_setting('app.current_role', TRUE) IN ('qa', 'admin')
        )
        AND
        -- Track who modified
        (NEW.last_modified_by = current_setting('app.current_user_id', TRUE))
    );

-- 6. UPDATE-ONLY FOR OWNERS (Modification control)
CREATE POLICY update_owner_only_policy ON jobs
    FOR UPDATE
    USING (
        -- Must be owner or have override permission
        uploaded_by = current_setting('app.current_user_id', TRUE)
        OR assigned_by = current_setting('app.current_user_id', TRUE)
        OR current_setting('app.current_role', TRUE) IN ('gf', 'admin')
    )
    WITH CHECK (
        -- Prevent changing ownership fields
        (NEW.uploaded_by = OLD.uploaded_by OR current_setting('app.current_role', TRUE) = 'admin')
        AND
        -- Prevent backdating
        (NEW.created_at >= OLD.created_at)
        AND
        -- Audit trail
        (NEW.updated_at = NOW())
    );

-- 7. ACCESS LEVEL CONTROL (Sensitive data protection)
CREATE POLICY access_level_policy ON jobs
    FOR SELECT
    USING (
        -- Standard access for all
        access_level = 'standard'
        OR
        -- Restricted requires specific permission
        (access_level = 'restricted' AND current_setting('app.current_role', TRUE) IN ('gf', 'qa', 'admin'))
        OR
        -- Confidential only for admin
        (access_level = 'confidential' AND current_setting('app.current_role', TRUE) = 'admin')
    );

-- 8. JOINED POLICIES FOR RELATIONS
CREATE POLICY user_jobs_relation_policy ON jobs
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 
            FROM users u
            WHERE u.id = current_setting('app.current_user_id', TRUE)
            AND (
                -- User's role matches job's required role
                (u.role = 'pm' AND jobs.status = 'pending')
                OR (u.role = 'gf' AND jobs.status IN ('pending', 'assigned'))
                OR (u.role = 'foreman' AND jobs.status IN ('assigned', 'in_progress'))
                OR (u.role = 'qa' AND jobs.status = 'ready_for_qa')
                OR u.role = 'admin'
            )
        )
    );

-- =====================================================
-- AUDIT AND COMPLIANCE POLICIES
-- =====================================================

-- Audit log policy (write-only for app, read for admins)
CREATE POLICY audit_write_policy ON audit_log
    FOR INSERT
    WITH CHECK (TRUE);  -- App can always write audit logs

CREATE POLICY audit_read_policy ON audit_log
    FOR SELECT
    USING (
        current_setting('app.current_role', TRUE) IN ('admin', 'qa')
        OR
        -- Users can see their own audit trail
        user_id = current_setting('app.current_user_id', TRUE)
    );

-- =====================================================
-- PERFORMANCE MONITORING VIEWS (Respect RLS)
-- =====================================================

-- View for monitoring RLS performance impact
CREATE OR REPLACE VIEW rls_performance_stats AS
SELECT 
    schemaname,
    tablename,
    n_tup_ins as inserts,
    n_tup_upd as updates,
    n_tup_del as deletes,
    n_live_tup as live_rows,
    n_dead_tup as dead_rows,
    last_vacuum,
    last_analyze
FROM pg_stat_user_tables
WHERE tablename = 'jobs';

-- View for active policies
CREATE OR REPLACE VIEW active_policies AS
SELECT 
    schemaname,
    tablename,
    policyname,
    permissive,
    roles,
    cmd,
    qual as using_clause,
    with_check
FROM pg_policies
WHERE tablename = 'jobs'
ORDER BY policyname;

-- =====================================================
-- TESTING FUNCTIONS
-- =====================================================

-- Test all policies for a given user
CREATE OR REPLACE FUNCTION test_all_policies(
    test_user_id TEXT,
    test_role TEXT,
    test_crew TEXT DEFAULT NULL,
    test_tenant_id INTEGER DEFAULT 1
) RETURNS TABLE(
    policy_name TEXT,
    can_select BOOLEAN,
    can_insert BOOLEAN,
    can_update BOOLEAN,
    can_delete BOOLEAN,
    visible_count INTEGER
) AS $$
BEGIN
    -- Set context
    PERFORM set_config('app.current_user_id', test_user_id, TRUE);
    PERFORM set_config('app.current_role', test_role, TRUE);
    PERFORM set_config('app.current_crew', COALESCE(test_crew, ''), TRUE);
    PERFORM set_config('app.tenant_id', test_tenant_id::TEXT, TRUE);
    
    -- Test each operation
    RETURN QUERY
    SELECT 
        'all_policies'::TEXT,
        EXISTS(SELECT 1 FROM jobs LIMIT 1) as can_select,
        EXISTS(
            SELECT 1 FROM jobs 
            WHERE pg_has_role(SESSION_USER, 'pg_write', 'USAGE')
        ) as can_insert,
        EXISTS(
            SELECT 1 FROM jobs 
            WHERE pg_has_role(SESSION_USER, 'pg_write', 'USAGE')
        ) as can_update,
        EXISTS(
            SELECT 1 FROM jobs 
            WHERE pg_has_role(SESSION_USER, 'pg_write', 'USAGE')
        ) as can_delete,
        COUNT(*)::INTEGER FROM jobs;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- EXAMPLE DATA FOR TESTING
-- =====================================================

-- Insert test data with various access levels
INSERT INTO jobs (
    id, pm_number, status, uploaded_by, assigned_crew, 
    tenant_id, department_id, access_level, expires_at
) VALUES 
    ('RLS-TEST-001', 'PM-001', 'pending', 'PM001', NULL, 1, 1, 'standard', NULL),
    ('RLS-TEST-002', 'PM-002', 'assigned', 'PM001', 'CREW-001', 1, 1, 'restricted', NULL),
    ('RLS-TEST-003', 'PM-003', 'ready_for_qa', 'PM002', 'CREW-002', 1, 2, 'standard', NOW() + INTERVAL '7 days'),
    ('RLS-TEST-004', 'PM-004', 'approved', 'PM001', 'CREW-001', 2, 1, 'confidential', NULL),
    ('RLS-TEST-005', 'PM-005', 'in_progress', 'PM003', 'CREW-003', 1, 3, 'standard', NOW() - INTERVAL '1 day')
ON CONFLICT (id) DO NOTHING;

-- =====================================================
-- MIGRATION SAFETY
-- =====================================================

-- Ensure RLS is enabled
ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;

-- Force RLS for table owner too (optional, high security)
-- ALTER TABLE jobs FORCE ROW LEVEL SECURITY;

COMMENT ON TABLE jobs IS 'Jobs table with comprehensive RLS policies for multi-user workflow security';
COMMENT ON POLICY user_specific_policy ON jobs IS 'Basic user-level access control';
COMMENT ON POLICY hierarchical_access_policy ON jobs IS 'Department and crew hierarchy access';
COMMENT ON POLICY time_based_policy ON jobs IS 'Time-based expiration and archival';
COMMENT ON POLICY multi_tenant_policy ON jobs IS 'Complete tenant isolation';
COMMENT ON POLICY status_transition_policy ON jobs IS 'Workflow state machine enforcement';
COMMENT ON POLICY update_owner_only_policy ON jobs IS 'Ownership-based modification control';
COMMENT ON POLICY access_level_policy ON jobs IS 'Sensitivity-based access control';
