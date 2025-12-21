# app/components/document_processing/services/classifier_service.py

from google import generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import json
import re

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
Your task is to structure the provided text into a strict JSON format.

========================
IMPORTANT MARKING RULES
========================
- In Sri Lankan exam papers, NO question or subquestion has 0 marks.
- If marks are NOT clearly specified, use null.
- NEVER assign marks = 0.

========================
PAPER & NUMBERING RULES
========================
- Sri Lankan exam papers are divided into sections such as:
  - Paper I (usually MCQs)
  - Paper II (Structured / Essay questions)

- EACH paper has its OWN numbering system.
  - Paper I numbering starts from 1.
  - Paper II numbering starts again from 1.
  - DO NOT continue numbering across papers (e.g., avoid 41, 42 for Paper II).

- Questions MUST be grouped under their correct paper.
- NEVER mix Paper I and Paper II questions in the same numbering scope.

========================
MCQ STRUCTURE RULES
========================
- MCQs usually belong to Paper I unless explicitly stated otherwise.
- Do NOT create artificial group keys (e.g., mcq_group_1).
- If multiple MCQs share common instructions or data:
  - Attach the shared information ONLY to the FIRST question number using "shared_stem".
  - Subsequent questions must reference it using "inherits_shared_stem_from".

========================
TARGET ANALYSIS
========================

1. **Metadata Extraction**
   Identify Sinhala or English indicators for:
   - Subject (විෂය)
   - Grade (ශ්‍රේණිය)
   - Term (වාරය)
   - Duration (කාලය)
   - Year (වර්ෂය)
   - Medium (Sinhala / English)

2. **Instructions (උපදෙස්)**
   - Extract general instructions at the beginning of EACH paper.
   - Store Paper I and Paper II instructions separately if applicable.

3. **Question Identification**
   - Detect which paper a question belongs to using headings such as:
     - "Paper I", "I කොටස", "බහුවරණ ප්‍රශ්න"
     - "Paper II", "II කොටස", "ව්‍යුහගත ප්‍රශ්න"
   - Group questions under the correct paper.

4. **Multiple Choice Questions (Paper I)**
   - Detect MCQs by options like:
     - (1)(2)(3)(4), (A)(B)(C)(D), (අ)(ආ)(ඉ)(ඊ)
   - Each MCQ MUST include:
     - "type": "mcq"
     - "text"
     - "options"
     - "marks": null

5. **Structured / Essay Questions (Paper II)**
   - Identify main questions and subquestions.
   - Assign marks ONLY if explicitly stated.

========================
OUTPUT FORMAT (STRICT JSON)
========================

{{
  "metadata": {{
    "subject": "string",
    "grade": "string",
    "year": "string",
    "term": "string",
    "duration": "string",
    "medium": "Sinhala/English"
  }},
  "instructions": {{
    "Paper_I": [],
    "Paper_II": []
  }},
  "PaperStructure": {{
    "Paper_I": {{
      "type": "MCQ",
      "questions": {{}}
    }},
    "Paper_II": {{
      "type": "Structured",
      "questions": {{}}
    }}
  }}
}}

========================
TEXT TO PROCESS
========================
{content}
"""

def separate_paper_content(text: str):
    """
    Separates paper content into:
    - Metadata
    - Instructions (Paper I / Paper II)
    - PaperStructure (Paper I / Paper II with independent numbering)

    Fully aligned with Sri Lankan exam paper formats.
    """
    if not text or not text.strip():
        return {}, {}, {}

    model = genai.GenerativeModel("gemini-2.5-flash")

    try:
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

        paper_metadata = result.get("metadata", {})

        instructions = result.get("instructions", {
            "Paper_I": [],
            "Paper_II": []
        })

        paper_structure = result.get("PaperStructure", {
            "Paper_I": {},
            "Paper_II": {}
        })

        # 🔒 Defensive normalization (optional but recommended)
        for paper_key in ["Paper_I", "Paper_II"]:
            paper = paper_structure.get(paper_key)
            if paper and "questions" not in paper:
                paper["questions"] = {}

        return paper_metadata, instructions, paper_structure

    except json.JSONDecodeError:
        print("❌ Error: Model output was not valid JSON.")
        return {}, {}, {}

    except Exception as e:
        print(f"❌ Error in Sinhala structure extraction: {e}")
        return {}, {}, {}
    
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
