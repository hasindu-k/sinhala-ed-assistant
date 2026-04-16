# app/components/document_processing/services/classifier_service.py

import json
import logging
import difflib
import re
from app.core.config import settings
from app.services.evaluation.gemini_cost_policy import EvaluationGeminiClient
from app.shared.ai.gemini_client import gemini_generate, gemini_generate_evaluation, gemini_generate_lightweight

logger = logging.getLogger(__name__)

# Define prompts and constants
CLASSIFY_PROMPT = """
You are a Sinhala educational document classifier.
Classify the following text into ONE category:
- term_test
- teacher_guide
- student_notes
- past_paper
- answer_scheme
- textbook
Respond with ONLY the category name.
TEXT:
{content}
"""

def classify_document(text: str) -> str:
    if not text or not text.strip():
        return "unknown"
    
    try:
        output = gemini_generate(CLASSIFY_PROMPT.format(content=text[:8000])).strip().lower()
        
        allowed = {
            "term_test", "teacher_guide", "student_notes",
            "past_paper", "answer_scheme", "textbook"
        }
        # Print for debugging
        print(f"Document classified as: {output}")
        return output if output in allowed else "unknown"

    except Exception as e:
        print(f"Error classifying document: {e}")
        return "unknown"

def _safe_json_loads(text: str) -> dict:
    """Robust JSON parsing that handles Markdown code blocks and whitespace."""
    if not text:
        return {}
    
    try:
        # Strip potential Markdown backticks
        clean_text = text.strip()
        if clean_text.startswith("```"):
            clean_text = re.sub(r'^```json\s*|\s*```$', '', clean_text, flags=re.MULTILINE)
        
        try:
            return json.loads(clean_text)
        except json.JSONDecodeError:
            # Try to repair truncated JSON
            repaired = _repair_json(clean_text)
            return json.loads(repaired)
    except Exception as e:
        logger.error(f"Failed to parse JSON response: {e}. Raw content: {text[:500]}...")
        return {}

def _repair_json(text: str) -> str:
    """Basic recovery for truncated JSON (unterminated strings/objects)."""
    text = text.strip()
    if not text: return "{}"

    # Remove trailing commas before closing braces/brackets, which Gemini
    # occasionally emits even in otherwise-valid JSON payloads.
    text = re.sub(r",(\s*[}\]])", r"\1", text)
    text = re.sub(r",\s*$", "", text)
    
    # 1. Close unterminated string if it ends abruptly
    # If the last character is NOT a quote but there's an odd number of quotes in the last line
    # or if it ends with backslash escape
    if text.count('"') % 2 != 0:
        text += '"'
    
    # 2. Close open braces/brackets
    open_braces = text.count('{') - text.count('}')
    open_brackets = text.count('[') - text.count(']')
    
    # Add closing markers in reverse order of opening
    # This is a naive stack-based approach
    stack = []
    for char in text:
        if char == '{': stack.append('}')
        elif char == '[': stack.append(']')
        elif char == '}': 
            if stack and stack[-1] == '}': stack.pop()
        elif char == ']':
            if stack and stack[-1] == ']': stack.pop()
    
    # Append missing closers
    while stack:
        text += stack.pop()

    text = re.sub(r",(\s*[}\]])", r"\1", text)
    return text


_ROMAN_NUMERAL_MAP = {
    "i": 1,
    "ii": 2,
    "iii": 3,
    "iv": 4,
    "v": 5,
}


def _roman_to_paper_key(token: str) -> str | None:
    normalized = str(token or "").strip().lower()
    value = _ROMAN_NUMERAL_MAP.get(normalized)
    if value is None:
        return None
    return f"Paper_{normalized.upper()}"


def _question_sort_key(label: str) -> tuple[int, str]:
    text = str(label or "").strip()
    match = re.search(r"\d+", text)
    return (int(match.group()) if match else 10**9, text)


def _question_has_sub_questions(question_data: dict) -> bool:
    return bool((question_data or {}).get("sub_questions"))


def _count_questions_with_subparts(questions: dict) -> int:
    return sum(1 for q in (questions or {}).values() if _question_has_sub_questions(q))


def _segment_exam_text_by_paper_headers(text: str) -> dict[str, str]:
    if not text:
        return {}

    header_pattern = re.compile(
        r"(?im)^\s*(?:"
        r"(?:(?:paper|part|section)\s*[-: ]*\s*(?P<leading>iii|ii|iv|v|i))"
        r"|(?:(?P<trailing>iii|ii|iv|v|i)\s*(?:paper|part|section|කොටස|භාගය))"
        r"|(?:(?:කොටස|භාගය)\s*(?P<sinhala>iii|ii|iv|v|i))"
        r")\b[^\n]*$"
    )

    matches = list(header_pattern.finditer(text))
    if len(matches) < 2:
        return {}

    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        token = match.group("leading") or match.group("trailing") or match.group("sinhala")
        paper_key = _roman_to_paper_key(token)
        if not paper_key:
            continue
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        section_text = text[start:end].strip()
        if section_text:
            sections[paper_key] = section_text
    return sections


def _prepare_exam_text_for_prompt(text: str) -> str:
    sections = _segment_exam_text_by_paper_headers(text)
    if len(sections) < 2:
        return text

    ordered = sorted(sections.items(), key=lambda item: _question_sort_key(item[0]))
    blocks = [
        f"{paper_key} SECTION (do not mix with other papers):\n{section_text}"
        for paper_key, section_text in ordered
    ]
    return (
        "The OCR text below was locally segmented by detected paper headers. "
        "Keep every question inside its own paper section and do not move questions across sections.\n\n"
        + "\n\n".join(blocks)
    )


def _normalize_extracted_exam_result(result: dict) -> dict:
    cleaned_result: dict[str, dict] = {}
    for paper_key, paper_data in (result or {}).items():
        if not str(paper_key).startswith("Paper_") or not isinstance(paper_data, dict):
            continue

        questions = paper_data.get("questions", {}) or {}
        if not isinstance(questions, dict):
            questions = {}
        ordered_questions = {
            str(label): value
            for label, value in sorted(questions.items(), key=lambda item: _question_sort_key(item[0]))
        }

        config = dict(paper_data.get("config", {}) or {})
        config["total_questions_available"] = len(ordered_questions)

        normalized_paper = dict(paper_data)
        normalized_paper["config"] = config
        normalized_paper["questions"] = ordered_questions
        cleaned_result[str(paper_key)] = normalized_paper

    paper_i = cleaned_result.get("Paper_I")
    paper_ii = cleaned_result.get("Paper_II")
    if paper_i and paper_ii:
        paper_i_questions = dict(paper_i.get("questions", {}) or {})
        paper_ii_questions = dict(paper_ii.get("questions", {}) or {})
        paper_i_subparts = _count_questions_with_subparts(paper_i_questions)
        paper_ii_subparts = _count_questions_with_subparts(paper_ii_questions)

        # Heuristic repair for the common Sri Lankan split:
        # Paper I is short-answer/no subparts, Paper II is main questions with subparts.
        if paper_i_subparts == 0 and paper_ii_subparts >= 3:
            migrated: dict[str, dict] = {}
            remaining_paper_ii: dict[str, dict] = {}
            for label, question_data in paper_ii_questions.items():
                if _question_has_sub_questions(question_data):
                    remaining_paper_ii[label] = question_data
                else:
                    migrated[label] = question_data

            if migrated and remaining_paper_ii:
                paper_i_questions.update(migrated)
                paper_i["questions"] = {
                    label: value
                    for label, value in sorted(paper_i_questions.items(), key=lambda item: _question_sort_key(item[0]))
                }
                paper_ii["questions"] = {
                    label: value
                    for label, value in sorted(remaining_paper_ii.items(), key=lambda item: _question_sort_key(item[0]))
                }
                paper_i["config"]["total_questions_available"] = len(paper_i["questions"])
                paper_ii["config"]["total_questions_available"] = len(paper_ii["questions"])
                logger.warning(
                    "Rebalanced extracted paper structure: moved %s plain questions from Paper_II to Paper_I.",
                    len(migrated),
                )

    return cleaned_result
    

