
import sys
import os
from sqlalchemy import create_engine, text

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.config import settings

def check_answer_doc():
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as conn:
        print("Checking latest AnswerDocument and its mapped answers...")
        
        # 1. Get the latest AnswerDocument
        result = conn.execute(text("SELECT id, mapped_answers FROM answer_documents ORDER BY created_at DESC LIMIT 1;")).fetchone()
        if not result:
            print("No answer documents found.")
            return
            
        doc_id = result[0]
        mapped = result[1]
        print(f"Latest AnswerDocument ID: {doc_id}")
        
        if mapped:
            print(f"Mapped answers keys: {list(mapped.keys())}")
            # Print a few samples
            for k in list(mapped.keys())[:5]:
                print(f"  Sample mapping: {k} -> {str(mapped[k])[:50]}")
        else:
            print("  mapped_answers is NULL or empty.")

if __name__ == "__main__":
    check_answer_doc()
