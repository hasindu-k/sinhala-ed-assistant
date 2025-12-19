# app/components/text_qa_summary/utils/safety.py
import re
from typing import List, Dict, Tuple, Set

# Sinhala stopwords (ignored concepts)
STOPWORDS = {
    "කරන", "යන්න", "සඳහන්", "පිළිබඳ", "කෙරෙයි", "වන්නේ", "ඇත", "වැනි", 
    "මෙම", "පමණක්", "දක්වයි", "හෝ", "සමඟ", "කටයුතු", "ඉතා", "බව", 
    "ගෙන", "සඳහා", "විස්තර", "කියවීමට", "එක", "දෙක", "තුන", "හතර",
    "පහ", "හය", "හත", "අට", "නවය", "දහය", "ඒ", "අ", "ඔ", "ඕ"
}


def extract_concepts(text: str) -> Set[str]:
    """Extract Sinhala words longer than 2 chars; ignore functional words."""
    # Find all Sinhala words (including compound words)
    words = re.findall(r"[අ-෴]{2,}(?:[ා-෴]*)?", text)
    
    # Filter stopwords and very common words
    filtered = {
        w for w in words 
        if w not in STOPWORDS and len(w) >= 2
    }
    
    return filtered


def concept_map_check(generated: str, source: str, grade: str = "9-11") -> Tuple[bool, List[str], List[str]]:
    """
    Check if generated text stays faithful to source, with grade-specific allowances.
    """
    src = extract_concepts(source)
    gen = extract_concepts(generated)

    extra = list(gen - src)
    missing = list(src - gen)
    
    # Grade-specific thresholds for concept faithfulness
    grade_thresholds = {
        "6-8": {"extra_allowed": 30, "missing_allowed": 0.8},  # 80% can be missing (simplification)
        "9-11": {"extra_allowed": 20, "missing_allowed": 0.7},  # 70% can be missing
        "12-13": {"extra_allowed": 15, "missing_allowed": 0.6},  # 60% can be missing
        "university": {"extra_allowed": 10, "missing_allowed": 0.5}  # 50% can be missing
    }
    
    thresholds = grade_thresholds.get(grade, grade_thresholds["9-11"])
    
    # Check extra concepts
    extra_valid = len(extra) <= thresholds["extra_allowed"]
    
    # Check missing concepts (allow some for simplification in lower grades)
    missing_threshold = len(src) * thresholds["missing_allowed"]
    missing_valid = len(missing) <= missing_threshold
    
    is_valid = extra_valid and missing_valid
    
    if not is_valid:
        print(f"[SAFETY] Grade {grade}: Safety check failed")
        print(f"  - Extra concepts: {len(extra)} > {thresholds['extra_allowed']}" if not extra_valid else "")
        print(f"  - Missing concepts: {len(missing)} > {missing_threshold}" if not missing_valid else "")
    
    return is_valid, missing, extra


def detect_misconceptions(generated: str, source: str, grade: str = "9-11") -> List[Dict]:
    """
    Detect misconceptions with grade-specific sensitivity.
    """
    src = extract_concepts(source)
    sentences = re.split(r"[.!?]", generated)
    
    flagged = []
    
    for s in sentences:
        s = s.strip()
        if len(s) < 10:  # Increased minimum length
            continue
        
        s_concepts = extract_concepts(s)
        new_concepts = s_concepts - src
        
        # Only flag if there are MANY new concepts (likely hallucination)
        if new_concepts:
            # Calculate ratio of new to total concepts in sentence
            total_concepts = len(s_concepts)
            if total_concepts > 0:
                new_ratio = len(new_concepts) / total_concepts
                
                # Different thresholds for different grades
                if grade == "6-8" and new_ratio > 0.4:  # 40% new concepts
                    flagged.append({
                        "sentence": s,
                        "new_concepts": list(new_concepts)[:5],
                        "reason": f"High ratio of new concepts ({new_ratio:.2f}) for grade 6-8"
                    })
                elif grade == "9-11" and new_ratio > 0.5:  # 50% new concepts
                    flagged.append({
                        "sentence": s,
                        "new_concepts": list(new_concepts)[:5],
                        "reason": f"High ratio of new concepts ({new_ratio:.2f}) for grade 9-11"
                    })
                elif grade == "12-13" and new_ratio > 0.6:  # 60% new concepts
                    flagged.append({
                        "sentence": s,
                        "new_concepts": list(new_concepts)[:5],
                        "reason": f"High ratio of new concepts ({new_ratio:.2f}) for academic level"
                    })
                elif grade == "university" and new_ratio > 0.7:  # 70% new concepts
                    flagged.append({
                        "sentence": s,
                        "new_concepts": list(new_concepts)[:5],
                        "reason": f"High ratio of new concepts ({new_ratio:.2f}) for university level"
                    })
    
    return flagged


def extract_key_concepts(text: str, top_n: int = 20) -> List[str]:
    """
    Extract key concepts from text (not just all words)
    This helps identify what's important to preserve
    """
    # Extract all words
    words = re.findall(r"[අ-෴]{3,}", text)
    
    # Count frequencies
    word_counts = {}
    for word in words:
        if word not in STOPWORDS:
            word_counts[word] = word_counts.get(word, 0) + 1
    
    # Get top N most frequent words (key concepts)
    sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
    return [word for word, count in sorted_words[:top_n]]


