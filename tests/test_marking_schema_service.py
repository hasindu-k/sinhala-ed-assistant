from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import MagicMock

import pytest

from app.schemas.evaluation import MarkingSchemaQuestionResponse, MarkingSchemaResponse
from app.services.evaluation.marking_schema_service import MarkingSchemaService


def make_response(session_id=None, confirmed=False):
    session_id = session_id or uuid4()
    return MarkingSchemaResponse(
        id=uuid4(),
        session_id=session_id,
        resource_id=None,
        is_confirmed=confirmed,
        created_at=None,
        updated_at=None,
        questions=[
            MarkingSchemaQuestionResponse(
                id=str(uuid4()),
                question_id=uuid4(),
                question_number="1(a)",
                question_text="Explain irrigation",
                reference_text="Reference points",
                max_marks=5,
                part_name="Paper_II",
            )
        ],
    )


def build_service():
    service = MarkingSchemaService(MagicMock())
    service.repository = MagicMock()
    service.resources = MagicMock()
    service.session_resources = MagicMock()
    service.chat_sessions = MagicMock()
    service.sessions = MagicMock()
    return service


def test_get_or_create_schema_generates_when_missing():
    service = build_service()
    session_id = uuid4()
    eval_session = SimpleNamespace(id=session_id, session_id=uuid4())
    created_schema = SimpleNamespace(id=uuid4(), evaluation_session_id=session_id, session_id=eval_session.session_id)
    response = make_response(session_id=session_id, confirmed=False)

    service._resolve_eval_session = MagicMock(return_value=eval_session)
    service.repository.get_marking_schema_by_session.side_effect = [None, created_schema]
    service._generate_marking_schema_items = MagicMock(return_value=[{"question_number": "1", "question_text": "Q", "reference_text": "R", "sort_order": 0}])
    service.repository.create_marking_schema.return_value = created_schema
    service._sync_schema_resource = MagicMock()
    service._to_response = MagicMock(return_value=response)

    result = service.get_or_create_schema(session_id, uuid4())

    assert result == response
    service.repository.create_marking_schema.assert_called_once()
    service.repository.replace_marking_schema_items.assert_called_once()
    service._sync_schema_resource.assert_called_once()


def test_get_or_create_schema_reuses_existing_schema():
    service = build_service()
    session_id = uuid4()
    eval_session = SimpleNamespace(id=session_id, session_id=uuid4())
    existing_schema = SimpleNamespace(id=uuid4(), evaluation_session_id=session_id)
    response = make_response(session_id=session_id, confirmed=True)

    service._resolve_eval_session = MagicMock(return_value=eval_session)
    service.repository.get_marking_schema_by_session.return_value = existing_schema
    service._to_response = MagicMock(return_value=response)

    result = service.get_or_create_schema(session_id, uuid4())

    assert result == response
    service.repository.create_marking_schema.assert_not_called()
    service.repository.replace_marking_schema_items.assert_not_called()


def test_save_schema_sets_draft_state():
    service = build_service()
    session_id = uuid4()
    eval_session = SimpleNamespace(id=session_id, session_id=uuid4())
    existing_schema = SimpleNamespace(id=uuid4(), evaluation_session_id=session_id, resource_id=None, is_confirmed=True)
    response = make_response(session_id=session_id, confirmed=False)

    service._resolve_eval_session = MagicMock(return_value=eval_session)
    service.repository.get_marking_schema_by_session.return_value = existing_schema
    service.repository.update_marking_schema.return_value = existing_schema
    service._to_response = MagicMock(return_value=response)
    service._sync_schema_resource = MagicMock()

    result = service.save_schema(
        session_id,
        payload=[{"question_number": "1", "question_text": "Q", "reference_text": "R"}],
        user_id=uuid4(),
        confirmed=False,
    )

    assert result == response
    service.repository.update_marking_schema.assert_called_once_with(existing_schema.id, is_confirmed=False)


