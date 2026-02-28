
import os
import psycopg2
from urllib.parse import urlparse

DATABASE_URL = "postgresql://miyuri:Miyuri123@localhost:5433/sinhala_learn"

def check_constraints():
    uri = urlparse(DATABASE_URL)
    conn = psycopg2.connect(
        dbname=uri.path[1:],
        user=uri.username,
        password=uri.password,
        host=uri.hostname,
        port=uri.port
    )
    cur = conn.cursor()
    
    query = """
    SELECT
        tc.table_name, 
        kcu.column_name, 
        rc.delete_rule,
        tc.constraint_name
    FROM 
        information_schema.table_constraints AS tc 
        JOIN information_schema.key_column_usage AS kcu
          ON tc.constraint_name = kcu.constraint_name
          AND tc.table_schema = kcu.table_schema
        JOIN information_schema.referential_constraints AS rc
          ON tc.constraint_name = rc.constraint_name
          AND tc.table_schema = rc.constraint_schema
    WHERE tc.constraint_type = 'FOREIGN KEY' 
      AND (
        (tc.table_name = 'answer_documents' AND kcu.column_name = 'resource_id') OR
        (tc.table_name = 'evaluation_resources' AND kcu.column_name = 'resource_id') OR
        (tc.table_name = 'session_resources' AND kcu.column_name = 'resource_id') OR
        (tc.table_name = 'resource_chunks' AND kcu.column_name = 'resource_id') OR
        (tc.table_name = 'evaluation_results' AND kcu.column_name = 'answer_document_id') OR
        (tc.table_name = 'question_scores' AND kcu.column_name = 'evaluation_result_id')
      );
    """
    
    cur.execute(query)
    rows = cur.fetchall()
    
    with open("constraints_output.txt", "w") as f:
        f.write(f"{'Table':<25} | {'Column':<20} | {'Delete Rule':<15} | {'Constraint Name'}\n")
        f.write("-" * 80 + "\n")
        for row in rows:
            f.write(f"{row[0]:<25} | {row[1]:<20} | {row[2]:<15} | {row[3]}\n")
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    try:
        check_constraints()
    except Exception as e:
        with open("constraints_output.txt", "w") as f:
            f.write(f"Error: {e}")
