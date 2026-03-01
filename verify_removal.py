
import os
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from pathlib import Path
from app.services.resource_service import ResourceService
from app.services.chat_session_service import ChatSessionService
from app.services.evaluation.answer_evaluation_service import AnswerEvaluationService
from app.shared.models.resource_file import ResourceFile
from app.shared.models.answer_evaluation import AnswerDocument, EvaluationResult, QuestionScore
from app.shared.models.evaluation_session import EvaluationResource, EvaluationSession
from app.shared.models.session_resources import SessionResource
from app.shared.models.resource_chunks import ResourceChunk

DATABASE_URL = "postgresql://miyuri:Miyuri123@localhost:5433/sinhala_learn"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def verify_full_removal():
    db = SessionLocal()
    resource_service = ResourceService(db)
    chat_service = ChatSessionService(db)
    eval_service = AnswerEvaluationService(db)
    
    # Use a dummy user ID (ensure it exists or use a known one)
    # Based on .env, maybe there's a user. Let's look for one.
    user = db.execute("SELECT id FROM users LIMIT 1").fetchone()
    if not user:
        print("No user found in database. Cannot proceed with verification.")
        return
    user_id = user[0]
    
    print(f"Using User ID: {user_id}")
    
    # 1. Upload Resource
    print("--- 1. Uploading Resource ---")
    filename = "test_removal.txt"
    content = b"This is a test file for removal verification."
    resource = resource_service.only_upload_resource_from_file(
        user_id=user_id,
        filename=filename,
        content_type="text/plain",
        content=content
    )

    resource_id = resource.id
    storage_path = resource.storage_path
    print(f"Resource created: {resource_id}, Path: {storage_path}")
    
    # 2. Attach to Chat Session
    print("--- 2. Attaching to Chat Session ---")
    chat_session = chat_service.create_session(user_id=user_id, mode="evaluation", title="Test Session")
    chat_service.attach_resource(session_id=chat_session.id, user_id=user_id, resource_id=resource_id, role="answer_script")
    print(f"Attached to Chat Session: {chat_session.id}")
    
    # 3. Attach to Evaluation Session (EvaluationResource)
    print("--- 3. Attaching to Evaluation Session ---")
    eval_session = EvaluationSession(session_id=chat_session.id, status="pending")
    db.add(eval_session)
    db.commit()
    db.refresh(eval_session)
    
    eval_resource = EvaluationResource(evaluation_session_id=eval_session.id, resource_id=resource_id, role="answer_script")
    db.add(eval_resource)
    db.commit()
    print(f"Attached to Evaluation Session: {eval_session.id}")
    
    # 4. Create AnswerDocument and Results
    print("--- 4. Creating AnswerDocument and Results ---")
    answer_doc = eval_service.create_answer_document(evaluation_session_id=eval_session.id, resource_id=resource_id)
    eval_result = eval_service.create_evaluation_result(answer_document_id=answer_doc.id, total_score=75.5, overall_feedback="Good job")
    eval_service.create_question_score(evaluation_result_id=eval_result.id, awarded_marks=10.0, feedback="Correct")
    print(f"AnswerDoc: {answer_doc.id}, Result: {eval_result.id}")
    
    # 5. Verify records exist
    print("--- 5. Verifying records exist ---")
    assert db.query(ResourceFile).get(resource_id) is not None
    assert db.query(SessionResource).filter_by(resource_id=resource_id).first() is not None
    assert db.query(EvaluationResource).filter_by(resource_id=resource_id).first() is not None
    assert db.query(AnswerDocument).get(answer_doc.id) is not None
    assert db.query(EvaluationResult).get(eval_result.id) is not None
    assert db.query(QuestionScore).filter_by(evaluation_result_id=eval_result.id).first() is not None
    assert os.path.exists(storage_path)
    print("All records and file exist.")
    
    # 6. Delete Resource
    print("--- 6. Deleting Resource ---")
    resource_service.delete_resource(resource_id, user_id)
    print("Delete call completed.")
    
    # 7. Verify everything is gone
    print("--- 7. Verifying Cascades ---")
    # ResourceFile should be gone
    assert db.query(ResourceFile).get(resource_id) is None
    # Linked records should be gone via CASCADE
    assert db.query(SessionResource).filter_by(resource_id=resource_id).first() is None
    assert db.query(EvaluationResource).filter_by(resource_id=resource_id).first() is None
    assert db.query(AnswerDocument).get(answer_doc.id) is None
    assert db.query(EvaluationResult).get(eval_result.id) is None
    # QuestionScore should be gone via cascading EvaluationResult
    assert db.query(QuestionScore).filter_by(evaluation_result_id=eval_result.id).first() is None
    # Physical file should be gone
    assert not os.path.exists(storage_path)
    
    print("SUCCESS: All records and physical file removed via cascades.")
    db.close()

if __name__ == "__main__":
    try:
        verify_full_removal()
    except Exception as e:
        print(f"Verification FAILED: {e}")
        import traceback
        traceback.print_exc()