# 1. Specialized Prompt for Sinhala Exam Extraction
SINHALA_STRUCTURE_PROMPT = """
You are an expert AI for analyzing Sri Lankan exam papers (Sinhala and English medium).
Your task is to structure the provided text into a strict JSON format containing ONLY the question structure.

========================
IMPORTANT MARKING RULES
========================
- In Sri Lankan exam papers, NO question or subquestion has 0 marks.
- If marks are NOT clearly specified, use null (not 0).
- NEVER assign marks = 0.
- Common mark indicators: "ලකුණු", "marks", numbers in parentheses like (05)

========================
PAPER & NUMBERING RULES
========================
- Sri Lankan exam papers are divided into parts such as:
  - Part I (usually MCQs) - "I කොටස", "Part I", "භාගය I"
  - Part II (Structured questions) - "II කොටස", "Part II", "භාගය II"
  - Part III (Essay questions) - "III කොටස", "Part III", "භාගය III"

- EACH paper has its OWN numbering system.
  - Paper I numbering: 1, 2, 3, ... (typically 1-40 for MCQs)
  - Paper II numbering: starts again from 1 or continues with own sequence
  - DO NOT continue numbering across papers

- Questions MUST be grouped under their correct paper.
- NEVER mix Paper I and Paper II questions in the same numbering scope.

========================
MCQ STRUCTURE RULES (Paper I)
========================
- MCQs usually belong to Paper I unless explicitly stated otherwise.
- Detect MCQs by options like:
  - (1)(2)(3)(4), (A)(B)(C)(D), (අ)(ආ)(ඉ)(ඊ)
  - Numbered list format: 1. ... 2. ... 3. ... 4. ...
- If multiple MCQs share common instructions or data:
  - Attach the shared information to the first question using "shared_stem"
  - Subsequent questions reference it using "inherits_shared_stem_from"
- Each MCQ MUST include:
  - "type": "mcq"
  - "text": question text
  - "options": array of option texts
  - "marks": usually null or 1

========================
STRUCTURED QUESTIONS (Paper II)
========================
- Main questions: numbered (1, 2, 3, etc.) or labeled (Q01, Q02, etc.)
- Sub-questions: labeled with letters (a, b, c) or (i, ii, iii) or (අ, ආ, ඉ)
- Extract marks from patterns:
  - "(05 ලකුණු)", "(5 marks)", "(10)", "05 ලකුණු"
- If a main question has sub-questions:
  - Main question "marks" = sum of sub-question marks (or null if unclear)
  - Each sub-question should have its own marks

========================
TEXT PATTERNS TO DETECT
========================
**Question Numbers:**
- "01.", "1)", "ප්‍රශ්නය 01", "Question 1"
- Look for consistent numbering patterns

**Sub-question Labels:**
- "(අ)", "(ආ)", "(ඉ)", "(a)", "(b)", "(c)", "(i)", "(ii)"

**Marks Patterns:**
- "(05 ලකුණු)", "(5 marks)", "05 ලකුණු", "5 marks"
- Extract the number before "ලකුණු" or "marks"

**Section Headers:**
- "I කොටස", "II කොටස", "Part A", "Part B"
- "බහුවරණ ප්‍රශ්න" (MCQs), "ව්‍යුහගත ප්‍රශ්න" (Structured)

========================
OUTPUT FORMAT (STRICT JSON)
========================

{{
  "PaperStructure": {{
    "Paper_I": {{
      "type": "MCQ",
      "questions": {{
        "1": {{
          "type": "mcq",
          "text": "question text",
          "options": ["option 1", "option 2", "option 3", "option 4"],
          "correct_answer": "2",
          "marks": 1
        }}
      }}
    }},
    "Paper_II": {{
      "type": "Structured",
      "questions": {{ ... }}
    }},
    "Paper_III": {{
      "type": "Structured",
      "questions": {{ ... }}
    }}
  }}
}}

========================
IMPORTANT NOTES
========================
1. Do NOT extract metadata (Subject, Year, Grade).
2. Do NOT extract general instructions.
3. Only extract the Question Structure.
4. If a paper section is not found in the text, return an empty questions object for that paper.
5. Preserve original question numbers/labels from the text.
6. Extract marks carefully - use null if uncertain, never use 0.

========================
TEXT TO PROCESS
========================
{content}
"""

def separate_paper_content(text: str):
    """
    Separates paper content into PaperStructure only.
    Returns: paper_structure (dict)
    """
    if not text or not text.strip():
        return {}

    try:
        logger.info("Starting Sinhala structure extraction.")
        response_text = gemini_generate(
            SINHALA_STRUCTURE_PROMPT.format(content=text[:20000]),
            json_mode=True
        )

        if not response_text:
            logger.error("Empty response from Gemini.")
            return {}

        result = _safe_json_loads(response_text)
        if not result:
            return {}
        
        logger.info("Sinhala structure extraction completed successfully.")

        paper_structure = result.get("PaperStructure", {})
        if not paper_structure:
            # Fallback for older model styles or flat results
            paper_structure = {k: v for k, v in result.items() if k.startswith("Paper_")}

        # 🔒 Defensive normalization
        # Ensure 'questions' key exists for all identified papers
        for paper_key, paper in paper_structure.items():
            if isinstance(paper, dict) and "questions" not in paper:
                paper["questions"] = {}

        logger.debug("Extracted Paper Structure: %s", paper_structure)
        
        return paper_structure

    except json.JSONDecodeError:
        print("❌ Error: Model output was not valid JSON.")
        return {}

    except Exception as e:
        print(f"❌ Error in Sinhala structure extraction: {e}")
        return {}
    
def fix_sinhala_ocr(text: str) -> str:
    """
    Fix OCR errors in Sinhala text such as broken ligatures, misplaced diacritics,
    or split grapheme clusters.
    """
    if not text or not text.strip():
        return text

    prompt = f"""
    You are a Sinhala OCR text corrector.
    Fix OCR errors such as:
    - broken conjunct letters (ex: ක් ෂ → ක්‍ෂ),
    - misplaced diacritics,
    - missing vowels,
    - unnecessary spaces inside words.
    
    Output ONLY the corrected Sinhala text. Do NOT add explanations.

    Text:
    {text}
    """

    try:
        corrected = gemini_generate_evaluation(
            prompt,
            budget=EvaluationGeminiClient.OCR_CORRECTION,
            reason="fix_sinhala_ocr",
        ).strip()
        return corrected if corrected else text

    except Exception as e:
        logger.error(f"Error in Sinhala OCR correction: {e}")
        return text

