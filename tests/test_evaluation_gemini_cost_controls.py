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
        calls.append(
            {
                "budget": budget.duty_name,
                "json_mode": json_mode,
                "reason": reason,
                "model": budget.model_name,
            }
        )
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
    assert calls[0].get("model", classifier_service.EvaluationGeminiClient.ANSWER_MAPPING.model_name) == classifier_service.EvaluationGeminiClient.ANSWER_MAPPING.model_name


def test_question_parsing_uses_configured_model(monkeypatch):
    calls = []

    def fake_gemini_generate(prompt, *, json_mode=False, model_name=None, max_retries=3):
        calls.append(
            {
                "json_mode": json_mode,
                "model_name": model_name,
                "max_retries": max_retries,
            }
        )
        return '{"Paper_I": {"questions": {}}, "Paper_II": {"questions": {}}}'

    monkeypatch.setattr(classifier_service, "gemini_generate", fake_gemini_generate)
    monkeypatch.setattr(
        classifier_service.settings,
        "EVAL_GEMINI_QUESTION_PARSING_MODEL",
        "gemini-2.5-flash",
    )

    result = classifier_service.extract_complete_exam_data("Sample question paper")

    assert result == {
        "Paper_I": {"config": {"total_questions_available": 0}, "questions": {}},
        "Paper_II": {"config": {"total_questions_available": 0}, "questions": {}},
    }
    assert len(calls) == 1
    assert calls[0]["json_mode"] is True
    assert calls[0]["model_name"] == "gemini-2.5-flash"


def test_reference_extraction_respects_request_budget(monkeypatch):
    calls = []

    def fake_gemini_generate_evaluation(prompt, *, budget, json_mode=False, reason=None):
        calls.append(
            {
                "budget": budget.duty_name,
                "reason": reason,
                "model": budget.model_name,
            }
        )
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
    assert all(
        call.get("model", grading_module.EvaluationGeminiClient.REFERENCE_SCHEMA.model_name)
        == grading_module.EvaluationGeminiClient.REFERENCE_SCHEMA.model_name
        for call in calls
    )
    assert len(result) == len(targets)


def test_reference_extraction_prompt_uses_per_question_evidence(monkeypatch):
    prompts = []

    def fake_gemini_generate_evaluation(prompt, *, budget, json_mode=False, reason=None):
        prompts.append(prompt)
        return '{"ref_1": "Reference 1"}'

    db = MagicMock()
    GradingService = _load_grading_service_class()
    grading_module = sys.modules["app.services.evaluation.grading_service"]
    monkeypatch.setattr(grading_module, "gemini_generate_evaluation", fake_gemini_generate_evaluation)
    service = GradingService(db)
    monkeypatch.setattr(
        service,
        "_build_reference_context_block",
        lambda question_info, syllabus_text: f"Evidence for {question_info['key']}",
    )

    result = service._batch_extract_reference_points(
        [
            {
                "key": "q-1",
                "target": SimpleNamespace(correct_answer=None),
                "question_text": "Question text",
                "max_marks": 2,
                "display_number": "1",
                "question_type": "short",
            }
        ],
        "Long syllabus content",
    )

    assert result == {"q-1": "Reference 1"}
    assert len(prompts) == 1
    assert "Evidence:\nEvidence for q-1" in prompts[0]
    assert "Do NOT use internal knowledge." in prompts[0]
    assert "{syllabus_for_prompt}" not in prompts[0]


def test_reference_extraction_drops_not_covered_and_uses_context_fallback(monkeypatch):
    def fake_gemini_generate_evaluation(prompt, *, budget, json_mode=False, reason=None):
        return '{"ref_1": "මෙම සාක්ෂිය තුළ මැකඩම් මාර්ග තැනීම පිළිබඳ තොරතුරු අඩංගු නොවේ."}'

    db = MagicMock()
    GradingService = _load_grading_service_class()
    grading_module = sys.modules["app.services.evaluation.grading_service"]
    monkeypatch.setattr(grading_module, "gemini_generate_evaluation", fake_gemini_generate_evaluation)
    service = GradingService(db)
    monkeypatch.setattr(
        service,
        "_build_reference_context_block",
        lambda question_info, syllabus_text: "Retrieved syllabus evidence",
    )

    result = service._batch_extract_reference_points(
        [
            {
                "key": "q-1",
                "target": SimpleNamespace(correct_answer=None),
                "question_text": "Question text",
                "max_marks": 4,
                "display_number": "1(a)",
                "question_type": "essay",
            }
        ],
        "Long syllabus content",
    )

    assert result == {"q-1": "Retrieved syllabus evidence"}


