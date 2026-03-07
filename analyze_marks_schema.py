import psycopg2

try:
    conn = psycopg2.connect("postgresql://miyuri:Miyuri123@localhost:5433/sinhala_learn")
    cur = conn.cursor()
    
    query = """
    SELECT id 
    FROM question_papers
    LIMIT 1;
    """
    cur.execute(query)
    papers = cur.fetchall()
    
    for p in papers:
        print(f"Paper: {p[0]}")
        cur.execute("SELECT id, label, max_marks FROM questions WHERE question_paper_id = %s ORDER BY label", (p[0],))
        qs = cur.fetchall()
        total_p1 = 0
        total_p2 = 0
        for q in qs:
            cur.execute("SELECT id, label, max_marks FROM sub_questions WHERE question_id = %s ORDER BY label", (q[0],))
            sqs = cur.fetchall()
            q_max = q[2] if q[2] else 0
            
            sq_total = sum((int(sq[2]) if sq[2] else 0) for sq in sqs) if sqs else float(q_max)
            
            if sqs:
                total_p2 += sq_total
            else:
                total_p1 += sq_total
        print(f"Total P1 (if all counted): {total_p1}")
        print(f"Total P2 (if all counted): {total_p2}")
        print(f"Total if 5 Best of P2 (assume 12 each): {total_p1 + (5*12)}")
        
    cur.close()
    conn.close()
except Exception as e:
    print("Error:", e)
