"""
Test PDF upload to NEXA backend
"""
import requests
from io import BytesIO
import json

# Create minimal PDF content
pdf_content = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> /Contents 4 0 R >>
endobj
4 0 obj
<< /Length 89 >>
stream
BT
/F1 12 Tf
100 700 Td
(PG&E Job Package Test) Tj
100 680 Td
(TAG-2 pole replacement required) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000229 00000 n 
trailer
<< /Size 5 /Root 1 0 R >>
startxref
365
%%EOF"""

# API endpoint
url = "https://nexa-doc-analyzer-oct2025.onrender.com/analyze-audit"

# Create file-like object
pdf_file = BytesIO(pdf_content)
pdf_file.name = "test_job.pdf"

# Upload the PDF
print("🚀 Uploading test PDF to NEXA backend...")
try:
    files = {'job_package': ('test_job.pdf', pdf_file, 'application/pdf')}
    response = requests.post(url, files=files, timeout=30)
    
    print(f"📊 Status Code: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print("✅ Analysis successful!")
        print(json.dumps(result, indent=2))
    else:
        print(f"❌ Error: {response.status_code}")
        print(f"Response: {response.text}")
        
except Exception as e:
    print(f"❌ Exception occurred: {e}")
    
print("\n🔍 Testing other endpoints...")

# Test health
health = requests.get("https://nexa-doc-analyzer-oct2025.onrender.com/health")
print(f"Health: {health.status_code} - {health.json()}")

# Test spec library
specs = requests.get("https://nexa-doc-analyzer-oct2025.onrender.com/spec-library")
print(f"Spec Library: {specs.status_code} - Total files: {specs.json().get('total_files', 'N/A')}")

# Test pricing status
pricing = requests.get("https://nexa-doc-analyzer-oct2025.onrender.com/pricing/pricing-status")
print(f"Pricing: {pricing.status_code} - Status: {pricing.json().get('status', 'N/A')}")
