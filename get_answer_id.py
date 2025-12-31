import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from app.core.database import SessionLocal
from app.shared.models.answer_evaluation import AnswerDocument

db = SessionLocal()
resource_id = '6bc6d206-272f-4261-962d-edde4c673462'
answer_doc = db.query(AnswerDocument).filter(AnswerDocument.resource_id == resource_id).first()

if answer_doc:
    print(f"Answer Document ID: {answer_doc.id}")
else:
    print("Answer Document not found")
