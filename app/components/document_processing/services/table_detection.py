import cv2
import numpy as np
import os
import tempfile
import pytesseract
from typing import List, Tuple

import logging
logger = logging.getLogger(__name__)

try:
    from ultralytics import YOLO
    ULTRALYTICS_AVAILABLE = True
except ImportError:
    ULTRALYTICS_AVAILABLE = False
    logger.warning("Ultralytics not available. Table detection will be limited.")

def detect_tables_with_yolo(image_input: str, model_path: str = "table_model.pt", conf_threshold: float = 0.5) -> Tuple[List[dict], int]:
    """
    Detect tables in an image using YOLO model.
    Returns table coordinates and count.
    """
    if not ULTRALYTICS_AVAILABLE:
        logger.error("Ultralytics not available for table detection")
        return [], 0
    
    try:
        # Check if model file exists, if not, log warning and return empty
        if not os.path.exists(model_path):
            logger.warning(f"YOLO model file not found: {model_path}")
            return [], 0
            
        # Load the model
        model = YOLO(model_path)
        
        # Run inference
        results = model.predict(
            source=image_input, 
            save=False, 
            conf=conf_threshold, 
            agnostic_nms=True
        )
        
        table_coords = []
        for r in results:
            boxes = r.boxes
            if boxes is not None:
                for box in boxes:
                    # Get coordinates (xyxy format)
                    coords = box.xyxy[0].cpu().numpy()
                    x1, y1, x2, y2 = coords
                    
                    table_coords.append({
                        'x1': int(x1),
                        'y1': int(y1),
                        'x2': int(x2),
                        'y2': int(y2),
                        'confidence': float(box.conf[0].cpu().numpy())
                    })
        
        logger.info(f"Detected {len(table_coords)} tables in image")
        return table_coords, len(table_coords)
        
    except Exception as e:
        logger.error(f"Error in YOLO table detection: {e}")
        return [], 0


