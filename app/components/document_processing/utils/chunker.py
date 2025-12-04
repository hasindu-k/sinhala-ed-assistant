# app/components/document_processing/utils/chunker.py

import re
from typing import List

def split_into_sentences(text: str) -> List[str]:
    """
    Split Sinhala + English text into sentences.
    Sinhala uses ':', '.', '!', '?', '။' etc.
    """
    pattern = r"(?<=[\.!\?]|[\.!\?][\"\'])\s+"
    sentences = re.split(pattern, text)
    return [s.strip() for s in sentences if s.strip()]


def approximate_token_count(text: str) -> int:
    """
    Approximate tokens. Gemini uses 1 token ≈ 3-4 characters avg.
    """
    return max(1, len(text) // 4)


def chunk_text(text: str, max_tokens: int = 300, overlap_tokens: int = 30):
    """
    Smart chunking for Sinhala/English documents.
    Splits text into ~max_tokens chunks with slight overlaps.
    """

    sentences = split_into_sentences(text)
    chunks = []

    current_chunk = ""
    current_tokens = 0

    for sentence in sentences:
        sentence_tokens = approximate_token_count(sentence)

        # If adding this sentence exceeds max_tokens, finalize chunk
        if current_tokens + sentence_tokens > max_tokens:
            chunks.append(current_chunk.strip())

            # Start new chunk with overlap from previous end
            if overlap_tokens > 0:
                tail = current_chunk[-overlap_tokens * 4 :]
                current_chunk = tail + " "

            else:
                current_chunk = ""

            current_tokens = approximate_token_count(current_chunk)

        # Add sentence
        current_chunk += sentence + " "
        current_tokens += sentence_tokens

    # Add final chunk
    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks
