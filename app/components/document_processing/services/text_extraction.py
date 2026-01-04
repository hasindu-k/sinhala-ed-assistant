import pdfplumber
import pytesseract
import cv2
import numpy as np
from typing import Literal

import logging
logger = logging.getLogger(__name__)

def classify_text_type(image_path: str) -> Literal["handwritten", "printed", "unknown"]:
    try:
        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            logger.warning(f"Cannot read image for classification: {image_path}")
            return "unknown"

        # Normalize contrast
        img = cv2.equalizeHist(img)

        # Binarize (text = white)
        _, bw = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # Remove noise
        bw = cv2.medianBlur(bw, 3)

        # ---- Stroke Width Estimation (distance transform) ----
        dist = cv2.distanceTransform(bw, cv2.DIST_L2, 5)

        # stroke width = distance * 2 (approx)
        stroke_width = dist[bw > 0] * 2

        mean_sw = np.mean(stroke_width)
        var_sw = np.var(stroke_width)

        # ---- Edge density ----
        edges = cv2.Canny(img, 80, 160)
        edge_density = np.sum(edges > 0) / edges.size

        # ---- Component irregularity ----
        contours, _ = cv2.findContours(bw, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        aspect_ratios = []
        for c in contours:
            x, y, w, h = cv2.boundingRect(c)
            if w * h < 20:  # ignore tiny dots
                continue
            aspect_ratios.append(w / float(h))

        var_ar = np.var(aspect_ratios) if aspect_ratios else 0

        # -------- Decision Rules --------
        # Tuned for Sinhala printed vs handwriting
        handwritten_score = 0

        if var_sw > 6:              # handwriting strokes vary more
            handwritten_score += 1
        if edge_density < 0.02:     # handwriting usually has fewer sharp edges
            handwritten_score += 1
        if var_ar > 0.35:           # handwritten characters vary shape more
            handwritten_score += 1

        if handwritten_score >= 2:
            result = "handwritten"
        else:
            result = "printed"

        logger.info(
            f"Text classification: {result} "
            f"(mean_sw={mean_sw:.2f}, var_sw={var_sw:.2f}, "
            f"edge_density={edge_density:.4f}, var_ar={var_ar:.4f})"
        )

        return result

    except Exception as e:
        logger.error(f"Error classifying text type: {e}")
        return "unknown"


def detect_language_from_text(text: str) -> Literal["sinhala", "english", "mixed", "unknown"]:
    """Lightweight heuristic to flag dominant script in extracted text."""
    sinhala = sum(1 for ch in text if 0x0D80 <= ord(ch) <= 0x0DFF)
    latin = sum(1 for ch in text if ("A" <= ch <= "Z") or ("a" <= ch <= "z"))
    total = sinhala + latin

    if total == 0:
        return "unknown"

    sinhala_ratio = sinhala / total
    latin_ratio = latin / total

    if sinhala_ratio >= 0.7:
        return "sinhala"
    if latin_ratio >= 0.7:
        return "english"
    return "mixed"

def extract_text_from_pdf(file_path: str) -> tuple:
    with pdfplumber.open(file_path) as pdf:
        text = ""
        logger.info("Extracting text from %d pages...", len(pdf.pages))
        for page_num, page in enumerate(pdf.pages, 1):
            page_text = page.extract_text() or ""
            text += f"\n\n--- PAGE {page_num} ---\n{page_text}"
    return text, len(pdf.pages)

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
