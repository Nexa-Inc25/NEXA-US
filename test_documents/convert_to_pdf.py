"""
Quick script to convert test documents to PDF format for the NEXA app
"""
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.units import inch
import os

def text_to_pdf(text_file, pdf_file):
    """Convert text file to PDF"""
    # Read the text file
    with open(text_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Create PDF
    doc = SimpleDocTemplate(pdf_file, pagesize=letter,
                           rightMargin=72, leftMargin=72,
                           topMargin=72, bottomMargin=18)
    
    # Container for the 'Flowable' objects
    elements = []
    
    # Define styles
    styles = getSampleStyleSheet()
    
    # Split content into paragraphs
    paragraphs = content.split('\n')
    
    for para in paragraphs:
        if para.strip():
            # Create paragraph
            p = Paragraph(para, styles['Normal'])
            elements.append(p)
            elements.append(Spacer(1, 0.2*inch))
    
    # Build PDF
    doc.build(elements)
    print(f"Created: {pdf_file}")

if __name__ == "__main__":
    # Convert both files
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    text_to_pdf(
        os.path.join(script_dir, 'sample_spec_book.txt'),
        os.path.join(script_dir, 'sample_spec_book.pdf')
    )
    
    text_to_pdf(
        os.path.join(script_dir, 'sample_audit_report.txt'),
        os.path.join(script_dir, 'sample_audit_report.pdf')
    )
    
    print("\n✅ PDF files created successfully!")
    print("You can now upload these to https://nexa-us.onrender.com")
