import re

SINHALA_LETTER = r"[අ-ෆ]"
ENGLISH_LETTER = r"[a-zA-Z]"
ROMAN = r"\b(i|ii|iii|iv|v|vi|vii|viii|ix|x)\b"

def extract_numbering(line: str) -> str:
    """
    Detect Sinhala/English/roman numbering patterns.
    Returns numbering string or ''.
    """

    patterns = [
        r"^\s*(\d+(\.\d+){0,3})",            # 1, 1.1, 1.1.1
        r"^\s*(Q\s*\d+)",                    # Q1, Q2
        r"^\s*(\d+\([a-z]\))",               # 1(a)
        r"^\s*(\d+\([අ-ෆ]\))",               # 1(අ)
        rf"^\s*({ROMAN})\.",                 # i. ii. iii.
        rf"^\s*({SINHALA_LETTER})\)",        # අ) ආ)
    ]

    for p in patterns:
        m = re.match(p, line.strip())
        if m:
            return m.group(1)

    return ""
