import sys
import os
from uuid import UUID

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.shared.models.resource_file import ResourceFile
from app.shared.models.evaluation_session import EvaluationResource

def check_resource(resource_id_str):
    db = SessionLocal()
    try:
        if not resource_id_str:
            print("No resource ID provided.")
            return

        res_id = UUID(resource_id_str)
        print(f"Checking Resource ID: {res_id}")

        # 1. Check ResourceFile
        resource = db.query(ResourceFile).filter(ResourceFile.id == res_id).first()
        if resource:
            print(f"✅ FOUND in `resource_files`.")
            print(f"   Filename: {resource.original_filename}")
            print(f"   Source: {resource.source_type}")
            print(f"   Storage Path: {resource.storage_path}")
        else:
            print(f"❌ NOT FOUND in `resource_files`.")

        # 2. Check EvaluationResource
        eval_res = db.query(EvaluationResource).filter(EvaluationResource.resource_id == res_id).first()
        if eval_res:
             print(f"✅ FOUND in `evaluation_resources`. Session: {eval_res.evaluation_session_id}, Role: {eval_res.role}")
        else:
             print(f"❌ NOT FOUND in `evaluation_resources`.")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_resource("847c8c3b-7725-4c96-a61d-718964441bcd")
