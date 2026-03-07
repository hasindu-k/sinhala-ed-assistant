import json
import psycopg2

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
        data = {
            "er_id": str(res[0]),
            "total_score": float(res[1]) if res[1] else 0.0,
            "filename": res[2],
            "mapped_answers": res[3],
            "scores": []
        }
        
        cur.execute("""
            SELECT qs.question_id, qs.sub_question_id, qs.awarded_marks, qs.feedback 
            FROM question_scores qs
            WHERE qs.evaluation_result_id = %s
        """, (res[0],))
        
        for row in cur.fetchall():
            data["scores"].append({
                "question_id": str(row[0]) if row[0] else None,
                "sub_question_id": str(row[1]) if row[1] else None,
                "awarded_marks": float(row[2]) if row[2] is not None else 0.0,
                "feedback": row[3]
            })
            
        with open("student1_dump.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print("Dumped to student1_dump.json")
    else:
        print("Not found")

except Exception as e:
    print("Error:", e)
