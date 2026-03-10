from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.components.document_processing.services.resource_processor_service import (
    ResourceProcessorService,
)


@pytest.fixture
def service():
    return ResourceProcessorService(db=MagicMock())


def test_is_need_to_analyze_layout_question_paper_false(service):
    assert service.is_need_to_analyze_layout("question_paper") is False


def test_is_need_to_analyze_layout_other_and_none_true(service):
    assert service.is_need_to_analyze_layout("lesson_note") is True
    assert service.is_need_to_analyze_layout(None) is True


def test_try_direct_pdf_extraction_success_returns_cleaned_text_and_pages(service):
    extract_text_from_pdf = MagicMock(return_value=(" raw text ", 3))
    basic_clean = MagicMock(return_value="cleaned text")

    text, pages = service._try_direct_pdf_extraction(
        "dummy.pdf", extract_text_from_pdf, basic_clean
    )

    assert text == "cleaned text"
    assert pages == 3
    basic_clean.assert_called_once_with(" raw text ")


def test_try_direct_pdf_extraction_exception_returns_none_zero(service):
    extract_text_from_pdf = MagicMock(side_effect=Exception("pdf failed"))
    basic_clean = MagicMock()

    text, pages = service._try_direct_pdf_extraction(
        "dummy.pdf", extract_text_from_pdf, basic_clean
    )

    assert text is None
    assert pages == 0
    basic_clean.assert_not_called()


def test_sniff_pdf_language_legacy_sinhala_forces_unknown(service, monkeypatch):
    class FakePage:
        def extract_text(self):
            return "YS% ,xld ud;d wm "

    class FakePdf:
        pages = [FakePage()]

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    fake_pdfplumber = SimpleNamespace(open=lambda _: FakePdf())
    monkeypatch.setitem(sys.modules, "pdfplumber", fake_pdfplumber)

    detect_language_from_text = MagicMock(return_value="english")

    lang = service._sniff_pdf_language("dummy.pdf", detect_language_from_text)

    assert lang == "unknown"
    detect_language_from_text.assert_not_called()


def test_sniff_pdf_language_normal_text_returns_detected_language(service, monkeypatch):
    class FakePage:
        def extract_text(self):
            return "This is a normal English text sample"

    class FakePdf:
        pages = [FakePage()]

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    fake_pdfplumber = SimpleNamespace(open=lambda _: FakePdf())
    monkeypatch.setitem(sys.modules, "pdfplumber", fake_pdfplumber)

    detect_language_from_text = MagicMock(return_value="english")

    lang = service._sniff_pdf_language("dummy.pdf", detect_language_from_text)

    assert lang == "english"
    detect_language_from_text.assert_called_once_with(
        "This is a normal English text sample"
    )
