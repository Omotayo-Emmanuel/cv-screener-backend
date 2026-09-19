"""
This module contains the Parser class, which is responsible for parsing input data and extracting relevant information. The Parser class provides methods to process different types of input formats and convert them into a structured format that can be easily used by other components of the application.
The Parser class is designed to handle various input formats, including text, JSON, and other structured

PDF and DOCX text extraction service.
Supports:
- PDF: uses pdfplumber (handles multi-column layouts better than PyPDF2)
- DOCX: uses python-docx
- File type detection via magic bytes (not just file extension)
"""

import io # For handling in-memory file streams
import os # For file path operations
import logging # For logging errors and information
from typing import BinaryIO # For type hinting binary file-like objects

import pdfplumber # For extracting text from PDF files
from docx import Document # For extracting text from DOCX files

# For better MIME (Multipurpose Internet Mail Extensions) type detection
# (falls back to file extension if not installed)
logger = logging.getLogger(__name__)

try:
    from magic import from_buffer as magic_from_buffer
except ImportError:
    magic_from_buffer = None
    logging.warning("python-magic library is not installed. File type detection will be based on file extensions.")
    
# Public Functions
def extract_text_from_pdf(file: BinaryIO) -> str:
    """
    Extracts text from a PDF file using pdfplumber.

    Args:
        file (BinaryIO): A binary file-like object representing the PDF file.

    Returns:
        str: The extracted text from the PDF file.
    
    Raises:
        ValueError: If parsing fails, PDF is corrupted, or no text found.
    """
    file_bytes = file.read()
    if not file_bytes:
        raise ValueError("No file content provided for PDF parsing.")
    
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            if len(pdf.pages) == 0:
                raise ValueError("PDF file has no pages.")
            
            
            all_text = []
            for page_num, page in enumerate(pdf.pages, start=1):
                try:
                    text = page.extract_text()
                    if text: # Only append if text is not None
                        all_text.append(text.strip())
                
                except Exception as e:
                    logger.warning(f"Could not extract text from page {page_num}: {e}")
                    # Continue to next page instead of failing the entire extraction
            
            extracted_text = "\n".join(all_text).strip()
            
            if not extracted_text: # If no text was extracted from any page, raise an error
                raise ValueError("PDF appears to be scanned or contains no extractable text (try OCR)")
            
            return extracted_text
    
    except pdfplumber.pdf.PDFSyntaxError as e:
        raise ValueError(f"Corrupted or invalid PDF: {e}")
    except Exception as e:
        logger.exception("Unexpected error during PDF parsing")
        raise ValueError(f"PDF parsing failed: {e}")
    

def extract_text_from_docx(file_bytes: bytes) -> str:
    """
    Extract all text from a DOCX file (provided as  byres)

    Args:
        file_bytes (bytes): Raw DOCX file content

    Returns:
        str: Extracted text as a single string
    
    Raises:
        ValueError: If parsing fails, file is corrupted, or no text found
    """
    
    if not file_bytes:
        raise ValueError("DOCX file is empty")
    
    
    try:
        doc = Document(io.BytesIO(file_bytes))
        
        # DOCX can have text in paragraphs, tables, headers, footers etc.
        all_text = []
        
        # Paragraphs
        for para in doc.paragraphs:
            if para.text.strip():
                all_text.append(para.text.strip())
        
        # Tables
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    cell_text = cell.text.strip()
                    if cell_text:
                        all_text.append(cell_text)
        
        # Header & footers (often contain useful context)
        for section in doc.sections:
            # Header
            if section.header:
                for para in section.header.paragraphs:
                    if para.text.strip():
                        all_text.append(para.text.strip())
            
            # Footer
            if section.footer:
                for para in section.footer.paragraphs:
                    if para.text.strip():
                        all_text.append(para.text.strip())
        
        extracted_text = "\n".join(all_text).strip()
        
        if not extracted_text:
            raise  ValueError("DOCX contains no extractable text")
        return extracted_text
    
    except Exception as e:
        logger.exception("Unexpected error while parsing DOCX")
        raise ValueError(f"DOCX parsing failed: {e}")
    

def detect_file_type(file_bytes: bytes) -> str | None:
    """
    Detects the file type based on magic bytes (file signature) or file extension.

    Args:
        file_bytes (bytes): Raw file content

    Returns:
        "pdf" | None: Detected MIME type or None if detection fails
    """
    if not file_bytes or len(file_bytes) < 4: # Minimum bytes needed for detection
        return None
    
    # PD signature: %PDF
    if file_bytes[:4] == b"%PDF":
        return "pdf"
    
    
    # DOCX is a ZIp archive with a specific signature: PK\x03\x04
    # this is a quick check - more throrough would inspect the ZIP contents
    
    if file_bytes[:4] == b"PK\x03\x04":
        # Look for "word/document.xml" inside the ZIP
        # Since we can't open the ZIp without extra  overhead, we'll trust the extension later
        # But we can check if it's a ZIP and then assume docx if the caller says so.
        # For safety, we return "zip" and let the caller decide.
        # But we know it's likely docx. We'll refine using magic if available.
        if magic_from_buffer:
            mime_type = magic_from_buffer(file_bytes, mime=True)
            if mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                return "docx"
            elif mime_type == "application/zip":
                return "zip" # Could be docx or other zip-based formats
        else:
            # Fallback to extension-based detection (not reliable)
            return "docx" # Assume docx if the caller says so
    return None


# Convinence Wrapper 
def extract_text_from_bytes(file_bytes: bytes, filename: str) -> str:
    """
    High-level function that detects file type from bytes and dispatches to the right parser.

    Args:
        file_bytes (bytes): Raw file content
        filename (str): Name of the file (used for extension-based detection)

    Returns:
        str: Extracted text
    
    Raises:
        ValueError: If parsing fails or file type is unsupported
    """
    # First try magic-based detection
    file_type = detect_file_type(file_bytes)
    
    # Fallback to extension if magic gave inconclusinve
    if file_type is None:
        if filename.lower().endswith(".pdf"):
            file_type = "pdf"
        elif filename.lower().endswith(".docx"):
            file_type = "docx"
    
    if file_type == "pdf":
        return extract_text_from_pdf(io.BytesIO(file_bytes))
    elif file_type == "docx":
        return extract_text_from_docx(file_bytes)
    else:
        raise ValueError(f"Unsupported or unrecognized file type. only PDF and DOCX are allowed."
                         f"Received: {filename if filename else 'unknown'}"
                         )