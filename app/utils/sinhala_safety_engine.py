# app/utils/sinhala_safety_engine.py
 
import logging
import re
import numpy as np

logger = logging.getLogger(__name__)
 
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
    # logger.info("paramtered sources %s", source)
    src_concepts = extract_concepts(source)
    flagged = []
    
    logger.info("Source concepts extracted: %d", len(src_concepts))
    
    for sentence in re.split(r"[.!?]", generated):
        sentence = sentence.strip()
        
        logger.info("Analyzing sentence: %s", sentence)
        
        if not sentence:
            continue

        sent_concepts = extract_concepts(sentence)

        logger.info("Extracted concepts: %d", len(sent_concepts))
        # Skip very short or trivial sentences
        if len(sent_concepts) < 6:
            continue

        unseen = sent_concepts - src_concepts
        unseen_ratio = len(unseen) / len(sent_concepts)
        
        logger.info("Sentence: %s | Unseen ratio: %.2f", sentence, unseen_ratio)
        
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
                "unseen_ratio": round(unseen_ratio, 2),
                "concept_count": len(sent_concepts),
            })

    return flagged

from app.services.semantic_similarity_service import SemanticSimilarityService

def attach_evidence(
    flagged_sentences: list[dict],
    context: str
) -> list[dict]:
    """
    Optimized version that batches all similarity calculations.
    """
    if not flagged_sentences or not context:
        return flagged_sentences

    # Split context into sentences once
    context_sentences = [
        s.strip()
        for s in re.split(r"[.!?]", context)
        if len(s.strip()) > 10
    ]
    
    if not context_sentences:
        return flagged_sentences

    # Extract all flagged sentences
    flagged_texts = [item["sentence"] for item in flagged_sentences]
    
    # Get concept sets for all flagged sentences at once
    flagged_concepts = [extract_concepts(s) for s in flagged_texts]
    context_concepts = [extract_concepts(s) for s in context_sentences]
    
    # Batch compute all pairwise similarities at once
    # This makes only ONE model call instead of N*M calls
    similarity_matrix = SemanticSimilarityService.compute_pairwise_similarities(
        flagged_texts, 
        context_sentences
    )
    
    enriched = []
    
    for i, item in enumerate(flagged_sentences):
        # Get best matching context sentence from similarity matrix
        similarities = similarity_matrix[i]  # Row for this flagged sentence
        best_idx = int(np.argmax(similarities))
        best_similarity = float(similarities[best_idx])
        best_match = context_sentences[best_idx]
        
        # Calculate concept overlap
        sent_concepts = flagged_concepts[i]
        ctx_concepts = context_concepts[best_idx]
        
        if sent_concepts:
            concept_overlap = len(sent_concepts & ctx_concepts) / len(sent_concepts)
        else:
            concept_overlap = 0.0
        
        enriched.append({
            **item,
            "evidence": best_match,
            "semantic_similarity_score": round(best_similarity, 3),
            "concept_overlap": round(concept_overlap, 3),
        })
    
    return enriched