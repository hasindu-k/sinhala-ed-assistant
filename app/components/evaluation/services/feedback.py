# app/components/evaluation/services/feedback.py

from app.shared.ai.gemini_client import gemini_generate


# ------------------------------------------------------------
# SUBQUESTION FEEDBACK
# ------------------------------------------------------------
def generate_feedback_for_answer(qid: str, student_answer: str, score_details: dict, language: str):

    chunks = " ".join(score_details["retrieved_context"])
    sem = score_details["semantic"]
    cov = score_details["coverage"]
    bm = score_details["bm25"]
    marks = score_details["final_score"]
    max_marks = score_details["max_score"]

    if language == "sinhala":
        prompt = f"""
ඔබ ගුරුවරයෙකු ලෙස සිසුවාගේ පිළිතුර සඳහා කෙටි ප්‍රතිචාරයක් ලබා දෙන්න.
Markdown හෝ bullet points භාවිතා නොකරන්න.

ප්‍රශ්න ID: {qid}
ලකුණු: {marks} / {max_marks}

සිසුවාගේ පිළිතුර:
{student_answer}

පද්ධතිය හඳුන්වාගත් සම්බන්ධ කරුණු:
{chunks}

Semantics = {sem}
Coverage = {cov}
BM25 = {bm}

පිළිතුරේ හොඳ කරුණු, දුර්වලතා, වැඩිදියුණු කළ යුතු කරුණු,
ඉදිරියට ලකුණු වැඩි කරගන්නේ කෙසේද යන්න පැහැදිලිව වාර්තා කරන්න.
"""

    else:
        prompt = f"""
Give a short teacher-style feedback for the student's answer.
Do not use markdown.

Question ID: {qid}
Marks: {marks} / {max_marks}

Student Answer:
{student_answer}

Relevant Context:
{chunks}

Semantic={sem}, Coverage={cov}, BM25={bm}

Explain briefly:
- What is strong
- What is missing
- What needs improvement
- How to score higher next time
"""

    return gemini_generate(prompt).strip()



# ------------------------------------------------------------
# OVERALL FEEDBACK
# ------------------------------------------------------------
def generate_overall_feedback(results: dict, final_score: float, max_score: float, language: str):

    perf_lines = []
    for qid, r in results.items():
        perf_lines.append(
            f"{qid}: {r.total_score}/{r.max_score} (sem={r.semantic_score}, cov={r.coverage_score}, bm25={r.bm25_score})"
        )
    perf_text = "\n".join(perf_lines)

    if language == "sinhala":
        prompt = f"""
සිසුවාගේ ප්‍රශ්න පත්‍රය සඳහා සාරාංශ ප්‍රතිචාරයක් ලබා දෙන්න.
Markdown භාවිතා නොකරන ලෙස යෝජනා කරයි.

මුළු ලකුණු: {final_score} / {max_score}

විග්‍රහ:
{perf_text}

සාරාංශයේ අන්තර්ගතය:
- ශක්තිමත් කරුණු
- වැඩිදියුණු කළ යුතු කරුණු
- ඉදිරියට කියවීමේ උපදෙස්
"""

    else:
        prompt = f"""
Write an overall evaluation summary.
No markdown.

Final Score: {final_score} / {max_score}

Breakdown:
{perf_text}

Include:
Strengths, weaknesses, improvements, general study advice.
"""

    return gemini_generate(prompt).strip()
