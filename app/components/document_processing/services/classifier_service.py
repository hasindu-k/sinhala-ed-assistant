# app/components/document_processing/services/classifier_service.py

import json
import logging
import difflib
import re
from app.shared.ai.gemini_client import gemini_generate, gemini_generate_lightweight

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
        
    return text
    

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
        corrected = gemini_generate(prompt).strip()
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

        response_text = gemini_generate(
            COMBINED_EXAM_PROMPT.format(content=text[:30000]),
            json_mode=True
        )

        result = _safe_json_loads(response_text)
        if not result or not isinstance(result, dict):
            return {}
            
        logger.info("Combined exam extraction completed successfully.")
        
        # 🔒 Generic Normalization: Accept any "Paper_*" keys
        cleaned_result = {
            k: v
            for k, v in result.items()
            if (
                isinstance(k, str)
                and (k.startswith("Paper_") or k.startswith("Part_") or k.startswith("Section_"))
                and v is not None
            )
        }
        cleaned_result = _annotate_exam_structure_metadata(cleaned_result)
        _log_detected_exam_structure(cleaned_result)
        return cleaned_result

    except json.JSONDecodeError:
        logger.error("❌ Error: Model output was not valid JSON.")
        return {}

    except Exception as e:
        logger.error(f"❌ Error in combined extraction: {e}")
        return {}

def _normalize_section_key(value: str) -> str:
    return re.sub(r'[^a-z0-9]+', '_', str(value or "").strip().lower()).strip('_')


def _looks_like_mcq_question(question_data: dict) -> bool:
    if not isinstance(question_data, dict):
        return False

    options = question_data.get("options")
    if isinstance(options, list) and len(options) >= 2:
        return True

    q_type = str(question_data.get("type") or "").strip().lower()
    if q_type == "mcq":
        return True

    text = str(question_data.get("text") or "")
    option_markers = re.findall(r'[\(\[](?:[1-4]|[A-Da-d]|[අආඇඈඉ])[\)\]]', text)
    return len(option_markers) >= 2


def _infer_question_type_from_parsed_data(question_data: dict) -> str:
    if not isinstance(question_data, dict):
        return "unknown"

    declared_type = str(question_data.get("type") or "").strip().lower()
    if declared_type in {"mcq", "essay", "structured", "short"}:
        return declared_type

    if _looks_like_mcq_question(question_data):
        return "mcq"

    sub_questions = question_data.get("sub_questions")
    if isinstance(sub_questions, dict) and sub_questions:
        return "structured"

    marks = question_data.get("marks")
    try:
        marks_value = int(marks) if marks is not None else None
    except Exception:
        marks_value = None

    text = str(question_data.get("text") or "").strip()
    word_count = len(re.findall(r'\w+', text))

    if marks_value is not None:
        if marks_value <= 2:
            return "short"
        if marks_value >= 8:
            return "essay"
        return "structured"

    if word_count >= 18:
        return "essay"
    if word_count <= 8:
        return "short"
    return "structured"


def _infer_section_type(section_key: str, paper_data: dict) -> tuple[str, dict]:
    questions = (paper_data or {}).get("questions", {}) or {}
    counts = {}

    for q_data in questions.values():
        q_type = _infer_question_type_from_parsed_data(q_data)
        counts[q_type] = counts.get(q_type, 0) + 1

    if not counts:
        fallback = str(((paper_data or {}).get("config", {}) or {}).get("question_type") or "").strip().lower()
        if fallback:
            return fallback, {fallback: 0}
        return "unknown", {}

    non_zero_types = [q_type for q_type, count in counts.items() if count > 0]
    if len(non_zero_types) == 1:
        return non_zero_types[0], counts
    return "mixed", counts


def _infer_numbering_scope(section_index: int, questions_dict: dict) -> str:
    question_numbers = [str(key).strip() for key in (questions_dict or {}).keys()]
    normalized_numbers = {
        re.sub(r'[^0-9]+', '', value)
        for value in question_numbers
        if re.sub(r'[^0-9]+', '', value)
    }

    if "1" in normalized_numbers:
        return "restarts_at_1" if section_index > 0 else "starts_at_1"
    return "custom_or_continuous"


