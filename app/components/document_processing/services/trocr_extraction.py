"""Temporary TrOCR abstraction layer.

This currently delegates to Tesseract so the OCR pipeline can call a stable
`trocr_predict` function before a real TrOCR model is integrated.
"""

from typing import Optional

import numpy as np
import pytesseract

from app.components.document_processing.ocr_config import OCR_LANG


def trocr_predict(image_crop: np.ndarray, tess_lang: Optional[str] = None) -> str:
    """Temporary TrOCR-compatible predictor implemented with Tesseract."""
    if image_crop is None or image_crop.size == 0:
        return ""

    tess_config = (
        "--oem 1 "
        "--psm 6 "
        "-c preserve_interword_spaces=1 "
    )

    return pytesseract.image_to_string(
        image_crop,
        lang=tess_lang or OCR_LANG,
        config=tess_config,
    )