def summary_fidelity_check(generated: str, source: str, grade: str = "9-11") -> Dict:
    """
    Check if summary preserves key concepts from source
    This is BETTER than simple concept mapping for summaries
    """
    # Get key concepts from source
    source_key_concepts = extract_key_concepts(source, top_n=15)
    generated_concepts = extract_concepts(generated)
    
    # Check which key concepts are preserved
    preserved = [concept for concept in source_key_concepts if concept in generated_concepts]
    missing_key = [concept for concept in source_key_concepts if concept not in generated_concepts]
    
    # Grade-specific expectations for key concept preservation
    preservation_targets = {
        "6-8": 0.4,  # Preserve 40% of key concepts
        "9-11": 0.6,  # Preserve 60% of key concepts
        "12-13": 0.7,  # Preserve 70% of key concepts
        "university": 0.8  # Preserve 80% of key concepts
    }
    
    target = preservation_targets.get(grade, 0.6)
    preservation_ratio = len(preserved) / len(source_key_concepts) if source_key_concepts else 0
    
    # Also check for hallucinations
    all_generated_concepts = extract_concepts(generated)
    all_source_concepts = extract_concepts(source)
    extra_concepts = list(all_generated_concepts - all_source_concepts)
    
    # Grade-specific thresholds for extra concepts
    extra_thresholds = {
        "6-8": 15,
        "9-11": 10,
        "12-13": 8,
        "university": 5
    }
    
    max_extra = extra_thresholds.get(grade, 10)
    
    return {
        "preserved_key_concepts": preserved,
        "missing_key_concepts": missing_key[:10],  # First 10 only
        "preservation_ratio": preservation_ratio,
        "preservation_target": target,
        "meets_preservation_target": preservation_ratio >= target,
        "extra_concepts": extra_concepts[:10],  # First 10 only
        "extra_concepts_count": len(extra_concepts),
        "within_extra_limit": len(extra_concepts) <= max_extra,
        "is_valid_summary": preservation_ratio >= target and len(extra_concepts) <= max_extra
    }


def adaptive_summary_clean(generated: str, source: str, flagged: List[Dict], grade: str = "9-11") -> str:
    """
    Adaptive cleaning that preserves important content while removing hallucinations
    """
    if not flagged:
        return generated
    
    # Get key concepts from source
    key_concepts = extract_key_concepts(source, top_n=10)
    
    sentences = re.split(r"(?<=[.!?])\s+", generated)
    cleaned_sentences = []
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence or len(sentence) < 5:
            continue
        
        should_remove = False
        
        # Check if this sentence was flagged
        for flag in flagged:
            flag_sentence = flag.get("sentence", "")
            if flag_sentence in sentence or sentence in flag_sentence:
                # Before removing, check if it contains important key concepts
                sentence_concepts = extract_concepts(sentence)
                important_in_sentence = any(concept in sentence_concepts for concept in key_concepts)
                
                if important_in_sentence:
                    # This sentence has important concepts - keep it but log
                    print(f"[SAFETY] Keeping flagged sentence with important concepts: {sentence[:80]}...")
                    should_remove = False
                    break
                else:
                    # No important concepts - can remove
                    should_remove = True
                    print(f"[CLEANING] Removing hallucinated sentence: {sentence[:80]}...")
                    break
        
        if not should_remove:
            cleaned_sentences.append(sentence)
    
    # Join sentences
    cleaned = ". ".join(cleaned_sentences)
    
    # Ensure proper punctuation
    if cleaned and cleaned[-1] not in ".!?":
        cleaned += "."
    
    # Post-processing for grade level
    cleaned = adjust_for_grade_level(cleaned, grade)
    
    return cleaned


def adjust_for_grade_level(text: str, grade: str) -> str:
    """
    Adjust summary for grade level without removing important content
    """
    sentences = re.split(r"[.!?]", text)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    if not sentences:
        return text
    
    adjusted_sentences = []
    
    if grade == "6-8":
        # For grade 6-8: simplify sentences but keep meaning
        for sentence in sentences:
            words = sentence.split()
            if len(words) > 20:
                # Split long sentences
                parts = []
                current_part = []
                current_length = 0
                
                for word in words:
                    current_part.append(word)
                    current_length += 1
                    
                    if current_length >= 10 and word.endswith(("යි", "ති", "ත", "ය", "ව")):
                        parts.append(" ".join(current_part))
                        current_part = []
                        current_length = 0
                
                if current_part:
                    parts.append(" ".join(current_part))
                
                adjusted_sentences.extend(parts)
            else:
                adjusted_sentences.append(sentence)
    
    elif grade == "university":
        # For university: ensure academic tone
        # Don't modify content, just ensure proper structure
        if len(sentences) < 3:
            # University summaries should be more substantial
            return text  # Keep as is
    
    else:
        # For other grades, keep as is
        adjusted_sentences = sentences
    
    return ". ".join(adjusted_sentences) + ("." if adjusted_sentences and not text.endswith(".") else "")


def hybrid_clean(text: str, flagged: List[Dict], grade: str = "9-11") -> str:
    """
    Original hybrid_clean function for Q&A (backward compatibility)
    """
    if not flagged:
        return text
    
    sentences = re.split(r"(?<=[.!?])\s+", text)
    cleaned_sentences = []
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        
        should_remove = False
        
        for flag in flagged:
            if flag.get("sentence", "") in sentence or sentence in flag.get("sentence", ""):
                should_remove = True
                break
        
        if not should_remove:
            cleaned_sentences.append(sentence)
    
    # Join with appropriate punctuation
    cleaned = ". ".join(cleaned_sentences)
    
    # Ensure proper ending punctuation
    if cleaned and cleaned[-1] not in ".!?":
        cleaned += "."
    
    return cleaned