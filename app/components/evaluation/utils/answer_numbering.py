import re

def clean_inline_markers(text: str):
    # Remove inline markers such as: a), a., i), ii., iii), iv), v), A), B)
    
    return re.sub(
    r'\b(i{1,3}|iv|v|[a-zA-Z])[\.\)]\s*', 
    '', 
    text
).strip()


def build_numbered_answers(raw_text: str, total_main_questions: int, subquestions_per_main: int = 26):
    """
    UNIVERSAL ANSWER EXTRACTOR (FINAL VERSION)

    - Uses teacher settings
    - Subquestions mapped by ORDER only (0→a, 1→b…)
    - Removes roman numerals from inside content
    - Removes a), b., c), iv), v) from answer paragraphs
    - Note: subquestions_per_main is now soft-capped (default high) to allow variable structures.
    """

    if not raw_text:
        return {}

    lines = raw_text.splitlines()
    answers = {}

    current_main = None
    current_sub_index = None
    buffer = []

    # Detect "1." or "1"
    main_pattern = re.compile(r'^(\d+)\.?$')

    # Detect ANY subquestion marker
    sub_marker_pattern = re.compile(
        r'^('
        r'[a-zA-Z]'           # letters
        r'|'
        r'i{1,3}|iv|v'        # roman numerals
        r')[\.\)]?\s*(.*)$'
    )

    # ---------------------------------------------------
    # INTERNAL SAVE FUNCTION
    # ---------------------------------------------------
    def store_answer(main_q, sub_idx, text):
        if main_q is None or sub_idx is None:
            return
        
        # We no longer strictly enforce subquestions_per_main here
        # to allow flexibility for papers with varying subcounts.
        # Max limit is implicitly 'z' (26) by logic below.

        cleaned = clean_inline_markers(text)
        key = chr(ord('a') + sub_idx)  # 0->a, 1->b, etc.
        qid = f"Q{int(main_q):02d}_{key}"

        answers[qid] = cleaned

    # ---------------------------------------------------
    # MAIN LOOP
    # ---------------------------------------------------
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Detect MAIN question number
        m_main = main_pattern.match(stripped)
        if m_main:
            if current_main and current_sub_index is not None and buffer:
                store_answer(current_main, current_sub_index, "\n".join(buffer))

            current_main = m_main.group(1)
            current_sub_index = None
            buffer = []
            continue

        # Detect SUB marker (any format)
        m_sub = sub_marker_pattern.match(stripped)
        if m_sub:
            tail = m_sub.group(2).strip()

            if current_main and current_sub_index is not None and buffer:
                store_answer(current_main, current_sub_index, "\n".join(buffer))

            # assign according to order, not marker
            if current_sub_index is None:
                current_sub_index = 0
            else:
                current_sub_index += 1

            # Limit subquestions to avoid infinite drift
            if current_sub_index >= 26: 
                current_sub_index -= 1
                buffer.append(stripped)
                continue

            buffer = []
            if tail:
                buffer.append(tail)
            continue

        # Normal text
        buffer.append(stripped)

    # Save remaining
    if current_main and current_sub_index is not None and buffer:
        store_answer(current_main, current_sub_index, "\n".join(buffer))

    return answers
