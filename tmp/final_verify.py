
import sys
import os
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Monkeypatch JSONB for SQLite testing
from sqlalchemy.dialects import postgresql
from sqlalchemy import JSON
postgresql.JSONB = JSON

# Mock settings for testing
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app.core.database import Base, engine
from app.shared.models.answer_evaluation import AnswerDocument, StudentAnswer, QuestionScore
from app.shared.models.question_papers import Question, SubQuestion, QuestionPaper

def final_verify():
    print("Testing data persistence...")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        rid = uuid.uuid4()
        sid = uuid.uuid4()
        aid = uuid.uuid4()
        
        # 1. AnswerDocument
        ad = AnswerDocument(id=aid, evaluation_session_id=sid, resource_id=rid, mapped_answers={})
        db.add(ad)
        
        # 2. StudentAnswer
        sa = StudentAnswer(id=uuid.uuid4(), answer_document_id=aid, answer_text="Hello Structured World")
        db.add(sa)
        
        # 3. QuestionScore
        qs = QuestionScore(id=uuid.uuid4(), evaluation_result_id=uuid.uuid4(), awarded_marks=5.5, student_answer="Hello Structured World")
        db.add(qs)
        
        db.commit()
        print("Commit success!")
        
        verify_sa = db.query(StudentAnswer).first()
        print(f"Verified StudentAnswer: {verify_sa.answer_text}")
        
        verify_qs = db.query(QuestionScore).first()
        print(f"Verified QuestionScore: Marks={verify_qs.awarded_marks}, Answer={verify_qs.student_answer}")
        
        print("\nALL DATABASE TESTS PASSED.")
        
    except Exception as e:
        print(f"Error during final verify: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    final_verify()
