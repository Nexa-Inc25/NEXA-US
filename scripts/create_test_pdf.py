"""
Create a real test PDF using reportlab
"""
try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    
    # Create a test PDF
    pdf_file = "pge_test_audit.pdf"
    c = canvas.Canvas(pdf_file, pagesize=letter)
    
    # Add PG&E audit content
    c.setFont("Helvetica-Bold", 16)
    c.drawString(100, 750, "PG&E Field Audit Report")
    
    c.setFont("Helvetica", 12)
    c.drawString(100, 720, "Date: October 10, 2025")
    c.drawString(100, 700, "Location: Stockton Division")
    c.drawString(100, 680, "Inspector: John Smith")
    
    c.setFont("Helvetica-Bold", 14)
    c.drawString(100, 640, "Infractions Found:")
    
    c.setFont("Helvetica", 11)
    c.drawString(100, 610, "1. TAG-2 pole replacement required - deteriorated pole")
    c.drawString(100, 590, "2. Missing grounding on transformer installation")
    c.drawString(100, 570, "3. Crew used incorrect cable type for overhead lines")
    c.drawString(100, 550, "4. Safety equipment not properly staged at work site")
    c.drawString(100, 530, "5. 07D-1 clearance violation near power lines")
    
    c.setFont("Helvetica-Bold", 14)
    c.drawString(100, 490, "Required Actions:")
    
    c.setFont("Helvetica", 11)
    c.drawString(100, 460, "- Replace pole within 30 days (TAG-2)")
    c.drawString(100, 440, "- Install proper grounding immediately")
    c.drawString(100, 420, "- Replace cable with approved type")
    c.drawString(100, 400, "- Retrain crew on safety protocols")
    
    c.save()
    print(f"✅ Created test PDF: {pdf_file}")
    
    # Now test upload
    import requests
    
    with open(pdf_file, 'rb') as f:
        files = {'file': (pdf_file, f, 'application/pdf')}
        response = requests.post(
            'https://nexa-doc-analyzer-oct2025.onrender.com/analyze-audit',
            files=files,
            timeout=60
        )
    
    print(f"\n📊 Upload Status: {response.status_code}")
    
    if response.status_code == 200:
        import json
        result = response.json()
        print("✅ SUCCESS! Analysis complete")
        print(f"Infractions found: {len(result.get('infractions', []))}")
        
        for i, inf in enumerate(result.get('infractions', [])[:3], 1):
            print(f"\n{i}. {inf.get('text', '')[:100]}")
            print(f"   Status: {inf.get('status')}, Confidence: {inf.get('confidence', 0):.0%}")
    else:
        print(f"Error: {response.text[:500]}")
        
except ImportError:
    print("❌ reportlab not installed. Installing...")
    import subprocess
    subprocess.check_call(['pip', 'install', 'reportlab'])
    print("✅ Installed. Run this script again.")
except Exception as e:
    print(f"Error: {e}")
