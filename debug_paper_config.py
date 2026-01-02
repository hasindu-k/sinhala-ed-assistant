import sys
import os
from sqlalchemy import inspect, text

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import engine

def check_paper_config():
    inspector = inspect(engine)
    
    print("--- Table Inspection: paper_config ---")
    
    if inspector.has_table("paper_config"):
        print("✅ Table `paper_config` EXISTS.")
        
        columns = inspector.get_columns("paper_config")
        col_names = [c['name'] for c in columns]
        print(f"Columns: {col_names}")
        
        required_cols = ["paper_part", "subject_name", "medium", "weightage", "selection_rules", "is_confirmed"]
        missing = [col for col in required_cols if col not in col_names]
        
        if missing:
             print(f"❌ Missing Columns: {missing}")
             print("Conclusion: The table exists but is OUTDATED. You MUST runs the migration.")
        else:
             print("✅ All required columns present.")
             print("Conclusion: The table is already up to date. You can SKIP the migration.")

        # Try to check ownership by attempting a dummy write (indirect check)
        # Verify permissions
        try:
             with engine.connect() as conn:
                 # This won't check OWNER but write access. Owner check is hard without pg_class logic.
                 print(f"Current DB User: {engine.url.username}")
    else:
        print("❌ Table `paper_config` DOES NOT EXIST.")

if __name__ == "__main__":
    check_paper_config()
