
import sys
import os
from sqlalchemy import create_engine, text

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.config import settings

def check_latest_data():
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as conn:
        print("Checking latest EvaluationResults and QuestionScores...")
        
        # 1. Get the latest EvaluationResult
        result = conn.execute(text("SELECT id, evaluated_at FROM evaluation_results ORDER BY evaluated_at DESC LIMIT 1;")).fetchone()
        if not result:
            print("No evaluation results found.")
            return
            
        latest_eval_id = result[0]
        eval_time = result[1]
        print(f"Latest Evaluation ID: {latest_eval_id} (at {eval_time})")
        
        # 2. Check QuestionScores for this evaluation
        print(f"\nQuestionScores for {latest_eval_id}:")
        scores = conn.execute(text(f"SELECT question_id, awarded_marks, student_answer FROM question_scores WHERE evaluation_result_id = '{latest_eval_id}';")).fetchall()
        for s in scores:
            print(f"  Q_ID: {s[0]} | Marks: {s[1]} | Answer: {s[2]}")
            
        # 3. Check StudentAnswers table
        print(f"\nLatest StudentAnswers entries:")
        student_ans = conn.execute(text("SELECT question_id, answer_text, created_at FROM student_answers ORDER BY created_at DESC LIMIT 5;")).fetchall()
        for sa in student_ans:
            print(f"  Q_ID: {sa[0]} | Text: {sa[1]} | Created: {sa[2]}")

if __name__ == "__main__":
    check_latest_data()
