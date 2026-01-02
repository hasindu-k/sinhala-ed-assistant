import sys
import os
from sqlalchemy import inspect

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import engine

def check_schema():
    inspector = inspect(engine)
    
    print("--- Schema Inspection ---")
    
    # Check Questions table
    if inspector.has_table("questions"):
        print("\nTable: questions")
        columns = inspector.get_columns("questions")
        col_names = [c['name'] for c in columns]
        print(f"Columns: {col_names}")
        if "paper_part" in col_names:
            print("✅ 'paper_part' column EXISTS.")
        else:
            print("❌ 'paper_part' column MISSING.")
    else:
        print("\n❌ Table 'questions' MISSING.")

    # Check SubQuestions table
    if inspector.has_table("sub_questions"):
        print("\nTable: sub_questions")
        columns = inspector.get_columns("sub_questions")
        col_names = [c['name'] for c in columns]
        print(f"Columns: {col_names}")
        if "parent_sub_question_id" in col_names:
            print("✅ 'parent_sub_question_id' column EXISTS.")
        else:
            print("❌ 'parent_sub_question_id' column MISSING.")
    else:
        print("\n❌ Table 'sub_questions' MISSING.")
    
if __name__ == "__main__":
    check_schema()
