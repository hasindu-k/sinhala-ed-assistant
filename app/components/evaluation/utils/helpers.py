# app/components/evaluation/utils/helpers.py

import re


# ------------------------------------------------------------
# Sinhala Tokenizer
# ------------------------------------------------------------
def tokenize_sinhala(text: str):
    """
    Sinhala-friendly tokenizer using Unicode blocks.
    Extracts Sinhala, English, and numeric terms.
    """
    if not text:
        return []

    words = re.findall(r"[අ-ෆa-zA-Z0-9]+", text)
    return [w.lower() for w in words]


# ------------------------------------------------------------
# Extract Main Question ID
# ------------------------------------------------------------
def extract_main_question_id(qid: str) -> str:
    """
    Q03_a → Q03
    Q02_d → Q02
    """
    return qid.split("_")[0]


# ------------------------------------------------------------
# Get subquestion index (a,b,c,d → 0,1,2,3)
# ------------------------------------------------------------
def get_sub_index(qid: str) -> int:
    """
    Converts Q04_c → 2
    """
    try:
        sub = qid.split("_")[1].lower()
        return "abcd".index(sub)
    except:
        return 0   # fallback for mislabelled qid


# ------------------------------------------------------------
# Select BEST N main questions based on total scores
# ------------------------------------------------------------
def select_best_main_questions(grouped: dict, required: int):
    """
    grouped = {
        "Q01": [SubResult, SubResult, ...],
        "Q02": [...],
    }
    """

    totals = {}

    for main_id, subresults in grouped.items():
        score_sum = sum(r.total_score for r in subresults)
        totals[main_id] = score_sum

    # Sort by descending total marks
    ordered = sorted(totals.keys(), key=lambda x: totals[x], reverse=True)

    # Return top N
    return ordered[:required]
