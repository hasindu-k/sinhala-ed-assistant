import pdfplumber
import pytesseract
import cv2
import numpy as np
from typing import Literal
from app.components.document_processing.services.table_detection import detect_tables_with_yolo

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

def process_ocr_for_images_with_tables(images) -> tuple:
    """
    OCR pipeline with YOLO table masking.

    Flow:
    1. Detect tables
    2. Mask table regions
    3. OCR non-table regions
    4. OCR tables separately
    5. Merge cleanly
    """

    extracted_text = ""
    page_count = 0

    for idx, pil_img in enumerate(images):
        page_count += 1

        img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        tess_config = (
            "--oem 1 "
            "--psm 6 "
            "-c preserve_interword_spaces=1 "
        )

        # -------------------------------------
        # 1️⃣ Detect tables using YOLO
        # -------------------------------------
        table_coords, num_tables = detect_tables_with_yolo(img)

        logger.info(f"Page {page_count}: Detected {num_tables} tables.")

        # -------------------------------------
        # 2️⃣ Mask table regions
        # -------------------------------------
        mask = np.ones(gray.shape, dtype=np.uint8) * 255

        for coords in table_coords:
            x1, y1, x2, y2 = coords["x1"], coords["y1"], coords["x2"], coords["y2"]
            mask[y1:y2, x1:x2] = 0

        non_table_img = cv2.bitwise_and(gray, gray, mask=mask)

        # -------------------------------------
        # 3️⃣ OCR non-table content
        # -------------------------------------
        text_non_table = pytesseract.image_to_string(
            non_table_img,
            lang="sin+eng",
            config=tess_config
        )

        # -------------------------------------
        # 4️⃣ OCR tables separately
        # -------------------------------------
        table_texts = []

        for t_idx, coords in enumerate(table_coords):
            x1, y1, x2, y2 = coords["x1"], coords["y1"], coords["x2"], coords["y2"]

            table_crop = gray[y1:y2, x1:x2]

            table_config = (
                "--oem 1 "
                "--psm 6 "
                "-c preserve_interword_spaces=1 "
                "-c textord_tablefind_good_text_size=12 "
            )

            t_text = pytesseract.image_to_string(
                table_crop,
                lang="sin+eng",
                config=table_config
            )

            table_texts.append(
                f"\n\n--- TABLE {t_idx + 1} (Page {page_count}) ---\n{t_text}"
            )

        # -------------------------------------
        # 5️⃣ Merge page result
        # -------------------------------------
        page_output = (
            f"\n\n--- PAGE {page_count} ---\n"
            + text_non_table
            + "\n".join(table_texts)
        )

        extracted_text += page_output

    return extracted_text, page_count