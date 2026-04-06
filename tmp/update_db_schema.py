
import sys
import os
from sqlalchemy import create_engine, text

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.config import settings

def apply_schema_updates():
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as conn:
        print("Applying schema updates...")
        
        # 1. Add student_answer column to question_scores if it doesn't exist
        try:
            print("Checking for student_answer column in question_scores...")
            conn.execute(text("ALTER TABLE question_scores ADD COLUMN IF NOT EXISTS student_answer TEXT;"))
            conn.commit()
            print("  Column student_answer ensured.")
        except Exception as e:
            print(f"  Error adding column: {e}")
            
        # 2. Create student_answers table if it doesn't exist
        try:
            print("Creating student_answers table if it doesn't exist...")
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS student_answers (
                id UUID PRIMARY KEY,
                answer_document_id UUID NOT NULL REFERENCES answer_documents(id) ON DELETE CASCADE,
                question_id UUID REFERENCES questions(id),
                sub_question_id UUID REFERENCES sub_questions(id),
                answer_text TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS ix_student_answers_answer_document_id ON student_answers (answer_document_id);
            """
            conn.execute(text(create_table_sql))
            conn.commit()
            print("  Table student_answers ensured.")
        except Exception as e:
            print(f"  Error creating table: {e}")

    print("\nSchema updates completed (idempotent).")

if __name__ == "__main__":
    apply_schema_updates()
