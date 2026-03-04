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
        clean_text = re.sub(r'^```json\s*|\s*```$', '', text.strip(), flags=re.MULTILINE)
        return json.loads(clean_text)
    except Exception as e:
        logger.error(f"Failed to parse JSON response: {e}. Raw content: {text[:500]}...")
        return {}
    

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
You are an expert AI for mapping student answers to exam questions.
Your task is to map the student's handwritten answer text (OCR output) to the correct Question ID from the provided question structure.

========================
INPUTS
========================
1. QUESTION STRUCTURE (JSON):
   - Contains the hierarchy of questions and sub-questions.
   - Each question has a unique "id" and a "label" (e.g., "1", "a", "i").

2. STUDENT ANSWER TEXT (OCR):
   - Raw text extracted from the student's answer script.
   - May contain noise, broken characters, or be out of order.
   - Students usually write the question number before the answer (e.g., "1. Answer...", "2(a) Answer...").

========================
TASK
========================
- Analyze the student's text to identify which part corresponds to which question.
- Map the extracted answer text to the corresponding "id" from the Question Structure.
- If a question is NOT answered, do NOT include it in the output (or map it to null).
- If an answer spans multiple lines, combine them.
- Ignore irrelevant text (headers, footers, noise).

========================
OUTPUT FORMAT (STRICT JSON)
========================
Return a single JSON object where keys are the "id" of the question/sub-question and values are the student's answer text.

Example:
{{
  "uuid-of-question-1": "Student's answer for question 1...",
  "uuid-of-subquestion-1a": "Student's answer for 1(a)..."
}}

========================
QUESTION STRUCTURE
========================
{structure}

========================
STUDENT ANSWER TEXT
========================
{answer_text}
"""

def map_student_answers(answer_text: str, question_structure: dict) -> dict:
    """
    Maps student answer text to question IDs using Gemini.
    """
    if not answer_text or not answer_text.strip():
        return {}

    try:
        logger.info("Starting student answer mapping.")
        # Convert structure to a simplified format for the prompt to save tokens
        simplified_structure = _simplify_structure_for_prompt(question_structure)
        
        response_text = gemini_generate(
            ANSWER_MAPPING_PROMPT.format(
                structure=json.dumps(
                    simplified_structure,
                    ensure_ascii=False,
                    indent=2
                ),
                answer_text=answer_text[:30000],
            ),
            json_mode=True,
        )

        if not response_text:
            logger.error("Empty response from Gemini.")
            return {}

        result = _safe_json_loads(response_text)

        if not isinstance(result, dict):
            logger.error("Mapping output is not a JSON object.")
            return {}
        
        logger.info("Mapped %d answers successfully.", len(result))
        return result

    except json.JSONDecodeError:
        logger.error("❌ Model output was not valid JSON.")
        return {}
    
    except Exception as e:
        logger.error(f"❌ Error in answer mapping: {e}")
        return {}

def _simplify_structure_for_prompt(questions: list) -> list:
    """
    Helper to create a lightweight structure for the AI prompt.
    """
    simple = []
    for q in questions:
        q_obj = {
            "id": str(q.id),
            "label": q.question_number,
            "text": q.question_text[:50] if q.question_text else ""
        }
        # Add sub-questions if any
        # Note: This assumes the input 'questions' list contains SQLAlchemy objects or dicts
        # We need to handle both or ensure consistent input. 
        # Assuming SQLAlchemy objects based on usage context, but let's be safe.
        
        sub_qs = getattr(q, "sub_questions", [])
        if sub_qs:
            q_obj["sub_questions"] = _simplify_sub_questions(sub_qs)
            
        simple.append(q_obj)
    return simple

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