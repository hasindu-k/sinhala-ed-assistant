# app/components/document_processing/services/classifier_service.py

import json
import logging
import re
from app.shared.ai.gemini_client import gemini_generate

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
- Sri Lankan exam papers are divided into sections such as:
  - Paper I (usually MCQs) - "I කොටස", "Part I", "භාගය I"
  - Paper II (Structured / Essay questions) - "II කොටස", "Part II", "භාගය II"

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
        }},
        "2": {{{{ ... }}}}
      }}
    }},
    "Paper_II": {{
      "type": "Structured",
      "questions": {{
        "1": {{
          "type": "structured",
          "text": "main question text",
          "marks": 20,
          "sub_questions": {{
            "a": {{{{"text": "sub-question a", "marks": 5, "correct_answer": "Expected key facts..."}}}},
            "b": {{{{"text": "sub-question b", "marks": 5, "correct_answer": "..."}}}},
            "c": {{{{"text": "sub-question c", "marks": 10, "correct_answer": "..."}}}}
          }}
        }},
        "2": {{{{ ... }}}}
      }}
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

        paper_structure = result.get("PaperStructure", {
            "Paper_I": {},
            "Paper_II": {}
        })

        # 🔒 Defensive normalization
        for paper_key in ["Paper_I", "Paper_II"]:
            paper = paper_structure.get(paper_key)
            if paper and "questions" not in paper:
                paper["questions"] = {}

        logger.debug("Extracted Paper Structure: %s", paper_structure)
        
        # Only returning paper_structure now
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
Return a single JSON object with keys "Paper_I" and "Paper_II". 
If a paper is missing, set it to null.

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
  "Paper_II": {{
    "config": {{
      "subject_detected": "History",
      "medium": "Sinhala",
      "total_marks": 60,
      "total_questions_available": 5,
      "suggested_weightage": 60,
      "selection_rules": {{"mode": "any", "count": 3}}
    }},
    "questions": {{
      "1": {{
        "type": "structured",
        "text": "Main question text",
        "marks": 20,
        "sub_questions": {{
          "a": {{"text": "Sub Q text", "marks": 5, "correct_answer": "fact 1, fact 2"}},
          "b": {{"text": "Sub Q text", "marks": 5, "correct_answer": "..."}}
        }}
      }}
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
        if not result:
            return {}
            
        logger.info("Combined exam extraction completed successfully.")
        
        # 🔒 Defensive Normalization
        # Ensure top-level keys exist even if model returns partially empty JSON
        cleaned_result = {
            "Paper_I": result.get("Paper_I"), 
            "Paper_II": result.get("Paper_II")
        }
        
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
You are a precision text-mapping and OCR correction AI. Your task is to extract answer text from the STUDENT ANSWER TEXT, clean it, and map it to the correct Question ID.

========================
OCR CLEANING RULES
========================
Before extracting, mentally fix OCR errors in the Sinhala text:
- Fix broken conjunct letters (ex: ක් ෂ → ක්‍ෂ).
- Properly align misplaced diacritics.
- Remove unnecessary spaces inside words.
- Ensure the resulting text is natural, readable Sinhala.

========================
INPUTS
========================
1. QUESTION STRUCTURE (JSON):
   - A list of questions with IDs, labels (e.g. "1", "a", "i"), and question text (topic context).

2. STUDENT ANSWER TEXT (OCR):
   - Raw text from the student's script. 
   - Context for identifying correct mappings should be derived from the question text provided.

========================
STRICT RULES
========================
1. **DO NOT ANSWER THE QUESTIONS.** If you generate an answer that isn't in the OCR, you have failed.
2. **CLEAN EXTRACTION**: Extract the student's answer but apply the OCR CLEANING RULES above. Do NOT fix the student's actual spelling mistakes, only OCR-induced garbage.
3. **MAPPING LOGIC**: 
   - Use question numbers and context to find the relevant answer.
   - For every ID in the provided structure, you MUST return a value: either the cleaned text or `null` if unattempted.
4. **NO HALLUCINATION**: If an answer is not present, return `null`.

========================
OUTPUT FORMAT (STRICT JSON)
========================
Return a raw JSON object: {{"id": "cleaned student text", ...}}
EVERY ID provided in the input structure MUST be a key in your output.

========================
QUESTION STRUCTURE
========================
{structure}

========================
STUDENT ANSWER TEXT
========================
{answer_text}
"""

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
        batch_size = 15 # Even smaller batch for safety
        
        for part_name, part_items in parts_map.items():
            logger.info("Mapping part: %s (%d items)", part_name, len(part_items))
            for i in range(0, len(part_items), batch_size):
                chunk = part_items[i : i + batch_size]
                logger.info("Processing batch %d for %s", (i // batch_size) + 1, part_name)
                
                response_text = gemini_generate(
                    ANSWER_MAPPING_PROMPT.format(
                        structure=json.dumps(chunk, ensure_ascii=False, indent=2),
                        answer_text=answer_text[:35000],
                    ),
                    json_mode=True,
                )

                if response_text:
                    batch_result = _safe_json_loads(response_text)
                    if isinstance(batch_result, dict):
                        # Merge results, keeping only the IDs we asked for in this chunk
                        chunk_ids = {item["id"] for item in chunk}
                        filtered_result = {k: v for k, v in batch_result.items() if k in chunk_ids}
                        all_mappings.update(filtered_result)
                    else:
                        logger.warning("Batch mapping for %s returned invalid type", part_name)
                else:
                    # Retry once on empty response
                    logger.warning("Empty response for %s batch - retrying...", part_name)
                    retry_response = gemini_generate(
                        ANSWER_MAPPING_PROMPT.format(
                            structure=json.dumps(chunk, ensure_ascii=False, indent=2),
                            answer_text=answer_text[:35000],
                        ),
                        json_mode=True,
                    )
                    if retry_response:
                        retry_result = _safe_json_loads(retry_response)
                        if isinstance(retry_result, dict):
                            chunk_ids = {item["id"] for item in chunk}
                            filtered_result = {k: v for k, v in retry_result.items() if k in chunk_ids}
                            all_mappings.update(filtered_result)
                            logger.info("Retry successful for %s batch: %d items", part_name, len(filtered_result))
                        else:
                            logger.error("Retry for %s batch returned invalid type", part_name)
                    else:
                        logger.error("Retry also failed for %s batch - skipping", part_name)


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