def _annotate_exam_structure_metadata(parsed_result: dict) -> dict:
    annotated = {}

    for section_index, (section_key, section_data) in enumerate(parsed_result.items()):
        if not isinstance(section_data, dict):
            annotated[section_key] = section_data
            continue

        section_copy = dict(section_data)
        config = dict(section_copy.get("config", {}) or {})
        questions = dict(section_copy.get("questions", {}) or {})

        detected_section_type, question_type_counts = _infer_section_type(section_key, section_copy)
        numbering_scope = _infer_numbering_scope(section_index, questions)

        config["detected_section_type"] = detected_section_type
        config["question_type_counts"] = question_type_counts
        config["numbering_scope"] = numbering_scope
        config["section_key_normalized"] = _normalize_section_key(section_key)
        section_copy["config"] = config

        for q_num, q_data in questions.items():
            if not isinstance(q_data, dict):
                continue
            q_copy = dict(q_data)
            q_copy["detected_question_type"] = _infer_question_type_from_parsed_data(q_copy)
            q_copy["section_key"] = section_key
            q_copy["numbering_scope"] = numbering_scope
            questions[q_num] = q_copy

        section_copy["questions"] = questions
        annotated[section_key] = section_copy

    return annotated


def _log_detected_exam_structure(parsed_result: dict) -> None:
    for section_key, section_data in (parsed_result or {}).items():
        if not isinstance(section_data, dict):
            continue

        config = section_data.get("config", {}) or {}
        questions = section_data.get("questions", {}) or {}
        logger.info(
            "[SECTION_DETECT] section=%s | type=%s | numbering_scope=%s | questions=%d | qtypes=%s",
            section_key,
            config.get("detected_section_type", "unknown"),
            config.get("numbering_scope", "unknown"),
            len(questions),
            config.get("question_type_counts", {}),
        )

        for q_num, q_data in questions.items():
            if not isinstance(q_data, dict):
                continue
            logger.info(
                "[QUESTION_TYPE] section=%s | q=%s | detected_type=%s | marks=%s | has_subquestions=%s",
                section_key,
                q_num,
                q_data.get("detected_question_type", "unknown"),
                q_data.get("marks"),
                bool(q_data.get("sub_questions")),
            )

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
6a. **NO PARAPHRASING / NO REWRITING**: Return only text that is visibly present in the OCR. Do NOT rewrite, summarize, improve grammar, or add missing words.
6b. **EXTRACTIVE OUTPUT ONLY**: Prefer copying the shortest exact span that still represents the student's answer.

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
CRITICAL: Every value must be extractive. If you cannot point to visible OCR text for it, omit it.

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
- do NOT paraphrase or rewrite the student's answer

