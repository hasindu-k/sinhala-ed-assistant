# app/utils/sinhala_safety_engine.py
 
import re
 
STOPWORDS = {
    "කරන", "යන්න", "සඳහන්", "පිළිබඳ", "කෙරෙයි", "වන්නේ", "ඇත", "වැනි", 
    "මෙම", "පමණක්", "දක්වයි", "හෝ", "සමඟ", "කටයුතු", "ඉතා", "බව", 
    "ගෙන", "සඳහා", "විස්තර", "කියවීමට", "එක", "දෙක", "තුන", "හතර",
    "පහ", "හය", "හත", "අට", "නවය", "දහය", "ඒ", "අ", "ඔ", "ඕ"
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
 