def extract_main_question_id(qid: str) -> str:
    return qid.split("_")[0]


def get_sub_index(qid: str) -> int:
    """
    Q04_c -> 2, supports full alphabet a-z.
    """
    try:
        sub = qid.split("_")[1].lower()
        return "abcdefghijklmnopqrstuvwxyz".index(sub)
    except Exception:
        return 0


def _main_sort_key(main_id: str) -> int:
    """
    "Q01" -> 1, safe fallback.
    """
    try:
        return int(main_id.replace("Q", ""))
    except Exception:
        return 10**9


def select_best_main_questions(grouped: dict, required: int):
    """
    Deterministic:
    - Higher total first
    - If tie: smaller main id first (Q01 before Q02)
    """
    totals = {}
    for main_id, subresults in grouped.items():
        totals[main_id] = sum(r.total_score for r in subresults)

    ordered = sorted(
        totals.keys(),
        key=lambda mid: (-totals[mid], _main_sort_key(mid)),
    )
    return ordered[:required]
