
from app.core.database import SessionLocal
from app.shared.models.answer_evaluation import MarkingReference
from app.services.evaluation.evaluation_workflow_service import EvaluationWorkflowService
from uuid import uuid4

def verify():
    db = SessionLocal()
    try:
        # Check if model can be queried (even if empty)
        count = db.query(MarkingReference).count()
        print(f"MarkingReference table accessible. Current count: {count}")
        
        # Check if service can be instantiated
        service = EvaluationWorkflowService(db)
        print("EvaluationWorkflowService instantiated successfully.")
        
        # Check if methods exist
        if hasattr(service, 'get_or_create_marking_scheme') and hasattr(service, 'approve_marking_scheme'):
            print("New methods found in EvaluationWorkflowService.")
        else:
            print("ERROR: New methods NOT found in EvaluationWorkflowService.")
            
    except Exception as e:
        print(f"Verification FAILED: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    verify()
