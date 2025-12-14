#app/components/text_qa_summary/utils/safety.py
import re

# Sinhala stopwords (ignored concepts)
STOPWORDS = {
    "කරන", "යන්න", "සඳහන්", "පිළිබඳ", "කෙරෙයි", "වන්නේ", "ඇත", "වැනි", 
    "මෙම", "පමණක්", "දක්වයි", "හෝ", "සමඟ", "කටයුතු", "ඉතා", "බව", 
    "ගෙන", "සඳහා", "විස්තර", "කියවීමට"
}


def extract_concepts(text: str) -> set:
    """Extract Sinhala words longer than 3 chars; ignore functional words."""
    words = re.findall(r"[අ-෴]{3,}", text)
    return {w for w in words if w not in STOPWORDS}


def concept_map_check(generated: str, source: str) -> tuple:
    src = extract_concepts(source)
    gen = extract_concepts(generated)

    extra = list(gen - src)
    missing = list(src - gen)

    # SAFE THRESHOLD: allow up to 20 unmatched Sinhala words
    is_valid = len(extra) <= 20
    return is_valid, missing, extra


def detect_misconceptions(generated: str, source: str) -> list:
    """Only flag sentences with EXTREME unrelated content."""
    src = extract_concepts(source)
    sentences = re.split(r"[.!?]", generated)

    flagged = []
    for s in sentences:
        if len(s.strip()) < 5:
            continue

        s_concepts = extract_concepts(s)
        new = s_concepts - src

        # Only detect hallucination if large cluster appears
        if len(new) >= 20:  # MEDIUM SAFETY
            flagged.append({"sentence": s.strip(), "new": list(new)})

    return flagged


def hybrid_clean(text: str, flagged: list) -> str:
    """Remove ONLY the extreme hallucinated sentences."""
    if not flagged:
        return text

    lines = text.split("\n")
    cleaned = []

    for line in lines:
        remove = False
        for f in flagged:
            if f["sentence"] in line:
                remove = True
                break
        if not remove:
            cleaned.append(line)

    return "\n".join(cleaned)