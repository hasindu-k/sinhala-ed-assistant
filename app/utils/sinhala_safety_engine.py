# app/utils/sinhala_safety_engine.py
 
import re
 
STOPWORDS = {
    "කරන","යන්න","සඳහා","පිළිබඳ","ඇත","වැනි","මෙම","බව","සමඟ"
}
 
def extract_concepts(text: str) -> set:
    words = re.findall(r"[අ-෴]{3,}", text)
    return set(w for w in words if w not in STOPWORDS)
 
def concept_map_check(generated: str, source: str):
    src = extract_concepts(source)
    gen = extract_concepts(generated)
    return {
        "missing_concepts": list(src - gen),
        "extra_concepts": list(gen - src)
    }
 
def detect_misconceptions(generated: str, source: str):
    src = extract_concepts(source)
    flagged = []
 
    for sentence in re.split(r"[.!?]", generated):
        new = extract_concepts(sentence) - src
        if len(new) >= 20:
            flagged.append(sentence.strip())
 
    return flagged
 