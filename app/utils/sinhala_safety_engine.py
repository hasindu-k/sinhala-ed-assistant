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
    """
    Relative, explainable misconception detection.

    For each sentence in the generated answer:
    - Extract concepts
    - Compare against source concepts
    - Flag only if a large proportion is unsupported
    - Assign severity based on unseen ratio

    Returns:
        List of dicts:
        [
          {
            "sentence": "...",
            "severity": "low|medium|high",
            "unseen_ratio": float
          }
        ]
    """
    src_concepts = extract_concepts(source)
    flagged = []

    for sentence in re.split(r"[.!?]", generated):
        sentence = sentence.strip()
        if not sentence:
            continue

        sent_concepts = extract_concepts(sentence)

        # Skip very short or trivial sentences
        if len(sent_concepts) < 6:
            continue

        unseen = sent_concepts - src_concepts
        unseen_ratio = len(unseen) / len(sent_concepts)

        # Only flag when majority is unsupported
        if unseen_ratio >= 0.5:
            if unseen_ratio >= 0.75:
                severity = "high"
            elif unseen_ratio >= 0.6:
                severity = "medium"
            else:
                severity = "low"

            flagged.append({
                "sentence": sentence,
                "severity": severity,
                "unseen_ratio": round(unseen_ratio, 2)
            })

    return flagged

def attach_evidence(
    flagged_sentences: list[dict],
    context: str
) -> list[dict]:
    """
    Attach supporting or conflicting evidence from context
    to each flagged sentence.
    """

    if not flagged_sentences or not context:
        return flagged_sentences

    # Split context into sentences
    context_sentences = [
        s.strip()
        for s in re.split(r"[.!?]", context)
        if len(s.strip()) > 10
    ]

    context_concepts = [
        extract_concepts(s) for s in context_sentences
    ]

    enriched = []

    for item in flagged_sentences:
        sentence = item["sentence"]
        sent_concepts = extract_concepts(sentence)

        best_match = None
        best_overlap = 0

        for ctx_sentence, ctx_concepts in zip(context_sentences, context_concepts):
            overlap = len(sent_concepts & ctx_concepts)
            if overlap > best_overlap:
                best_overlap = overlap
                best_match = ctx_sentence

        enriched.append({
            **item,
            "evidence": best_match
        })

    return enriched
