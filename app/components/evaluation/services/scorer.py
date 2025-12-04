# app/components/evaluation/services/scorer.py

from app.components.evaluation.services.semantic_model import xlmr
from app.components.evaluation.utils.text_utils import tokenize_sinhala, normalize_sinhala
from rank_bm25 import BM25Okapi
import numpy as np


def build_bm25(syllabus_chunks):
    tokenized = [tokenize_sinhala(chunk) for chunk in syllabus_chunks]
    return BM25Okapi(tokenized)


def semantic_score(student_answer: str, retrieved: str) -> float:
    if not student_answer.strip() or not retrieved.strip():
        return 0.0

    try:
        clean_student = normalize_sinhala(student_answer)
        clean_retrieved = normalize_sinhala(retrieved)

        a = xlmr.encode(clean_student, convert_to_tensor=True)
        b = xlmr.encode(clean_retrieved, convert_to_tensor=True)

        similarity = float((a @ b.T) / (a.norm() * b.norm()))

        return (similarity + 1) / 2

    except Exception as e:
        print(f"[XLM-R ERROR] {e}")
        return 0.0



def coverage_score(student_answer: str, retrieved: str) -> float:
    if not student_answer.strip() or not retrieved.strip():
        return 0.0

    student_words = set(tokenize_sinhala(student_answer))
    chunk_words = set(tokenize_sinhala(retrieved))

    if len(chunk_words) == 0:
        return 0.0

    return min(len(student_words.intersection(chunk_words)) / len(chunk_words), 1.0)


def bm25_score(question_text: str, bm25: BM25Okapi) -> float:
    tokens = tokenize_sinhala(question_text)
    if not tokens:
        return 0.0

    scores = bm25.get_scores(tokens)
    max_score = float(scores.max()) if len(scores) else 0.0

    BM25_MAX = 6.0  # replace with dynamic if needed
    return min(max_score / BM25_MAX, 1.0)


def retrieve_chunks(question_text: str, bm25: BM25Okapi, syllabus_chunks, top_n=3):
    tokens = tokenize_sinhala(question_text)

    if not tokens:
        return [syllabus_chunks[0]]

    scores = bm25.get_scores(tokens)
    top_indices = np.argsort(scores)[::-1][:top_n]

    retrieved = [syllabus_chunks[i] for i in top_indices if scores[i] > 0.1]

    if not retrieved:
        retrieved.append(syllabus_chunks[int(np.argmax(scores))])

    return retrieved


def compute_scores_for_answer(
    question_text,
    student_answer,
    syllabus_chunks,
    rubric,
    marks_distribution,
    qid,
    bm25

):

    main_id = qid.split("_")[0]
    sub_id = qid.split("_")[1]          # a, b, c, d
    sub_index = ord(sub_id) - 97        # 0, 1, 2, 3

    # NEW FIX: use single universal marks list
    allocated_marks = marks_distribution[sub_index]

    retrieved_list = retrieve_chunks(question_text, bm25, syllabus_chunks)
    combined_text = " ".join(retrieved_list)

    sem = semantic_score(student_answer, combined_text)
    cov = coverage_score(student_answer, combined_text)
    bm = bm25_score(question_text, bm25)

    final_weighted = (
        sem * rubric["semantic_weight"] +
        cov * rubric["coverage_weight"] +
        bm * rubric["bm25_weight"]
    )

    final_marks = final_weighted * allocated_marks
    final_marks = max(0, min(final_marks, allocated_marks))

    return {
        "semantic": sem,
        "coverage": cov,
        "bm25": bm,
        "allocated_marks": allocated_marks,
        "final_score": final_marks,
        "max_score": allocated_marks,
        "retrieved_context": retrieved_list,
    }
