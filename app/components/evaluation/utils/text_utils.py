# app/components/evaluation/utils/text_utils.py

import re


# ------------------------------------------------------------
# 1. Basic Sinhala Tokenizer
# ------------------------------------------------------------

def tokenize_sinhala(text: str) -> list:
    """
    Very simple Sinhala-friendly tokenizer.
    Splits text into words, removes punctuation, lowercases,
    and keeps Sinhala + English words.
    """

    if not text or not isinstance(text, str):
        return []

    # Remove punctuation
    cleaned = re.sub(r"[^\w\s\u0D80-\u0DFF]", " ", text)

    # Lowercase English (Sinhala unaffected)
    cleaned = cleaned.lower()

    # Split by spaces
    tokens = cleaned.split()

    # Remove numbers and empty tokens
    tokens = [t for t in tokens if t.strip() and not t.isdigit()]

    return tokens



# ------------------------------------------------------------
# 2. Normalize Sinhala text (optional)
# ------------------------------------------------------------

def normalize_sinhala(text: str) -> str:
    """
    This removes duplicate spaces and simple noise.
    Helps keep encoding consistent for XLM-R.
    """

    if not text or not isinstance(text, str):
        return ""

    text = text.replace("\u200d", "")       # Zero-width joiner
    text = text.replace("\u200c", "")       # Zero-width non-joiner

    # Remove weird repeating space patterns
    text = re.sub(r"\s+", " ", text)

    return text.strip()



# ------------------------------------------------------------
# 3. Sentence Splitter (optional)
# ------------------------------------------------------------

def split_sentences(text: str) -> list:
    """
    Rough Sinhala/English sentence splitter.
    Not required for scoring, but useful later.
    """

    if not text or not isinstance(text, str):
        return []

    # Split by Sinhala full-stop or English punctuation
    parts = re.split(r"[\.!?]|[\u0DF4]", text)

    # Clean each piece
    sentences = [p.strip() for p in parts if p.strip()]

    return sentences
