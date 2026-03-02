import os
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.components.document_processing.services import table_detection


def _resolve_path(env_key: str, default_relative: str) -> Path:
    value = os.getenv(env_key)
    if value:
        return Path(value).expanduser().resolve()
    return (PROJECT_ROOT / default_relative).resolve()


MODEL_PATH = _resolve_path("TABLE_MODEL_PATH", "utils/table_model.pt")
TABLE_IMAGE_PATH = _resolve_path(
    "TABLE_IMAGE_PATH", "tests/fixtures/page_with_table.png"
)
NO_TABLE_IMAGE_PATH = _resolve_path(
    "NO_TABLE_IMAGE_PATH", "tests/fixtures/page_without_table.png"
)


def _skip_if_not_ready() -> None:
    if not table_detection.ULTRALYTICS_AVAILABLE:
        pytest.skip("Ultralytics is not installed in this environment")

    if not MODEL_PATH.exists():
        pytest.skip(f"YOLO model file not found: {MODEL_PATH}")

    missing = [
        str(p)
        for p in [TABLE_IMAGE_PATH, NO_TABLE_IMAGE_PATH]
        if not p.exists()
    ]
    if missing:
        pytest.skip(f"Required integration test image(s) missing: {', '.join(missing)}")


@pytest.mark.integration
def test_detects_table_in_table_image():
    _skip_if_not_ready()

    coords, count = table_detection.detect_tables_with_yolo(
        str(TABLE_IMAGE_PATH),
        model_path=str(MODEL_PATH),
    )

    assert count >= 1
    assert len(coords) >= 1


@pytest.mark.integration
def test_detects_no_table_in_non_table_image():
    _skip_if_not_ready()

    coords, count = table_detection.detect_tables_with_yolo(
        str(NO_TABLE_IMAGE_PATH),
        model_path=str(MODEL_PATH),
    )

    assert count == 0
    assert coords == []
