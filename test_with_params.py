"""
Test with additional parameters that might be required
"""
import requests

pdf_bytes = b"""%PDF-1.0
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj  
3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Contents 4 0 R>>endobj
4 0 obj<</Length 44>>stream
BT /F1 12 Tf 72 720 Td (TAG-2 replacement) Tj ET
endstream endobj
xref
0 5
0000000000 65535 f 
trailer<</Size 5/Root 1 0 R>>
startxref
248
%%EOF"""

url = "https://nexa-doc-analyzer-oct2025.onrender.com/analyze-audit"

# Try different parameter combinations
tests = [
    {
        'name': 'Test 1: With max_infractions',
        'files': {'job_package': ('test.pdf', pdf_bytes, 'application/pdf')},
        'data': {'max_infractions': 50}
    },
    {
        'name': 'Test 2: With confidence_threshold',
        'files': {'job_package': ('test.pdf', pdf_bytes, 'application/pdf')},
        'data': {'confidence_threshold': 0.7}
    },
    {
        'name': 'Test 3: With both parameters',
        'files': {'job_package': ('test.pdf', pdf_bytes, 'application/pdf')},
        'data': {'max_infractions': 50, 'confidence_threshold': 0.7}
    },
    {
        'name': 'Test 4: Just file, no extra params',
        'files': {'job_package': ('test.pdf', pdf_bytes, 'application/pdf')},
        'data': {}
    }
]

for test in tests:
    print(f"\n{'='*50}")
    print(test['name'])
    print('='*50)
    
    try:
        if test['data']:
            response = requests.post(url, files=test['files'], data=test['data'], timeout=30)
        else:
            response = requests.post(url, files=test['files'], timeout=30)
            
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ SUCCESS!")
            result = response.json()
            if 'infractions' in result:
                print(f"Infractions found: {len(result['infractions'])}")
            break
        else:
            error = response.text[:200]
            print(f"Error: {error}")
    except Exception as e:
        print(f"Exception: {e}")
