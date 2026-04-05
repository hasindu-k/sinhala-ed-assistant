# app/utils/sinhala_nlp.py

import logging
from typing import List
import re

logger = logging.getLogger(__name__)

try:
    from indicnlp.tokenize import sentence_tokenize, indic_tokenize
    INDIC_NLP_AVAILABLE = True
except ImportError:
    logger.warning("indic-nlp-library not found, using regex fallback for sentence splitting.")
    INDIC_NLP_AVAILABLE = False


def split_sentences_sinhala(text: str) -> List[str]:
    """
    Split Sinhala text into sentences using indic-nlp-library if available.
    Falls back to regex splitting otherwise.
    """
    if not text:
        return []

    # Normalize Sinhala danda to period if present (as a pre-processing step)
    text = text.replace("।", ".")

    if INDIC_NLP_AVAILABLE:
        try:
            sentences = sentence_tokenize.sentence_split(text, lang='si')
            return [s.strip() for s in sentences if s.strip()]
        except Exception as e:
            logger.error(f"Error using indic-nlp-library for sentence splitting: {e}")
            # Fallback will happen below

    # Regex fallback
    # insert a delimiter after punctuation
    x = re.sub(r"([.!?]+)", r"\1<SPLIT>", text)
    parts = x.split("<SPLIT>")
    return [p.strip() for p in parts if p.strip()]


def tokenize_sinhala_words(text: str) -> List[str]:
    """
    Tokenize text into words/tokens using indic-nlp-library if available.
    """
    if not text:
        return []
        
    if INDIC_NLP_AVAILABLE:
        try:
            return indic_tokenize.trivial_tokenize(text, lang='si')
        except Exception as e:
            logger.error(f"Error using indic-nlp-library for tokenization: {e}")
            
    # Fallback to simple whitespace split
    return text.split()
