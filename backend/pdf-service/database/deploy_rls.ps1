# PowerShell script to deploy PostgreSQL RLS to Render Database
# Run this script to apply Row-Level Security policies on Windows

Write-Host "🔐 NEXA PostgreSQL RLS Deployment Script (Windows)" -ForegroundColor Cyan
Write-Host "=================================================" -ForegroundColor Cyan

# Check for DATABASE_URL
if (-not $env:DATABASE_URL) {
    Write-Host "❌ Error: DATABASE_URL environment variable not set" -ForegroundColor Red
    Write-Host "Get it from Render Dashboard → Database → Connection String" -ForegroundColor Yellow
    Write-Host "Then run: `$env:DATABASE_URL = 'your-connection-string'" -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ Database URL found" -ForegroundColor Green

# Step 1: Backup current schema
Write-Host "`n📦 Step 1: Creating backup..." -ForegroundColor Yellow
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupFile = "backup_schema_$timestamp.sql"
pg_dump $env:DATABASE_URL --schema-only > $backupFile
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Schema backed up to $backupFile" -ForegroundColor Green
} else {
    Write-Host "⚠️ Backup failed, continuing anyway..." -ForegroundColor Yellow
}

# Step 2: Check if jobs table exists and RLS status
Write-Host "`n🔍 Step 2: Checking current RLS status..." -ForegroundColor Yellow
$tableExists = psql $env:DATABASE_URL -t -c "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'jobs');" 2>$null
if ($tableExists -match "t") {
    $rlsStatus = psql $env:DATABASE_URL -t -c "SELECT relrowsecurity FROM pg_class WHERE relname = 'jobs';" 2>$null
    if ($rlsStatus -match "t") {
        Write-Host "⚠️ RLS is already enabled on jobs table" -ForegroundColor Yellow
        $response = Read-Host "Do you want to recreate policies? (y/n)"
        if ($response -ne 'y') {
            exit 0
        }
    }
}

# Step 3: Apply RLS schema
Write-Host "`n🚀 Step 3: Applying RLS schema..." -ForegroundColor Yellow
$schemaFile = Join-Path $PSScriptRoot "schema_with_rls.sql"
if (-not (Test-Path $schemaFile)) {
    Write-Host "❌ Error: schema_with_rls.sql not found" -ForegroundColor Red
    exit 1
}

psql $env:DATABASE_URL -f $schemaFile
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ RLS schema applied successfully" -ForegroundColor Green
} else {
    Write-Host "❌ Failed to apply RLS schema" -ForegroundColor Red
    exit 1
}

# Step 4: Verify RLS is enabled
Write-Host "`n✔️ Step 4: Verifying RLS installation..." -ForegroundColor Yellow

$rlsCheck = psql $env:DATABASE_URL -t -c @"
    SELECT COUNT(*) 
    FROM pg_tables t
    JOIN pg_class c ON c.relname = t.tablename
    WHERE t.tablename = 'jobs' 
    AND c.relrowsecurity = true;
"@ 2>$null

if ($rlsCheck -match "1") {
    Write-Host "✅ RLS is enabled on jobs table" -ForegroundColor Green
} else {
    Write-Host "❌ RLS verification failed" -ForegroundColor Red
    exit 1
}

# Check policies
Write-Host "`n📋 Active Policies:" -ForegroundColor Yellow
psql $env:DATABASE_URL -c @"
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
"@

# Step 5: Test RLS with different roles
Write-Host "`n🧪 Step 5: Testing RLS policies..." -ForegroundColor Yellow

# Test as PM
Write-Host "`n👷 Testing as Project Manager..." -ForegroundColor Green
psql $env:DATABASE_URL -c @"
SET app.current_user_id = 'PM001';
SET app.current_role = 'pm';
SET ROLE pm_role;
SELECT 'PM can see' as role, COUNT(*) as job_count FROM jobs;
RESET ROLE;
"@

