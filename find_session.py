import os
import psycopg2

try:
    conn = psycopg2.connect("postgresql://miyuri:Miyuri123@localhost:5433/sinhala_learn")
    cur = conn.cursor()
    
    query = """
    SELECT ad.id, ad.evaluation_session_id, rd.original_filename
    FROM answer_documents ad
    JOIN resource_files rd ON ad.resource_id = rd.id
    WHERE rd.original_filename ILIKE '%student 1%' OR rd.original_filename ILIKE '%student 2%'
    ORDER BY ad.created_at DESC LIMIT 5;
    """
    cur.execute(query)
    for row in cur.fetchall():
        print(row)
        
    cur.close()
    conn.close()
except Exception as e:
    print("Error:", e)
