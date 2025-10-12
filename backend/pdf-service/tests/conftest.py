"""
Shared pytest fixtures for NEXA PDF Service tests
Provides test clients, temporary directories, and mock data
"""
import pytest
import sys
import os
import shutil
import tempfile
from pathlib import Path
from fastapi.testclient import TestClient

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import apps after path setup
from app_electrical import app as electrical_app
from app_oct2025_enhanced import app as enhanced_app


@pytest.fixture(scope="function")
def electrical_client():
    """Test client for app_electrical.py"""
    client = TestClient(electrical_app)
    yield client
    # Clean up any test data
    electrical_app.dependency_overrides = {}


@pytest.fixture(scope="function")
def enhanced_client():
    """Test client for app_oct2025_enhanced.py"""
    client = TestClient(enhanced_app)
    yield client
    # Clean up any test data
    enhanced_app.dependency_overrides = {}


@pytest.fixture(scope="function")
def temp_data_dir():
    """Create temporary data directory for testing"""
    temp_dir = tempfile.mkdtemp(prefix="nexa_test_")
    yield temp_dir
    # Clean up after test
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture(scope="function")
def sample_spec_pdf(temp_data_dir):
    """Create a sample spec PDF for testing"""
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    
    pdf_path = Path(temp_data_dir) / "test_spec.pdf"
    c = canvas.Canvas(str(pdf_path), pagesize=letter)
    c.drawString(100, 750, "Test Electrical Specification")
    c.drawString(100, 730, "GO 95 - General Order 95")
    c.drawString(100, 710, "CPUC regulations")
    c.drawString(100, 690, "12kV insulators required")
    c.drawString(100, 670, "Minimum clearance: 8 feet")
    c.save()
    
    return str(pdf_path)


@pytest.fixture(scope="function")
def sample_audit_pdf(temp_data_dir):
    """Create a sample audit PDF for testing"""
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    
    pdf_path = Path(temp_data_dir) / "test_audit.pdf"
    c = canvas.Canvas(str(pdf_path), pagesize=letter)
    c.drawString(100, 750, "Electrical Audit Report")
    c.drawString(100, 730, "Go-back Infraction: Crossarm at 20 inches violating GO 95")
    c.drawString(100, 710, "Go-back Infraction: Underground conduit at 36 inches")
    c.drawString(100, 690, "Violation of CPUC requirements")
    c.save()
    
    return str(pdf_path)


@pytest.fixture(scope="function")
def mock_spec_entities():
    """Mock spec entities for testing"""
    return {
        'STANDARD': [
            {'word': 'GO 95', 'score': 0.95},
            {'word': 'CPUC', 'score': 0.93},
            {'word': 'ANSI C29.1', 'score': 0.91}
        ],
        'EQUIPMENT': [
            {'word': 'insulator', 'score': 0.90},
            {'word': 'conductor', 'score': 0.88},
            {'word': 'crossarm', 'score': 0.89}
        ],
        'MEASURE': [
            {'word': '12kV', 'score': 0.87},
            {'word': '8 feet', 'score': 0.85},
            {'word': '20 inches', 'score': 0.86}
        ]
    }


@pytest.fixture(scope="function")
def empty_pdf_content():
    """Return empty PDF file content"""
    return b"" 


@pytest.fixture(scope="function")
def large_pdf_content():
    """Return oversized PDF content for testing size limits"""
    # Create 1MB of data (for testing without memory issues)
    return b"x" * (1024 * 1024)


@pytest.fixture(autouse=True)
def reset_performance_metrics():
    """Reset performance metrics before each test"""
    from app_electrical import performance_metrics
    
    performance_metrics.update({
        "requests_total": 0,
        "requests_success": 0,
        "requests_failed": 0,
        "avg_response_time": 0,
        "entity_extraction_times": []
    })
    yield
