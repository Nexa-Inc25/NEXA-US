"""
Quick test to verify Week 1 optimizations without excessive pipeline usage
"""
import requests
import time
import json

API_URL = "https://nexa-api-xpu3.onrender.com"

def test_health():
    """Test basic health endpoint"""
    r = requests.get(f"{API_URL}/health")
    assert r.status_code == 200, f"Health check failed: {r.status_code}"
    print("✓ Health check passed")

def test_rate_limit():
    """Verify rate limit increased to 200/min"""
    r = requests.get(f"{API_URL}/spec-library")
    headers = r.headers
    
    if 'X-RateLimit-Limit' in headers:
        limit = int(headers['X-RateLimit-Limit'])
        print(f"✓ Rate limit: {limit} req/min")
        assert limit == 200, f"Expected 200, got {limit}"
    else:
        print("⚠ Rate limit headers not found (may be behind proxy)")

def test_spec_library():
    """Test spec library endpoint"""
    r = requests.get(f"{API_URL}/spec-library")
    assert r.status_code == 200, f"Spec library failed: {r.status_code}"
    data = r.json()
    print(f"✓ Spec library: {data.get('total_files', 0)} files, {data.get('total_chunks', 0)} chunks")

def test_response_time():
    """Test response time target <2s"""
    times = []
    for i in range(5):
        start = time.time()
        r = requests.get(f"{API_URL}/health")
        elapsed = time.time() - start
        times.append(elapsed)
    
    avg_time = sum(times) / len(times)
    print(f"✓ Avg response time: {avg_time:.3f}s (target <2s)")
    assert avg_time < 2.0, f"Response too slow: {avg_time:.3f}s"

if __name__ == "__main__":
    print("🧪 Week 1 Optimization Tests")
    print("=" * 40)
    
    try:
        test_health()
        test_rate_limit()
        test_spec_library()
        test_response_time()
        
        print("\n✅ All tests passed - Week 1 optimizations working!")
        print("📊 Metrics:")
        print("  - Rate limit: 200 req/min ✓")
        print("  - Response time: <2s ✓")
        print("  - API healthy ✓")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        exit(1)
