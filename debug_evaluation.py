
import logging
from uuid import UUID
from app.core.database import SessionLocal
from app.shared.models.answer_evaluation import AnswerDocument
from app.shared.models.evaluation_session import EvaluationSession
from app.services.evaluation.question_paper_service import QuestionPaperService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def debug_evaluation(answer_doc_id_str):
    db = SessionLocal()
    try:
        answer_doc_id = UUID(answer_doc_id_str)
        answer_doc = db.query(AnswerDocument).filter(AnswerDocument.id == answer_doc_id).first()
        
        if not answer_doc:
            print("Answer Document not found")
            return

        print(f"Answer Document ID: {answer_doc.id}")
        print(f"Mapped Answers Keys: {list(answer_doc.mapped_answers.keys()) if answer_doc.mapped_answers else 'None'}")
        print(f"Mapped Answers Content (First 100 chars): {str(answer_doc.mapped_answers)[:100] if answer_doc.mapped_answers else 'None'}")

        eval_session = db.query(EvaluationSession).filter(EvaluationSession.id == answer_doc.evaluation_session_id).first()
        if not eval_session:
            print("Evaluation Session not found")
            return
            
        print(f"Evaluation Session ID: {eval_session.id}")
        print(f"Chat Session ID: {eval_session.session_id}")

        qp_service = QuestionPaperService(db)
        qps = qp_service.get_question_papers_by_chat_session(eval_session.session_id)
        
        if not qps:
            print("No Question Papers found for this session")
            return

        qp = qps[0]
        print(f"Question Paper ID: {qp.id}")
        
        questions = qp_service.get_questions_by_paper(qp.id)
        print(f"Found {len(questions)} main questions")
        
        for q in questions:
            print(f"  Q: {q.question_number} (ID: {q.id})")
            if q.sub_questions:
                for sq in q.sub_questions:
                    print(f"    SQ: {sq.label} (ID: {sq.id})")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    # The ID from the user's request
    debug_evaluation("3bb92abb-4296-45c4-9f2d-549f4ee43e0a")
