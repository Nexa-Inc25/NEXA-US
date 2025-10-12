"""
Test with CORRECT parameter name: 'file' not 'job_package'
"""
import requests
import json

pdf_bytes = b"""%PDF-1.0
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj  
3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Contents 4 0 R>>endobj
4 0 obj<</Length 80>>stream
BT /F1 12 Tf 72 720 Td (PG&E Audit Report) Tj 
72 700 Td (TAG-2 pole replacement) Tj ET
endstream endobj
trailer<</Size 5/Root 1 0 R>>
%%EOF"""

url = "https://nexa-doc-analyzer-oct2025.onrender.com/analyze-audit"

print("🚀 Testing with CORRECT parameter name: 'file'")
print("-" * 50)

# Use 'file' as the parameter name!
files = {'file': ('test_audit.pdf', pdf_bytes, 'application/pdf')}

try:
    response = requests.post(url, files=files, timeout=60)
    
    print(f"📊 Status Code: {response.status_code}")
    
    if response.status_code == 200:
        print("✅ SUCCESS! Analysis completed!")
        result = response.json()
        print(f"\n📋 Analysis Results:")
        print(json.dumps(result, indent=2)[:2000])
    else:
        print(f"❌ Error {response.status_code}")
        print(f"Response: {response.text[:500]}")
        
except Exception as e:
    print(f"❌ Exception: {e}")
