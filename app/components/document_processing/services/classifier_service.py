# app/components/document_processing/services/classifier_service.py

from google import generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import json
import logging
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
    
    model = genai.GenerativeModel("gemini-2.5-flash")
    
    try:
        response = model.generate_content(
            CLASSIFY_PROMPT.format(content=text[:8000]),
            safety_settings={
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }
        )
        
        output = response.text.strip().lower()
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
          "marks": null
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
            "a": {{{{"text": "sub-question a", "marks": 5}}}},
            "b": {{{{"text": "sub-question b", "marks": 5}}}},
            "c": {{{{"text": "sub-question c", "marks": 10}}}}
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

    # Initialize model (ensure api_key is configured elsewhere)
    model = genai.GenerativeModel("gemini-2.0-flash-exp") # Updated to latest flash model for better speed/cost

    try:
        logger.info("Starting Sinhala structure extraction.")
        response = model.generate_content(
            SINHALA_STRUCTURE_PROMPT.format(content=text[:20000]),
            generation_config={"response_mime_type": "application/json"},
            safety_settings={
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }
        )

        result = json.loads(response.text)
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

    model = genai.GenerativeModel("gemini-2.5-flash")

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
        response = model.generate_content(prompt)
        corrected = response.text.strip()

        return corrected
    except Exception as e:
        print("Error in Sinhala OCR correction:", e)
        return text

PAPER_CONFIG_PROMPT = """
You are an expert Exam Configuration AI.
Your task is to analyze the provided exam paper text (Sinhala/English) and extract the **grading configuration** required to set up an evaluation system.

========================
ANALYSIS GOALS
========================
1. **Identify Papers:** Detect if the text contains Paper I, Paper II, or both.
2. **Extract Scoring Logic:** Find total marks and specific selection rules (e.g., "Answer 4 questions from Part II").
3. **Calculate Counts:** Count the total available questions for each paper.

========================
EXTRACTION RULES
========================

**1. Paper Identification (`paper_part`)**
   - Look for headers: "Paper I", "I කොටස" (Part I), "Paper II", "II කොටස" (Part II).
   - If the paper is purely Multiple Choice (1-40), it is usually "Paper_I".
   - If the paper is Structured/Essay, it is usually "Paper_II".

**2. Selection Rules (`selection_rules`)**
   - Read the "Instructions" (උපදෙස්) section carefully.
   - **Scenario A: Answer All**
     - If instructions say "Answer all questions", return: `{{{{"mode": "all"}}}}`
   
   - **Scenario B: Specific Counts per Section (The most common for Paper II)**
     - If it says "Answer 4 from Part II and 1 from Part III", return exactly:
       `{{{{"Part_II": 4, "Part_III": 1}}}}`
     - If it says "Answer 2 questions from Section A and 3 from Section B", return:
       `{{{{"Section_A": 2, "Section_B": 3}}}}`

   - **Scenario C: Compulsory + Choice**
     - If it says "Question 1 is compulsory, select 4 others", return:
       `{{{{"compulsory": [1], "choose_any": 4}}}}`

**3. Total Marks (`total_marks`)**
   - **Paper I:** Usually 1 mark per question (e.g., 40 questions = 40 marks).
   - **Paper II:** Look for "Total Marks" or sum the marks of the *required* number of questions.
   - If unable to find explicit marks, estimate based on standard Sri Lankan Ordinary Level standards (Paper I: 40, Paper II: 100).

**4. Weightage (`suggested_weightage`)**
   - This is rarely in the text. Suggest a standard value:
   - Paper I default: 40% (0.4)
   - Paper II default: 60% (0.6)

========================
OUTPUT FORMAT (Strict JSON)
========================
Return a JSON object containing a list of configurations found.

{{
  "configs": [
    {{
      "paper_part": "Paper_I",       // e.g. "Paper_I", "Paper_II"
      "subject_detected": "History", // For UI verification only
      "medium": "Sinhala",           // "Sinhala" or "English"
      "total_marks": 40,             // Integer
      "total_questions_available": 40, // How many distinct questions exist in text
      "suggested_weightage": 40,     // Percentage (integer)
      "selection_rules": {{           // The logic for valid submission
         "mode": "all"               
      }}
    }},
    {{
      "paper_part": "Paper_II",
      "subject_detected": "History",
      "medium": "Sinhala",
      "total_marks": 100,
      "total_questions_available": 9,
      "suggested_weightage": 60,
      "selection_rules": {{           // Example for "Answer 4 from Part II and 1 from Part III"
         "Part_II": 4,
         "Part_III": 1,
         "compulsory": [1]           // Include only if specific questions are mandatory
      }}
    }}
  ]
}}

========================
TEXT TO PROCESS
========================
{content}
"""

