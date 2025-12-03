# app/components/evaluation/services/scorer.py

import numpy as np
from rank_bm25 import BM25Okapi

from app.shared.ai.embeddings import semantic_similarity
from app.components.evaluation.utils.helpers import tokenize_sinhala

# BM25 model will be injected each evaluation
# syllabus_chunks will be passed dynamically


# ------------------------------------------------------------
# Chunk Retrieval
# ------------------------------------------------------------
def retrieve_chunks(question: str, syllabus_chunks: list, bm25: BM25Okapi):
    tokens = tokenize_sinhala(question)

    if not tokens:
        return [syllabus_chunks[0]]

    scores = bm25.get_scores(tokens)

    # Top 3 chunks
    top_idx = np.argsort(scores)[::-1][:3]

    retrieved = []
    for idx in top_idx:
        if scores[idx] > 0.1:
            retrieved.append(syllabus_chunks[idx])

    if not retrieved:
        retrieved.append(syllabus_chunks[int(np.argmax(scores))])

    return retrieved


# ------------------------------------------------------------
# Coverage Score
# ------------------------------------------------------------
def coverage_score(student: str, combined: str):
    if not student.strip() or not combined.strip():
        return 0.0

    s_words = set(tokenize_sinhala(student))
    c_words = set(tokenize_sinhala(combined))

    if len(c_words) == 0:
        return 0.0

    cov = len(s_words.intersection(c_words)) / len(c_words)
    return min(cov * 1.3, 1.0)


# ------------------------------------------------------------
# BM25 Score
# ------------------------------------------------------------
def bm25_score(question_text, bm25):
    tokenized = tokenize_sinhala(question_text)
    if not tokenized:
        return 0.0

    scores = bm25.get_scores(tokenized)

    # Convert to list to safely check length
    scores_list = scores.tolist()

    if len(scores_list) == 0:
        return 0.0

    max_score = float(max(scores_list))

    # Normalization
    normalized = min(max_score / 8.0, 1.0)
    return normalized


# ------------------------------------------------------------
# Main scoring function per subquestion
# ------------------------------------------------------------
def compute_scores_for_answer(
    question_text: str,
    student_answer: str,
    syllabus_chunks: list,
    rubric: dict,
    marks_distribution: list,
    qid: str
):

    # ---------------------------
    # BM25 Model Setup
    # ---------------------------
    tokenized_syllabus = [tokenize_sinhala(c) for c in syllabus_chunks]
    bm25 = BM25Okapi(tokenized_syllabus)

    # ---------------------------
    # Retrieve chunks
    # ---------------------------
    chunks = retrieve_chunks(question_text, syllabus_chunks, bm25)
    combined_text = " ".join(chunks)

    # ---------------------------
    # Raw Scores
    # ---------------------------
    sem = semantic_similarity(student_answer, combined_text)
    cov = coverage_score(student_answer, combined_text)
    bm = bm25_score(question_text, bm25)

    # ---------------------------
    # Weighted combine
    # ---------------------------
    weighted = (
        sem * rubric["semantic_weight"]
        + cov * rubric["coverage_weight"]
        + bm * rubric["bm25_weight"]
    )

    # ---------------------------
    # Allocate marks for this subquestion
    # ---------------------------
    main_id, sub = qid.split("_")
    sub_index = "abcd".index(sub.lower())  # Q01_a → index 0

    allocated_marks = marks_distribution[sub_index]

    # ---------------------------
    # Word count penalty
    # ---------------------------
    words = tokenize_sinhala(student_answer)
    expected = allocated_marks * 10

    if len(words) < expected * 0.3:
        weighted *= 0.7
    elif len(words) < expected * 0.6:
        weighted *= 0.85

    # ---------------------------
    # Convert to actual marks
    # ---------------------------
    final_score = weighted * allocated_marks

    # Bonus for excellent answers
    if sem > 0.7 and cov > 0.5:
        final_score = min(final_score * 1.1, allocated_marks)

    # boundaries
    final_score = max(0, min(final_score, allocated_marks))

    return {
        "semantic": sem,
        "coverage": cov,
        "bm25": bm,
        "final_score": final_score,
        "max_score": allocated_marks,
        "allocated_marks": allocated_marks,
        "retrieved_context": chunks
    }
