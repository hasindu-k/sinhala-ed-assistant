import pdfplumber
import pytesseract
import cv2
import numpy as np
from typing import Literal
from app.components.document_processing.services.table_detection import detect_tables_with_yolo

import logging
logger = logging.getLogger(__name__)

try:
    from ultralytics import YOLO
    ULTRALYTICS_AVAILABLE = True
except Exception as e:
    logger.warning(f"Ultralytics YOLO not available: {e}")
    YOLO = None
    ULTRALYTICS_AVAILABLE = False
layout_model = None
if ULTRALYTICS_AVAILABLE:
    try:
        layout_model = YOLO("utils/yolov8m-doclaynet.pt")
    except Exception as e:
        logger.error(f"Failed to load layout YOLO model: {e}")
        layout_model = None

lang = "sin+eng"  # Tesseract language setting for Sinhala and English

def classify_text_type(image_input: str) -> Literal["handwritten", "printed", "unknown"]:
    """
    Classify text as handwritten or printed.
    
    Args:
        image_input: Either a file path (str) or numpy array (from PIL/cv2)
    """
    try:
        # Handle both file path and numpy array inputs
        if isinstance(image_input, str):
            img = cv2.imread(image_input, cv2.IMREAD_GRAYSCALE)
            if img is None:
                logger.warning(f"Cannot read image for classification: {image_input}")
                return "unknown"
        else:
            img = image_input
            if len(img.shape) == 3:
                img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

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

def process_ocr_for_images_with_tables(images, force_layout_analysis: bool = False) -> tuple:
    """
    OCR pipeline with:
    - Table detection
    - Layout detection (DocLayNet)
    - Column clustering
    - Reading order reconstruction
    - Block-wise OCR
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
        # 1️⃣ Detect tables
        # -------------------------------------
        table_coords, num_tables = detect_tables_with_yolo(img)
        logger.info(f"Page {page_count}: Detected {num_tables} tables.")

        # Create a mask for the table areas to exclude them from OCR
        table_mask = np.zeros_like(gray)
        for coords in table_coords:
            x1, y1, x2, y2 = coords["x1"], coords["y1"], coords["x2"], coords["y2"]
            table_mask[y1:y2, x1:x2] = 255  # Mark table areas with white in the mask

        # If force_layout_analysis is True, always perform layout detection
        if force_layout_analysis:
            # -------------------------------------
            # 2️⃣ Detect layout excluding tables
            # -------------------------------------
            text_regions = detect_layout_excluding_tables(img, table_coords)

            # -------------------------------------
            # 3️⃣ Column clustering
            # -------------------------------------
            columns = detect_columns(text_regions, img.shape[1])

            # -------------------------------------
            # 4️⃣ Reading order reconstruction
            # -------------------------------------
            reading_order = sort_regions_by_reading_order(columns)

        else:
            # If force_layout_analysis is False, skip layout analysis
            reading_order = []

        # -------------------------------------
        # 5️⃣ OCR TEXT BLOCKS IN ORDER
        # -------------------------------------
        page_text = ""

        if reading_order:
            for box in reading_order:
                x1, y1, x2, y2 = box

                crop = gray[y1:y2, x1:x2]

                text = pytesseract.image_to_string(
                    crop,
                    lang=lang,
                    config=tess_config
                )

                page_text += text.strip() + "\n\n"
        else:
            # Perform OCR on the entire page excluding table areas
            # Use bitwise NOT to exclude the table areas from OCR
            non_table_area = cv2.bitwise_and(gray, gray, mask=cv2.bitwise_not(table_mask))

            full_page_text = pytesseract.image_to_string(
                non_table_area,
                lang=lang,
                config=tess_config
            )
            page_text = full_page_text.strip()

        # -------------------------------------
        # 6️⃣ OCR TABLES SEPARATELY
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
                lang=lang,
                config=table_config
            )

            table_texts.append(
                f"\n\n--- TABLE {t_idx + 1} (Page {page_count}) ---\n{t_text.strip()}"
            )

        # -------------------------------------
        # 7️⃣ Merge page result
        # -------------------------------------
        page_output = (
            f"\n\n--- PAGE {page_count} ---\n"
            + page_text
            + "\n".join(table_texts)
        )

        extracted_text += page_output

    return extracted_text, page_count

def detect_layout_excluding_tables(img, table_coords, conf_threshold=0.6):
    """
    Detect layout regions (Text, Title, Section-header)
    excluding areas overlapping with already detected tables.
    """

    results = layout_model(img, imgsz=1024)

    text_regions = []

    def overlaps(box, table):
        x1, y1, x2, y2 = box
        tx1, ty1, tx2, ty2 = table
        return not (x2 < tx1 or x1 > tx2 or y2 < ty1 or y1 > ty2)

    # Convert table coords format
    formatted_tables = [
        (t["x1"], t["y1"], t["x2"], t["y2"])
        for t in table_coords
    ]

    for r in results:
        for box in r.boxes:
            cls_id = int(box.cls[0])
            class_name = layout_model.names[cls_id]
            conf = float(box.conf[0])

            if conf < conf_threshold:
                continue

            xyxy = list(map(int, box.xyxy[0].tolist()))

            if class_name in ["Text", "Title", "Section-header"]:

                # Exclude if overlapping with table
                if any(overlaps(xyxy, t) for t in formatted_tables):
                    continue

                text_regions.append(xyxy)

    return text_regions

def detect_columns(text_blocks, image_width):
    """
    Cluster text blocks into columns using horizontal CENTER distance.
    More stable than x_min clustering.
    """

    if not text_blocks:
        return []

    # Sort by horizontal center
    text_blocks = sorted(
        text_blocks,
        key=lambda b: (b[0] + b[2]) / 2
    )

    columns = []

    # Slightly larger threshold for robustness
    column_threshold = image_width * 0.12

    for box in text_blocks:
        box_center = (box[0] + box[2]) / 2
        placed = False

        for col in columns:
            if abs(box_center - col["center"]) < column_threshold:
                col["boxes"].append(box)

                # Update column center using box centers
                col["center"] = np.mean(
                    [(b[0] + b[2]) / 2 for b in col["boxes"]]
                )

                placed = True
                break

        if not placed:
            columns.append({
                "center": box_center,
                "boxes": [box]
            })

    logger.info(
        f"Clustered {len(text_blocks)} text blocks into {len(columns)} columns."
    )

    return columns

def sort_regions_by_reading_order(columns):
    """
    Sort columns left-to-right,
    then blocks top-to-bottom within each column.
    """

    if not columns:
        return []

    # Sort columns by horizontal position
    columns = sorted(columns, key=lambda c: c["center"])

    reading_order = []

    for col in columns:
        sorted_boxes = sorted(col["boxes"], key=lambda b: b[1])
        reading_order.extend(sorted_boxes)

    logger.info(f"Sorted {len(reading_order)} text regions into reading order.")
    return reading_order