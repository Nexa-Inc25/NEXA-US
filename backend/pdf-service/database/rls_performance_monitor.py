"""
RLS Performance Monitoring and Testing Tool
Validates optimization effectiveness and identifies bottlenecks
"""

import os
import time
import logging
from typing import Dict, List, Tuple, Any
import psycopg2
from psycopg2.extras import RealDictCursor
import json
from datetime import datetime, timedelta
import statistics

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RLSPerformanceMonitor:
    """
    Monitor and test RLS performance with various optimization techniques
    """
    
    def __init__(self, database_url: str = None):
        self.database_url = database_url or os.getenv("DATABASE_URL")
        if self.database_url and self.database_url.startswith("postgres://"):
            self.database_url = self.database_url.replace("postgres://", "postgresql://", 1)
        
        self.results = {
            'baseline': {},
            'with_indexes': {},
            'with_optimized_policies': {},
            'with_materialized_views': {}
        }
    
    def connect(self):
        """Get database connection"""
        return psycopg2.connect(self.database_url)
    
    def run_performance_tests(self) -> Dict[str, Any]:
        """
        Run comprehensive performance tests
        """
        logger.info("🚀 Starting RLS Performance Tests")
        logger.info("=" * 50)
        
        # Test 1: Index effectiveness
        self.test_index_usage()
        
        # Test 2: Policy performance by role
        self.test_role_performance()
        
        # Test 3: Query plan analysis
        self.analyze_query_plans()
        
        # Test 4: Materialized view performance
        self.test_materialized_views()
        
        # Test 5: Concurrent user simulation
        self.test_concurrent_access()
        
        # Test 6: Large dataset performance
        self.test_large_dataset()
        
        # Generate report
        return self.generate_report()
    
    def test_index_usage(self) -> Dict[str, Any]:
        """
        Verify indexes are being used effectively
        """
        logger.info("\n📊 Testing Index Usage...")
        
        with self.connect() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Check index statistics
                cursor.execute("""
                    SELECT 
                        indexrelname as index_name,
                        idx_scan as scans,
                        idx_tup_read as tuples_read,
                        idx_tup_fetch as tuples_fetched,
                        pg_size_pretty(pg_relation_size(indexrelid)) as size
                    FROM pg_stat_user_indexes
                    WHERE schemaname = 'public' 
                        AND tablename = 'jobs'
                    ORDER BY idx_scan DESC
                """)
                
                index_stats = cursor.fetchall()
                
                # Check for unused indexes
                cursor.execute("""
                    SELECT 
                        indexrelname as unused_index
                    FROM pg_stat_user_indexes
                    WHERE schemaname = 'public'
                        AND tablename = 'jobs'
                        AND idx_scan = 0
                        AND indexrelname != 'jobs_pkey'
                """)
                
                unused = cursor.fetchall()
                
                results = {
                    'index_stats': index_stats,
                    'unused_indexes': [r['unused_index'] for r in unused],
                    'index_efficiency': self.calculate_index_efficiency(cursor)
                }
                
                logger.info(f"✅ Found {len(index_stats)} indexes")
                logger.info(f"⚠️  {len(unused)} unused indexes")
                
                return results
    
    def calculate_index_efficiency(self, cursor) -> float:
        """
        Calculate overall index efficiency
        """
        cursor.execute("""
            SELECT 
                SUM(idx_scan) as total_index_scans,
                SUM(seq_scan) as total_seq_scans
            FROM pg_stat_user_tables
            WHERE schemaname = 'public' AND tablename = 'jobs'
        """)
        
        result = cursor.fetchone()
        if result and result['total_index_scans'] and result['total_seq_scans']:
            total_scans = result['total_index_scans'] + result['total_seq_scans']
            efficiency = (result['total_index_scans'] / total_scans) * 100 if total_scans > 0 else 0
            return round(efficiency, 2)
        return 0.0
    
    def test_role_performance(self) -> Dict[str, Any]:
        """
        Test query performance for each role
        """
        logger.info("\n👥 Testing Role-Based Performance...")
        
        test_cases = [
            ('PM', 'pm_role', 'USER-1', None, None),
            ('Foreman', 'foreman_role', 'F-1', 'CREW-1', None),
            ('GF', 'gf_role', 'GF-1', None, 1),
            ('QA', 'qa_role', 'QA-1', None, None)
        ]
        
        results = {}
        
        with self.connect() as conn:
            for role_name, role_db, user_id, crew_id, dept_id in test_cases:
                with conn.cursor() as cursor:
                    # Set session context
                    cursor.execute("SET app.current_user_id = %s", (user_id,))
                    cursor.execute("SET app.current_role = %s", (role_name.lower(),))
                    if crew_id:
                        cursor.execute("SET app.current_crew = %s", (crew_id,))
                    if dept_id:
                        cursor.execute("SET app.current_department = %s", (str(dept_id),))
                    
                    # Measure query time
                    start_time = time.time()
                    cursor.execute(f"SET ROLE {role_db}")
                    cursor.execute("SELECT COUNT(*) FROM jobs")
                    count = cursor.fetchone()[0]
                    cursor.execute("RESET ROLE")
                    query_time = time.time() - start_time
                    
                    # Get query plan
                    cursor.execute(f"SET ROLE {role_db}")
                    cursor.execute("EXPLAIN (FORMAT JSON, ANALYZE) SELECT * FROM jobs LIMIT 100")
                    plan = cursor.fetchone()[0]
                    cursor.execute("RESET ROLE")
                    
                    results[role_name] = {
                        'visible_rows': count,
                        'query_time_ms': round(query_time * 1000, 2),
                        'uses_index': self.check_index_usage(plan),
                        'plan_cost': plan[0]['Plan']['Total Cost'] if plan else None
                    }
                    
                    logger.info(f"✅ {role_name}: {count} rows in {query_time*1000:.2f}ms")
        
        return results
    
    def check_index_usage(self, plan: List[Dict]) -> bool:
        """
        Check if query plan uses indexes
        """
        if not plan or not plan[0]:
            return False
        
        plan_str = json.dumps(plan)
        return 'Index Scan' in plan_str or 'Bitmap Index Scan' in plan_str
    
    def analyze_query_plans(self) -> Dict[str, Any]:
        """
        Analyze query plans for common operations
        """
        logger.info("\n🔍 Analyzing Query Plans...")
        
        queries = {
            'filter_by_status': "SELECT * FROM jobs WHERE status = 'pending'",
            'filter_by_crew': "SELECT * FROM jobs WHERE crew_id = 'CREW-1'",
            'filter_by_user': "SELECT * FROM jobs WHERE user_id = 'USER-1'",
            'complex_filter': """
                SELECT * FROM jobs 
                WHERE status IN ('pending', 'assigned') 
                AND crew_id = 'CREW-1' 
                AND is_archived = FALSE
            """,
            'with_json': "SELECT * FROM jobs WHERE final_analysis->>'repealable' = 'true'"
        }
        
        results = {}
        
        with self.connect() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                for query_name, query in queries.items():
                    cursor.execute(f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {query}")
                    plan = cursor.fetchone()
                    
                    if plan and plan['QUERY PLAN']:
                        plan_data = plan['QUERY PLAN'][0]
                        results[query_name] = {
                            'execution_time': plan_data.get('Execution Time', 0),
                            'planning_time': plan_data.get('Planning Time', 0),
                            'uses_index': self.check_index_usage([plan_data]),
                            'rows_returned': plan_data['Plan'].get('Actual Rows', 0)
                        }
                    
                    logger.info(f"✅ {query_name}: {results[query_name]['execution_time']:.2f}ms")
        
        return results
    
    def test_materialized_views(self) -> Dict[str, Any]:
        """
        Test materialized view performance vs direct queries
        """
        logger.info("\n📋 Testing Materialized Views...")
        
        results = {}
        
        with self.connect() as conn:
            with conn.cursor() as cursor:
                # Test direct query
                start_time = time.time()
                cursor.execute("""
                    SELECT * FROM jobs 
                    WHERE is_active = TRUE 
                    AND is_archived = FALSE
                    LIMIT 100
                """)
                direct_time = time.time() - start_time
                
                # Test materialized view
                start_time = time.time()
                cursor.execute("SELECT * FROM active_jobs_mv LIMIT 100")
                mv_time = time.time() - start_time
                
                improvement = ((direct_time - mv_time) / direct_time * 100) if direct_time > 0 else 0
                
                results = {
                    'direct_query_ms': round(direct_time * 1000, 2),
                    'materialized_view_ms': round(mv_time * 1000, 2),
                    'improvement_percent': round(improvement, 2)
                }
                
                logger.info(f"✅ MV Performance: {improvement:.2f}% improvement")
        
        return results
    
    def test_concurrent_access(self, num_users: int = 10) -> Dict[str, Any]:
        """
        Simulate concurrent user access
        """
        logger.info(f"\n👥 Testing Concurrent Access ({num_users} users)...")
        
        import concurrent.futures
        
        def simulate_user(user_id: int) -> float:
            """Simulate a single user query"""
            with self.connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SET app.current_user_id = %s", (f'USER-{user_id}',))
                    cursor.execute("SET app.current_role = 'foreman'")
                    cursor.execute("SET app.current_crew = %s", (f'CREW-{user_id % 5}',))
                    
                    start = time.time()
                    cursor.execute("SELECT COUNT(*) FROM jobs")
                    cursor.fetchone()
                    return time.time() - start
        
        # Run concurrent queries
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_users) as executor:
            futures = [executor.submit(simulate_user, i) for i in range(num_users)]
            times = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        results = {
            'num_users': num_users,
            'avg_response_ms': round(statistics.mean(times) * 1000, 2),
            'max_response_ms': round(max(times) * 1000, 2),
            'min_response_ms': round(min(times) * 1000, 2),
            'std_dev_ms': round(statistics.stdev(times) * 1000, 2) if len(times) > 1 else 0
        }
        
        logger.info(f"✅ Avg response: {results['avg_response_ms']}ms")
        
        return results
    
    def test_large_dataset(self, num_records: int = 10000) -> Dict[str, Any]:
        """
        Test performance with large dataset
        """
        logger.info(f"\n📈 Testing Large Dataset ({num_records} records)...")
        
        with self.connect() as conn:
            with conn.cursor() as cursor:
                # Insert test data if needed
                cursor.execute("SELECT COUNT(*) FROM jobs WHERE id LIKE 'PERF-TEST-%'")
                existing = cursor.fetchone()[0]
                
                if existing < num_records:
                    logger.info(f"Inserting {num_records - existing} test records...")
                    cursor.execute("""
                        INSERT INTO jobs (id, pm_number, user_id, crew_id, status, tenant_id)
                        SELECT 
                            'PERF-TEST-' || i,
                            'PM-' || i,
                            'USER-' || (i % 100),
                            'CREW-' || (i % 20),
                            CASE i % 4
                                WHEN 0 THEN 'pending'
                                WHEN 1 THEN 'assigned'
                                WHEN 2 THEN 'ready_for_qa'
                                ELSE 'approved'
                            END,
                            (i % 5) + 1
                        FROM generate_series(%s, %s) AS i
                        ON CONFLICT (id) DO NOTHING
                    """, (existing + 1, num_records))
                    conn.commit()
                
                # Test queries on large dataset
                queries = [
                    ("Simple filter", "SELECT COUNT(*) FROM jobs WHERE status = 'pending'"),
                    ("Complex filter", """
                        SELECT COUNT(*) FROM jobs 
                        WHERE status IN ('pending', 'assigned') 
                        AND crew_id LIKE 'CREW-%'
                        AND created_at > NOW() - INTERVAL '30 days'
                    """),
                    ("Aggregation", """
                        SELECT status, COUNT(*), AVG(total_savings)
                        FROM jobs
                        GROUP BY status
                    """)
                ]
                
                results = {}
                for query_name, query in queries:
                    start = time.time()
                    cursor.execute(query)
                    cursor.fetchall()
                    query_time = time.time() - start
                    results[query_name] = round(query_time * 1000, 2)
                    logger.info(f"✅ {query_name}: {results[query_name]}ms")
        
        return {
            'dataset_size': num_records,
            'query_times': results
        }
    
    def generate_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive performance report
        """
        logger.info("\n📊 Generating Performance Report...")
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'database_url': self.database_url.split('@')[1] if '@' in self.database_url else 'local',
            'tests': {
                'index_usage': self.test_index_usage(),
                'role_performance': self.test_role_performance(),
                'query_plans': self.analyze_query_plans(),
                'materialized_views': self.test_materialized_views(),
                'concurrent_access': self.test_concurrent_access(),
                'large_dataset': self.test_large_dataset()
            },
            'recommendations': self.generate_recommendations()
        }
        
        # Save report
        report_file = f"rls_performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"✅ Report saved to {report_file}")
        
        return report
    
    def generate_recommendations(self) -> List[str]:
        """
        Generate optimization recommendations based on test results
        """
        recommendations = []
        
        # Check index efficiency
        with self.connect() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Check for missing indexes
                cursor.execute("""
                    SELECT 
                        schemaname,
                        tablename,
                        attname,
                        n_distinct,
                        correlation
                    FROM pg_stats
                    WHERE tablename = 'jobs'
                        AND n_distinct > 100
                        AND correlation < 0.1
                        AND attname NOT IN (
                            SELECT a.attname
                            FROM pg_index i
                            JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
                            WHERE i.indrelid = 'jobs'::regclass
                        )
                """)
                
                unindexed = cursor.fetchall()
                if unindexed:
                    for col in unindexed:
                        recommendations.append(
                            f"Consider adding index on {col['attname']} (high cardinality, low correlation)"
                        )
                
                # Check for bloat
                cursor.execute("""
                    SELECT 
                        pg_size_pretty(pg_total_relation_size('jobs')) as total_size,
                        (pg_stat_get_live_tuples('jobs'::regclass) + 
                         pg_stat_get_dead_tuples('jobs'::regclass)) as total_rows,
                        pg_stat_get_dead_tuples('jobs'::regclass) as dead_rows
                """)
                
                bloat = cursor.fetchone()
                if bloat and bloat['dead_rows'] > bloat['total_rows'] * 0.2:
                    recommendations.append(
                        f"High bloat detected ({bloat['dead_rows']} dead rows). Run VACUUM FULL."
                    )
                
                # Check for slow queries
                if cursor.execute("SELECT 1 FROM pg_stat_statements LIMIT 1"):
                    cursor.execute("""
                        SELECT 
                            query,
                            mean_exec_time
                        FROM pg_stat_statements
                        WHERE query LIKE '%jobs%'
                            AND mean_exec_time > 100
                        ORDER BY mean_exec_time DESC
                        LIMIT 5
                    """)
                    
                    slow_queries = cursor.fetchall()
                    if slow_queries:
                        recommendations.append(
                            f"Found {len(slow_queries)} slow queries (>100ms). Review query patterns."
                        )
        
        if not recommendations:
            recommendations.append("✅ Performance is optimal. No immediate optimizations needed.")
        
        return recommendations

def run_performance_suite():
    """
    Run complete performance test suite
    """
    monitor = RLSPerformanceMonitor()
    report = monitor.run_performance_tests()
    
    # Print summary
    print("\n" + "="*50)
    print("🎯 PERFORMANCE TEST SUMMARY")
    print("="*50)
    
    # Index efficiency
    index_eff = report['tests']['index_usage']['index_efficiency']
    print(f"📊 Index Efficiency: {index_eff}%")
    
    # Role performance
    for role, stats in report['tests']['role_performance'].items():
        print(f"👤 {role}: {stats['query_time_ms']}ms for {stats['visible_rows']} rows")
    
    # Concurrent performance
    concurrent = report['tests']['concurrent_access']
    print(f"👥 Concurrent Access: {concurrent['avg_response_ms']}ms avg ({concurrent['num_users']} users)")
    
    # Recommendations
    print("\n📋 Recommendations:")
    for i, rec in enumerate(report['recommendations'], 1):
        print(f"  {i}. {rec}")
    
    return report

if __name__ == "__main__":
    try:
        report = run_performance_suite()
        print("\n✅ Performance testing complete!")
        print(f"📄 Full report saved to: rls_performance_report_*.json")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
