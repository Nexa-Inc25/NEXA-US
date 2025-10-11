"""
Test with a properly formatted PDF
"""
import requests
import json

# Create a valid PDF with proper structure
pdf_bytes = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Count 1 /Kids [3 0 R] >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> >>
endobj
4 0 obj
<< /Length 178 >>
stream
BT
/F1 12 Tf
72 720 Td
(PG&E Job Package Audit Report) Tj
72 700 Td
(Location: Stockton Division) Tj
72 680 Td
(Issue: TAG-2 pole replacement required) Tj
72 660 Td
(Crew: 2-man crew needed) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000280 00000 n 
trailer
<< /Size 5 /Root 1 0 R >>
startxref
508
%%EOF"""

url = "https://nexa-doc-analyzer-oct2025.onrender.com/analyze-audit"

print("🚀 Uploading valid PDF to NEXA backend")
print("-" * 50)

files = {'file': ('audit_report.pdf', pdf_bytes, 'application/pdf')}

try:
    response = requests.post(url, files=files, timeout=60)
    
    print(f"📊 Status Code: {response.status_code}")
    
    if response.status_code == 200:
        print("✅ SUCCESS! PDF Analysis completed!")
        result = response.json()
        
        print(f"\n📋 Analysis Summary:")
        print(f"- Status: {result.get('status', 'N/A')}")
        print(f"- Processing Time: {result.get('processing_time', 'N/A')}")
        
        infractions = result.get('infractions', [])
        print(f"- Infractions Found: {len(infractions)}")
        
        if infractions:
            print("\n🔍 Detected Issues:")
            for i, infraction in enumerate(infractions[:5], 1):
                print(f"\n  {i}. Text: {infraction.get('text', '')[:100]}")
                print(f"     Status: {infraction.get('status', 'N/A')}")
                print(f"     Confidence: {infraction.get('confidence', 0):.1%}")
                
                # Show cost impact if available
                cost = infraction.get('cost_impact', {})
                if cost and cost.get('total_cost'):
                    print(f"     Cost Impact: ${cost.get('total_cost', 0):,.2f}")
        else:
            print("\n✅ No infractions detected - Job package is compliant!")
            
    elif response.status_code == 400:
        print(f"❌ Bad Request (400)")
        print(f"Error: {response.text[:500]}")
    elif response.status_code == 422:
        print(f"❌ Validation Error (422)")
        print(f"Details: {response.text[:500]}")
    else:
        print(f"❌ Unexpected Error ({response.status_code})")
        print(f"Response: {response.text[:500]}")
        
except Exception as e:
    print(f"❌ Exception occurred: {e}")

print("\n" + "="*50)
print("Test complete!")