COMBINED_EXAM_PROMPT = """
You are an expert AI for analyzing Sri Lankan exam papers (Sinhala and English medium).
Your task is to extract BOTH the **grading configuration** and the **question structure** into a single strict JSON format.

========================
SECTION 1: CONFIGURATION RULES
========================
Analyze the text to determine how the paper should be graded.
1. **Paper Identification:** Detect if text contains Paper I (Part 1), Paper II (Part 2), or both.
   - Look for headers like "කොටස I" (Part I), "කොටස II" (Part II), "I කොටස", "II කොටස".
   - DO NOT assume Paper I is always MCQ. It can contain structured questions too.
2. **Total Marks:** 
   - Look for "මුළු ලකුණු" (Total Marks) for each section.
   - For Paper I: If MCQs, usually 1 mark each. If structured, look for explicit marks.
   - For Paper II: Look for "Total Marks" or sum the sub-question marks.
3. **Selection Rules:** Read instructions (e.g., "Answer 3 from 5").
   - If "Answer all": {{"mode": "all"}}
   - If "Answer any X": {{"mode": "any", "count": X}}
   - If "Partially compulsory": {{"compulsory": [1, 2], "choose_any": 3}}

========================
SECTION 2: QUESTION STRUCTURE RULES
========================
**Question Detection:**
- Identify main questions (1, 2, 3...) and sub-questions (a, b, c or i, ii, iii).
- Preserve the exact question numbering and mapping from the paper.

**MCQ Structure:**
- Detect MCQs by options like (1)(2)(3)(4) or (A)(B)(C)(D).
- If multiple MCQs share a "shared_stem", attach it to the first and use "inherits_shared_stem_from" for others.

**Structured Structure:**
- Use "type": "structured".
- Sub-questions: Map labels (අ, ආ, ඉ or a, b, c) to "sub_questions" dictionary.
- Marks: Extract from "(ලකුණු 05)", "(5 marks)", "20 කි".
- **Rule:** Never assign 0 marks. Use null if unknown.

========================
SECTION 3: ROBUST LAYOUT & TEXT REPAIR
========================
You are receiving text from a system OCR or digital extraction which may have jumbled line orders due to multi-column layouts or PDF encoding issues.
1. **Restore Logical Flow**: Use linguistic context to re-order the questions. If sub-question (b) appears before (a) in the text, logically group them correctly in the JSON.
2. **Exhaustive Detection**: Every numbered (1, 2...) or lettered ((a), (b)... / (අ), (ආ)...) item MUST be captured. If sub-questions span multiple pages or are interrupted by tables, bridge the gap and include them all.
3. **Sinhala Repair**: Fix broken conjuncts (ක් ෂ → ක්‍ෂ), diacritic drifts, and accidental spaces within words.

========================
OUTPUT FORMAT (STRICT JSON)
========================
Return a single JSON object where keys are "Paper_I", "Paper_II", "Paper_III", etc. 
Only include keys for papers actually found in the text.

{{
  "Paper_I": {{
    "config": {{
      "subject_detected": "History",
      "medium": "Sinhala", 
      "total_marks": 40,
      "total_questions_available": 9,
      "suggested_weightage": 40,
      "selection_rules": {{"mode": "all"}}
    }},
    "questions": {{
      "1": {{
        "type": "structured",
        "text": "Question text here",
        "marks": 5
      }},
      "2": {{ "..." }}
    }}
  }},
  "Paper_III": {{
    "config": {{
      "total_marks": 20,
      "selection_rules": {{"mode": "any", "count": 1}}
    }},
    "questions": {{
      "1": {{ "type": "structured", "text": "Essay prompt...", "marks": 20 }}
    }}
  }}
}}

========================
TEXT TO PROCESS
========================
{content}
"""

def extract_complete_exam_data(text: str):
    """
    Extracts both Configuration (Marks/Rules) and Structure (Questions) in one pass.
    """
    if not text or not text.strip():
        return {}

    try:
        logger.info("Starting combined exam extraction.")

        prepared_text = _prepare_exam_text_for_prompt(text[:30000])
        response_text = gemini_generate(
            COMBINED_EXAM_PROMPT.format(content=prepared_text),
            json_mode=True,
            model_name=settings.EVAL_GEMINI_QUESTION_PARSING_MODEL,
        )

        result = _safe_json_loads(response_text)
        if not result or not isinstance(result, dict):
            return {}
            
        logger.info("Combined exam extraction completed successfully.")
        
        # 🔒 Generic Normalization: Accept any "Paper_*" keys
        cleaned_result = _normalize_extracted_exam_result(result)
        
        # Log basics for debugging
        if cleaned_result.get("Paper_I"):
            logger.info(f"Paper I Detected: {len(cleaned_result['Paper_I'].get('questions', {}))} questions")
        if cleaned_result.get("Paper_II"):
            logger.info(f"Paper II Detected: {len(cleaned_result['Paper_II'].get('questions', {}))} questions")

        return cleaned_result

    except json.JSONDecodeError:
        logger.error("❌ Error: Model output was not valid JSON.")
        return {}

    except Exception as e:
        logger.error(f"❌ Error in combined extraction: {e}")
        return {}

ANSWER_MAPPING_PROMPT = """
You are a STRICT answer extraction AI for Sri Lankan exam papers.
Your ONLY job: find the text the student wrote under each question number. Nothing else.

========================
CRITICAL RULES — READ CAREFULLY
========================
1. **QUESTION NUMBER FIRST**: The ONLY way to assign an answer to a question is if the student wrote that question's number BEFORE the answer text (e.g., "1(a)", "2.a", "3", "(b)", etc.). Look for these number markers in the student's handwriting/OCR.

2. **PAPER ISOLATION**: Sri Lankan papers have distinct parts (Part I, II, III, etc.).
   - Numbering often starts again from 1 or repeats in each part.
   - **CONTEXT HINT**: Look for headers like "භාගය I", "Part II", "III කොටස" in the student text.
   - **IMPORTANT**: If the student text is currently in a section titled "Part III", do NOT map a question "1" found there to a "Part I" question ID.

3. **DO NOT USE TOPIC/MEANING**: NEVER assign an answer based on what the question asks about or what topic the answer covers.

4. **ONE ANSWER PER SECTION**: Each physical section of the student's paper maps to EXACTLY ONE question.

5. **NULL if no marker found**: If you cannot find a question number marker that clearly matches a given question ID, return `null` for that ID.

6. **OCR CLEANING ONLY**: Fix obvious Sinhala OCR errors. Do NOT correct the student's actual content.

7. **NEVER INFER FROM CONTENT SIMILARITY**: If a student answer discusses the right topic but there is no visible marker for that exact question label, DO NOT map it.

8. **SUB-QUESTION STRICTNESS**: Do not map a text to `5(අ)`, `5(ආ)`, etc. unless the OCR contains a visible marker such as `5(අ)`, `5 අ`, `5.අ`, `(අ)` under question 5, or another clearly equivalent written marker.

========================
HOW TO FIND QUESTION MARKERS
========================
Look for these common student styles:
- Paper I: "1.", "2.", "3.", "1-", "2-", "(1)", "(2)", "1 ", "2 "
- Paper II: "1(a)", "1.a", "1 a", "1. (අ)", "(අ)", "ආ)", "1.අ"
- Sinhala labels: "1.", "2.", "3." (using Sinhala numerals if applicable, but usually standard digits)

Steps:
1. Scan the student text for Part/Section headers (I, II, III, etc.) to establish context.
2. For each question in the structure, find the corresponding marker in the correct context.
3. If multiple instances of "1" exist, use the "Part" context (e.g., text following a "Part II" header) to decide.
4. Short answers (MCQs) are often just a single word or number (e.g., "1. 3"). Capture these!

========================
INPUTS
========================
QUESTION STRUCTURE (JSON): Question IDs, labels, and the question text.
STUDENT ANSWER TEXT (OCR): Raw OCR text from the student's answer script.

========================
OUTPUT FORMAT (STRICT JSON)
========================
Return a raw JSON object: {{"id": "cleaned student text", ...}}
CRITICAL: The keys MUST BE the exact `id` string (UUID) from the structure.
ONLY include keys for questions that the student actually ATTEMPTED.
CRITICAL AVOID MAPPING QUESTION TEXT: If a section only contains the phrasing of the question itself, do NOT map it.

========================
QUESTION STRUCTURE
========================
{structure}

========================
STUDENT ANSWER TEXT
========================
{answer_text}
"""

