import google.generativeai as genai

CLASSIFY_PROMPT = """
You are a document classification assistant for Sinhala educational materials.

Classify the following text into exactly ONE of the following categories:
- term_test
- teacher_guide
- student_notes
- past_paper
- answer_scheme
- textbook

Only respond with the category name. No explanation.

TEXT:
{content}
"""

def classify_document(text: str) -> str:
    prompt = CLASSIFY_PROMPT.format(content=text[:5000])  # avoid giant prompt
    
    response = genai.generate_text(
        model="models/gemini-1.5-flash",
        prompt=prompt,
        max_output_tokens=10,
    )
    
    label = response.text.strip().lower()

    # fallback safety
    allowed = {
        "term_test",
        "teacher_guide",
        "student_notes",
        "past_paper",
        "answer_scheme",
        "textbook"
    }

    return label if label in allowed else "unknown"