Rules:
1. The OCR block already belongs to main question {main_no}. Do NOT map outside this main question.
2. Prefer visible sub-question markers like `(අ)`, `(ආ)`, `(ඇ)`, `අ)`, `ආ)`, `a`, `b`, `c`.
3. If inner sub-question markers are weak or missing, but the student clearly wrote multiple answers in sequence inside this same main-question block, split them in the same order as the provided structure.
4. If the block only supports one sub-question answer confidently, return only that one.
5. Copy the student's wording from the block. Only do light OCR cleanup.
6. Return the shortest exact OCR-supported span for each sub-question, not a rewritten explanation.
7. If a candidate requires paraphrasing or reconstruction, do NOT return it.
8. Do NOT invent missing answers.

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
    match = re.match(r'^([^\(\)\s]+)(?:\(([^\)]+)\))?$', raw_label)

    if match:
        main_no, sub_label = match.groups()
        main_token = re.escape(main_no.strip())
        if sub_label:
            sub_clean = re.escape(sub_label.strip())
            patterns.extend([
                rf'(?<!\w){main_token}\s*[\.\-:)]?\s*\(\s*{sub_clean}\s*\)',
                rf'(?<!\w){main_token}\s*[\.\-:)]?\s*{sub_clean}(?!\w)',
                rf'(?:(?<=\n)|(?<=\r)|^)\s*\(\s*{sub_clean}\s*\)',
                rf'(?:(?<=\n)|(?<=\r)|^)\s*{sub_clean}[\)\.\-:]',
            ])
        else:
            patterns.extend([
                rf'(?:(?<=\n)|(?<=\r)|^)\s*{main_token}[\)\.\-:\s]',
                rf'(?<!\w){main_token}\s*\)',
                rf'(?<!\w){main_token}\s*[\.\-:]\s*',
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
    match = re.match(r'^([^\(\)\s]+)(?:\(([^\)]+)\))?$', raw_label)
    if not match:
        return "", ""
    main_no, sub_label = match.groups()
    return (main_no or "").strip(), (sub_label or "").strip()


def _extract_plain_main_label_value(label: str) -> str:
    main_label, sub_label = _extract_main_and_sub_label(label)
    if sub_label:
        return ""
    return str(main_label or "").strip()


def _looks_like_main_number_context(window_text: str, main_no: str) -> bool:
    # New helper: accept OCR variants of the main question number as long as the
    # nearby text still looks like a numbered answer block.
    if not window_text or not main_no:
        return False

    patterns = [
        rf'(?:(?<=\n)|(?<=\r)|^)\s*{re.escape(main_no)}[\)\.\-:\s]',
        rf'(?<!\w){re.escape(main_no)}\s*\)',
        rf'(?<!\w){re.escape(main_no)}\s*[\.\-:]\s*',
    ]
    return any(re.search(pattern, window_text, flags=re.IGNORECASE | re.MULTILINE) for pattern in patterns)


def _build_sub_label_variants(sub_label: str) -> list[str]:
    # New helper: OCR can distort Sinhala sub-labels, so we tolerate the most
    # common nearby variants when checking whether the student wrote `(අ)/(ආ)/...`.
    raw = str(sub_label or "").strip()
    if not raw:
        return []

    variants = {raw, raw.lower(), raw.upper()}

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


def _looks_like_structured_short_answer(mapped_text: str) -> bool:
    # New heuristic for Paper I style numbered answers: these are shorter than
    # full essay blocks, but still substantial enough that we can anchor them to
    # a numbered OCR block safely.
    text = str(mapped_text or "").strip()
    normalized = _normalize_marker_text(text)
    if len(normalized) >= 18:
        return True
    if len(re.findall(r'\S+', text)) >= 5:
        return True
    return False


def _extract_numeric_label_value(label: str) -> int | None:
    raw_label = str(label or "").strip()
    match = re.match(r'^(\d+)', raw_label)
    if not match:
        return None
    try:
        return int(match.group(1))
    except Exception:
        return None


def _extract_numbered_answer_blocks(
    source_text: str,
    expected_numbers: set[str] | None = None,
) -> list[dict]:
    """
    Build a reusable OCR block index for evaluation answer sheets.
    We prefer visible numbered starts, but allow slightly looser separators than
    strict line starts because OCR often collapses newlines between answers.
    """
    text = str(source_text or "")
    if not text.strip():
        return []

    candidate_pattern = re.compile(
        r'(^|[\r\n]|[ \t]{2,})\s*([A-Za-z]+|\d{1,2})\s*[\)\.\-:]?(?=\s)',
        flags=re.IGNORECASE | re.MULTILINE,
    )
    matches = []
    seen_starts: set[int] = set()

    for match in candidate_pattern.finditer(text):
        number = str(match.group(2) or "").strip()
        if not number:
            continue
        normalized_number = number.upper() if re.fullmatch(r'[A-Za-z]+', number) else number
        if expected_numbers and normalized_number not in expected_numbers and number not in expected_numbers:
            continue

        start = match.start(2)
        if start in seen_starts:
            continue
        seen_starts.add(start)
        matches.append((start, normalized_number))

    blocks: list[dict] = []
    for idx, (start, number) in enumerate(matches):
        end = matches[idx + 1][0] if idx + 1 < len(matches) else len(text)
        block_text = text[start:end].strip()
        if not block_text:
            continue
        blocks.append({
            "number": number,
            "start": start,
            "text": block_text,
        })

    return blocks


def _extract_plain_numbered_blocks(source_text: str) -> list[dict]:
    """
    New helper for Paper I style sheets: split OCR into numbered answer blocks
    like `1. ...`, `2) ...`, etc., so validation can anchor to the student's
    numbering flow before looking at semantics.
    """
    return _extract_numbered_answer_blocks(source_text)


def _char_ngram_overlap_ratio(text_a: str, text_b: str, n: int = 3) -> float:
    norm_a = _normalize_marker_text(text_a)
    norm_b = _normalize_marker_text(text_b)
    if len(norm_a) < n or len(norm_b) < n:
        return 0.0

    ngrams_a = {norm_a[i:i + n] for i in range(len(norm_a) - n + 1)}
    ngrams_b = {norm_b[i:i + n] for i in range(len(norm_b) - n + 1)}
    if not ngrams_a or not ngrams_b:
        return 0.0

    return len(ngrams_a & ngrams_b) / max(1, min(len(ngrams_a), len(ngrams_b)))


def _token_overlap_ratio(text_a: str, text_b: str) -> float:
    tokens_a = {
        token for token in re.findall(r'\w+', str(text_a or "").lower(), flags=re.UNICODE)
        if len(token) >= 2
    }
    tokens_b = {
        token for token in re.findall(r'\w+', str(text_b or "").lower(), flags=re.UNICODE)
        if len(token) >= 2
    }
    if not tokens_a or not tokens_b:
        return 0.0
    return len(tokens_a & tokens_b) / max(1, min(len(tokens_a), len(tokens_b)))


def _is_supported_by_block(block_text: str, candidate_text: str) -> bool:
    """
    Evaluation-only block support check for long OCR answers.
    Exact normalized containment is ideal, but long Sinhala OCR answers often
    drift enough that we need overlap-based acceptance inside the same detected
    main-question block.
    """
    block_norm = _normalize_marker_text(block_text)
    value_norm = _normalize_marker_text(candidate_text)
    if len(value_norm) < 6 or not block_norm:
        return False

    if value_norm in block_norm:
        return True

    char_overlap = _char_ngram_overlap_ratio(candidate_text, block_text)
    token_overlap = _token_overlap_ratio(candidate_text, block_text)

    if len(value_norm) >= 80:
        return char_overlap >= 0.18 or token_overlap >= 0.40
    return char_overlap >= 0.24 or token_overlap >= 0.48


def _extractive_units_from_block(block_text: str) -> list[str]:
    text = str(block_text or "").strip()
    if not text:
        return []

    normalized_lines = []
    for line in re.split(r'[\r\n]+', text):
        line = line.strip()
        if not line:
            continue
        parts = re.split(r'\s*[ං•●▪]\s*', line)
        for part in parts:
            part = part.strip(" -:\t")
            if part:
                normalized_lines.append(part)
    return normalized_lines or [text]


def _extract_supported_span_from_block(block_text: str, candidate_text: str) -> str:
    """
    Prefer the student's OCR span over Gemini's cleaned wording.
    When exact containment is unavailable, choose the closest OCR segment from
    the same detected block so grading remains extractive.
    """
    text = str(block_text or "").strip()
    candidate = str(candidate_text or "").strip()
    if not text or not candidate:
        return candidate

    block_norm = _normalize_marker_text(text)
    candidate_norm = _normalize_marker_text(candidate)
    if candidate_norm and candidate_norm in block_norm:
        return candidate

    units = _extractive_units_from_block(text)
    best_span = ""
    best_score = 0.0

    for start in range(len(units)):
        combined = ""
        for end in range(start, min(len(units), start + 3)):
            combined = f"{combined} {units[end]}".strip()
            char_overlap = _char_ngram_overlap_ratio(candidate, combined)
            token_overlap = _token_overlap_ratio(candidate, combined)
            score = max(char_overlap, token_overlap)
            if score > best_score:
                best_score = score
                best_span = combined

    if best_span:
        return best_span
    return candidate


def _extract_supported_span_for_label(source_text: str, candidate_text: str, label: str) -> str:
    """
    Normalize accepted mappings back to OCR-supported spans for the specific
    labeled answer block whenever possible.
    """
    source = str(source_text or "")
    candidate = str(candidate_text or "").strip()
    if not source or not candidate:
        return candidate

    main_label, _ = _extract_main_and_sub_label(label)
    if main_label:
        block_text, _ = _extract_main_question_block(source, main_label)
        if block_text and _is_supported_by_block(block_text, candidate):
            return _extract_supported_span_from_block(block_text, candidate)

    if _is_supported_by_block(source, candidate):
        return _extract_supported_span_from_block(source, candidate)

    return candidate


def _looks_like_subanswer_unit(unit_text: str) -> bool:
    text = str(unit_text or "").strip()
    if not text:
        return False
    norm = _normalize_marker_text(text)
    if len(norm) < 18:
        return False
    if len(re.findall(r'\S+', text)) < 4:
        return False
    return True


def _fill_paper_ii_subparts_from_ordered_ocr_units(
    answer_text: str,
    chunk: list[dict],
    filtered_result: dict,
    allowed_main_nos: set[str] | None = None,
) -> None:
    """
    Final fast extractive fallback for Paper II:
    if a main-answer block visibly contains multiple OCR-separated units, assign
    those units to the remaining subparts in order without asking Gemini again.
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

        block_text, _ = _extract_main_question_block(answer_text, main_no)
        if not block_text:
            continue

        bullet_count = len(re.findall(r'[ං•●▪]', block_text))
        if bullet_count < max(1, len(remaining_subparts) - 1):
            continue

        existing_norms = {
            _normalize_marker_text(filtered_result[item["id"]])
            for item in subparts
            if item["id"] in filtered_result and filtered_result.get(item["id"])
        }

        candidate_units = []
        for unit in _extractive_units_from_block(block_text):
            unit = str(unit or "").strip()
            unit_norm = _normalize_marker_text(unit)
            if (
                not _looks_like_subanswer_unit(unit)
                or unit_norm in existing_norms
            ):
                continue
            candidate_units.append(unit)

        if len(candidate_units) < len(remaining_subparts):
            continue

        candidate_units = candidate_units[:len(remaining_subparts)]
        for sub_item, unit in zip(remaining_subparts, candidate_units):
            filtered_result[sub_item["id"]] = unit
            logger.info(
                "Filled missing Paper II sub-part %s from ordered OCR unit in main %s.",
                sub_item.get("label"),
                main_no,
            )


def _has_plain_number_block_support(source_text: str, mapped_text: str, label: str) -> bool:
    """
    New fallback for non-subquestion numbered answers such as Paper I short
    structured responses: accept the mapping when the answer text clearly
    appears inside the correct numbered OCR block even if the exact marker is
    too noisy for the stricter label validator.
    """
    if not source_text or not mapped_text or not label:
        return False

    main_no, sub_label = _extract_main_and_sub_label(label)
    if not main_no or sub_label:
        return False

    mapped_norm = _normalize_marker_text(mapped_text)
    if len(mapped_norm) < 8:
        return False

    if not _looks_like_structured_short_answer(mapped_text):
        return False

    block_text, _ = _extract_main_question_block(source_text, main_no)
    if not block_text:
        return False

    block_body = re.sub(
        rf'^\s*{re.escape(main_no)}\s*[\)\.\-:\s]*',
        '',
        str(block_text),
        count=1,
        flags=re.IGNORECASE,
    ).strip()
    if not block_body:
        return False

    block_norm = _normalize_marker_text(block_body)
    overlap_ratio = _char_ngram_overlap_ratio(mapped_text, block_body)
    token_ratio = _token_overlap_ratio(mapped_text, block_body)
    return (
        mapped_norm in block_norm
        or overlap_ratio >= 0.20
        or token_ratio >= 0.45
    )


def _recover_plain_number_candidates_from_blocks(
    answer_text: str,
    chunk: list[dict],
    filtered_result: dict,
    deferred_candidates: list[dict],
) -> None:
    """
    Prefer anchored Paper I recovery from detected numbered OCR blocks before
    falling back to loose document-order matching.
    """
    if not answer_text or not deferred_candidates:
        return

    blocks = _extract_plain_numbered_blocks(answer_text)
    if not blocks:
        return

    blocks_by_no = {str(block.get("number")): block for block in blocks if block.get("number")}
    chunk_by_id = {str(item.get("id")): item for item in chunk}

    for candidate in deferred_candidates:
        candidate_id = str(candidate.get("id"))
        if candidate_id in filtered_result:
            continue

        item = chunk_by_id.get(candidate_id)
        label_no = _extract_plain_main_label_value((item or {}).get("label"))
        if not label_no:
            continue
        normalized_label_no = label_no.upper() if re.fullmatch(r'[A-Za-z]+', label_no) else label_no

        block = blocks_by_no.get(str(normalized_label_no))
        if not block:
            continue

        block_body = re.sub(
            rf'^\s*{re.escape(str(normalized_label_no))}\s*[\)\.\-:\s]*',
            '',
            str(block.get("text") or ''),
            count=1,
            flags=re.IGNORECASE,
        ).strip()
        candidate_text = str(candidate.get("text") or "").strip()
        if not _looks_like_structured_short_answer(candidate_text):
            continue

        candidate_norm = _normalize_marker_text(candidate_text)
        block_norm = _normalize_marker_text(block_body)
        if len(candidate_norm) < 4 or len(block_norm) < 4:
            continue

        overlap_ratio = _char_ngram_overlap_ratio(candidate_text, block_body)
        token_ratio = _token_overlap_ratio(candidate_text, block_body)
        if (
            candidate_norm in block_norm
            or overlap_ratio >= 0.20
            or token_ratio >= 0.45
        ):
            filtered_result[candidate_id] = candidate_text
            logger.info(
                "Recovered plain numbered answer %s from numbered OCR block %s (char_overlap=%.2f, token_overlap=%.2f).",
                (item or {}).get("label") or candidate_id,
                normalized_label_no,
                overlap_ratio,
                token_ratio,
            )


def _recover_plain_number_candidates_by_order(
    answer_text: str,
    chunk: list[dict],
    filtered_result: dict,
    deferred_candidates: list[dict],
) -> None:
    """
    New Paper I fallback: when OCR weakens explicit number markers, recover
    short structured answers by preserving their visible order in the answer
    script. This only applies to plain numbered questions without sub-parts.
    """
    if not answer_text or not deferred_candidates:
        return

    normalized_answer = _normalize_marker_text(answer_text)
    if not normalized_answer:
        return

    item_by_id = {str(item.get("id")): item for item in chunk}
    candidate_by_id = {str(candidate.get("id")): candidate for candidate in deferred_candidates}

    ordered_items = sorted(
        [
            item
            for item in chunk
            if not item.get("is_sub_question")
            and _extract_numeric_label_value(item.get("label")) is not None
        ],
        key=lambda item: _extract_numeric_label_value(item.get("label")) or 10**9,
    )
    if not ordered_items:
        return

    cursor = 0
    for item in ordered_items:
        item_id = str(item.get("id"))
        existing_text = filtered_result.get(item_id)
        candidate_text = existing_text or (candidate_by_id.get(item_id) or {}).get("text")
        candidate_norm = _normalize_marker_text(candidate_text)
        if len(candidate_norm) < 4:
            continue

        position = normalized_answer.find(candidate_norm, cursor)
        if position < 0:
            continue

        if item_id in candidate_by_id and item_id not in filtered_result:
            filtered_result[item_id] = candidate_text
            logger.info(
                "Recovered plain numbered answer %s by ordered OCR flow fallback.",
                item.get("label") or item_id,
            )

        cursor = position + len(candidate_norm)


def _extract_main_question_block(source_text: str, main_no: str) -> tuple[str, int]:
    """
    New helper: isolate the OCR block that begins at a Paper II main question
    number so deferred sub-question snippets can be reassigned by position.
    """
    if not source_text or not main_no:
        return "", -1

    blocks = _extract_numbered_answer_blocks(source_text)
    for block in blocks:
        if str(block.get("number") or "") == str(main_no):
            return str(block.get("text") or ""), int(block.get("start", -1))

    source = str(source_text)
    main_patterns = [
        rf'(?:(?<=\n)|(?<=\r)|^)\s*{re.escape(main_no)}[\)\.\-:\s]',
        rf'(?<!\d){re.escape(main_no)}\s*\)',
        rf'(?<!\d){re.escape(main_no)}\s*[\.\-:]\s*',
    ]
    best_match = None
    for pattern in main_patterns:
        match = re.search(pattern, source, flags=re.IGNORECASE | re.MULTILINE)
        if match and (best_match is None or match.start() < best_match.start()):
            best_match = match

    if not best_match:
        return "", -1

    block_start = best_match.start()
    return source[block_start:block_start + 1800], block_start


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

    if _has_plain_number_block_support(source_text, mapped_text, label):
        return True

    if _has_main_question_block_support(source_text, mapped_text, label):
        return True

    if _has_nearby_subquestion_support(source_text, mapped_text, label):
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

        remaining_ids = {item["id"] for item in remaining_subparts}
        for key, value in block_result.items():
            if key not in remaining_ids or not value:
                continue

            if not _is_supported_by_block(block_text, value):
                continue

            filtered_result[key] = _extract_supported_span_from_block(block_text, value)
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
        for candidate in raw_candidates:
            value = str(candidate.get("text") or "").strip()
            value_norm = _normalize_marker_text(value)
            if (
                len(value_norm) < 6
                or value_norm in existing_norms
                or not _is_supported_by_block(block_text, value)
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
            filtered_result[sub_item["id"]] = _extract_supported_span_from_block(
                block_text,
                candidate["text"],
            )
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
    _fill_paper_ii_subparts_from_ordered_ocr_units(
        answer_text,
        chunk,
        filtered_result,
        allowed_main_nos=allowed_main_nos,
    )


def _detect_paper_ii_evidenced_main_nos(answer_text: str, chunk: list[dict]) -> set[str]:
    """
    Fast pre-pass: detect substantial numbered Paper II answer blocks directly
    from OCR so we only invoke Gemini on mains that visibly exist.
    """
    main_nos = {
        str(item.get("parent_main_label") or "")
        for item in chunk
        if item.get("is_sub_question") and item.get("parent_main_label")
    }
    evidenced: set[str] = set()

    for main_no in sorted(main_nos, key=lambda value: int(value) if str(value).isdigit() else 10**9):
        block_text, _ = _extract_main_question_block(answer_text, main_no)
        if not block_text:
            continue

        block_body = re.sub(
            rf'^\s*{re.escape(main_no)}\s*[\)\.\-:\s]*',
            '',
            str(block_text),
            count=1,
            flags=re.IGNORECASE,
        ).strip()
        if _looks_like_full_main_answer(block_body):
            evidenced.add(main_no)

    return evidenced


def _fast_map_paper_ii_by_main_blocks(answer_text: str, chunk: list[dict]) -> tuple[dict, set[str]]:
    """
    Faster Paper II path: map only the evidenced main-question blocks instead of
    issuing one large whole-part prompt and several recovery prompts.
    """
    evidenced_main_nos = _detect_paper_ii_evidenced_main_nos(answer_text, chunk)
    if not evidenced_main_nos:
        return {}, set()

    filtered_result: dict = {}
    _fill_paper_ii_subparts_from_main_blocks(
        answer_text,
        chunk,
        filtered_result,
        allowed_main_nos=evidenced_main_nos,
    )
    return filtered_result, evidenced_main_nos

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
                fast_result = {}
                evidenced_main_nos: set[str] = set()

                if _is_paper_ii_part(part_name):
                    fast_result, evidenced_main_nos = _fast_map_paper_ii_by_main_blocks(part_answer_text, chunk)
                    evidenced_subpart_count = sum(
                        1
                        for item in chunk
                        if item.get("is_sub_question")
                        and str(item.get("parent_main_label") or "") in evidenced_main_nos
                    )
                    required_fast_count = max(
                        3,
                        (evidenced_subpart_count * 2 + 2) // 3,
                    )
                    if fast_result and (
                        len(evidenced_main_nos) <= 2 or len(fast_result) >= required_fast_count
                    ):
                        all_mappings.update(fast_result)
                        logger.info(
                            "Batch %d for %s: fast main-block mapping accepted %d answers across mains %s; skipped whole-part Gemini call.",
                            (i // batch_size) + 1,
                            part_name,
                            len(fast_result),
                            sorted(evidenced_main_nos),
                        )
                        continue
                    if fast_result:
                        logger.info(
                            "Batch %d for %s: fast main-block mapping found %d answers across mains %s, but coverage was below threshold (%d/%d); running whole-part fallback.",
                            (i // batch_size) + 1,
                            part_name,
                            len(fast_result),
                            sorted(evidenced_main_nos),
                            len(fast_result),
                            required_fast_count,
                        )
                
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
                    seeded_fast_count = len(fast_result) if _is_paper_ii_part(part_name) else 0
                    filtered_result = dict(fast_result) if _is_paper_ii_part(part_name) else {}
                    deferred_main_block_candidates = []
                    deferred_plain_number_candidates = []
                    evidenced_main_nos = set(evidenced_main_nos)
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
                                filtered_result[k] = _extract_supported_span_for_label(
                                    part_answer_text,
                                    v,
                                    q_label,
                                )
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

                            if (
                                q_item
                                and not q_item.get("is_sub_question")
                                and _extract_numeric_label_value(q_label) is not None
                                and not _is_paper_ii_part(part_name)
                            ):
                                deferred_plain_number_candidates.append({
                                    "id": k,
                                    "text": v,
                                    "original_label": q_label,
                                })

                            # Existing guard: if neither direct marker support nor
                            # the deferred Paper II main-block path applies, reject it.
                            if not _has_marker_supported_mapping(part_answer_text, v, q_label):
                                logger.warning(
                                    "Discarding unsupported mapping for ID %s - no matching source marker found for label %s.",
                                    k,
                                    q_label,
                                )
                                continue

                            filtered_result[k] = _extract_supported_span_for_label(
                                part_answer_text,
                                v,
                                q_label,
                            )

                    if _is_paper_ii_part(part_name):
                        _run_paper_ii_recovery_passes(
                            part_answer_text,
                            chunk,
                            filtered_result,
                            deferred_main_block_candidates,
                            evidenced_main_nos,
                            surfaced_candidates_by_main,
                        )
                    else:
                        _recover_plain_number_candidates_from_blocks(
                            part_answer_text,
                            chunk,
                            filtered_result,
                            deferred_plain_number_candidates,
                        )
                        _recover_plain_number_candidates_by_order(
                            part_answer_text,
                            chunk,
                            filtered_result,
                            deferred_plain_number_candidates,
                        )

                    all_mappings.update(filtered_result)
                    initial_supported_count = sum(1 for result_id in batch_result.keys() if result_id in chunk_ids)
                    recovered_count = max(0, len(filtered_result) - initial_supported_count - seeded_fast_count)
                    discarded_count = max(0, initial_supported_count - max(0, len(filtered_result) - seeded_fast_count))
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
