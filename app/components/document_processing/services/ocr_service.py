# app/components/document_processing/services/ocr_service.py

import os
from fastapi import UploadFile
import cv2
import numpy as np
from pdf2image import convert_from_path
import pytesseract
from PIL import Image

from app.components.document_processing.utils.file_loader import save_upload_to_temp


async def process_ocr_file(file: UploadFile) -> dict:
    """
    Full OCR pipeline using shared temp loader:
    1. Save uploaded file to temporary location
    2. Detect PDF or image
    3. Convert PDF pages -> images (if PDF)
    4. Run Tesseract OCR on each page
    5. Return structured OCR response
    """

    # 1. Save file to temp
    temp_path = await save_upload_to_temp(file)
    ext = file.filename.split(".")[-1].lower()

    # 2. Detect PDF or image
    is_pdf = ext == "pdf"

    if is_pdf:
        images = convert_from_path(temp_path)  # List of PIL images
    else:
        images = [Image.open(temp_path)]       # Single PIL image

    extracted_text = ""
    page_count = 0

    for pil_img in images:
        page_count += 1

        # -----------------------------
        # Convert PIL → OpenCV (BGR)
        # -----------------------------
        img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Run OCR
        text = pytesseract.image_to_string(gray, lang="sin+eng")

        extracted_text += f"\n\n--- PAGE {page_count} ---\n{text}"

    # 4. Try to remove temp file
    try:
        os.remove(temp_path)
    except:
        pass

    # 5. Return results
    return {
        "filename": file.filename,
        "pages": page_count,
        "text": extracted_text.strip(),
    }