PAPER_II_MAIN_BLOCK_PROMPT = """
You are a STRICT answer extraction AI for Sri Lankan exam papers.
You are given ONE already-isolated Paper II answer block for a single main question number.

Your job:
- map the student's writing inside this one block to the given sub-question IDs only
- return ONLY text that visibly appears in this block
- do NOT use topic matching from outside this block

Rules:
1. The OCR block already belongs to main question {main_no}. Do NOT map outside this main question.
2. Prefer visible sub-question markers like `(අ)`, `(ආ)`, `(ඇ)`, `අ)`, `ආ)`, `a`, `b`, `c`.
3. If inner sub-question markers are weak or missing, but the student clearly wrote multiple answers in sequence inside this same main-question block, split them in the same order as the provided structure.
4. If the block only supports one sub-question answer confidently, return only that one.
5. Copy the student's wording from the block. Only do light OCR cleanup.
6. Do NOT invent missing answers.

Return raw JSON only:
{{"uuid": "student answer text"}}

MAIN QUESTION NUMBER:
{main_no}

SUB-QUESTION STRUCTURE:
{structure}

OCR BLOCK:
{answer_text}
"""


def _is_hallucinated_question_text(mapped_text: str, q_text: str, threshold: float = 0.85) -> bool:
    """
    Detects if the mapped student answer is just a hallucination of the
    original printed question text from the paper.
    """
    if not q_text or not mapped_text or len(mapped_text.strip()) < 5:
        return False

    q_norm = q_text.strip().replace(" ", "")
    m_norm = mapped_text.strip().replace(" ", "")

    # Basic length check: if the student provided a very long answer,
    # it's likely not just a hallucinated question even if it contains the question.
    if len(m_norm) > len(q_norm) + 50:
        return False

    # Check exact match or very high similarity
    ratio = difflib.SequenceMatcher(None, q_norm[:len(m_norm)], m_norm).ratio()
    if ratio > threshold:
        return True

    # Check if the mapping is a substring of the question (often happens with OCR fragments)
    if len(m_norm) > 10 and m_norm in q_norm:
        return True

    return False


def _normalize_marker_text(text: str) -> str:
    # New helper: normalize OCR-heavy text before checking whether
    # a mapped snippet is actually anchored to a visible question marker.
    return re.sub(r'[\s\.,;:!?\-()\[\]{}"\'`]+', '', str(text or "").lower())


def _build_label_marker_patterns(label: str) -> list[str]:
    # New helper: build tolerant regex patterns for the label styles students
    # commonly write, so we validate mappings against markers, not semantics.
    raw_label = str(label or "").strip()
    if not raw_label:
        return []

    patterns = []
    normalized = _normalize_marker_text(raw_label)
    match = re.match(r'^(\d+)(?:\(([^\)]+)\))?$', raw_label)

    if match:
        main_no, sub_label = match.groups()
        if sub_label:
            sub_clean = re.escape(sub_label.strip())
            patterns.extend([
                rf'(?<!\d){re.escape(main_no)}\s*[\.\-:)]?\s*\(\s*{sub_clean}\s*\)',
                rf'(?<!\d){re.escape(main_no)}\s*[\.\-:)]?\s*{sub_clean}(?!\w)',
                rf'(?:(?<=\n)|(?<=\r)|^)\s*\(\s*{sub_clean}\s*\)',
                rf'(?:(?<=\n)|(?<=\r)|^)\s*{sub_clean}[\)\.\-:]',
            ])
        else:
            patterns.extend([
                rf'(?:(?<=\n)|(?<=\r)|^)\s*{re.escape(main_no)}[\)\.\-:\s]',
                rf'(?<!\d){re.escape(main_no)}\s*\)',
            ])

    if normalized:
        patterns.append(re.escape(normalized))

    # Preserve order while removing duplicates.
    seen = set()
    unique_patterns = []
    for pattern in patterns:
        if pattern not in seen:
            seen.add(pattern)
            unique_patterns.append(pattern)
    return unique_patterns


def _extract_main_and_sub_label(label: str) -> tuple[str, str]:
    # New helper: split a label like `2(අ)` into its main-question number and
    # sub-question marker so we can validate nearby OCR context more flexibly.
    raw_label = str(label or "").strip()
    match = re.match(r'^(\d+)(?:\(([^\)]+)\))?$', raw_label)
    if not match:
        return "", ""
    main_no, sub_label = match.groups()
    return (main_no or "").strip(), (sub_label or "").strip()


def _looks_like_main_number_context(window_text: str, main_no: str) -> bool:
    # New helper: accept OCR variants of the main question number as long as the
    # nearby text still looks like a numbered answer block.
    if not window_text or not main_no:
        return False

    patterns = [
        rf'(?:(?<=\n)|(?<=\r)|^)\s*{re.escape(main_no)}[\)\.\-:\s]',
        rf'(?<!\d){re.escape(main_no)}\s*\)',
        rf'(?<!\d){re.escape(main_no)}\s*[\.\-:]\s*',
    ]
    return any(re.search(pattern, window_text, flags=re.IGNORECASE | re.MULTILINE) for pattern in patterns)


def _build_sub_label_variants(sub_label: str) -> list[str]:
    # New helper: OCR can distort Sinhala sub-labels, so we tolerate the most
    # common nearby variants when checking whether the student wrote `(අ)/(ආ)/...`.
    raw = str(sub_label or "").strip()
    if not raw:
        return []

    variants = {raw}

    # Keep only Sinhala letters for OCR-tolerant matching.
    sinhala_only = "".join(ch for ch in raw if '\u0D80' <= ch <= '\u0DFF')
    if sinhala_only:
        variants.add(sinhala_only)
        variants.add(sinhala_only.replace("ැ", "ැ"))

    # Frequent OCR confusion in the current data: `(ඈඇ)` may appear as just
    # one of the visible glyphs, so keep the individual characters too.
    if len(sinhala_only) > 1:
        for ch in sinhala_only:
            variants.add(ch)

    return [v for v in variants if v]


def _has_nearby_subquestion_support(source_text: str, mapped_text: str, label: str) -> bool:
    """
    New fallback validator for Paper II sub-questions:
    if OCR weakens the exact sub-question marker, accept the mapping when the
    answer snippet appears near the right main-question number and a plausible
    nearby sub-label variant.
    """
    if not source_text or not mapped_text or not label:
        return False

    main_no, sub_label = _extract_main_and_sub_label(label)
    if not main_no or not sub_label:
        return False

    source = str(source_text)
    mapped_norm = _normalize_marker_text(mapped_text)
    sub_variants = _build_sub_label_variants(sub_label)
    if not mapped_norm or not sub_variants:
        return False

    main_patterns = [
        rf'(?:(?<=\n)|(?<=\r)|^)\s*{re.escape(main_no)}[\)\.\-:\s]',
        rf'(?<!\d){re.escape(main_no)}\s*\)',
    ]

    for pattern in main_patterns:
        for match in re.finditer(pattern, source, flags=re.IGNORECASE | re.MULTILINE):
            # New window strategy: look at the answer block immediately after the
            # main question marker instead of requiring an exact `2(අ)` style hit.
            window = source[match.start():match.start() + 1400]
            normalized_window = _normalize_marker_text(window)
            if mapped_norm not in normalized_window:
                continue

            if not _looks_like_main_number_context(window, main_no):
                continue

            if any(variant in normalized_window for variant in [_normalize_marker_text(v) for v in sub_variants]):
                return True

    return False


