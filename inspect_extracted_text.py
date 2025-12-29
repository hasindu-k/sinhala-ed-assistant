import sys
import os
from uuid import UUID

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.shared.models.question_papers import QuestionPaper

def check_text(session_id_str):
    db = SessionLocal()
    try:
        session_id = UUID(session_id_str)
        print(f"Checking Text for Session: {session_id}")

        qp = db.query(QuestionPaper).filter(QuestionPaper.evaluation_session_id == session_id).first()
        if not qp:
            print("❌ Question Paper record NOT FOUND.")
            return
        
        if qp.extracted_text:
            print("✅ Extracted Text FOUND.")
            print(f"Length: {len(qp.extracted_text)} characters")
            print("-" * 20)
            print(qp.extracted_text[:1000]) # Print first 1000 chars
            print("-" * 20)
        else:
            print("⚠️ Question Paper record found, but `extracted_text` is EMPTY/NULL.")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    # Using the session ID from previous context
    check_text("7934778f-924b-49e2-9adb-cdd5cf47aeb6")
