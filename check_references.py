import psycopg2
import json

try:
    conn = psycopg2.connect("postgresql://miyuri:Miyuri123@localhost:5433/sinhala_learn")
    cur = conn.cursor()
    
    query = """
    SELECT q.id, q.question_number, q.correct_answer
    FROM questions q
    WHERE q.id IN (
        SELECT question_id FROM question_scores WHERE evaluation_result_id = 'e331d92d-9705-4e83-88f9-02b1925ce520' AND question_id IS NOT NULL
    )
    ORDER BY q.question_number;
    """
    cur.execute(query)
    qs = cur.fetchall()
    
    out = {}
    for q in qs:
        out[str(q[0])] = {"num": q[1], "ans": q[2]}
        
    query_sq = """
    SELECT sq.id, sq.label, sq.correct_answer
    FROM sub_questions sq
    WHERE sq.id IN (
        SELECT sub_question_id FROM question_scores WHERE evaluation_result_id = 'e331d92d-9705-4e83-88f9-02b1925ce520' AND sub_question_id IS NOT NULL
    )
    ORDER BY sq.label;
    """
    cur.execute(query_sq)
    sqs = cur.fetchall()
    
    for sq in sqs:
        out[str(sq[0])] = {"label": sq[1], "ans": sq[2]}

    with open("check_references.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    cur.close()
    conn.close()
except Exception as e:
    print("Error:", e)
