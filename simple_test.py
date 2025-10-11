"""
Simple test to see exact error from analyze-audit
"""
import requests

# Create the absolute minimum valid PDF
pdf_bytes = b"""%PDF-1.0
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj
3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Contents 4 0 R>>endobj
4 0 obj<</Length 35>>stream
BT /F1 12 Tf 72 720 Td (TEST) Tj ET
endstream endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000052 00000 n 
0000000101 00000 n 
0000000178 00000 n 
trailer<</Size 5/Root 1 0 R>>
startxref
248
%%EOF"""

url = "https://nexa-doc-analyzer-oct2025.onrender.com/analyze-audit"

print("Uploading minimal PDF...")
files = {'job_package': ('test.pdf', pdf_bytes, 'application/pdf')}
response = requests.post(url, files=files, timeout=60)

print(f"Status: {response.status_code}")
print(f"Headers: {dict(response.headers)}")
print(f"Response: {response.text[:1000]}")  # First 1000 chars

# If it's JSON, parse it
try:
    data = response.json()
    print("\nParsed JSON:")
    import json
    print(json.dumps(data, indent=2)[:2000])  # First 2000 chars of formatted JSON
except:
    print("Not valid JSON")
