"""TrOCR abstraction layer for handwritten Sinhala OCR."""

import logging
from functools import lru_cache
from typing import Optional

import numpy as np
from PIL import Image

from app.components.document_processing.ocr_config import (
    TROCR_DEVICE,
    TROCR_MAX_NEW_TOKENS,
    TROCR_MODEL_NAME,
)

logger = logging.getLogger(__name__)


def _resolve_device() -> str:
    if TROCR_DEVICE and TROCR_DEVICE != "auto":
        return TROCR_DEVICE

    try:
        import torch

        return "cuda" if torch.cuda.is_available() else "cpu"
    except Exception:
        return "cpu"


@lru_cache(maxsize=1)
def _load_trocr_model():
    from transformers import TrOCRProcessor, VisionEncoderDecoderModel

    device = _resolve_device()
    logger.info("Loading TrOCR model '%s' on %s", TROCR_MODEL_NAME, device)

    processor = TrOCRProcessor.from_pretrained(TROCR_MODEL_NAME)
    model = VisionEncoderDecoderModel.from_pretrained(TROCR_MODEL_NAME)
    model.to(device)
    model.eval()

    return processor, model, device


def _to_pil_rgb(image_crop: np.ndarray) -> Image.Image:
    if image_crop.ndim == 2:
        image = Image.fromarray(image_crop)
    else:
        image = Image.fromarray(image_crop[..., ::-1])
    return image.convert("RGB")


def trocr_predict(image_crop: np.ndarray, tess_lang: Optional[str] = None) -> str:
    """Predict handwritten text from an image crop using the Sinhala TrOCR model."""
    del tess_lang

    if image_crop is None or image_crop.size == 0:
        return ""

    import torch

    processor, model, device = _load_trocr_model()
    image = _to_pil_rgb(image_crop)
    pixel_values = processor(images=image, return_tensors="pt").pixel_values.to(device)

    with torch.no_grad():
        generated_ids = model.generate(
            pixel_values,
            max_new_tokens=TROCR_MAX_NEW_TOKENS,
        )

    return processor.batch_decode(generated_ids, skip_special_tokens=True)[0].strip()
