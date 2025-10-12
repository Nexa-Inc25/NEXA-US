#!/usr/bin/env python3
"""
Load Testing Script for ML Document Analyzer
Simulates production workloads to test scaling
"""

import asyncio
import aiohttp
import time
import json
import random
import numpy as np
from typing import List, Dict, Any
from pathlib import Path
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LoadTester:
    """
    Simulates various load scenarios for the ML analyzer
    """
    
    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
        self.results = []
        self.start_time = None
        self.end_time = None
        
        # Test data
        self.test_infractions = [
            "Pole clearance only 16 ft over street - violation",
            "Conduit cover 20 inches for secondary - infraction",
            "18 ft clearance over street meets requirement",
            "30 inches cover for primary service compliant",
            "Missing vibration damper on 350 foot span",
            "ACSR conductor with #4 AWG size installed",
            "Pin insulator installed in horizontal plane",
            "8'-6\" clearance from railroad tangent track",
            "Ground clearance 15 feet in vehicle accessible area",
            "0-750V clearance only 2 inches, below minimum"
        ]
        
        # Test PDFs (create small test files)
        self.test_pdfs = self._create_test_pdfs()
    
    def _create_test_pdfs(self) -> List[Path]:
        """Create small test PDF files"""
        
        test_dir = Path("test_pdfs")
        test_dir.mkdir(exist_ok=True)
        
        pdfs = []
        for i in range(5):
            pdf_path = test_dir / f"test_spec_{i}.pdf"
            
            # Create a simple text file (mock PDF for testing)
            with open(pdf_path, 'w') as f:
                f.write(f"""
                Test Specification Document {i}
                
                Section 1: Clearances
                - Minimum clearance over streets: 18 feet
                - Minimum clearance over sidewalks: 15 feet
                - Railroad tangent track clearance: 8'-6"
                
                Section 2: Underground Requirements  
                - Conduit depth: minimum 30 inches for primary
                - Conduit depth: minimum 24 inches for secondary
                - Material: PVC Schedule 40 or HDPE
                
                Section 3: Standards
                - Comply with G.O. 95
                - Follow ANSI standards
                - Reference PG&E Document {1000 + i}
                """)
            
            pdfs.append(pdf_path)
        
        return pdfs
    
    async def test_endpoint(self, session: aiohttp.ClientSession, 
                           endpoint: str, method: str = "GET", 
                           data: Any = None, files: Any = None) -> Dict:
        """Test a single endpoint"""
        
        start = time.time()
        
        try:
            if method == "GET":
                async with session.get(f"{self.base_url}{endpoint}") as response:
                    status = response.status
                    content = await response.text()
            elif method == "POST":
                if files:
                    async with session.post(f"{self.base_url}{endpoint}", data=files) as response:
                        status = response.status
                        content = await response.text()
                else:
                    async with session.post(f"{self.base_url}{endpoint}", json=data) as response:
                        status = response.status
                        content = await response.text()
            
            duration = time.time() - start
            
            return {
                "endpoint": endpoint,
                "status": status,
                "duration": duration,
                "success": 200 <= status < 300,
                "timestamp": time.time()
            }
            
        except Exception as e:
            duration = time.time() - start
            
            return {
                "endpoint": endpoint,
                "status": 0,
                "duration": duration,
                "success": False,
                "error": str(e),
                "timestamp": time.time()
            }
    
    async def test_analyze_goback(self, session: aiohttp.ClientSession, 
                                  concurrent: int = 10) -> List[Dict]:
        """Test analyze-go-back endpoint with concurrent requests"""
        
        logger.info(f"Testing /analyze-go-back with {concurrent} concurrent requests...")
        
        tasks = []
        for i in range(concurrent):
            infraction = random.choice(self.test_infractions)
            task = self.test_endpoint(
                session, 
                "/analyze-go-back",
                method="POST",
                data={"infraction_text": infraction}
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        return results
    
    async def test_batch_analyze(self, session: aiohttp.ClientSession,
                                batch_size: int = 10) -> Dict:
        """Test batch analysis endpoint"""
        
        logger.info(f"Testing /batch-analyze-go-backs with batch size {batch_size}...")
        
        batch = random.sample(self.test_infractions, min(batch_size, len(self.test_infractions)))
        
        result = await self.test_endpoint(
            session,
            "/batch-analyze-go-backs",
            method="POST",
            data=batch
        )
        
        return result
    
    async def test_spec_upload(self, session: aiohttp.ClientSession) -> Dict:
        """Test spec upload endpoint"""
        
        logger.info("Testing /learn-spec endpoint...")
        
        if not self.test_pdfs:
            return {"error": "No test PDFs available"}
        
        pdf_path = random.choice(self.test_pdfs)
        
        with open(pdf_path, 'rb') as f:
            data = aiohttp.FormData()
            data.add_field('file', f, 
                          filename=pdf_path.name,
                          content_type='application/pdf')
            
            result = await self.test_endpoint(
                session,
                "/learn-spec",
                method="POST",
                files=data
            )
        
        return result
    
    async def test_metrics(self, session: aiohttp.ClientSession) -> Dict:
        """Test metrics endpoints"""
        
        logger.info("Testing monitoring endpoints...")
        
        endpoints = [
            "/ml/metrics",
            "/ml/scaling-recommendations",
            "/monitoring/metrics",
            "/monitoring/alerts",
            "/health"
        ]
        
        results = []
        for endpoint in endpoints:
            result = await self.test_endpoint(session, endpoint)
            results.append(result)
        
        return results
    
    async def sustained_load_test(self, 
                                  duration_seconds: int = 60,
                                  users: int = 10,
                                  think_time: float = 1.0):
        """
        Simulate sustained load with multiple users
        
        Args:
            duration_seconds: How long to run the test
            users: Number of concurrent users
            think_time: Delay between requests per user
        """
        
        logger.info(f"Starting sustained load test: {users} users for {duration_seconds}s")
        
        self.start_time = time.time()
        self.results = []
        
        async with aiohttp.ClientSession() as session:
            # First, ensure health check passes
            health = await self.test_endpoint(session, "/health")
            if not health["success"]:
                logger.error("Health check failed, aborting test")
                return
            
            end_time = time.time() + duration_seconds
            user_tasks = []
            
            # Create user simulation tasks
            for user_id in range(users):
                user_tasks.append(
                    self._simulate_user(session, user_id, end_time, think_time)
                )
            
            # Run all users concurrently
            await asyncio.gather(*user_tasks)
        
        self.end_time = time.time()
        
        # Calculate and report statistics
        self._report_statistics()
    
    async def _simulate_user(self, session: aiohttp.ClientSession,
                           user_id: int, end_time: float, think_time: float):
        """Simulate a single user's behavior"""
        
        logger.info(f"User {user_id} started")
        
        while time.time() < end_time:
            # Random action
            action = random.choice([
                "analyze",      # 50% weight
                "analyze",
                "batch",        # 20% weight
                "metrics",      # 20% weight
                "upload"        # 10% weight
            ])
            
            if action == "analyze":
                results = await self.test_analyze_goback(session, concurrent=1)
                self.results.extend(results)
                
            elif action == "batch":
                result = await self.test_batch_analyze(session, batch_size=5)
                self.results.append(result)
                
            elif action == "metrics":
                results = await self.test_metrics(session)
                self.results.extend(results)
                
            elif action == "upload":
                result = await self.test_spec_upload(session)
                self.results.append(result)
            
            # Think time
            await asyncio.sleep(think_time + random.random())
        
        logger.info(f"User {user_id} finished")
    
    async def spike_test(self, 
                        initial_users: int = 5,
                        spike_users: int = 50,
                        spike_duration: int = 30):
        """
        Test system behavior under sudden load spike
        """
        
        logger.info(f"Spike test: {initial_users} -> {spike_users} users")
        
        async with aiohttp.ClientSession() as session:
            # Normal load
            logger.info(f"Phase 1: Normal load ({initial_users} users)")
            await self._run_concurrent_requests(session, initial_users, duration=30)
            
            # Spike
            logger.info(f"Phase 2: Spike ({spike_users} users)")
            await self._run_concurrent_requests(session, spike_users, duration=spike_duration)
            
            # Recovery
            logger.info(f"Phase 3: Recovery ({initial_users} users)")
            await self._run_concurrent_requests(session, initial_users, duration=30)
        
        self._report_statistics()
    
    async def _run_concurrent_requests(self, session: aiohttp.ClientSession,
                                      users: int, duration: int):
        """Run concurrent requests for a duration"""
        
        end_time = time.time() + duration
        
        while time.time() < end_time:
            results = await self.test_analyze_goback(session, concurrent=users)
            self.results.extend(results)
            await asyncio.sleep(0.5)
    
    def _report_statistics(self):
        """Generate and print test statistics"""
        
        if not self.results:
            logger.warning("No results to report")
            return
        
        # Calculate statistics
        total_requests = len(self.results)
        successful = [r for r in self.results if r.get("success", False)]
        failed = [r for r in self.results if not r.get("success", False)]
        
        durations = [r["duration"] for r in successful if "duration" in r]
        
        if durations:
            p50 = np.percentile(durations, 50)
            p95 = np.percentile(durations, 95)
            p99 = np.percentile(durations, 99)
        else:
            p50 = p95 = p99 = 0
        
        # Calculate throughput
        if self.start_time and self.end_time:
            test_duration = self.end_time - self.start_time
            throughput = total_requests / test_duration
        else:
            test_duration = 0
            throughput = 0
        
        # Group by endpoint
        endpoint_stats = {}
        for r in self.results:
            endpoint = r.get("endpoint", "unknown")
            if endpoint not in endpoint_stats:
                endpoint_stats[endpoint] = {
                    "count": 0,
                    "success": 0,
                    "failed": 0,
                    "durations": []
                }
            
            endpoint_stats[endpoint]["count"] += 1
            if r.get("success"):
                endpoint_stats[endpoint]["success"] += 1
                if "duration" in r:
                    endpoint_stats[endpoint]["durations"].append(r["duration"])
            else:
                endpoint_stats[endpoint]["failed"] += 1
        
        # Print report
        print("\n" + "="*60)
        print("LOAD TEST RESULTS")
        print("="*60)
        print(f"Test Duration: {test_duration:.1f} seconds")
        print(f"Total Requests: {total_requests}")
        print(f"Successful: {len(successful)} ({len(successful)/total_requests*100:.1f}%)")
        print(f"Failed: {len(failed)} ({len(failed)/total_requests*100:.1f}%)")
        print(f"Throughput: {throughput:.1f} req/s")
        print()
        print("Response Times (successful requests):")
        print(f"  Mean: {np.mean(durations):.3f}s" if durations else "  No data")
        print(f"  P50: {p50:.3f}s")
        print(f"  P95: {p95:.3f}s")
        print(f"  P99: {p99:.3f}s")
        print(f"  Min: {np.min(durations):.3f}s" if durations else "  No data")
        print(f"  Max: {np.max(durations):.3f}s" if durations else "  No data")
        print()
        print("Endpoint Statistics:")
        for endpoint, stats in endpoint_stats.items():
            success_rate = (stats["success"] / stats["count"] * 100) if stats["count"] > 0 else 0
            avg_duration = np.mean(stats["durations"]) if stats["durations"] else 0
            print(f"  {endpoint}:")
            print(f"    Requests: {stats['count']}")
            print(f"    Success Rate: {success_rate:.1f}%")
            print(f"    Avg Duration: {avg_duration:.3f}s")
        
        # Save detailed results
        results_file = f"load_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump({
                "summary": {
                    "duration": test_duration,
                    "total_requests": total_requests,
                    "successful": len(successful),
                    "failed": len(failed),
                    "throughput": throughput,
                    "p50": p50,
                    "p95": p95,
                    "p99": p99
                },
                "endpoint_stats": endpoint_stats,
                "detailed_results": self.results[:100]  # First 100 for review
            }, f, indent=2)
        
        print(f"\nDetailed results saved to: {results_file}")
        print("="*60)

