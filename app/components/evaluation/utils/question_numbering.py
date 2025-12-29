# app/components/evaluation/utils/question_numbering.py

import re
import logging

logger = logging.getLogger(__name__)

# ------------------------------------------------------------
# MAIN QUESTION PATTERN (supports: 1. , 2. , 10. )
# ------------------------------------------------------------
MAIN_PATTERN = re.compile(r'^(\d{1,2})\.\s*$')


# ------------------------------------------------------------
# SUB QUESTION PATTERN
# Supports:
#   i)   ii)   iii)   iv)
#   a)   b)    c)
#   A)   B)
# ------------------------------------------------------------
SUB_PATTERN = re.compile(
    r'^('
    r'[a-zA-Z]'             # A, B, C, a, b, c
    r'|'
    r'i{1,3}|iv|v'          # i, ii, iii, iv, v
    r')\)\s*(.*)$'
)


# ------------------------------------------------------------
# CLEAN TEXT: remove extra spaces, OCR junk
# ------------------------------------------------------------
def clean_text(text: str) -> str:
    if not text:
        return ""
    text = text.strip()
    text = re.sub(r'\s+', ' ', text)
    return text


# ------------------------------------------------------------
# MAIN FUNCTION: BUILD STRUCTURED QUESTION OUTPUT
# ------------------------------------------------------------
def build_numbered_questions(raw_text: str, total_main: int, sub_count: int) -> dict:
    """
    Universal question numbering module.
    Works with Hasindu's cleaned OCR output:

        1.
        i) ...
        ii) ...
        iii) ...
        iv) ...

        2.
        i) ...
        ii) ...
        ...

    Produces:
        Q01_a, Q01_b, Q01_c, Q01_d
        Q02_a, Q02_b, ...
    """

    if not raw_text:
        return {}

    lines = raw_text.splitlines()
    questions = {}

    current_main = None
    current_sub_index = None
    buffer = []

    # --------------------------------------------------------
    # Helper function: store subquestion
    # --------------------------------------------------------
    def store_subquestion(main_no, idx, text):
        if main_no is None or idx is None:
            return
        if idx >= sub_count:
            return

        cleaned = clean_text(text)
        letter = chr(ord("a") + idx)
        qid = f"Q{int(main_no):02d}_{letter}"

        questions[qid] = cleaned
        logger.info(f"[STORE] {qid}: {cleaned}")

    # --------------------------------------------------------
    # Process line-by-line
    # --------------------------------------------------------
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # ---------------------------
        # Detect MAIN question
        # ---------------------------
        m_main = MAIN_PATTERN.match(stripped)
        if m_main:
            # Save previous subquestion before switching
            if current_main and current_sub_index is not None and buffer:
                store_subquestion(current_main, current_sub_index, " ".join(buffer))

            current_main = int(m_main.group(1))
            current_sub_index = None
            buffer = []
            continue

        # ---------------------------
        # Detect SUB question
        # ---------------------------
        m_sub = SUB_PATTERN.match(stripped)
        if m_sub:
            text_after_marker = m_sub.group(2).strip()

            # Save previous subquestion
            if current_main and current_sub_index is not None and buffer:
                store_subquestion(current_main, current_sub_index, " ".join(buffer))

            # Assign next sub index
            current_sub_index = 0 if current_sub_index is None else current_sub_index + 1

            if current_sub_index < sub_count:
                buffer = []
                if text_after_marker:
                    buffer.append(text_after_marker)
            else:
                # More subquestions than expected → treat as continuation text
                current_sub_index -= 1
                buffer.append(stripped)

            continue

        # ---------------------------
        # Normal text → part of subquestion
        # ---------------------------
        buffer.append(stripped)

    # --------------------------------------------------------
    # Save last subquestion if exists
    # --------------------------------------------------------
    if current_main and current_sub_index is not None and buffer:
        store_subquestion(current_main, current_sub_index, " ".join(buffer))

    # --------------------------------------------------------
    # Only return up to requested main questions
    # --------------------------------------------------------
    final = {}
    for qid in sorted(questions.keys()):
        main_num = int(qid[1:3])
        if main_num <= total_main:
            final[qid] = questions[qid]

    return final
