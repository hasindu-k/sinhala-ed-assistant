
import sys
import os
from sqlalchemy import create_engine, text

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.config import settings

def verify_schema():
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as conn:
        print("Verifying schema updates...")
        
        # 1. Check question_scores column
        try:
            result = conn.execute(text("SELECT student_answer FROM question_scores LIMIT 1;"))
            print("  Column student_answer in question_scores exists and is queryable.")
        except Exception as e:
            print(f"  Error querying student_answer: {e}")
            
        # 2. Check student_answers table
        try:
            result = conn.execute(text("SELECT id FROM student_answers LIMIT 1;"))
            print("  Table student_answers table exists and is queryable.")
        except Exception as e:
            print(f"  Error querying student_answers table: {e}")

if __name__ == "__main__":
    verify_schema()
