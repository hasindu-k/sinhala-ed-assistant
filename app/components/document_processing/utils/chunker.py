# app/components/document_processing/utils/chunker.py

import re
from typing import List, Dict
from app.components.document_processing.utils.numbering import extract_numbering
from app.utils.sinhala_nlp import split_sentences_sinhala, tokenize_sinhala_words


def split_into_sentences(text: str) -> List[str]:
    return split_sentences_sinhala(text)


def approximate_token_count(text: str) -> int:
    """Approximate tokens. Sinhala uses ~2.5 chars per token for LLMs."""
    # Heuristic: 1 token ~= 2.5 chars for Sinhala (vs 4 for English)
    return max(1, int(len(text) / 2.5))


def chunk_text(
    text: str,
    max_tokens: int = 220,
    overlap_tokens: int = 60
) -> List[Dict]:
    """
    Chunk text into metadata chunks:
    Each chunk contains:
    - chunk_id
    - text
    - numbering (first detected numbering in chunk)
    """

    sentences = split_into_sentences(text)

    chunks: List[Dict] = []

    current_chunk_text = ""
    current_chunk_tokens = 0
    current_chunk_numberings = []

    chunk_id = 0

    for sentence in sentences:
        numbering = extract_numbering(sentence)
        sentence_tokens = approximate_token_count(sentence)

        # Will this exceed max size?
        if current_chunk_tokens + sentence_tokens > max_tokens and current_chunk_text:
            # ---- finalize current chunk ----
            chunks.append({
                "chunk_id": chunk_id,
                "text": current_chunk_text.strip(),
                "numbering": current_chunk_numberings[0] if current_chunk_numberings else None
            })
            chunk_id += 1

            # ---- overlap logic ----
            if overlap_tokens > 0:
                overlap_chars = overlap_tokens * 4
                tail = current_chunk_text[-overlap_chars:]
                current_chunk_text = tail + " "
                current_chunk_tokens = approximate_token_count(current_chunk_text)

                # extract numbering from overlapped tail
                first_line = current_chunk_text.strip().split("\n")[0]
                overlap_num = extract_numbering(first_line)
                current_chunk_numberings = [overlap_num] if overlap_num else []

            else:
                current_chunk_text = ""
                current_chunk_tokens = 0
                current_chunk_numberings = []

        # ---- append sentence to chunk ----
        current_chunk_text += sentence + " "
        current_chunk_tokens += sentence_tokens

        if numbering:
            current_chunk_numberings.append(numbering)

    # ---- final chunk ----
    if current_chunk_text.strip():
        chunks.append({
            "chunk_id": chunk_id,
            "text": current_chunk_text.strip(),
            "numbering": current_chunk_numberings[0] if current_chunk_numberings else None
        })

    return chunks
