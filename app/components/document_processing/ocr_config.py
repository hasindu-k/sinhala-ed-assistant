# app\components\document_processing\ocr_config.py

import os
import logging

logger = logging.getLogger(__name__)

OCR_LANG = "sin+eng"
OCR_CONFIG_EXTRA = ""

custom_model_name = "sin_eng_custom"
custom_model_filename = f"{custom_model_name}.traineddata"

utils_dir = os.path.join(os.getcwd(), "utils")
custom_model_path = os.path.join(utils_dir, custom_model_filename)

if os.path.exists(custom_model_path):
    logger.info(f"Custom Tesseract model found: {custom_model_path}")

    OCR_LANG = custom_model_name

    # SET TESSDATA PREFIX
    os.environ["TESSDATA_PREFIX"] = os.path.abspath(utils_dir)

else:
    logger.warning(
        f"Custom Tesseract model not found at {custom_model_path}. Using default language: {OCR_LANG}"
    )