async def main():
    """Run load tests"""
    
    import argparse
    
    parser = argparse.ArgumentParser(description="Load test the ML Document Analyzer")
    parser.add_argument("--url", default="http://localhost:8001", help="Base URL")
    parser.add_argument("--test", choices=["sustained", "spike", "quick"], 
                       default="quick", help="Test type")
    parser.add_argument("--users", type=int, default=10, help="Number of concurrent users")
    parser.add_argument("--duration", type=int, default=60, help="Test duration in seconds")
    parser.add_argument("--think-time", type=float, default=1.0, help="Think time between requests")
    
    args = parser.parse_args()
    
    tester = LoadTester(base_url=args.url)
    
    if args.test == "quick":
        # Quick test with a few requests
        logger.info("Running quick test...")
        async with aiohttp.ClientSession() as session:
            # Test each endpoint type once
            await tester.test_analyze_goback(session, concurrent=5)
            await tester.test_batch_analyze(session, batch_size=5)
            await tester.test_metrics(session)
        tester._report_statistics()
        
    elif args.test == "sustained":
        # Sustained load test
        await tester.sustained_load_test(
            duration_seconds=args.duration,
            users=args.users,
            think_time=args.think_time
        )
        
    elif args.test == "spike":
        # Spike test
        await tester.spike_test(
            initial_users=args.users,
            spike_users=args.users * 5,
            spike_duration=30
        )

if __name__ == "__main__":
    asyncio.run(main())
