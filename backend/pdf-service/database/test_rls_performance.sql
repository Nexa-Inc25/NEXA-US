-- =====================================================
-- RLS Performance Test Suite
-- Run this to verify optimization effectiveness
-- =====================================================

\timing on
\echo '🚀 Starting RLS Performance Tests'
\echo '=================================='

-- =====================================================
-- Test 1: Index Usage Verification
-- =====================================================
\echo '\n📊 Test 1: Verifying Index Usage'
\echo '---------------------------------'

-- Check that indexes exist and are being used
SELECT 
    indexrelname as index_name,
    idx_scan as times_used,
    idx_tup_read as tuples_read,
    pg_size_pretty(pg_relation_size(indexrelid)) as size
FROM pg_stat_user_indexes
WHERE schemaname = 'public' 
    AND tablename = 'jobs'
    AND idx_scan > 0
ORDER BY idx_scan DESC
LIMIT 10;

-- =====================================================
-- Test 2: Simple Query Performance (PM Role)
-- =====================================================
\echo '\n👤 Test 2: PM Query Performance'
\echo '-------------------------------'

-- Set PM context
SET app.current_user_id = 'PM-001';
SET app.current_role = 'pm';
SET ROLE pm_role;

-- Measure query time
EXPLAIN (ANALYZE, BUFFERS) 
SELECT COUNT(*) FROM jobs WHERE user_id = 'PM-001';

-- Should use index scan
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM jobs 
WHERE user_id = 'PM-001' 
LIMIT 10;

RESET ROLE;

-- =====================================================
-- Test 3: Crew-based Query (Foreman Role)
-- =====================================================
\echo '\n👷 Test 3: Foreman Query Performance'
\echo '------------------------------------'

-- Set Foreman context
SET app.current_user_id = 'F-001';
SET app.current_role = 'foreman';
SET app.current_crew = 'CREW-001';
SET ROLE foreman_role;

-- Test crew filter (should use idx_jobs_crew_id)
EXPLAIN (ANALYZE, BUFFERS)
SELECT COUNT(*) FROM jobs WHERE crew_id = 'CREW-001';

-- Test compound filter (should use idx_jobs_status_crew)
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM jobs 
WHERE crew_id = 'CREW-001' 
    AND status = 'assigned'
LIMIT 10;

RESET ROLE;

-- =====================================================
-- Test 4: Status-based Query (QA Role)
-- =====================================================
\echo '\n✅ Test 4: QA Query Performance'
\echo '--------------------------------'

-- Set QA context
SET app.current_user_id = 'QA-001';
SET app.current_role = 'qa';
SET ROLE qa_role;

-- Should use partial index idx_jobs_qa_ready
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM jobs 
WHERE status = 'ready_for_qa'
ORDER BY submission_date
LIMIT 20;

RESET ROLE;

-- =====================================================
-- Test 5: Complex Multi-condition Query
-- =====================================================
\echo '\n🔍 Test 5: Complex Query Performance'
\echo '------------------------------------'

-- Test query with multiple conditions
EXPLAIN (ANALYZE, BUFFERS)
SELECT 
    j.id,
    j.pm_number,
    j.status,
    j.total_savings
FROM jobs j
WHERE j.status IN ('pending', 'assigned')
    AND j.is_active = TRUE
    AND j.is_archived = FALSE
    AND j.tenant_id = 1
    AND j.created_at > NOW() - INTERVAL '30 days'
ORDER BY j.created_at DESC
LIMIT 50;

-- =====================================================
-- Test 6: Materialized View Performance
-- =====================================================
\echo '\n📋 Test 6: Materialized View Performance'
\echo '----------------------------------------'

-- Direct query (baseline)
\echo 'Direct query from jobs table:'
EXPLAIN (ANALYZE, BUFFERS)
SELECT COUNT(*) 
FROM jobs 
WHERE is_active = TRUE 
    AND is_archived = FALSE;

-- Materialized view query (should be faster)
\echo 'Query from materialized view:'
EXPLAIN (ANALYZE, BUFFERS)
SELECT COUNT(*) 
FROM active_jobs_mv;

-- =====================================================
-- Test 7: Aggregation Performance
-- =====================================================
\echo '\n📈 Test 7: Aggregation Query Performance'
\echo '----------------------------------------'

