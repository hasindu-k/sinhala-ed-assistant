import os
import psycopg2
import json

try:
    conn = psycopg2.connect("postgresql://miyuri:Miyuri123@localhost:5433/sinhala_learn")
    cur = conn.cursor()
    
    query = """
    SELECT er.id, er.total_score, rd.original_filename, ad.mapped_answers 
    FROM evaluation_results er
    JOIN answer_documents ad ON er.answer_document_id = ad.id
    JOIN resource_files rd ON ad.resource_id = rd.id
    WHERE rd.original_filename ILIKE '%student 1%'
    ORDER BY er.evaluated_at DESC LIMIT 1;
    """
    cur.execute(query)
    res = cur.fetchone()
    if res:
        print(f"Latest Student 1 Result: ER_ID={res[0]}, Score={res[1]}, File={res[2]}")
        
        mapped_answers = res[3]
        print(f"Mapped Answers keys: {len(mapped_answers)}")
        
        cur.execute("""
            SELECT qs.question_id, qs.sub_question_id, qs.awarded_marks, qs.feedback 
            FROM question_scores qs
            WHERE qs.evaluation_result_id = %s
            ORDER BY qs.question_id, qs.sub_question_id
        """, (res[0],))
        scores = cur.fetchall()
        print("\nScores:")
        for s in scores[:10]:
            print(f"Q_ID={s[0]}, SQ_ID={s[1]}, Marks={s[2]}")
            
    else:
        print("No student 1 result found.")
        
    cur.close()
    conn.close()
except Exception as e:
    print("Error:", e)
