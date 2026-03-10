from pathlib import Path
import sys
from unittest.mock import patch

import cv2
import numpy as np
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.components.document_processing.services import table_detection


def _blank_pil(width: int = 200, height: int = 200) -> Image.Image:
    arr = np.full((height, width, 3), 255, dtype=np.uint8)
    return Image.fromarray(arr)


def test_detect_tables_with_yolo_returns_empty_when_ultralytics_unavailable(tmp_path):
    image_path = tmp_path / "page.jpg"
    cv2.imwrite(str(image_path), np.full((100, 100, 3), 255, dtype=np.uint8))

    with patch.object(table_detection, "ULTRALYTICS_AVAILABLE", False):
        coords, count = table_detection.detect_tables_with_yolo(str(image_path))

    assert coords == []
    assert count == 0


def test_detect_tables_with_yolo_returns_empty_when_model_missing(tmp_path):
    image_path = tmp_path / "page.jpg"
    cv2.imwrite(str(image_path), np.full((100, 100, 3), 255, dtype=np.uint8))

    missing_model = tmp_path / "missing_model.pt"
    with patch.object(table_detection, "ULTRALYTICS_AVAILABLE", True):
        coords, count = table_detection.detect_tables_with_yolo(
            str(image_path), model_path=str(missing_model)
        )

    assert coords == []
    assert count == 0


def test_split_image_into_columns_returns_original_when_no_separator(tmp_path):
    image_path = tmp_path / "single_column.jpg"
    cv2.imwrite(str(image_path), np.full((200, 200, 3), 255, dtype=np.uint8))

    out = table_detection.split_image_into_columns(str(image_path))

    assert out == [str(image_path)]


def test_detect_tables_in_images_aggregates_count_and_coords():
    images = [_blank_pil(), _blank_pil()]

    calls = [
        ([{"x1": 1, "y1": 2, "x2": 3, "y2": 4, "confidence": 0.95}], 1),
        ([], 0),
    ]

    with patch.object(table_detection, "detect_tables_with_yolo", side_effect=calls):
        has_tables, coords, total = table_detection.detect_tables_in_images(images)

    assert has_tables is True
    assert total == 1
    assert len(coords) == 1
    assert coords[0]["x1"] == 1


def test_extract_table_text_from_images_returns_empty_when_no_tables():
    images = [_blank_pil()]

    with patch.object(
        table_detection,
        "detect_tables_in_images",
        return_value=(False, [], 0),
    ):
        text, processed = table_detection.extract_table_text_from_images(images)

    assert text == ""
    assert processed == 0


def test_extract_table_text_from_images_uses_ocr_output(tmp_path):
    images = [_blank_pil()]

    table_img_path = tmp_path / "table_1.jpg"
    cv2.imwrite(str(table_img_path), np.full((50, 50), 255, dtype=np.uint8))

    with patch.object(
        table_detection,
        "detect_tables_in_images",
        return_value=(True, [{"x1": 1}], 1),
    ), patch.object(
        table_detection,
        "extract_tables_from_image",
        return_value=([str(table_img_path)], 1),
    ), patch.object(
        table_detection.pytesseract,
        "image_to_string",
        return_value="A1  B1\nA2  B2",
    ):
        text, processed = table_detection.extract_table_text_from_images(images)

    assert processed == 1
    assert "TABLE 1 (Page 1)" in text
    assert "A1  B1" in text


def test_extract_tables_from_image_returns_empty_when_no_detection(tmp_path):
    image_path = tmp_path / "page.jpg"
    cv2.imwrite(str(image_path), np.full((120, 120, 3), 255, dtype=np.uint8))

    with patch.object(
        table_detection,
        "detect_tables_with_yolo",
        return_value=([], 0),
    ):
        paths, count = table_detection.extract_tables_from_image(str(image_path))

    assert paths == []
    assert count == 0


def test_extract_tables_from_image_crops_detected_table(tmp_path):
    image_path = tmp_path / "page.jpg"
    img = np.full((100, 100, 3), 255, dtype=np.uint8)
    cv2.imwrite(str(image_path), img)

    detection = ([{"x1": 10, "y1": 10, "x2": 60, "y2": 60, "confidence": 0.9}], 1)

    with patch.object(table_detection, "ULTRALYTICS_AVAILABLE", True), patch.object(
        table_detection,
        "detect_tables_with_yolo",
        return_value=detection,
    ):
        paths, count = table_detection.extract_tables_from_image(str(image_path))

    assert count == 1
    assert len(paths) == 1
    assert Path(paths[0]).exists()
