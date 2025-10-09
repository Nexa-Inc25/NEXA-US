#!/usr/bin/env python3
"""
Convert image-only PDFs to text-extractable PDFs using OCR
Handles PDFs that fail with "No text could be extracted from PDF"
"""

import os
import sys
from pathlib import Path
from typing import List, Optional

try:
    import pytesseract
    from pdf2image import convert_from_path
    from PIL import Image
    import PyPDF2
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
except ImportError as e:
    print(f"Missing required package: {e}")
    print("\nInstall required packages:")
    print("pip install pytesseract pdf2image pillow PyPDF2 reportlab")
    sys.exit(1)

def check_pdf_has_text(pdf_path: str) -> bool:
    """Check if PDF already contains extractable text"""
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = ""
            for page in reader.pages:
                text += page.extract_text()
            return len(text.strip()) > 10  # Has meaningful text
    except Exception as e:
        print(f"Error checking PDF: {e}")
        return False

def ocr_pdf_to_text(pdf_path: str, output_path: Optional[str] = None) -> str:
    """
    Convert image-only PDF to text using OCR
    Returns the extracted text and optionally saves to a new PDF
    """
    if output_path is None:
        output_path = pdf_path.replace('.pdf', '_OCR.pdf')
    
    print(f"Processing: {os.path.basename(pdf_path)}")
    
    # Check if already has text
    if check_pdf_has_text(pdf_path):
        print("  ✓ PDF already contains extractable text")
        return ""
    
    print("  → Converting PDF to images...")
    try:
        # Convert PDF to images
        images = convert_from_path(pdf_path, dpi=300)
        
        all_text = []
        
        print(f"  → Running OCR on {len(images)} pages...")
        for i, image in enumerate(images, 1):
            # Perform OCR on each page
            text = pytesseract.image_to_string(image)
            all_text.append(f"--- Page {i} ---\n{text}\n")
            print(f"    Page {i}/{len(images)} processed")
        
        combined_text = "\n".join(all_text)
        
        # Save text to file
        text_file = output_path.replace('.pdf', '.txt')
        with open(text_file, 'w', encoding='utf-8') as f:
            f.write(combined_text)
        
        print(f"  ✓ Text saved to: {text_file}")
        print(f"  ✓ Extracted {len(combined_text)} characters")
        
        return combined_text
        
    except Exception as e:
        print(f"  ✗ Error processing PDF: {e}")
        return ""

def process_problem_pdfs():
    """Process the specific PDFs that failed to upload"""
    problem_files = [
        "015116 3-Wire Crossarm Construction 12, 17, and 21 KV.pdf",
        "094674 - EFD SENSORS STANDARD_With added dimensions.pdf (P)_1.pdf",
        "Vertical Primary Construction.pdf"
    ]
    
    print("\n" + "="*60)
    print("🔧 IMAGE-ONLY PDF CONVERTER")
    print("="*60)
    
    # Look for the files in common directories
    search_dirs = [
        ".",
        "./specs",
        "./documents",
        "../specs",
        "../../specs",
        r"C:\Users\mikev\CascadeProjects\nexa-inc-mvp\specs"
    ]
    
    for filename in problem_files:
        found = False
        print(f"\n📄 Looking for: {filename}")
        
        for search_dir in search_dirs:
            full_path = os.path.join(search_dir, filename)
            if os.path.exists(full_path):
                found = True
                print(f"   Found in: {search_dir}")
                ocr_pdf_to_text(full_path)
                break
        
        if not found:
            print(f"   ✗ File not found in searched directories")
    
    print("\n" + "="*60)
    print("✅ CONVERSION COMPLETE")
    print("="*60)
    print("\nNext steps:")
    print("1. Review the generated .txt files to verify OCR quality")
    print("2. If text looks good, you can manually add it to your spec library")
    print("3. Consider using a better quality scan if OCR results are poor")

def main():
    """Main function with menu"""
    if len(sys.argv) > 1:
        # Process specific file passed as argument
        pdf_file = sys.argv[1]
        if os.path.exists(pdf_file):
            ocr_pdf_to_text(pdf_file)
        else:
            print(f"File not found: {pdf_file}")
    else:
        # Process the known problem files
        process_problem_pdfs()

if __name__ == "__main__":
    # Check if Tesseract is installed
    try:
        pytesseract.get_tesseract_version()
    except:
        print("\n⚠️  Tesseract OCR is not installed or not in PATH")
        print("\nWindows installation:")
        print("1. Download from: https://github.com/UB-Mannheim/tesseract/wiki")
        print("2. Install and add to PATH")
        print("3. Or set path in script: pytesseract.pytesseract.tesseract_cmd = r'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'")
        sys.exit(1)
    
    main()