COMBINED_EXAM_PROMPT = """
You are an expert AI for analyzing Sri Lankan exam papers (Sinhala and English medium).
Your task is to extract BOTH the **grading configuration** and the **question structure** into a single strict JSON format.

========================
SECTION 1: CONFIGURATION RULES
========================
Analyze the text to determine how the paper should be graded.
1. **Paper Identification:** Detect if text contains Paper I (MCQ), Paper II (Structured), or both.
2. **Total Marks:** - Paper I: Usually 1 mark per question (e.g., 40 qs = 40 marks).
   - Paper II: Look for "Total Marks" or sum the sub-question marks.
3. **Selection Rules:** Read instructions (e.g., "Answer 4 questions").
   - If "Answer all": return {{{{"mode": "all"}}}}
   - If "Answer 4 from Part A and 1 from Part B": return {{{{"Part_A": 4, "Part_B": 1}}}}
   - If "Question 1 compulsory, select 4 others": return {{{{"compulsory": [1], "choose_any": 4}}}}

========================
SECTION 2: QUESTION STRUCTURE RULES
========================
**Paper I (MCQ):**
- Questions 1-40 (typically).
- Format: Question text + Options list.
- If multiple MCQs share common instructions or data:
  - Attach the shared information to the first question using "shared_stem"
  - Subsequent questions reference it using "inherits_shared_stem_from"
- Only use "shared_stem" when two or more consecutive MCQs clearly depend on the same instruction, paragraph, diagram, or data.
- Options: (1)..(4), (A)..(D), (අ)..(ඊ).
- Marks: Usually 1 or null.

**Paper II (Structured):**
- Main Questions: 1, 2, 3...
- Sub-questions: a, b, c... or i, ii, iii...
- Marks: Extract specific marks like "(05 marks)", "(10)", "ලකුණු 05".
- **Rule:** Never assign 0 marks. Use null if unknown.

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
      "total_questions_available": 40,
      "suggested_weightage": 40,
      "selection_rules": {{{{"mode": "all"}}}}
    }},
    "questions": {{
      "1": {{
        "type": "mcq",
        "text": "Question text here",
        "options": ["Op1", "Op2", "Op3", "Op4"],
        "marks": 1
      }},
      "2": {{
        "type": "mcq",
        "shared_stem": "Common instruction / paragraph here",
        "text": "Next question text",
        "options": ["Op1", "Op2", "Op3", "Op4"],
        "marks": 1
      }},
      "3": {{
          "type": "mcq",
          "inherits_shared_stem_from": 2,
          "text": "Next question text",
          "options": ["Op1", "Op2", "Op3", "Op4"],
          "marks": 1
      }},
      "4": {{ ... }}
    }}
  }},
  "Paper_II": {{
    "config": {{
      "subject_detected": "History",
      "medium": "Sinhala",
      "total_marks": 100,
      "total_questions_available": 7,
      "suggested_weightage": 60,
      "selection_rules": {{
        "compulsory": [1],
        "choose_any": 4
      }}
    }},
    "questions": {{
      "1": {{
        "type": "structured",
        "text": "Main question text",
        "marks": 20,
        "sub_questions": {{
          "a": {{{{"text": "Sub Q text", "marks": 5}}}},
          "b": {{{{"text": "Sub Q text", "marks": 15}}}}
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

    # Initialize model
    model = genai.GenerativeModel("gemini-2.5-flash") 

    try:
        logger.info("Starting combined exam extraction.")
        response = model.generate_content(
            COMBINED_EXAM_PROMPT.format(content=text[:30000]), # Increased char limit slightly for full papers
            generation_config={"response_mime_type": "application/json"},
            safety_settings={
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }
        )

        result = json.loads(response.text)
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