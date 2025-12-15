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

**Target Analysis:**
1.  **Metadata**: Look for Sinhala/English terms:
    - Subject (විෂය)
    - Grade (ශ්‍රේණිය)
    - Term (වාරය) - e.g., "First Term", "පළමු වාර"
    - Duration (කාලය) - e.g., "පැය 2", "2 hours"
    - Year (වර්ෂය)

2.  **Instructions (උපදෙස්)**: Extract the list of rules given to students at the start.

3.  **Structure (Questions & Marks)**:
    - Identify **main questions** starting with numbers (1, 2, 3...) or Sinhala indicators.
    - **Crucial**: Identify mark allocations.
      - Look for patterns like: "(XX marks)", "(ලකුණු XX)", "[XX]", "(XX)".
      - In Sinhala papers, marks are often at the end of the line inside brackets.
    - Identify **subquestions**:
      - Common formats: "(i)", "(ii)", "(a)", "(b)", "(අ)", "(ආ)".
      - Assign marks to each subquestion if specified.

**Output Format (Strict JSON):**
{{
  "metadata": {{
    "subject": "string (e.g. Science / විද්‍යාව)",
    "grade": "string (e.g. 10)",
    "year": "string",
    "term": "string",
    "duration": "string",
    "medium": "Sinhala/English"
  }},
  "instructions": ["instruction 1", "instruction 2"],
  "PaperStructure": {{
    "main_questions": {{
      "1": {{
        "total_marks": 12,
        "subquestions": {{
          "a": {{ "text": "<text>", "marks": 3 }},
          "b": {{ "text": "<text>", "marks": 3 }}
        }}
      }},
      "2": {{
        "total_marks": 8,
        "subquestions": {{
          "a": {{ "text": "<text>", "marks": 4 }},
          "b": {{ "text": "<text>", "marks": 4 }}
        }}
      }}
    }}
  }}
}}

**TEXT TO PROCESS:**
{content}
"""

def separate_paper_content(text: str):
    """
    Separates paper content into Metadata, Instructions, and Structure 
    with specific support for Sinhala terms and formatting.
    """
    if not text or not text.strip():
        return {}, [], []

    model = genai.GenerativeModel("gemini-2.5-flash")

    try:
        # We assume the text might be long, so we take a safe chunk. 
        # For structure extraction, usually the first 15k-20k characters capture the bulk 
        # of the hierarchy if it's not a massive document.
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
        instructions = result.get("instructions", [])
        paper_structure = result.get("PaperStructure", {}).get("main_questions", {})

        # Post-processing: If the model returns null for marks but the user needs 0, handle it here.
        # But usually keeping it None/null is safer until manual verification.

        return paper_metadata, instructions, paper_structure

    except json.JSONDecodeError:
        print("Error: Model output was not valid JSON.")
        # Fallback: Return raw text segments if JSON fails (optional backup logic)
        return {}, [], []
        
    except Exception as e:
        print(f"Error in Sinhala structure extraction: {e}")
        return {}, [], []
    
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
