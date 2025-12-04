# app/components/evaluation/utils/question_numbering.py

import re
import logging

logger = logging.getLogger(__name__)


def normalize_ocr_text(raw: str) -> str:
    logger.info("Raw OCR text received: %s", raw[:300])

    text = raw.replace("\n", " ").replace("\t", " ").strip()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"(\d+)\s*[\.\)]", r"\1.", text)

    logger.info("Normalized text: %s", text[:300])
    return text


def split_into_main_blocks(text: str, total_main: int) -> list:
    logger.info("Splitting into main question blocks...")

    pattern = r"(\d\.)"
    parts = re.split(pattern, text)

    blocks = []
    for i in range(1, len(parts), 2):
        number = parts[i]
        content = parts[i+1]
        block = f"{number} {content}".strip()
        blocks.append(block)
        logger.info("Detected block: %s", block[:200])

    logger.info("Total main blocks detected: %s", len(blocks))
    return blocks[:total_main]


def extract_subquestions(block: str, expected_sub_count: int) -> list:
    logger.info("Extracting sub-questions from block: %s", block[:200])

    block = block.replace("\u201c", '"').replace("\u201d", '"')

    # 1. Quoted questions
    quoted = re.findall(r'"([^"]+)"', block)
    if quoted:
        logger.info("Found quoted subquestions: %s", quoted)
        return quoted[:expected_sub_count]

    # 2. Comma separated
    parts = [p.strip() for p in block.split(",") if len(p.strip()) > 5]
    if len(parts) >= expected_sub_count:
        logger.info("Found comma-separated subquestions: %s", parts)
        return parts[:expected_sub_count]

    # 3. Split by question marks
    q_parts = re.split(r"\?\s*", block)
    cleaned = [q.strip() + "?" for q in q_parts if len(q.strip()) > 5]

    logger.info("Found question-mark separated subquestions: %s", cleaned)
    return cleaned[:expected_sub_count]


def build_numbered_questions(raw_text: str, total_main: int, sub_count: int) -> dict:
    logger.info("=== Building structured question numbering ===")
    cleaned = normalize_ocr_text(raw_text)

    main_blocks = split_into_main_blocks(cleaned, total_main)
    result = {}

    for i, block in enumerate(main_blocks):
        main_number = i + 1
        subs = extract_subquestions(block, sub_count)

        for j, sq in enumerate(subs):
            letter = chr(ord("a") + j)
            qid = f"Q{main_number:02}_{letter}"
            result[qid] = sq
            logger.info("Created question ID %s: %s", qid, sq)

    logger.info("Final structured questions: %s", result)
    return result
