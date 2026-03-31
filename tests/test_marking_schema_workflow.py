from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import MagicMock, patch

import pytest

from app.services.evaluation.evaluation_workflow_service import EvaluationWorkflowService


def build_workflow():
    workflow = EvaluationWorkflowService(MagicMock())
    workflow.answers = MagicMock()
    workflow.sessions = MagicMock()
    workflow.resource_files = MagicMock()
    workflow.marking_schemas = MagicMock()
    workflow._get_evaluation_context = MagicMock(return_value=("syllabus", "rubric", []))
    workflow._build_question_map_helper = MagicMock(return_value={"q1": "target"})
    workflow._ensure_answer_owner = MagicMock()
    return workflow


def test_evaluate_answer_blocks_when_marking_schema_missing():
    workflow = build_workflow()
    answer_id = uuid4()
    user_id = uuid4()
    eval_session_id = uuid4()

    answer_doc = SimpleNamespace(id=answer_id, resource_id=uuid4(), evaluation_session_id=eval_session_id, mapped_answers={"q1": "answer"})
    answer_resource = SimpleNamespace(id=answer_doc.resource_id, extracted_text="text")
    eval_session = SimpleNamespace(id=eval_session_id, session_id=uuid4())

    workflow._ensure_answer_owner.return_value = answer_doc
    workflow.resource_files.get_resource.return_value = answer_resource
    workflow.sessions.get_evaluation_session.return_value = eval_session
    workflow.marking_schemas.ensure_schema_confirmed.side_effect = ValueError("Marking schema must be confirmed before grading")

    with pytest.raises(ValueError, match="Marking schema must be confirmed before grading"):
        workflow.evaluate_answer(answer_id, user_id)


def test_evaluate_answer_uses_confirmed_saved_references():
    workflow = build_workflow()
    answer_id = uuid4()
    user_id = uuid4()
    eval_session_id = uuid4()

    answer_doc = SimpleNamespace(id=answer_id, resource_id=uuid4(), evaluation_session_id=eval_session_id, mapped_answers={"q1": "answer"})
    answer_resource = SimpleNamespace(id=answer_doc.resource_id, extracted_text="text")
    eval_session = SimpleNamespace(id=eval_session_id, session_id=uuid4())
    grading_result = SimpleNamespace(id=uuid4())

    workflow._ensure_answer_owner.return_value = answer_doc
    workflow.resource_files.get_resource.return_value = answer_resource
    workflow.sessions.get_evaluation_session.return_value = eval_session
    workflow.marking_schemas.get_confirmed_reference_map.return_value = {"q1": "saved reference"}

    with patch("app.services.evaluation.grading_service.GradingService") as grading_service_cls:
        grading_service = grading_service_cls.return_value
        grading_service.grade_answer_document.return_value = grading_result

        result = workflow.evaluate_answer(answer_id, user_id)

    assert result == grading_result
    grading_service.grade_answer_document.assert_called_once()
    assert grading_service.grade_answer_document.call_args.kwargs["reference_map"] == {"q1": "saved reference"}
