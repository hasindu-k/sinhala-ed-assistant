import sys
import types
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.components.document_processing.services import classifier_service


def _load_grading_service_class():
    fake_embeddings = types.ModuleType("app.shared.ai.embeddings")
    fake_embeddings.xlmr = MagicMock()
    fake_embeddings.ml_semaphore = None
    fake_embeddings.ensure_sentences_cached = lambda *args, **kwargs: None
    fake_embeddings._embedding_cache = {}
    sys.modules["app.shared.ai.embeddings"] = fake_embeddings

    from app.services.evaluation.grading_service import GradingService

    return GradingService


def test_single_pass_answer_mapping_uses_one_gemini_call(monkeypatch):
    calls = []

    def fake_gemini_generate_evaluation(prompt, *, budget, json_mode=False, reason=None):
        calls.append({"budget": budget.duty_name, "json_mode": json_mode, "reason": reason})
        return '{"q-1": "1. student answer"}'

    monkeypatch.setattr(classifier_service, "gemini_generate_evaluation", fake_gemini_generate_evaluation)
    monkeypatch.setattr(classifier_service, "_has_marker_supported_mapping", lambda *args, **kwargs: True)
    monkeypatch.setattr(classifier_service, "_is_hallucinated_question_text", lambda *args, **kwargs: False)
    monkeypatch.setattr(classifier_service, "_get_part_specific_answer_text", lambda text, part: text)
    monkeypatch.setattr(classifier_service, "_suppress_cross_part_duplicate_mappings", lambda mappings, _: mappings)

    question = SimpleNamespace(
        id="q-1",
        question_number="1",
        part_name="Paper_I",
        question_text="Who was the king?",
        sub_questions=[],
    )

    result = classifier_service.map_student_answers("1. student answer", [question])

    assert result == {"q-1": "1. student answer"}
    assert len(calls) == 1
    assert calls[0]["budget"] == "answer_mapping"
    assert calls[0]["reason"] == "single_pass_full_paper"


def test_reference_extraction_respects_request_budget(monkeypatch):
    calls = []

    def fake_gemini_generate_evaluation(prompt, *, budget, json_mode=False, reason=None):
        calls.append({"budget": budget.duty_name, "reason": reason})
        key_count = prompt.count("--- Key: ref_")
        payload = {f"ref_{idx + 1}": f"Reference {idx + 1}" for idx in range(key_count)}
        import json

        return json.dumps(payload)

    db = MagicMock()
    GradingService = _load_grading_service_class()
    grading_module = sys.modules["app.services.evaluation.grading_service"]
    monkeypatch.setattr(grading_module, "gemini_generate_evaluation", fake_gemini_generate_evaluation)
    monkeypatch.setattr(grading_module.settings, "EVAL_GEMINI_REFERENCE_SCHEMA_MAX_REQUESTS", 2)
    service = GradingService(db)

    targets = []
    for idx in range(6):
        target = SimpleNamespace(correct_answer=None)
        targets.append(
            {
                "key": f"q-{idx}",
                "target": target,
                "question_text": ("Question text " + str(idx) + " ") * 120,
                "max_marks": 5,
                "display_number": str(idx + 1),
                "question_type": "essay",
            }
        )

    result = service._batch_extract_reference_points(targets, "Syllabus content")

    assert len(calls) == 2
    assert all(call["budget"] == "reference_extraction" for call in calls)
    assert len(result) == len(targets)