def _has_direct_marker_supported_mapping(source_text: str, mapped_text: str, label: str) -> bool:
    """
    New helper: keep the stricter marker checks separate from the relaxed
    main-block fallback so Paper II answers can be reassigned more safely later.
    """
    if not source_text or not mapped_text or not label:
        return False

    source = str(source_text)
    mapped_norm = _normalize_marker_text(mapped_text)
    if len(mapped_norm) < 4:
        return False

    marker_patterns = _build_label_marker_patterns(label)
    if not marker_patterns:
        return False

    normalized_source = _normalize_marker_text(source)

    for pattern in marker_patterns:
        if pattern == re.escape(_normalize_marker_text(label)):
            marker_match = re.search(pattern, normalized_source, flags=re.IGNORECASE)
            if not marker_match:
                continue
            start_idx = marker_match.start()
            window = normalized_source[start_idx:start_idx + 900]
            if mapped_norm in window:
                return True
            continue

        for match in re.finditer(pattern, source, flags=re.IGNORECASE | re.MULTILINE):
            window = source[match.start():match.start() + 900]
            if mapped_norm in _normalize_marker_text(window):
                return True

    return False


def _has_main_question_block_support(source_text: str, mapped_text: str, label: str) -> bool:
    """
    New fallback for handwritten Paper II answers: OCR often keeps the main
    question number but drops the inner `(අ)/(ආ)/(ඇ)` marker. In that case,
    accept the mapping if the full answer text clearly appears inside the
    numbered answer block for the correct main question.
    """
    if not source_text or not mapped_text or not label:
        return False

    main_no, sub_label = _extract_main_and_sub_label(label)
    if not main_no or not sub_label:
        return False

    mapped_text = str(mapped_text or "").strip()
    mapped_norm = _normalize_marker_text(mapped_text)
    if len(mapped_norm) < 20:
        return False

    # New safety gate: only relax the rule for substantial answer-like text so
    # we do not reintroduce the old short-snippet false mappings.
    if not _looks_like_full_main_answer(mapped_text):
        return False

    source = str(source_text)
    main_patterns = [
        rf'(?:(?<=\n)|(?<=\r)|^)\s*{re.escape(main_no)}[\)\.\-:\s]',
        rf'(?<!\d){re.escape(main_no)}\s*\)',
        rf'(?<!\d){re.escape(main_no)}\s*[\.\-:]\s*',
    ]

    numbered_answer_pattern = re.compile(
        r'(?:(?<=\n)|(?<=\r)|^)\s*\d+\s*[\)\.\-:\s]',
        flags=re.IGNORECASE | re.MULTILINE,
    )

    seen_starts = set()
    for pattern in main_patterns:
        for match in re.finditer(pattern, source, flags=re.IGNORECASE | re.MULTILINE):
            if match.start() in seen_starts:
                continue
            seen_starts.add(match.start())

            block_start = match.start()
            tail = source[block_start + 1:]
            next_match = numbered_answer_pattern.search(tail)
            block_end = len(source)
            if next_match:
                block_end = block_start + 1 + next_match.start()

            block = source[block_start:block_end]
            if mapped_norm in _normalize_marker_text(block):
                return True

    return False


def _extract_main_question_block(source_text: str, main_no: str) -> tuple[str, int]:
    """
    New helper: isolate the OCR block that begins at a Paper II main question
    number so deferred sub-question snippets can be reassigned by position.
    """
    if not source_text or not main_no:
        return "", -1

    source = str(source_text)
    main_patterns = [
        rf'(?:(?<=\n)|(?<=\r)|^)\s*{re.escape(main_no)}[\)\.\-:\s]',
        rf'(?<!\d){re.escape(main_no)}\s*\)',
        rf'(?<!\d){re.escape(main_no)}\s*[\.\-:]\s*',
    ]
    numbered_answer_pattern = re.compile(
        r'(?:(?<=\n)|(?<=\r)|^)\s*\d+\s*[\)\.\-:\s]',
        flags=re.IGNORECASE | re.MULTILINE,
    )

    best_match = None
    for pattern in main_patterns:
        match = re.search(pattern, source, flags=re.IGNORECASE | re.MULTILINE)
        if match and (best_match is None or match.start() < best_match.start()):
            best_match = match

    if not best_match:
        return "", -1

    block_start = best_match.start()
    tail = source[block_start + 1:]
    next_match = numbered_answer_pattern.search(tail)
    block_end = len(source)
    if next_match:
        block_end = block_start + 1 + next_match.start()

    return source[block_start:block_end], block_start


def _find_normalized_substring_index(haystack: str, needle: str) -> int:
    """
    New helper: find OCR answer snippets after normalization so ordering can be
    estimated even when spacing and punctuation drift.
    """
    haystack_norm = _normalize_marker_text(haystack)
    needle_norm = _normalize_marker_text(needle)
    if not haystack_norm or not needle_norm:
        return -1
    return haystack_norm.find(needle_norm)


def _split_answer_text_by_number_restart(answer_text: str) -> tuple[str, str]:
    """
    New helper: answer sheets usually restart numbering from `1` when Paper II
    begins. Split the OCR text at the last visible restart so Paper I and
    Paper II validators do not compete over the same repeated numbers.
    """
    text = str(answer_text or "")
    restart_pattern = re.compile(
        r'(?:(?<=\n)|(?<=\r)|^)\s*1[\)\.\-:\s]',
        flags=re.IGNORECASE | re.MULTILINE,
    )
    matches = list(restart_pattern.finditer(text))
    if len(matches) < 2:
        return text, text

    restart_at = matches[-1].start()
    return text[:restart_at], text[restart_at:]


def _get_part_specific_answer_text(answer_text: str, part_name: str) -> str:
    """
    New helper: isolate repeated numbering scopes so Paper II matching uses the
    OCR tail where long answers restart from `1`.
    """
    paper_i_text, paper_ii_text = _split_answer_text_by_number_restart(answer_text)
    normalized_part = str(part_name or "").strip().lower()

    if "paper_ii" in normalized_part or "part ii" in normalized_part:
        return paper_ii_text or str(answer_text or "")
    if "paper_i" in normalized_part or "part i" in normalized_part:
        return paper_i_text or str(answer_text or "")
    return str(answer_text or "")


def _has_marker_supported_mapping(source_text: str, mapped_text: str, label: str) -> bool:
    """
    New validation layer: keep Gemini in an extraction role by requiring
    source-text marker support for the returned answer snippet.
    """
    if not source_text or not mapped_text or not label:
        return False

    # New early decision: keep direct marker checks separate from relaxed
    # main-block support so Paper II reassignment can decide how to use each.
    if _has_direct_marker_supported_mapping(source_text, mapped_text, label):
        return True

    if _has_main_question_block_support(source_text, mapped_text, label):
        return True

    return False

    source = str(source_text)
    mapped_norm = _normalize_marker_text(mapped_text)
    if len(mapped_norm) < 4:
        return False

    marker_patterns = _build_label_marker_patterns(label)
    if not marker_patterns:
        return False

    normalized_source = _normalize_marker_text(source)

    for pattern in marker_patterns:
        if pattern == re.escape(_normalize_marker_text(label)):
            marker_match = re.search(pattern, normalized_source, flags=re.IGNORECASE)
            if not marker_match:
                continue
            start_idx = marker_match.start()
            window = normalized_source[start_idx:start_idx + 900]
            if mapped_norm in window:
                return True
            continue

        for match in re.finditer(pattern, source, flags=re.IGNORECASE | re.MULTILINE):
            window = source[match.start():match.start() + 900]
            if mapped_norm in _normalize_marker_text(window):
                return True

    # New fallback for Paper II style sub-questions where OCR often weakens the
    # exact `(අ)/(ආ)/(ඈඇ)` marker but still preserves nearby main-question context.
    if _has_nearby_subquestion_support(source_text, mapped_text, label):
        return True

    # New final fallback: some answer sheets preserve only the main question
    # number, so let full-length Paper II sub-answers pass when they clearly
    # belong to the correct numbered answer block.
    if _has_main_question_block_support(source_text, mapped_text, label):
        return True

    return False


