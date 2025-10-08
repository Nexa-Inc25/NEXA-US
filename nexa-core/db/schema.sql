-- Nexa Core Database Schema
-- Postgres 15 with Row-Level Security (RLS)

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For fuzzy text search

-- ============================================================================
-- USERS & AUTH
-- ============================================================================

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    uuid UUID DEFAULT uuid_generate_v4() UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('general_foreman', 'crew_foreman', 'qa', 'admin')),
    api_key VARCHAR(100) UNIQUE,
    phone VARCHAR(20),
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_api_key ON users(api_key);

-- ============================================================================
-- JOBS & SCHEDULING (General Foreman Domain)
-- ============================================================================

CREATE TABLE jobs (
    id SERIAL PRIMARY KEY,
    uuid UUID DEFAULT uuid_generate_v4() UNIQUE NOT NULL,
    job_number VARCHAR(50) UNIQUE NOT NULL,
    gf_id INTEGER REFERENCES users(id) NOT NULL,
    assigned_foreman_id INTEGER REFERENCES users(id),
    
    -- Pre-field data from GF
    location JSONB NOT NULL,  -- {address, coordinates, utility_pole_id}
    work_type VARCHAR(50) NOT NULL,  -- 'capacitor', 'switch', 'recloser', 'cable', etc.
    scheduled_date DATE NOT NULL,
    estimated_hours INTEGER,
    
    -- Planning data
    pre_field_notes TEXT,
    required_specs JSONB,  -- Array of spec IDs needed
    materials JSONB,       -- Array of materials/equipment
    safety_requirements JSONB,
    
    -- Status tracking
    status VARCHAR(20) DEFAULT 'planned' CHECK (status IN ('planned', 'assigned', 'in_progress', 'submitted', 'under_qa', 'approved', 'go_back', 'closed')),
    
    -- QR code for mobile access
    qr_code_data TEXT,  -- Encrypted job ID + auth token
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_jobs_gf ON jobs(gf_id);
CREATE INDEX idx_jobs_foreman ON jobs(assigned_foreman_id);
CREATE INDEX idx_jobs_scheduled_date ON jobs(scheduled_date);

-- ============================================================================
-- SUBMISSIONS (Crew Foreman Domain - As-Builts)
-- ============================================================================

CREATE TABLE submissions (
    id SERIAL PRIMARY KEY,
    uuid UUID DEFAULT uuid_generate_v4() UNIQUE NOT NULL,
    job_id INTEGER REFERENCES jobs(id) NOT NULL,
    foreman_id INTEGER REFERENCES users(id) NOT NULL,
    
    -- As-built data from field
    as_built_data JSONB NOT NULL,  -- Form data (specs, measurements, etc.)
    photos JSONB,  -- Array of S3 URLs: [{url, caption, timestamp, lat, lon}]
    
    -- Compliance fields
    equipment_installed JSONB,  -- {type, serial_number, manufacturer, spec_compliance}
    measurements JSONB,  -- {spacing, clearance, grounding, etc.}
    weather_conditions VARCHAR(100),
    crew_notes TEXT,
    
    -- Metadata
    submitted_from VARCHAR(20) DEFAULT 'mobile',  -- 'mobile' or 'web'
    submitted_offline BOOLEAN DEFAULT false,
    gps_coordinates JSONB,  -- {lat, lon, accuracy, timestamp}
    device_info JSONB,  -- {os, app_version, device_id}
    
    -- Status
    status VARCHAR(20) DEFAULT 'submitted' CHECK (status IN ('draft', 'submitted', 'under_review', 'approved', 'returned', 'go_back')),
    qa_reviewed_by INTEGER REFERENCES users(id),
    qa_reviewed_at TIMESTAMP,
    
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    synced_at TIMESTAMP,  -- When offline submission synced
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_submissions_job ON submissions(job_id);
CREATE INDEX idx_submissions_foreman ON submissions(foreman_id);
CREATE INDEX idx_submissions_status ON submissions(status);

-- RLS for submissions (foreman can only see their own)
ALTER TABLE submissions ENABLE ROW LEVEL SECURITY;

CREATE POLICY foreman_own_submissions ON submissions
    FOR ALL
    USING (foreman_id = current_setting('app.current_user_id')::INTEGER OR 
           EXISTS (SELECT 1 FROM users WHERE id = current_setting('app.current_user_id')::INTEGER AND role IN ('qa', 'admin')));

-- ============================================================================
-- AUDITS & GO-BACKS (QA/PGE Domain)
-- ============================================================================

CREATE TABLE audits (
    id SERIAL PRIMARY KEY,
    uuid UUID DEFAULT uuid_generate_v4() UNIQUE NOT NULL,
    submission_id INTEGER REFERENCES submissions(id) NOT NULL,
    
    -- PGE go-back document
    pge_audit_pdf_url TEXT,  -- S3 URL of PGE audit/go-back PDF
    pge_audit_date DATE,
    pge_inspector VARCHAR(255),
    pge_reference_number VARCHAR(100),
    
    -- Infractions from PGE
    infractions JSONB,  -- Array from PGE doc: [{description, severity, spec_cited}]
    
    -- Analyzer results (from multi-spec service)
    repeal_analysis JSONB,  -- Full analyzer output: [{infraction, status, confidence, match_count, reasons}]
    
    -- QA actions
    contestable BOOLEAN,  -- Auto-set based on repeal_analysis
    contest_filed BOOLEAN DEFAULT false,
    contest_notes TEXT,
    contest_filed_date DATE,
    
    -- Resolution
    resolution VARCHAR(20) CHECK (resolution IN ('pending', 'upheld', 'overturned', 'partial')),
    resolution_date DATE,
    resolution_notes TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audits_submission ON audits(submission_id);
CREATE INDEX idx_audits_contestable ON audits(contestable);
CREATE INDEX idx_audits_resolution ON audits(resolution);

-- ============================================================================
-- SPEC LIBRARY (Reference for Analysis)
-- ============================================================================

CREATE TABLE spec_files (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) UNIQUE NOT NULL,
    file_hash VARCHAR(64) UNIQUE NOT NULL,  -- SHA256
    s3_url TEXT,
    
    -- Metadata
    spec_number VARCHAR(50),  -- e.g., '057875', '092813'
    title TEXT,
    category VARCHAR(100),  -- 'capacitors', 'switches', 'cables', etc.
    version VARCHAR(20),
    effective_date DATE,
    
    -- Analyzer integration
    chunk_count INTEGER,
    uploaded_to_analyzer BOOLEAN DEFAULT false,
    analyzer_file_id TEXT,  -- ID from multi-spec service
    
    uploaded_by INTEGER REFERENCES users(id),
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_spec_files_category ON spec_files(category);
CREATE INDEX idx_spec_files_number ON spec_files(spec_number);

-- ============================================================================
-- ACTIVITY LOG (Audit Trail)
-- ============================================================================

CREATE TABLE activity_log (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50),  -- 'job', 'submission', 'audit', etc.
    entity_id INTEGER,
    details JSONB,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_activity_user ON activity_log(user_id);
CREATE INDEX idx_activity_entity ON activity_log(entity_type, entity_id);
CREATE INDEX idx_activity_created ON activity_log(created_at);

-- ============================================================================
-- FUNCTIONS & TRIGGERS
-- ============================================================================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_jobs_updated_at BEFORE UPDATE ON jobs FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_submissions_updated_at BEFORE UPDATE ON submissions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_audits_updated_at BEFORE UPDATE ON audits FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Auto-set contestable flag based on analyzer results
CREATE OR REPLACE FUNCTION set_contestable_flag()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.repeal_analysis IS NOT NULL THEN
        NEW.contestable := EXISTS (
            SELECT 1 FROM jsonb_array_elements(NEW.repeal_analysis) elem
            WHERE elem->>'status' = 'REPEALABLE' AND (elem->>'confidence')::FLOAT > 70
        );
    END IF;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER set_audit_contestable BEFORE INSERT OR UPDATE ON audits FOR EACH ROW EXECUTE FUNCTION set_contestable_flag();

-- ============================================================================
-- VIEWS (Common Queries)
-- ============================================================================

-- Active jobs needing assignment
CREATE VIEW jobs_needing_assignment AS
SELECT j.*, u.name as gf_name
FROM jobs j
JOIN users u ON j.gf_id = u.id
WHERE j.status = 'planned' AND j.assigned_foreman_id IS NULL;

-- Submissions awaiting QA
CREATE VIEW submissions_pending_qa AS
SELECT s.*, j.job_number, u.name as foreman_name
FROM submissions s
JOIN jobs j ON s.job_id = j.id
JOIN users u ON s.foreman_id = u.id
WHERE s.status = 'submitted' AND s.qa_reviewed_at IS NULL;

-- Contestable audits
CREATE VIEW contestable_audits AS
SELECT a.*, s.uuid as submission_uuid, j.job_number
FROM audits a
JOIN submissions s ON a.submission_id = s.id
JOIN jobs j ON s.job_id = j.id
WHERE a.contestable = true AND a.contest_filed = false;

-- ============================================================================
-- SEED DATA (Development)
-- ============================================================================

-- Insert test users
INSERT INTO users (email, name, role, api_key) VALUES
('gf@nexa.com', 'John Smith', 'general_foreman', 'gf_test_key_123'),
('foreman@nexa.com', 'Mike Johnson', 'crew_foreman', 'foreman_test_key_456'),
('qa@nexa.com', 'Sarah Davis', 'qa', 'qa_test_key_789'),
('admin@nexa.com', 'Admin User', 'admin', 'admin_test_key_000');

-- Insert sample job
INSERT INTO jobs (job_number, gf_id, location, work_type, scheduled_date, status) VALUES
('JOB-2025-001', 1, '{"address": "123 Main St", "coordinates": {"lat": 37.7749, "lon": -122.4194}}', 'capacitor', CURRENT_DATE + INTERVAL '7 days', 'planned');

COMMIT;
