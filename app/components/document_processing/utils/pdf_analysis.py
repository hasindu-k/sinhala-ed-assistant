def check_for_tables_in_pdf(file_path: str, is_scanned: bool) -> bool:
    import pdfplumber
    
    if is_scanned:
        return False

    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            if tables:
                return True
    return False


def check_for_images_in_pdf(file_path: str, is_scanned: bool) -> bool:
    import fitz  # PyMuPDF

    if is_scanned:
        return False
    
    doc = fitz.open(file_path)
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        images = page.get_images(full=True)
        if images:
            return True
    return False

def is_text_based(file_path: str, content_type: str):
    import pdfplumber
    if content_type != "application/pdf":
        return False

    with pdfplumber.open(file_path) as pdf:
        if any(page.extract_text() for page in pdf.pages):
            return True
    return False