def _looks_like_full_main_answer(mapped_text: str) -> bool:
    # New heuristic: main-question answers should look materially longer than
    # the short snippets that often belong to Paper I objective answers.
    text = str(mapped_text or "").strip()
    normalized = _normalize_marker_text(text)
    if len(normalized) >= 80:
        return True
    if len(re.findall(r'\S+', text)) >= 12:
        return True
    if len(re.findall(r'[.!?]|[।]|[\n\r]', text)) >= 2:
        return True
    if re.search(r'[\(\[]\s*[අආඇඈඉEeAaBbCcIiVv]+\s*[\)\]]', text):
        return True
    return False


def _suppress_cross_part_duplicate_mappings(all_mappings: dict, flat_structure: list) -> dict:
    """
    New safeguard: prevent the same short snippet from counting as both a
    Paper I answer and a Paper II main-question answer.
    """
    if not all_mappings:
        return all_mappings

    item_by_id = {str(item.get("id")): item for item in flat_structure}
    grouped: dict[str, list[tuple[str, str, dict]]] = {}

    for key, value in all_mappings.items():
        norm_text = _normalize_marker_text(value)
        if len(norm_text) < 4:
            continue
        grouped.setdefault(norm_text, []).append((key, value, item_by_id.get(str(key), {})))

    filtered = dict(all_mappings)
    for _, entries in grouped.items():
        if len(entries) < 2:
            continue

        keepers = []
        for key, value, item in entries:
            is_main_with_children = bool(item.get("has_sub_questions"))
            if is_main_with_children and not _looks_like_full_main_answer(value):
                logger.warning(
                    "Discarding duplicate short mapping for ID %s - looks like a short-answer snippet, not a full main-question answer.",
                    key,
                )
                filtered.pop(key, None)
                continue
            keepers.append((key, value, item))

        if keepers:
            continue

    return filtered


def _is_paper_ii_part(part_name: str) -> bool:
    # New helper: keep Paper II-specific recovery logic scoped to the long-answer
    # section where numbering restarts and sub-question markers are less reliable.
    normalized = str(part_name or "").strip().lower().replace(" ", "_")
    return normalized in {"paper_ii", "part_ii"} or "paper_ii" in normalized or "part_ii" in normalized


def _map_paper_ii_main_block_subparts(block_text: str, main_no: str, subparts: list[dict]) -> dict:
    # New helper: after isolating one numbered Paper II answer block, ask Gemini
    # to split only that block into the relevant sub-parts instead of guessing
    # sub-question labels from the whole answer script at once.
    if not block_text or not main_no or not subparts:
        return {}

    try:
        response_text = gemini_generate(
            PAPER_II_MAIN_BLOCK_PROMPT.format(
                main_no=main_no,
                structure=json.dumps(subparts, ensure_ascii=False, indent=2),
                answer_text=str(block_text)[:12000],
            ),
            json_mode=True,
        )
        parsed = _safe_json_loads(response_text) if response_text else {}
        if not isinstance(parsed, dict):
            return {}
        return parsed
    except Exception as e:
        logger.warning("Paper II main-block mapping failed for main %s: %s", main_no, e)
        return {}


def _reassign_paper_ii_main_block_candidates(
    answer_text: str,
    deferred_candidates: list[dict],
    chunk: list[dict],
    filtered_result: dict,
) -> None:
    """
    New post-pass for Paper II: when OCR only proves the main-question block,
    reassign the returned snippets to that main question's sub-parts in block
    order instead of trusting Gemini's guessed sub-label directly.
    """
    if not deferred_candidates:
        return

    deferred_by_main: dict[str, list[dict]] = {}
    for candidate in deferred_candidates:
        deferred_by_main.setdefault(candidate["main_no"], []).append(candidate)

    chunk_by_main: dict[str, list[dict]] = {}
    for item in chunk:
        if not item.get("is_sub_question"):
            continue
        main_no = str(item.get("parent_main_label") or "")
        chunk_by_main.setdefault(main_no, []).append(item)

    for main_no, candidates in deferred_by_main.items():
        block_text, _ = _extract_main_question_block(answer_text, main_no)
        if not block_text:
            continue

        ordered_subparts = chunk_by_main.get(main_no, [])
        if not ordered_subparts:
            continue

        accepted_ids = set(filtered_result.keys())
        remaining_subparts = [item for item in ordered_subparts if item["id"] not in accepted_ids]
        if not remaining_subparts:
            continue

        unique_candidates = {}
        for candidate in candidates:
            unique_candidates.setdefault(_normalize_marker_text(candidate["text"]), candidate)

        sorted_candidates = sorted(
            unique_candidates.values(),
            key=lambda candidate: (
                _find_normalized_substring_index(block_text, candidate["text"])
                if _find_normalized_substring_index(block_text, candidate["text"]) >= 0
                else 10**9
            ),
        )

        for sub_item, candidate in zip(remaining_subparts, sorted_candidates):
            filtered_result[sub_item["id"]] = candidate["text"]
            logger.info(
                "Reassigned deferred Paper II main-block answer from label %s to %s.",
                candidate.get("original_label"),
                sub_item.get("label"),
            )


def _fill_paper_ii_subparts_from_main_blocks(
    answer_text: str,
    chunk: list[dict],
    filtered_result: dict,
    allowed_main_nos: set[str] | None = None,
) -> None:
    """
    New recovery pass for Paper II:
    once a main-question block is isolated by number, map only that block to the
    remaining sub-parts so we do not depend on whole-paper leaf-label guesses.
    """
    subparts_by_main: dict[str, list[dict]] = {}
    for item in chunk:
        if not item.get("is_sub_question"):
            continue
        main_no = str(item.get("parent_main_label") or "")
        if not main_no:
            continue
        subparts_by_main.setdefault(main_no, []).append(item)

    for main_no, subparts in subparts_by_main.items():
        # New safety gate: only expand mains that already showed evidence in the
        # first whole-paper pass, so recovery does not invent extra attempted
        # mains like 3/6/7 just because a numbered block exists somewhere.
        if allowed_main_nos is not None and main_no not in allowed_main_nos:
            continue

        remaining_subparts = [item for item in subparts if item["id"] not in filtered_result]
        if not remaining_subparts:
            continue

        block_text, _ = _extract_main_question_block(answer_text, main_no)
        if not block_text or len(_normalize_marker_text(block_text)) < 20:
            continue

        block_result = _map_paper_ii_main_block_subparts(block_text, main_no, remaining_subparts)
        if not isinstance(block_result, dict):
            continue

        normalized_block = _normalize_marker_text(block_text)
        remaining_ids = {item["id"] for item in remaining_subparts}
        for key, value in block_result.items():
            if key not in remaining_ids or not value:
                continue

            value_norm = _normalize_marker_text(value)
            if len(value_norm) < 6 or value_norm not in normalized_block:
                continue

            filtered_result[key] = value
            target = next((item for item in remaining_subparts if item["id"] == key), None)
            logger.info(
                "Recovered Paper II sub-part %s from isolated main-question block %s.",
                target.get("label") if target else key,
                main_no,
            )