def test_confirm_schema_sets_confirmed_state():
    service = build_service()
    session_id = uuid4()
    eval_session = SimpleNamespace(id=session_id, session_id=uuid4())
    existing_schema = SimpleNamespace(id=uuid4(), evaluation_session_id=session_id, resource_id=None, is_confirmed=False)
    response = make_response(session_id=session_id, confirmed=True)

    service._resolve_eval_session = MagicMock(return_value=eval_session)
    service.repository.get_marking_schema_by_session.return_value = existing_schema
    service.repository.update_marking_schema.return_value = existing_schema
    service._to_response = MagicMock(return_value=response)
    service._sync_schema_resource = MagicMock()

    result = service.confirm_schema(
        session_id,
        payload=[{"question_number": "1", "question_text": "Q", "reference_text": "R"}],
        user_id=uuid4(),
    )

    assert result == response
    service.repository.update_marking_schema.assert_called_once_with(existing_schema.id, is_confirmed=True)


def test_delete_schema_removes_resource_link():
    service = build_service()
    session_id = uuid4()
    resource_id = uuid4()
    eval_session = SimpleNamespace(id=session_id, session_id=uuid4())
    existing_schema = SimpleNamespace(id=uuid4(), evaluation_session_id=session_id, resource_id=resource_id)

    service._resolve_eval_session = MagicMock(return_value=eval_session)
    service.repository.get_marking_schema_by_session.return_value = existing_schema
    service.repository.delete_marking_schema.return_value = True

    deleted = service.delete_schema(session_id, uuid4())

    assert deleted is True
    service.session_resources.detach_resources_by_label.assert_called_once_with(eval_session.session_id, service.SESSION_RESOURCE_LABEL)
    service.resources.delete_resource.assert_called_once()


def test_ensure_schema_confirmed_blocks_missing_and_draft():
    service = build_service()
    session_id = uuid4()
    eval_session = SimpleNamespace(id=session_id, session_id=uuid4())
    service._resolve_eval_session = MagicMock(return_value=eval_session)

    service.repository.get_marking_schema_by_session.return_value = None
    with pytest.raises(ValueError):
        service.ensure_schema_confirmed(session_id, uuid4())

    service.repository.get_marking_schema_by_session.return_value = SimpleNamespace(id=uuid4(), evaluation_session_id=session_id, is_confirmed=False)
    with pytest.raises(ValueError):
        service.ensure_schema_confirmed(session_id, uuid4())


def test_get_confirmed_reference_map_uses_saved_question_ids_and_numbers():
    service = build_service()
    session_id = uuid4()
    question_id = uuid4()
    service.ensure_schema_confirmed = MagicMock(
        return_value=MarkingSchemaResponse(
            id=uuid4(),
            session_id=session_id,
            resource_id=None,
            is_confirmed=True,
            created_at=None,
            updated_at=None,
            questions=[
                MarkingSchemaQuestionResponse(
                    id="item-1",
                    question_id=question_id,
                    question_number="1(a)",
                    question_text="Q",
                    reference_text="Saved reference",
                    max_marks=4,
                    part_name=None,
                )
            ],
        )
    )

    result = service.get_confirmed_reference_map(session_id, uuid4())

    assert result[str(question_id)] == "Saved reference"
    assert result["1(a)"] == "Saved reference"
    assert result["1a"] == "Saved reference"


def test_build_pdf_fetches_schema_and_returns_pdf_bytes():
    pytest.importorskip("fitz")
    service = build_service()
    session_id = uuid4()
    user_id = uuid4()
    response = make_response(session_id=session_id, confirmed=True)

    service.get_or_create_schema = MagicMock(return_value=response)
    service._resolve_pdf_font_path = MagicMock(return_value=None)

    pdf_bytes = service.build_pdf(session_id, user_id)

    assert pdf_bytes.startswith(b"%PDF")
    service.get_or_create_schema.assert_called_once_with(session_id, user_id)


def test_render_pdf_includes_marking_schema_content():
    fitz = pytest.importorskip("fitz")
    service = build_service()
    service._resolve_pdf_font_path = MagicMock(return_value=None)
    response = make_response(confirmed=True)

    pdf_bytes = service._render_pdf(response)
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    extracted_text = "\n".join(page.get_text() for page in doc)
    doc.close()

    assert "Generated Marking Scheme" in extracted_text
    assert "Question 1(a) (5 marks)" in extracted_text
    assert "Reference points" in extracted_text