def split_image_into_columns(image_path: str, output_dir: str = None) -> List[str]:
    """
    Split an image into columns using morphological operations.
    Returns list of paths to split column images.
    """
    try:
        # Load image
        img = cv2.imread(image_path)
        if img is None:
            logger.error(f"Cannot load image: {image_path}")
            return []
            
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Invert + binarize
        binary = cv2.adaptiveThreshold(
            gray, 255,
            cv2.ADAPTIVE_THRESH_MEAN_C,
            cv2.THRESH_BINARY_INV,
            15, 5
        )
        
        h, w = binary.shape
        
        # Detect vertical lines using morphology
        vertical_kernel = cv2.getStructuringElement(
            cv2.MORPH_RECT, (1, h // 2)
        )
        
        vertical_lines = cv2.morphologyEx(
            binary, cv2.MORPH_OPEN, vertical_kernel, iterations=1
        )
        
        # Find contours of vertical lines
        contours, _ = cv2.findContours(
            vertical_lines, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        
        xs = []
        for cnt in contours:
            x, y, cw, ch = cv2.boundingRect(cnt)
            if ch > h * 0.3:  # long enough vertical structure
                xs.append(x)
        
        if not xs:
            logger.warning("No column separator found, returning original image")
            return [image_path]
        
        # Use median x (robust)
        split_x = int(np.median(xs))
        logger.info(f"Splitting image at x = {split_x}")
        
        # Split image
        left_col = img[:, :split_x]
        right_col = img[:, split_x:]
        
        # Save split images
        if output_dir is None:
            output_dir = os.path.dirname(image_path)
        
        base_name = os.path.splitext(os.path.basename(image_path))[0]
        left_path = os.path.join(output_dir, f"{base_name}_left_column.jpg")
        right_path = os.path.join(output_dir, f"{base_name}_right_column.jpg")
        
        cv2.imwrite(left_path, left_col)
        cv2.imwrite(right_path, right_col)
        
        logger.info(f"Split image saved as: {left_path}, {right_path}")
        return [left_path, right_path]
        
    except Exception as e:
        logger.error(f"Error splitting image into columns: {e}")
        return [image_path]


def extract_tables_from_image(image_path: str, model_path: str = "table_model.pt") -> Tuple[List[str], int]:
    """
    Extract table regions from an image using YOLO detection.
    Returns list of paths to extracted table images and count.
    """
    if not ULTRALYTICS_AVAILABLE:
        logger.error("Ultralytics not available for table extraction")
        return [], 0
    
    try:
        # Detect tables first
        table_coords, num_tables = detect_tables_with_yolo(image_path, model_path)
        
        if num_tables == 0:
            logger.info("No tables detected in image")
            return [], 0
        
        # Load original image
        img = cv2.imread(image_path)
        if img is None:
            logger.error(f"Cannot load image for table extraction: {image_path}")
            return [], 0
        
        # Create output directory
        base_name = os.path.splitext(os.path.basename(image_path))[0]
        output_dir = os.path.join(os.path.dirname(image_path), f"{base_name}_extracted_tables")
        os.makedirs(output_dir, exist_ok=True)
        
        extracted_paths = []
        
        # Extract each detected table
        for i, coords in enumerate(table_coords):
            x1, y1, x2, y2 = coords['x1'], coords['y1'], coords['x2'], coords['y2']
            
            # Crop the table region
            table_crop = img[y1:y2, x1:x2]
            
            # Save the cropped table
            table_path = os.path.join(output_dir, f"table_{i+1}.jpg")
            cv2.imwrite(table_path, table_crop)
            extracted_paths.append(table_path)
            
            logger.info(f"Extracted table {i+1} to: {table_path}")
        
        return extracted_paths, len(extracted_paths)
        
    except Exception as e:
        logger.error(f"Error extracting tables from image: {e}")
        return [], 0


def detect_tables_in_images(images) -> Tuple[bool, List[dict], int]:
    """
    Detect tables in a list of PIL images.
    Returns has_tables, table_coordinates, number_of_tables.
    """
    try:
        all_table_coords = []
        total_tables = 0
        
        with tempfile.TemporaryDirectory() as temp_dir:
            for idx, pil_img in enumerate(images):
                # Convert PIL to OpenCV format and save temporarily
                temp_path = os.path.join(temp_dir, f"temp_page_{idx}.jpg")
                cv2_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
                cv2.imwrite(temp_path, cv2_img)
                
                # Detect tables in this image
                table_coords, num_tables = detect_tables_with_yolo(temp_path)
                all_table_coords.extend(table_coords)
                total_tables += num_tables
        
        has_tables = total_tables > 0
        logger.info(f"Total tables detected across {len(images)} images: {total_tables}")
        
        return has_tables, all_table_coords, total_tables
        
    except Exception as e:
        logger.error(f"Error detecting tables in images: {e}")
        return False, [], 0


def extract_table_text_from_images(images) -> Tuple[str, int]:
    """
    Extract text from detected tables in images using OCR.
    Returns extracted text and number of tables processed.
    """
    try:
        # Detect tables first
        has_tables, table_coords, num_tables = detect_tables_in_images(images)
        
        if not has_tables:
            logger.info("No tables detected for text extraction")
            return "", 0
        
        extracted_text = ""
        tables_processed = 0
        
        with tempfile.TemporaryDirectory() as temp_dir:
            for idx, pil_img in enumerate(images):
                # Convert PIL to OpenCV format and save temporarily
                temp_path = os.path.join(temp_dir, f"temp_page_{idx}.jpg")
                cv2_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
                cv2.imwrite(temp_path, cv2_img)
                
                # Extract tables from this image
                table_paths, num_extracted = extract_tables_from_image(temp_path)
                
                # Process each extracted table with OCR
                for table_idx, table_path in enumerate(table_paths):
                    try:
                        # Load table image
                        table_img = cv2.imread(table_path, cv2.IMREAD_GRAYSCALE)
                        
                        # Configure Tesseract for table text extraction
                        tess_config = (
                            "--oem 1 "
                            "--psm 6 "
                            "-c preserve_interword_spaces=1 "
                            "-c textord_tablefind_good_text_size=12 "
                        )
                        
                        # Extract text from table
                        table_text = pytesseract.image_to_string(
                            table_img, lang="sin+eng", config=tess_config
                        )
                        
                        extracted_text += f"\n\n--- TABLE {tables_processed + 1} (Page {idx + 1}) ---\n{table_text}"
                        tables_processed += 1
                        
                        logger.info(f"Extracted text from table {table_idx + 1} on page {idx + 1}")
                        
                    except Exception as e:
                        logger.error(f"Error extracting text from table {table_path}: {e}")
                        continue
        
        logger.info(f"Total tables processed for text extraction: {tables_processed}")
        return extracted_text, tables_processed
        
    except Exception as e:
        logger.error(f"Error in table text extraction: {e}")
        return "", 0