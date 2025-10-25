from pdfminer.high_level import extract_text
import io

def parse_resume_pdf(pdf_bytes: bytes) -> str:
    """
    Extracts text from a PDF file provided as bytes.
    """
    try:
        # Create a file-like object from the bytes
        pdf_file = io.BytesIO(pdf_bytes)
        
        # Extract text using pdfminer.six
        text = extract_text(pdf_file)
        return text
    
    except Exception as e:
        print(f"Error during PDF text extraction: {e}")
        return ""
