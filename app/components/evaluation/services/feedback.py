from app.shared.ai.gemini_client import gemini_generate


# ------------------------------------------------------------
# helper: flatten dict feedback into clean readable text
# ------------------------------------------------------------
def _format_feedback_block(data: dict, language: str) -> str:
    if not isinstance(data, dict):
        return str(data)

    # Sinhala version
    if language == "sinhala":
        return (
            f"🔹 ශක්තිමත් කරුණු: {data.get('strengths', '')}\n"
            f"🔹 දුර්වලතා: {data.get('weaknesses', '')}\n"
            f"🔹 වැඩිදියුණු කළ යුතු කරුණු: {data.get('improvements', '')}\n"
            f"🔹 ඉදිරියට ලකුණු වැඩි කරගැනීම: {data.get('next_steps', '')}"
        )

    # English version
    return (
        f"Strengths: {data.get('strengths', '')}\n"
        f"Weaknesses: {data.get('weaknesses', '')}\n"
        f"Improvements: {data.get('improvements', '')}\n"
        f"Next Steps: {data.get('next_steps', '')}"
    )


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

    # Sinhala prompt
    if language == "sinhala":
        prompt = f"""
ඔබ ගුරුවරයෙකු ලෙස සිසුවාගේ පිළිතුර සඳහා සරල සංවිධානය කළ ප්‍රතිචාරයක් ලබා දෙන්න.
Markdown හෝ bullet points භාවිතා නොකරන්න.

ප්‍රශ්න ID: {qid}
ලකුණු: {marks} / {max_marks}

සිසුවාගේ පිළිතුර:
{student_answer}

අදාළ කරුණු:
{chunks}

Sem={sem}, Coverage={cov}, BM25={bm}

ඔබ ලබා දිය යුතු විග්‍රහය:
strengths, weaknesses, improvements, next_steps

JSON ආකාරයේ structured feedback දෙන්න:
{{ "strengths":"", "weaknesses":"", "improvements":"", "next_steps":"" }}
"""

    # English prompt
    else:
        prompt = f"""
Give structured teacher feedback as JSON only.

Do not use markdown.

Question ID: {qid}
Marks: {marks} / {max_marks}

Student Answer:
{student_answer}

Relevant Context:
{chunks}

Sem={sem}, Coverage={cov}, BM25={bm}

Provide JSON with:
strengths, weaknesses, improvements, next_steps

Format:
{{ "strengths":"...", "weaknesses":"...", "improvements":"...", "next_steps":"..." }}
"""

    raw = gemini_generate(prompt).strip()

    # Try parsing JSON-like output into dict
    try:
        import json

        data = json.loads(raw)
        return _format_feedback_block(data, language)

    except Exception:
        # if not JSON, return original text as safe fallback
        return raw


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
සිසුවාගේ මුළු ප්‍රශ්න පත්‍රය සඳහා structured සාරාංශ ප්‍රතිචාරයක් JSON ආකාරයෙන් ලබා දෙන්න.
Markdown නොකරන්න.

මුළු ලකුණු: {final_score} / {max_score}

විස්තර:
{perf_text}

JSON format:
{{
 "strengths":"",
 "weaknesses":"",
 "improvements":"",
 "advice":""
}}
"""
    else:
        prompt = f"""
Give an overall evaluation summary as structured JSON.
No markdown.

Final Score: {final_score} / {max_score}

Breakdown:
{perf_text}

JSON format:
{{
 "strengths":"...",
 "weaknesses":"...",
 "improvements":"...",
 "advice":"..."
}}
"""

    raw = gemini_generate(prompt).strip()

    try:
        import json

        data = json.loads(raw)

        # Sinhala or English formatted text output
        if language == "sinhala":
            return (
                f"🔷 ශක්තිමත් කරුණු: {data.get('strengths', '')}\n"
                f"🔷 දුර්වලතා: {data.get('weaknesses', '')}\n"
                f"🔷 වැඩිදියුණු කිරීම්: {data.get('improvements', '')}\n"
                f"🔷 ඉදිරියට උපදෙස්: {data.get('advice', '')}"
            )

        else:
            return (
                f"Strengths: {data.get('strengths', '')}\n"
                f"Weaknesses: {data.get('weaknesses', '')}\n"
                f"Improvements: {data.get('improvements', '')}\n"
                f"Advice: {data.get('advice', '')}"
            )

    except Exception:
        return raw
