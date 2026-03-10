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
        cleaned_result = {k: v for k, v in result.items() if k.startswith("Paper_") and v is not None}
        
        # Log basics for debugging
        if cleaned_result["Paper_I"]:
            logger.info(f"Paper I Detected: {len(cleaned_result['Paper_I'].get('questions', {}))} questions")
        if cleaned_result["Paper_II"]:
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
            for i in range(0, len(part_items), batch_size):
                chunk = part_items[i : i + batch_size]
                logger.info("Processing batch %d for %s", (i // batch_size) + 1, part_name)
                chunk_ids = {item["id"] for item in chunk}
                
                def _call_mapping(c):
                    return gemini_generate(
                        ANSWER_MAPPING_PROMPT.format(
                            structure=json.dumps(c, ensure_ascii=False, indent=2),
                            answer_text=answer_text[:35000],
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
                    for k, v in batch_result.items():
                        if k in chunk_ids and v:
                            # Find original question text for hallucination check
                            q_item = next((item for item in chunk if item["id"] == k), None)
                            q_text = q_item.get("text", "") if q_item else ""
                            
                            if not _is_hallucinated_question_text(v, q_text):
                                filtered_result[k] = v
                            else:
                                logger.warning(f"Discarding hallucinated answer for ID {k} - matches question text.")

                    all_mappings.update(filtered_result)
                    logger.info("Batch %d for %s: got %d/%d valid mappings (filtered %d hallucinated).",
                                (i // batch_size) + 1, part_name, len(filtered_result), len(chunk), len(batch_result) - len(filtered_result))
                else:
                    logger.error("Batch %d for %s: FAILED after retry — skipping batch.",
                                 (i // batch_size) + 1, part_name)


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
                "text": sq.sub_question_text[:200] if sq.sub_question_text else ""
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
            "text": q.question_text[:200] if q.question_text else ""
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