def _fill_missing_paper_ii_subparts_from_surfaced_candidates(
    answer_text: str,
    chunk: list[dict],
    filtered_result: dict,
    surfaced_candidates_by_main: dict[str, list[dict]],
    allowed_main_nos: set[str] | None = None,
) -> None:
    """
    New final fallback for Paper II:
    if Gemini already surfaced plausible sub-part answers for a real attempted
    main question, reuse those raw candidates to fill any still-missing sub-part
    slots inside that same main block.
    """
    subparts_by_main: dict[str, list[dict]] = {}
    for item in chunk:
        if not item.get("is_sub_question"):
            continue
        main_no = str(item.get("parent_main_label") or "")
        if not main_no:
            continue
        subparts_by_main.setdefault(main_no, []).append(item)

    for main_no, subparts in subparts_by_main.items():
        if allowed_main_nos is not None and main_no not in allowed_main_nos:
            continue

        remaining_subparts = [item for item in subparts if item["id"] not in filtered_result]
        if not remaining_subparts:
            continue

        raw_candidates = surfaced_candidates_by_main.get(main_no, [])
        if not raw_candidates:
            continue

        block_text, _ = _extract_main_question_block(answer_text, main_no)
        if not block_text:
            continue

        existing_norms = {
            _normalize_marker_text(filtered_result[item["id"]])
            for item in subparts
            if item["id"] in filtered_result and filtered_result.get(item["id"])
        }

        unique_candidates = {}
        normalized_block = _normalize_marker_text(block_text)
        for candidate in raw_candidates:
            value = str(candidate.get("text") or "").strip()
            value_norm = _normalize_marker_text(value)
            if (
                len(value_norm) < 6
                or value_norm in existing_norms
                or value_norm not in normalized_block
            ):
                continue
            unique_candidates.setdefault(value_norm, candidate)

        if not unique_candidates:
            continue

        sorted_candidates = sorted(
            unique_candidates.values(),
            key=lambda candidate: (
                _find_normalized_substring_index(block_text, candidate["text"])
                if _find_normalized_substring_index(block_text, candidate["text"]) >= 0
                else 10**9
            ),
        )

        for sub_item, candidate in zip(remaining_subparts, sorted_candidates):
            filtered_result[sub_item["id"]] = candidate["text"]
            logger.info(
                "Filled missing Paper II sub-part %s from surfaced main-block candidate for main %s.",
                sub_item.get("label"),
                main_no,
            )


def _run_paper_ii_recovery_passes(
    answer_text: str,
    chunk: list[dict],
    filtered_result: dict,
    deferred_main_block_candidates: list[dict],
    evidenced_main_nos: set[str],
    surfaced_candidates_by_main: dict[str, list[dict]],
) -> None:
    """
    Keep the newer Paper II recovery flow together so cleanup stays scoped to the
    evaluation mapping path without touching older learning-mode helpers.
    """
    allowed_main_nos = {main_no for main_no in evidenced_main_nos if main_no}
    if not allowed_main_nos:
        return

    _reassign_paper_ii_main_block_candidates(
        answer_text,
        deferred_main_block_candidates,
        chunk,
        filtered_result,
    )
    _fill_paper_ii_subparts_from_main_blocks(
        answer_text,
        chunk,
        filtered_result,
        allowed_main_nos=allowed_main_nos,
    )
    _fill_missing_paper_ii_subparts_from_surfaced_candidates(
        answer_text,
        chunk,
        filtered_result,
        surfaced_candidates_by_main,
        allowed_main_nos=allowed_main_nos,
    )

