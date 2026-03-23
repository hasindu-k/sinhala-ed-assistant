
import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import uuid

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Monkeypatch JSONB for SQLite testing
from sqlalchemy.dialects import postgresql
from sqlalchemy import JSON
postgresql.JSONB = JSON

# Mock settings for testing
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app.core.database import Base, engine
from app.shared.models.answer_evaluation import StudentAnswer, QuestionScore, AnswerDocument
from app.shared.models.question_papers import Question, SubQuestion, QuestionPaper

def verify_models():
    print("Initializing test database (in-memory sqlite)...")
    Base.metadata.create_all(bind=engine)
    
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        print("Creating mock question paper...")
        rid = uuid.uuid4()
        # Note: we need a mock for other tables if FKs are enforced, but SQLite won't unless PRAGMA is on
        qp = QuestionPaper(id=uuid.uuid4(), resource_id=rid)
        db.add(qp)
        
        q1 = Question(id=uuid.uuid4(), question_paper_id=qp.id, question_text="What is this?", max_marks=2)
        db.add(q1)
        
        sq1 = SubQuestion(id=uuid.uuid4(), question_id=q1.id, label="a", sub_question_text="Part a", max_marks=1)
        db.add(sq1)
        
        print("Creating mock answer document...")
        sid = uuid.uuid4()
        ad = AnswerDocument(id=uuid.uuid4(), evaluation_session_id=sid, resource_id=rid, mapped_answers={"1": "Student Answer 1"})
        db.add(ad)
        
        print("Verifying StudentAnswer insertion...")
        sa = StudentAnswer(
            answer_document_id=ad.id,
            question_id=q1.id,
            answer_text="Structured student answer for Q1"
        )
        db.add(sa)
        
        sa_sub = StudentAnswer(
            answer_document_id=ad.id,
            sub_question_id=sq1.id,
            answer_text="Structured student answer for Q1(a)"
        )
        db.add(sa_sub)
        
        print("Verifying QuestionScore with student_answer field...")
        qs = QuestionScore(
            evaluation_result_id=uuid.uuid4(), # Just a mock UUID
            question_id=q1.id,
            awarded_marks=2,
            student_answer="Structured student answer for Q1"
        )
        db.add(qs)
        
        db.commit()
        print("Database commit successful!")
        
        # Query back
        res_sa = db.query(StudentAnswer).all()
        print(f"Retrieved {len(res_sa)} StudentAnswers.")
        for r in res_sa:
            print(f" SA: ID={r.id}, Text={r.answer_text}")
            
        res_qs = db.query(QuestionScore).filter(QuestionScore.question_id == q1.id).first()
        print(f"Retrieved QuestionScore: Marks={res_qs.awarded_marks}, Answer={res_qs.student_answer}")
        
        print("\nSUCCESS: Database models and relationships verified.")
        
    except Exception as e:
        print(f"\nFAILURE: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    verify_models()
