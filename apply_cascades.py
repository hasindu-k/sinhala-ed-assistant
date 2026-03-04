
import os
import psycopg2
from urllib.parse import urlparse

DATABASE_URL = "postgresql://miyuri:Miyuri123@localhost:5433/sinhala_learn"

def apply_migrations():
    uri = urlparse(DATABASE_URL)
    conn = psycopg2.connect(
        dbname=uri.path[1:],
        user=uri.username,
        password=uri.password,
        host=uri.hostname,
        port=uri.port
    )
    conn.autocommit = False
    cur = conn.cursor()
    
    # List of changes: (Table, Constraint, Column, TargetTable)
    changes = [
        ('resource_chunks', 'resource_chunks_resource_id_fkey', 'resource_id', 'resource_files'),
        ('session_resources', 'session_resources_resource_id_fkey', 'resource_id', 'resource_files'),
        ('evaluation_resources', 'evaluation_resources_resource_id_fkey', 'resource_id', 'resource_files'),
        ('answer_documents', 'answer_documents_resource_id_fkey', 'resource_id', 'resource_files'),
        ('evaluation_results', 'evaluation_results_answer_document_id_fkey', 'answer_document_id', 'answer_documents'),
        ('question_scores', 'question_scores_evaluation_result_id_fkey', 'evaluation_result_id', 'evaluation_results')
    ]
    
    try:
        for table, constraint, column, target in changes:
            print(f"Updating {table}.{column}...")
            # Drop constraint
            cur.execute(f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {constraint};")
            # Add constraint with ON DELETE CASCADE
            cur.execute(f"""
                ALTER TABLE {table} 
                ADD CONSTRAINT {constraint} 
                FOREIGN KEY ({column}) 
                REFERENCES {target}(id) 
                ON DELETE CASCADE;
            """)
        
        conn.commit()
        print("Successfully applied all schema changes.")
    except Exception as e:
        conn.rollback()
        print(f"Error applying migrations: {e}")
        raise
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    apply_migrations()
