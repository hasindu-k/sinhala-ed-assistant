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

def is_reliably_text_based(file_path: str) -> bool:
    import pdfplumber

    with pdfplumber.open(file_path) as pdf:
        pages_with_real_text = 0

        for page in pdf.pages:
            text = page.extract_text()
            if text and len(text.strip()) > 200:
                pages_with_real_text += 1

        return pages_with_real_text >= len(pdf.pages) * 0.8

def should_use_direct_text_extraction(file_path: str) -> bool:
    import os
    ext = os.path.splitext(file_path)[1].lower()

    if ext in {".png", ".jpg", ".jpeg", ".tiff"}:
        # Images are never text-based
        return False

    if ext == ".pdf":
        return is_reliably_text_based(file_path)

    raise ValueError(f"Unsupported file type: {ext}")