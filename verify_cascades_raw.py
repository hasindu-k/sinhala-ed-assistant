
import psycopg2
from urllib.parse import urlparse
import uuid
import os

DATABASE_URL = "postgresql://miyuri:Miyuri123@localhost:5433/sinhala_learn"

def verify_cascades_raw():
    uri = urlparse(DATABASE_URL)
    conn = psycopg2.connect(
        dbname=uri.path[1:],
        user=uri.username,
        password=uri.password,
        host=uri.hostname,
        port=uri.port
    )
    conn.autocommit = True
    cur = conn.cursor()
    
    try:
        # Get a user
        cur.execute("SELECT id FROM users LIMIT 1")
        user = cur.fetchone()
        if not user:
            print("No user found.")
            return
        user_id = user[0]
        
        # 1. Insert Resource
        res_id = str(uuid.uuid4())
        print(f"Creating test resource: {res_id}")
        cur.execute(
            "INSERT INTO resource_files (id, user_id, original_filename, storage_path) VALUES (%s, %s, %s, %s)",
            (res_id, user_id, "cascade_test.txt", "uploads/cascade_test.txt")
        )
        
        # 2. Insert Session and Evaluation data
        session_id = str(uuid.uuid4())
        cur.execute(
            "INSERT INTO chat_sessions (id, user_id, mode, channel, title) VALUES (%s, %s, %s, %s, %s)",
            (session_id, user_id, "evaluation", "text", "Test Session")
        )

        
        cur.execute(
            "INSERT INTO session_resources (session_id, resource_id, label) VALUES (%s, %s, %s)",
            (session_id, res_id, "answer_script")
        )
        
        eval_id = str(uuid.uuid4())
        cur.execute(
            "INSERT INTO evaluation_sessions (id, session_id, status) VALUES (%s, %s, %s)",
            (eval_id, session_id, "pending")
        )
        
        cur.execute(
            "INSERT INTO evaluation_resources (id, evaluation_session_id, resource_id, role) VALUES (%s, %s, %s, %s)",
            (str(uuid.uuid4()), eval_id, res_id, "answer_script")
        )
        
        doc_id = str(uuid.uuid4())
        cur.execute(
            "INSERT INTO answer_documents (id, evaluation_session_id, resource_id) VALUES (%s, %s, %s)",
            (doc_id, eval_id, res_id)
        )
        
        res_res_id = str(uuid.uuid4())
        cur.execute(
            "INSERT INTO evaluation_results (id, answer_document_id, total_score) VALUES (%s, %s, %s)",
            (res_res_id, doc_id, 80.0)
        )
        
        cur.execute(
            "INSERT INTO question_scores (id, evaluation_result_id, awarded_marks) VALUES (%s, %s, %s)",
            (str(uuid.uuid4()), res_res_id, 10.0)
        )
        
        print("Test data inserted successfully.")
        
        # 3. Delete Resource
        print("Deleting resource...")
        cur.execute("DELETE FROM resource_files WHERE id = %s", (res_id,))
        
        # 4. Verify everything is gone
        print("Checking for orphaned records...")
        
        checks = [
            ("session_resources", "resource_id", res_id),
            ("evaluation_resources", "resource_id", res_id),
            ("answer_documents", "resource_id", res_id),
            ("evaluation_results", "answer_document_id", doc_id),
            ("question_scores", "evaluation_result_id", res_res_id)
        ]
        
        all_gone = True
        for table, col, val in checks:
            cur.execute(f"SELECT COUNT(*) FROM {table} WHERE {col} = %s", (val,))
            count = cur.fetchone()[0]
            if count > 0:
                print(f"FAILED: {count} records remain in {table}")
                all_gone = False
            else:
                print(f"Verified: {table} cleaned up.")
                
        if all_gone:
            print("SUCCESS: Database cascades are working perfectly.")
            
        # Cleanup session and evaluation (the resource deletion removed the links, but not the session itself)
        cur.execute("DELETE FROM evaluation_sessions WHERE id = %s", (eval_id,))
        cur.execute("DELETE FROM chat_sessions WHERE id = %s", (session_id,))
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    verify_cascades_raw()
