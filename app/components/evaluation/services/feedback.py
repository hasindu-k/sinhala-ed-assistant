# app/components/evaluation/services/feedback.py

from app.shared.ai.gemini_client import gemini_generate


# ------------------------------------------------------------
# SUBQUESTION FEEDBACK
# ------------------------------------------------------------
def generate_feedback_for_answer(qid: str, student_answer: str, score_details: dict, language: str):
    """
    Produces short, clear feedback tied to the student's content and the retrieved context.
    """

    chunks = " ".join(score_details["retrieved_context"])
    sem = score_details["semantic"]
    cov = score_details["coverage"]
    bm = score_details["bm25"]
    marks = score_details["final_score"]
    max_marks = score_details["max_score"]

    if language == "sinhala":
        prompt = f"""
ඔබ ගුරුවරයෙකු ලෙස සිසුවාගේ පිළිතුර සඳහා කෙටි, පැහැදිලි ප්‍රතිචාරයක් ලියන්න.  
ඉන් නොවෙයි: Markdown, code blocks, bullet points.

[ප්‍රශ්න ID]
{qid}

[සිසුවාගේ පිළිතුර]
{student_answer}

[පරිදි ග්‍රහණය කළ සම්බන්ධ කරුණු]
{chunks}

[ලකුණු]
{marks} / {max_marks}

[පද්ධතියේ විග්‍රහය]
Semantics = {sem}
Coverage = {cov}
BM25 = {bm}

සම්පූර්ණ ප්‍රතිචාරය සිංහලෙන් ලබාදෙන්න:
- පිළිතුරේ හොඳ කරුණු
- දිග වැඩිය යුතු කරුණු
- ප්‍රශ්නයට සම්බන්ධ නොවන කරුණු (ඇත්තෙන් තිබේ නම්)
- පසුගිය පිළිතුර සුදුසු ලෙස ඇගයීමට උදවු වන උපදෙස්
"""

    else:  # English
        prompt = f"""
Write a short, clear teacher-style feedback for the student’s answer.

[Question ID]
{qid}

[Student Answer]
{student_answer}

[Relevant Extracted Context]
{chunks}

[Marks]
{marks} / {max_marks}

[System Analysis]
Semantic: {sem}
Coverage: {cov}
BM25: {bm}

In 4–6 sentences explain:
- What was correct
- What was missing
- What should be improved
- How the student can score higher next time
"""

    return gemini_generate(prompt)
    


# ------------------------------------------------------------
# OVERALL FEEDBACK
# ------------------------------------------------------------
def generate_overall_feedback(results: dict, final_score: float, max_score: float, language: str):
    """
    Produces a summary feedback for the entire paper.
    """

    # Build a condensed performance summary
    performance = []

    for qid, r in results.items():
        performance.append(
            f"{qid}: {r.total_score}/{r.max_score} "
            f"(sem={r.semantic_score}, cov={r.coverage_score}, bm25={r.bm25_score})"
        )

    perf_text = "\n".join(performance)

    if language == "sinhala":
        prompt = f"""
ඔබ ගුරුවරයෙකු ලෙස සිසුවාගේ මුළු ප්‍රශ්න පත්‍රය සඳහා සාරාංශ ප්‍රතිචාරයක් ලියන්න.  
Markdown, bullet points, code blocks භාවිතා නොකරන්න.

[මුළු ලකුණු]
{final_score} / {max_score}

[විග්‍රහ]
{perf_text}

ප්‍රතිචාරයේ අන්තර්ගතය:
- මුළු ප්‍රශ්න පත්‍රයේ ශක්තිමත් කරුණු
- අඩුපාඩු සහ වැඩිදියුණු කළ යුතු කරුණු
- පසුගිය පිළිතුර වැඩි දියුණු කරගැනීමට උපදෙස්
දිග අවුරුදු දෙකකට ඉදිරියට අධ්‍යයනයට බලපෑම් ඇති නොවන ලෙස කෙටි හා පැහැදිලිව ලියන්න.
"""

    else:
        prompt = f"""
Write an overall evaluation summary for the student's performance.

[Final Score]
{final_score} / {max_score}

[Breakdown]
{perf_text}

Your summary must include:
- strengths
- weaknesses
- suggested improvements
- general study guidance

Write clearly in 5–7 sentences.
"""

    return gemini_generate(prompt)