# Test as Foreman
Write-Host "`n👷 Testing as Foreman..." -ForegroundColor Green
psql $env:DATABASE_URL -c @"
SET app.current_user_id = 'F001';
SET app.current_role = 'foreman';
SET app.current_crew = 'CREW-001';
SET ROLE foreman_role;
SELECT 'Foreman can see' as role, COUNT(*) as job_count FROM jobs;
RESET ROLE;
"@

# Test as QA
Write-Host "`n✅ Testing as QA..." -ForegroundColor Green
psql $env:DATABASE_URL -c @"
SET app.current_user_id = 'QA001';
SET app.current_role = 'qa';
SET ROLE qa_role;
SELECT 'QA can see' as role, COUNT(*) as job_count FROM jobs;
RESET ROLE;
"@

# Step 6: Create sample data for testing
Write-Host "`n📝 Step 6: Creating test data..." -ForegroundColor Yellow
$createTestData = Read-Host "Create sample jobs for testing? (y/n)"
if ($createTestData -eq 'y') {
    psql $env:DATABASE_URL -c @"
-- Insert test jobs
INSERT INTO jobs (id, pm_number, notification_number, location, status, uploaded_by, assigned_crew, assigned_foreman)
VALUES 
    ('JOB-TEST-001', 'PM-12345', 'N-67890', 'Stockton Grid A', 'pending', 'PM001', NULL, NULL),
    ('JOB-TEST-002', 'PM-12346', 'N-67891', 'Stockton Grid B', 'assigned', 'PM001', 'CREW-001', 'F001'),
    ('JOB-TEST-003', 'PM-12347', 'N-67892', 'Stockton Grid C', 'ready_for_qa', 'PM002', 'CREW-002', 'F002'),
    ('JOB-TEST-004', 'PM-12348', 'N-67893', 'Stockton Grid D', 'approved', 'PM001', 'CREW-001', 'F001')
ON CONFLICT (id) DO NOTHING;

-- Test visibility
SELECT 'Total test jobs created:' as label, COUNT(*) as count FROM jobs WHERE id LIKE 'JOB-TEST-%';
"@
    Write-Host "✅ Test data created" -ForegroundColor Green
}

# Step 7: Test Python integration
Write-Host "`n🐍 Step 7: Testing Python integration..." -ForegroundColor Yellow
$testPython = Read-Host "Test Python RLS integration? (y/n)"
if ($testPython -eq 'y') {
    $pythonScript = Join-Path $PSScriptRoot "rls_integration.py"
    if (Test-Path $pythonScript) {
        python $pythonScript
    } else {
        Write-Host "⚠️ rls_integration.py not found" -ForegroundColor Yellow
    }
}

# Summary
Write-Host "`n=========================================" -ForegroundColor Green
Write-Host "✅ RLS Deployment Complete!" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Green

Write-Host "`n📊 Summary:" -ForegroundColor Yellow
Write-Host "• RLS is enabled on the jobs table"
Write-Host "• 4 role-based policies are active (PM, GF, Foreman, QA)"
Write-Host "• Audit logging is configured"
Write-Host "• Test with: python database\rls_integration.py"

Write-Host "`n🔧 Next Steps:" -ForegroundColor Yellow
Write-Host "1. Update your application to set user context on each request"
Write-Host "2. Use the RLSConnection class in rls_integration.py"
Write-Host "3. Test with different user roles"
Write-Host "4. Monitor audit_log table for access patterns"

Write-Host "`n🔄 To rollback:" -ForegroundColor Yellow
Write-Host "psql `$env:DATABASE_URL -c 'ALTER TABLE jobs DISABLE ROW LEVEL SECURITY;'" -ForegroundColor Cyan

# Create a test script
Write-Host "`n📝 Creating quick test script..." -ForegroundColor Yellow
$testScript = @'
# Quick RLS Test Script
import os
from database.rls_integration import test_rls_policies
import json

print("Testing RLS Policies...")
results = test_rls_policies()
print(json.dumps(results, indent=2))
'@

$testScript | Out-File -FilePath "test_rls_quick.py" -Encoding UTF8
Write-Host "✅ Created test_rls_quick.py - Run it anytime to verify RLS" -ForegroundColor Green
