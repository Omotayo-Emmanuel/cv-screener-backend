
import sys
import os
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.services.parser import extract_text_from_bytes

# Getting the directory of this test script
test_dir = Path(__file__).parent

# Test PDF
pdf_path  = test_dir / "sample.pdf"
# Test  with a real PDF file
with open(pdf_path, "rb") as f:
    text = extract_text_from_bytes(f.read(), "sample.pdf")
    print(f"Extracted {len(text)} characters from {pdf_path.name} PDF file.")
    print(text[:500])  # Print the first 500 characters of the extracted text
    
    
# Test with a real DOCX file
docx_path = test_dir / "sample.docx"
with open(docx_path, "rb") as f:
    text = extract_text_from_bytes(f.read(), "sample.docx")
    print(f"Extracted {len(text)} characters from {docx_path.name} DOCX file.")
    print(text[:500])  # Print the first 500 characters of the extracted text