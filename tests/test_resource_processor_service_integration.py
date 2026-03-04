import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from dotenv import dotenv_values, load_dotenv
from sqlalchemy import create_engine, text

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.components.document_processing.services.resource_processor_service import (
    ResourceProcessorService,
)
from app.components.document_processing.services.text_extraction import (
    detect_language_from_text,
    extract_text_from_pdf,
)
from app.components.document_processing.utils.text_cleaner import basic_clean


ENGLISH_PDF_PATH = (PROJECT_ROOT / "tests/fixtures/english_text.pdf").resolve()
LEGACY_PDF_PATH = (PROJECT_ROOT / "tests/fixtures/legacy_sinhala.pdf").resolve()


def _load_env_test_or_skip() -> Path:
    env_candidates = [PROJECT_ROOT / "env.test", PROJECT_ROOT / ".env.test"]
    env_path = next((candidate for candidate in env_candidates if candidate.exists()), None)
    if env_path is None:
        pytest.skip("env.test or .env.test not found at project root")
    load_dotenv(env_path, override=False)
    return env_path


def _require_separate_test_db_or_skip(env_path: Path) -> str:
    values = dotenv_values(env_path)
    test_db_url = values.get("TEST_DATABASE_URL")
    if not test_db_url:
        pytest.skip("TEST_DATABASE_URL is required in env.test/.env.test")

    app_db_url = os.getenv("DATABASE_URL")
    if app_db_url and app_db_url == test_db_url:
        pytest.skip("TEST_DATABASE_URL must be different from DATABASE_URL")

    return test_db_url


def _check_db_connection_or_skip(test_db_url: str) -> None:
    try:
        engine = create_engine(test_db_url)
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:
        pytest.skip(f"Cannot connect to TEST_DATABASE_URL: {exc}")


def _require_fixture_pdf_or_skip(path: Path) -> str:
    if not path.exists():
        pytest.skip(f"Missing fixture PDF: {path}")
    return str(path)


@pytest.fixture(scope="module", autouse=True)
def _integration_precheck():
    env_path = _load_env_test_or_skip()
    test_db_url = _require_separate_test_db_or_skip(env_path)
    _check_db_connection_or_skip(test_db_url)


@pytest.fixture
def service() -> ResourceProcessorService:
    return ResourceProcessorService(db=MagicMock())


@pytest.mark.integration
def test_try_direct_pdf_extraction_with_real_pdf(service):
    english_pdf_path = _require_fixture_pdf_or_skip(ENGLISH_PDF_PATH)

    text, pages = service._try_direct_pdf_extraction(
        str(english_pdf_path), extract_text_from_pdf, basic_clean
    )

    assert pages >= 1
    assert text is not None
    assert text.strip() != ""


@pytest.mark.integration
def test_sniff_pdf_language_returns_english_for_real_english_pdf(service):
    english_pdf_path = _require_fixture_pdf_or_skip(ENGLISH_PDF_PATH)

    lang = service._sniff_pdf_language(str(english_pdf_path), detect_language_from_text)

    assert lang == "english"


@pytest.mark.integration
def test_sniff_pdf_language_returns_unknown_for_legacy_pdf(service):
    legacy_pdf_path = _require_fixture_pdf_or_skip(LEGACY_PDF_PATH)

    lang = service._sniff_pdf_language(str(legacy_pdf_path), detect_language_from_text)

    assert lang == "unknown"