def map_student_answers(answer_text: str, question_structure: list) -> dict:
    """
    Maps student answer text to question IDs using Gemini.
    Processes questions in batches for robustness.
    """
    if not answer_text or not answer_text.strip():
        return {}

    try:
        logger.info("Starting student answer mapping by parts.")
        flat_structure = _simplify_structure_for_prompt(question_structure)
        
        # Group by part to maintain context
        parts_map = {}
        for item in flat_structure:
            part = item.get("part") or "Unknown"
            if part not in parts_map:
                parts_map[part] = []
            parts_map[part].append(item)
            
        all_mappings = {}
        batch_size = 100  # Process all questions in a part together to prevent misattribution
        
        for part_name, part_items in parts_map.items():
            logger.info("Mapping part: %s (%d items)", part_name, len(part_items))
            # New part isolation: repeated numbering restarts between Paper I and
            # Paper II, so validate each part against its own OCR region.
            part_answer_text = _get_part_specific_answer_text(answer_text, part_name)
            for i in range(0, len(part_items), batch_size):
                chunk = part_items[i : i + batch_size]
                logger.info("Processing batch %d for %s", (i // batch_size) + 1, part_name)
                chunk_ids = {item["id"] for item in chunk}
                
                def _call_mapping(c):
                    return gemini_generate(
                        ANSWER_MAPPING_PROMPT.format(
                            structure=json.dumps(c, ensure_ascii=False, indent=2),
                            answer_text=part_answer_text[:35000],
                        ),
                        json_mode=True,
                    )

                response_text = _call_mapping(chunk)
                print(f"=== RAW GEMINI RESPONSE FOR {part_name} ===")
                print(response_text)
                print("=============================================")
                batch_result = _safe_json_loads(response_text) if response_text else None

                # Retry on BOTH empty response AND JSON parse failure
                if not isinstance(batch_result, dict):
                    reason = "empty response" if not response_text else "JSON parse failure"
                    logger.warning("Batch mapping for %s batch %d: %s — retrying...",
                                   part_name, (i // batch_size) + 1, reason)
                    response_text = _call_mapping(chunk)
                    batch_result = _safe_json_loads(response_text) if response_text else None

                if isinstance(batch_result, dict):
                    # We accept any key that the model returned, as long as it's in the original structure chunk
                    filtered_result = {}
                    deferred_main_block_candidates = []
                    evidenced_main_nos: set[str] = set()
                    surfaced_candidates_by_main: dict[str, list[dict]] = {}
                    for k, v in batch_result.items():
                        if k in chunk_ids and v:
                            # Find original question text for hallucination check
                            q_item = next((item for item in chunk if item["id"] == k), None)
                            q_text = q_item.get("text", "") if q_item else ""
                            q_label = q_item.get("label", "") if q_item else ""

                            if _is_hallucinated_question_text(v, q_text):
                                logger.warning(f"Discarding hallucinated answer for ID {k} - matches question text.")
                                continue

                            # New recovery signal: if Gemini surfaced a non-hallucinated
                            # Paper II sub-question at all, treat its parent main number as
                            # worth a block-level retry even if strict marker validation
                            # fails on this first pass.
                            if q_item and q_item.get("is_sub_question") and _is_paper_ii_part(part_name):
                                parent_main = str(q_item.get("parent_main_label") or "")
                                evidenced_main_nos.add(parent_main)
                                surfaced_candidates_by_main.setdefault(parent_main, []).append({
                                    "id": k,
                                    "text": v,
                                    "original_label": q_label,
                                })

                            # New decision split: keep direct marker matches as-is,
                            # but defer Paper II main-block-only hits so they can be
                            # reassigned to sub-parts in their actual OCR order.
                            if _has_direct_marker_supported_mapping(part_answer_text, v, q_label):
                                filtered_result[k] = v
                                if q_item and q_item.get("is_sub_question"):
                                    evidenced_main_nos.add(str(q_item.get("parent_main_label") or ""))
                                continue

                            if (
                                q_item
                                and q_item.get("is_sub_question")
                                and _has_main_question_block_support(part_answer_text, v, q_label)
                            ):
                                evidenced_main_nos.add(str(q_item.get("parent_main_label") or ""))
                                deferred_main_block_candidates.append({
                                    "id": k,
                                    "text": v,
                                    "main_no": str(q_item.get("parent_main_label") or ""),
                                    "original_label": q_label,
                                })
                                continue

                            # Existing guard: if neither direct marker support nor
                            # the deferred Paper II main-block path applies, reject it.
                            if not _has_marker_supported_mapping(part_answer_text, v, q_label):
                                logger.warning(
                                    "Discarding unsupported mapping for ID %s - no matching source marker found for label %s.",
                                    k,
                                    q_label,
                                )
                                continue

                            filtered_result[k] = v

                    if _is_paper_ii_part(part_name):
                        _run_paper_ii_recovery_passes(
                            part_answer_text,
                            chunk,
                            filtered_result,
                            deferred_main_block_candidates,
                            evidenced_main_nos,
                            surfaced_candidates_by_main,
                        )

                    all_mappings.update(filtered_result)
                    initial_supported_count = sum(1 for result_id in batch_result.keys() if result_id in chunk_ids)
                    recovered_count = max(0, len(filtered_result) - initial_supported_count)
                    discarded_count = max(0, initial_supported_count - len(filtered_result) + recovered_count)
                    logger.info(
                        "Batch %d for %s: got %d/%d valid mappings (discarded %d initial outputs, recovered %d via Paper II post-pass).",
                        (i // batch_size) + 1,
                        part_name,
                        len(filtered_result),
                        len(chunk),
                        discarded_count,
                        recovered_count,
                    )
                else:
                    logger.error("Batch %d for %s: FAILED after retry — skipping batch.",
                                 (i // batch_size) + 1, part_name)


        # New post-pass: remove short duplicate snippets that would otherwise
        # be counted in both Paper I and Paper II.
        all_mappings = _suppress_cross_part_duplicate_mappings(all_mappings, flat_structure)
        logger.info("Mapped %d answers total across all parts.", len(all_mappings))
        return all_mappings

    except Exception as e:
        logger.error(f"❌ Error in answer mapping: {e}")
        return {}

def map_student_answers(answer_text: str, question_structure: list) -> dict:
    """
    Maps student answer text to question IDs using a single Gemini request.
    Local validation still rejects hallucinated or unsupported mappings.
    """
    if not answer_text or not answer_text.strip():
        return {}

    try:
        logger.info("Starting student answer mapping in one pass.")
        flat_structure = _simplify_structure_for_prompt(question_structure)
        response_text = gemini_generate_evaluation(
            ANSWER_MAPPING_PROMPT.format(
                structure=json.dumps(flat_structure, ensure_ascii=False, indent=2),
                answer_text=answer_text[:35000],
            ),
            budget=EvaluationGeminiClient.ANSWER_MAPPING,
            json_mode=True,
            reason="single_pass_full_paper",
        )
        print("=== RAW GEMINI RESPONSE FOR SINGLE-PASS ANSWER MAPPING ===")
        print(response_text)
        print("========================================================")
        batch_result = _safe_json_loads(response_text) if response_text else None

        if not isinstance(batch_result, dict):
            logger.error("Single-pass answer mapping failed: invalid JSON or empty response.")
            return {}

        by_id = {item["id"]: item for item in flat_structure}
        part_text_cache: dict[str, str] = {}
        filtered_result = {}

        for key, value in batch_result.items():
            if key not in by_id or not value:
                continue

            q_item = by_id[key]
            q_text = q_item.get("text", "")
            q_label = q_item.get("label", "")
            part_name = q_item.get("part") or "Unknown"
            if part_name not in part_text_cache:
                part_text_cache[part_name] = _get_part_specific_answer_text(answer_text, part_name)
            part_answer_text = part_text_cache[part_name]

            if _is_hallucinated_question_text(value, q_text):
                logger.warning("Discarding hallucinated answer for ID %s - matches question text.", key)
                continue

            if not _has_marker_supported_mapping(part_answer_text, value, q_label):
                logger.warning(
                    "Discarding unsupported mapping for ID %s - no matching source marker found for label %s.",
                    key,
                    q_label,
                )
                continue

            filtered_result[key] = value

        filtered_result = _suppress_cross_part_duplicate_mappings(filtered_result, flat_structure)
        logger.info(
            "Single-pass answer mapping completed. accepted=%d requested=%d",
            len(filtered_result),
            len(flat_structure),
        )
        return filtered_result

    except Exception as e:
        logger.error(f"Error in answer mapping: {e}")
        return {}


def _simplify_structure_for_prompt(questions: list) -> list:
    """
    Helper to create a flat list of all questions and sub-questions for the AI prompt.
    """
    flat_list = []
    
    def process_sub_questions(sub_qs, parent_label, parent_part):
        for sq in sub_qs:
            full_label = f"{parent_label}({sq.label})"
            flat_list.append({
                "id": str(sq.id),
                "label": full_label,
                "part": parent_part,  # inherit parent's part for correct grouping
                "text": sq.sub_question_text[:200] if sq.sub_question_text else "",
                # New metadata: keep the parent main label so Paper II sub-parts
                # can be reassigned within the correct numbered answer block.
                "parent_main_label": parent_label,
                "is_sub_question": True,
            })
            # Handle recursive children
            children = getattr(sq, "children", [])
            if children:
                process_sub_questions(children, full_label, parent_part)

    for q in questions:
        q_part = getattr(q, "part_name", "") or ""
        # Add the main question
        flat_list.append({
            "id": str(q.id),
            "label": q.question_number,
            "part": q_part,
            "text": q.question_text[:200] if q.question_text else "",
            # New flag used by duplicate suppression to detect main questions
            # that should contain a fuller answer block.
            "has_sub_questions": bool(getattr(q, "sub_questions", [])),
            "parent_main_label": q.question_number,
            "is_sub_question": False,
        })
        
        # Add all sub-questions recursively, inheriting parent's part
        sub_qs = getattr(q, "sub_questions", [])
        if sub_qs:
            process_sub_questions(sub_qs, q.question_number, q_part)

            
    return flat_list

RUBRIC_EXTRACT_PROMPT = """
You are an expert examiner. Extract the marking scheme (correct answers) from the provided text.
Identify each question number/label and its corresponding "Correct Answer" or "Acceptable Point".

Format: STRICT JSON object where keys are question labels (e.g., "1", "1(a)", "1.ii") and values are the correct answer string.

Guidelines:
- MCQs: Use the option number (1, 2, 3, 4) or text.
- Essays: Concise bullet points of the expected answer.
- Preserve original labels as they appear (e.g., 1අ, 1a).

TEXT:
{content}
"""

def extract_rubric_answers(text: str) -> dict:
    """
    Extracts a mapping of question identifiers to correct answers from rubric text.
    """
    if not text or len(text.strip()) < 10:
        return {}
        
    try:
        logger.info("Extracting structured answers from rubric.")
        response_text = gemini_generate(
            RUBRIC_EXTRACT_PROMPT.format(content=text[:20000]),
            json_mode=True
        )
        if not response_text:
            return {}
            
        return _safe_json_loads(response_text)
    except Exception as e:
        logger.error(f"Error extracting rubric answers: {e}")
        return {}
def _simplify_sub_questions(sub_questions: list) -> list:
    simple_subs = []
    for sq in sub_questions:
        sq_obj = {
            "id": str(sq.id),
            "label": sq.label,
            "text": sq.sub_question_text[:50] if sq.sub_question_text else ""
        }
        children = getattr(sq, "children", [])
        if children:
            sq_obj["children"] = _simplify_sub_questions(children)
        simple_subs.append(sq_obj)
    return simple_subs

def generate_session_title(message_content: str) -> str:
    """
    Generate an intelligent session title using a lightweight Gemini model.
    Uses gemini-1.5-flash-8b for faster processing and reduced rate limiting.
    """
    if not message_content or not message_content.strip():
        return "New Chat"
    
    try:
        # Use lightweight model for title generation to avoid rate limits
        title = gemini_generate_lightweight(message_content[:500])  # Shorter input
        
        # Fallback if generation fails or returns empty
        if not title or len(title) > 80:  # Stricter length limit
            return "New Chat"
            
        logger.info(f"Generated session title: {title}")
        return title
        
    except Exception as e:
        logger.error(f"Error generating session title: {e}")
        return "New Chat"