def test_reference_extraction_drops_additional_sinhala_placeholder_variants(monkeypatch):
    def fake_gemini_generate_evaluation(prompt, *, budget, json_mode=False, reason=None):
        return '{"ref_1": "මෙම සාධක වලින් එකක්වත් ලබා දී ඇති සාක්ෂිවල අඩංගු නොවේ."}'

    db = MagicMock()
    GradingService = _load_grading_service_class()
    grading_module = sys.modules["app.services.evaluation.grading_service"]
    monkeypatch.setattr(grading_module, "gemini_generate_evaluation", fake_gemini_generate_evaluation)
    service = GradingService(db)
    monkeypatch.setattr(
        service,
        "_build_reference_context_block",
        lambda question_info, syllabus_text: "Recovered evidence block",
    )

    result = service._batch_extract_reference_points(
        [
            {
                "key": "q-1",
                "target": SimpleNamespace(correct_answer=None),
                "question_text": "Question text",
                "max_marks": 4,
                "display_number": "1(a)",
                "question_type": "essay",
            }
        ],
        "Long syllabus content",
    )

    assert result == {"q-1": "Recovered evidence block"}


def test_reference_extraction_maps_display_number_keys_back_to_question_ids(monkeypatch):
    def fake_gemini_generate_evaluation(prompt, *, budget, json_mode=False, reason=None):
        return '{"1(අ)": "Reference from display key"}'

    db = MagicMock()
    GradingService = _load_grading_service_class()
    grading_module = sys.modules["app.services.evaluation.grading_service"]
    monkeypatch.setattr(grading_module, "gemini_generate_evaluation", fake_gemini_generate_evaluation)
    service = GradingService(db)

    result = service._batch_extract_reference_points(
        [
            {
                "key": "q-1",
                "target": SimpleNamespace(correct_answer=None),
                "question_text": "Question text",
                "max_marks": 4,
                "display_number": "1.අ",
                "question_type": "essay",
            }
        ],
        "Long syllabus content",
    )

    assert result == {"q-1": "Reference from display key"}


def test_reference_extraction_rejects_raw_page_fallback_context(monkeypatch):
    def fake_gemini_generate_evaluation(prompt, *, budget, json_mode=False, reason=None):
        return "{}"

    db = MagicMock()
    GradingService = _load_grading_service_class()
    grading_module = sys.modules["app.services.evaluation.grading_service"]
    monkeypatch.setattr(grading_module, "gemini_generate_evaluation", fake_gemini_generate_evaluation)
    service = GradingService(db)
    monkeypatch.setattr(
        service,
        "_build_reference_context_block",
        lambda question_info, syllabus_text: "--- PAGE 1 --- cover text ... [Context Clipped]",
    )

    result = service._batch_extract_reference_points(
        [
            {
                "key": "q-1",
                "target": SimpleNamespace(correct_answer=None),
                "question_text": "Question text",
                "max_marks": 4,
                "display_number": "1",
                "question_type": "essay",
            }
        ],
        "Long syllabus content",
    )

    assert result == {}


def test_generate_initial_marking_scheme_passes_target_to_reference_extraction(monkeypatch):
    db = MagicMock()
    GradingService = _load_grading_service_class()
    service = GradingService(db)
    service.marking_refs = MagicMock()

    captured = {}

    def fake_batch_extract(questions, syllabus_text):
        captured["questions"] = questions
        return {"q-1": "Reference"}

    monkeypatch.setattr(service, "_batch_extract_reference_points", fake_batch_extract)

    target = SimpleNamespace(id="target-1", question_number="1", correct_answer=None)
    service.generate_initial_marking_scheme(
        evaluation_session_id=SimpleNamespace(),
        syllabus_text="Syllabus",
        questions=[{"key": "q-1", "target": target, "text": "Question text"}],
    )

    assert captured["questions"][0]["target"] is target


def test_safe_json_loads_repairs_trailing_comma():
    payload = """
    {
      "a": "one",
      "b": "two",
    }
    """

    result = classifier_service._safe_json_loads(payload)

    assert result == {"a": "one", "b": "two"}


def test_normalize_extracted_exam_result_rebalances_plain_questions():
    raw = {
        "Paper_I": {
            "config": {"total_questions_available": 1},
            "questions": {
                "1": {"type": "structured", "text": "Q1", "marks": 1},
                "2": {"type": "structured", "text": "Q2", "marks": 1},
            },
        },
        "Paper_II": {
            "config": {"total_questions_available": 5},
            "questions": {
                "3": {"type": "structured", "text": "Misplaced Paper I question", "marks": 1},
                "1": {
                    "type": "structured",
                    "text": "Main 1",
                    "marks": 10,
                    "sub_questions": {"a": {"text": "Sub A", "marks": 5}},
                },
                "2": {
                    "type": "structured",
                    "text": "Main 2",
                    "marks": 10,
                    "sub_questions": {"a": {"text": "Sub A", "marks": 5}},
                },
                "4": {
                    "type": "structured",
                    "text": "Main 4",
                    "marks": 10,
                    "sub_questions": {"a": {"text": "Sub A", "marks": 5}},
                },
            },
        },
    }

    normalized = classifier_service._normalize_extracted_exam_result(raw)

    assert normalized["Paper_I"]["config"]["total_questions_available"] == 3
    assert normalized["Paper_II"]["config"]["total_questions_available"] == 3
    assert "3" in normalized["Paper_I"]["questions"]
    assert "3" not in normalized["Paper_II"]["questions"]
