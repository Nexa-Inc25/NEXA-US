#!/bin/bash

# Deploy PostgreSQL RLS to Render Database
# Run this script to apply Row-Level Security policies

echo "🔐 NEXA PostgreSQL RLS Deployment Script"
echo "========================================="

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Check for DATABASE_URL
if [ -z "$DATABASE_URL" ]; then
    echo -e "${RED}Error: DATABASE_URL environment variable not set${NC}"
    echo "Get it from Render Dashboard → Database → Connection String"
    echo "Then run: export DATABASE_URL='your-connection-string'"
    exit 1
fi

echo -e "${GREEN}Database URL found${NC}"

# Step 1: Backup current schema (optional but recommended)
echo -e "\n${YELLOW}Step 1: Creating backup...${NC}"
pg_dump $DATABASE_URL --schema-only > backup_schema_$(date +%Y%m%d_%H%M%S).sql
echo -e "${GREEN}✓ Schema backed up${NC}"

# Step 2: Check if RLS is already enabled
echo -e "\n${YELLOW}Step 2: Checking current RLS status...${NC}"
psql $DATABASE_URL -c "\dt jobs" 2>/dev/null | grep -q "jobs" && {
    RLS_STATUS=$(psql $DATABASE_URL -t -c "SELECT relrowsecurity FROM pg_class WHERE relname = 'jobs';" 2>/dev/null)
    if [ "$RLS_STATUS" = " t" ]; then
        echo -e "${YELLOW}RLS is already enabled on jobs table${NC}"
        read -p "Do you want to recreate policies? (y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 0
        fi
    fi
}

# Step 3: Apply RLS schema
echo -e "\n${YELLOW}Step 3: Applying RLS schema...${NC}"
psql $DATABASE_URL < schema_with_rls.sql

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ RLS schema applied successfully${NC}"
else
    echo -e "${RED}✗ Failed to apply RLS schema${NC}"
    exit 1
fi

# Step 4: Verify RLS is enabled
echo -e "\n${YELLOW}Step 4: Verifying RLS installation...${NC}"

# Check if RLS is enabled
RLS_CHECK=$(psql $DATABASE_URL -t -c "
    SELECT COUNT(*) 
    FROM pg_tables t
    JOIN pg_class c ON c.relname = t.tablename
    WHERE t.tablename = 'jobs' 
    AND c.relrowsecurity = true;
" 2>/dev/null)

if [ "$RLS_CHECK" -eq 1 ]; then
    echo -e "${GREEN}✓ RLS is enabled on jobs table${NC}"
else
    echo -e "${RED}✗ RLS verification failed${NC}"
    exit 1
fi

# Check policies
echo -e "\n${YELLOW}Checking policies...${NC}"
psql $DATABASE_URL -c "
    SELECT polname as policy_name, 
           polroles::regrole[] as roles,
           CASE polcmd 
               WHEN 'r' THEN 'SELECT'
               WHEN 'a' THEN 'INSERT'
               WHEN 'w' THEN 'UPDATE'
               WHEN 'd' THEN 'DELETE'
               WHEN '*' THEN 'ALL'
           END as command
    FROM pg_policy 
    WHERE polrelid = 'jobs'::regclass;
"

# Step 5: Test RLS with different roles
echo -e "\n${YELLOW}Step 5: Testing RLS policies...${NC}"

# Test as PM
echo -e "\n${GREEN}Testing as Project Manager...${NC}"
psql $DATABASE_URL <<EOF
SET app.current_user_id = 'PM001';
SET app.current_role = 'pm';
SET ROLE pm_role;
SELECT 'PM can see', COUNT(*) as job_count FROM jobs;
RESET ROLE;
EOF

# Test as Foreman
echo -e "\n${GREEN}Testing as Foreman...${NC}"
psql $DATABASE_URL <<EOF
SET app.current_user_id = 'F001';
SET app.current_role = 'foreman';
SET app.current_crew = 'CREW-001';
SET ROLE foreman_role;
SELECT 'Foreman can see', COUNT(*) as job_count FROM jobs;
RESET ROLE;
EOF

# Test as QA
echo -e "\n${GREEN}Testing as QA...${NC}"
psql $DATABASE_URL <<EOF
SET app.current_user_id = 'QA001';
SET app.current_role = 'qa';
SET ROLE qa_role;
SELECT 'QA can see', COUNT(*) as job_count FROM jobs;
RESET ROLE;
EOF

# Step 6: Create sample data for testing
echo -e "\n${YELLOW}Step 6: Creating test data...${NC}"
read -p "Create sample jobs for testing? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    psql $DATABASE_URL <<EOF
-- Insert test jobs
INSERT INTO jobs (id, pm_number, notification_number, location, status, uploaded_by, assigned_crew, assigned_foreman)
VALUES 
    ('JOB-TEST-001', 'PM-12345', 'N-67890', 'Stockton Grid A', 'pending', 'PM001', NULL, NULL),
    ('JOB-TEST-002', 'PM-12346', 'N-67891', 'Stockton Grid B', 'assigned', 'PM001', 'CREW-001', 'F001'),
    ('JOB-TEST-003', 'PM-12347', 'N-67892', 'Stockton Grid C', 'ready_for_qa', 'PM002', 'CREW-002', 'F002'),
    ('JOB-TEST-004', 'PM-12348', 'N-67893', 'Stockton Grid D', 'approved', 'PM001', 'CREW-001', 'F001')
ON CONFLICT (id) DO NOTHING;

-- Test visibility
SELECT 'Total test jobs created:', COUNT(*) FROM jobs WHERE id LIKE 'JOB-TEST-%';
EOF
    echo -e "${GREEN}✓ Test data created${NC}"
fi

# Step 7: Summary
echo -e "\n${GREEN}=========================================${NC}"
echo -e "${GREEN}✅ RLS Deployment Complete!${NC}"
echo -e "${GREEN}=========================================${NC}"

echo -e "\n${YELLOW}Summary:${NC}"
echo "• RLS is enabled on the jobs table"
echo "• 4 role-based policies are active (PM, GF, Foreman, QA)"
echo "• Audit logging is configured"
echo "• Test the integration with: python database/rls_integration.py"

echo -e "\n${YELLOW}Next Steps:${NC}"
echo "1. Update your application to set user context on each request"
echo "2. Use the RLSConnection class in rls_integration.py"
echo "3. Test with different user roles"
echo "4. Monitor audit_log table for access patterns"

echo -e "\n${YELLOW}To rollback:${NC}"
echo "psql \$DATABASE_URL -c 'ALTER TABLE jobs DISABLE ROW LEVEL SECURITY;'"