-- Group by with aggregation
EXPLAIN (ANALYZE, BUFFERS)
SELECT 
    status,
    COUNT(*) as count,
    AVG(total_savings) as avg_savings,
    SUM(repealable_count) as total_repealable
FROM jobs
WHERE tenant_id = 1
GROUP BY status
ORDER BY count DESC;

-- =====================================================
-- Test 8: JSONB Query Performance
-- =====================================================
\echo '\n🔧 Test 8: JSONB Query Performance'
\echo '----------------------------------'

-- Should use GIN index
EXPLAIN (ANALYZE, BUFFERS)
SELECT id, pm_number, final_analysis
FROM jobs
WHERE final_analysis @> '{"repealable": true}'::jsonb
LIMIT 10;

-- =====================================================
-- Test 9: Concurrent User Simulation
-- =====================================================
\echo '\n👥 Test 9: Simulating Concurrent Access'
\echo '---------------------------------------'

-- Simulate multiple users accessing simultaneously
DO $$
DECLARE
    start_time timestamp;
    end_time timestamp;
    i integer;
BEGIN
    start_time := clock_timestamp();
    
    FOR i IN 1..10 LOOP
        PERFORM COUNT(*) FROM jobs WHERE user_id = 'USER-' || i;
    END LOOP;
    
    end_time := clock_timestamp();
    RAISE NOTICE 'Concurrent simulation time: % ms', 
        EXTRACT(MILLISECOND FROM (end_time - start_time));
END $$;

-- =====================================================
-- Test 10: Large Dataset Performance
-- =====================================================
\echo '\n📊 Test 10: Large Dataset Performance'
\echo '-------------------------------------'

-- Test on full dataset
SELECT 
    COUNT(*) as total_records,
    COUNT(DISTINCT user_id) as unique_users,
    COUNT(DISTINCT crew_id) as unique_crews
FROM jobs;

-- Paginated query (common pattern)
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM jobs
WHERE status = 'pending'
ORDER BY created_at DESC
LIMIT 20 OFFSET 100;

-- =====================================================
-- Performance Summary
-- =====================================================
\echo '\n📊 PERFORMANCE SUMMARY'
\echo '====================='

-- Overall statistics
SELECT 
    'Index Efficiency' as metric,
    ROUND(
        100.0 * SUM(idx_scan) / NULLIF(SUM(seq_scan + idx_scan), 0), 
        2
    ) || '%' as value
FROM pg_stat_user_tables
WHERE tablename = 'jobs'
UNION ALL
SELECT 
    'Cache Hit Rate',
    ROUND(
        100.0 * SUM(heap_blks_hit) / NULLIF(SUM(heap_blks_hit + heap_blks_read), 0),
        2
    ) || '%'
FROM pg_statio_user_tables
WHERE tablename = 'jobs'
UNION ALL
SELECT 
    'Dead Tuple Ratio',
    ROUND(
        100.0 * n_dead_tup / NULLIF(n_live_tup + n_dead_tup, 0),
        2
    ) || '%'
FROM pg_stat_user_tables
WHERE tablename = 'jobs'
UNION ALL
SELECT 
    'Table Size',
    pg_size_pretty(pg_total_relation_size('jobs'))
UNION ALL
SELECT 
    'Index Size',
    pg_size_pretty(
        SUM(pg_relation_size(indexrelid))
    )
FROM pg_stat_user_indexes
WHERE tablename = 'jobs';

-- Check for slow queries (if pg_stat_statements is enabled)
\echo '\n🐌 Checking for Slow Queries'
\echo '----------------------------'

-- This will error if pg_stat_statements is not enabled
-- That's okay - it's optional
SELECT 
    SUBSTRING(query, 1, 50) || '...' as query_preview,
    calls,
    ROUND(mean_exec_time::numeric, 2) as avg_ms,
    ROUND(max_exec_time::numeric, 2) as max_ms
FROM pg_stat_statements
WHERE query LIKE '%jobs%'
    AND query NOT LIKE '%pg_stat%'
    AND mean_exec_time > 100
ORDER BY mean_exec_time DESC
LIMIT 5;

\echo '\n✅ Performance tests complete!'
\echo 'Expected results:'
\echo '- All queries should use index scans (not seq scans)'
\echo '- Query times should be <100ms for most operations'
\echo '- Index efficiency should be >80%'
\echo '- Cache hit rate should be >90%'
\echo '- Dead tuple ratio should be <20%'

\timing off
