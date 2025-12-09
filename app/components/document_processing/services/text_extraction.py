import pdfplumber
import pytesseract
import cv2
import numpy as np

def extract_text_from_pdf(file_path: str) -> str:
    with pdfplumber.open(file_path) as pdf:
        text = ""
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text

def process_ocr_for_images(images) -> tuple:
    extracted_text = ""
    page_count = 0
    for pil_img in images:
        page_count += 1
        img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        processed = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        tess_config = (
            "--oem 1 "
            "--psm 6 "
            "-c preserve_interword_spaces=1 "
        )

        text = pytesseract.image_to_string(
            processed, lang="sin+eng", config=tess_config
        )

        extracted_text += f"\n\n--- PAGE {page_count} ---\n{text}"

    return extracted_text, page_count
