
from uuid import UUID
from app.core.database import SessionLocal
from app.shared.models.answer_evaluation import EvaluationResult

def delete_evaluation_result(answer_doc_id_str):
    db = SessionLocal()
    try:
        answer_doc_id = UUID(answer_doc_id_str)
        result = db.query(EvaluationResult).filter(EvaluationResult.answer_document_id == answer_doc_id).first()
        
        if result:
            print(f"Deleting EvaluationResult ID: {result.id}")
            db.delete(result)
            db.commit()
            print("Deleted successfully.")
        else:
            print("No EvaluationResult found to delete.")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    # The ID from the user's request
    delete_evaluation_result("3bb92abb-4296-45c4-9f2d-549f4ee43e0a")
