# SinLearn - Sinhala Ed Assistant 📚🇱🇰

An AI-powered educational assistant designed to support Sinhala medium students and teachers.  
This project combines **mobile learning apps**, **AI services (OCR, STT, RAG, grading)**, and **infrastructure tools** to create a complete ecosystem for Sinhala education.

---

## 📂 Project Structure

```sinhala-ed-assistant/
├─ mobile/ # Flutter mobile app for students and teachers
├─ api/ # FastAPI backend (OCR, STT, embeddings, RAG, grading)
├─ infra/ # Infrastructure (docker-compose, env files, deployment scripts)
└─ README.md # Project documentation
```
Team Responsibilities

The work is divided into four main functional areas. Each member is responsible for one part and supports the integration work.

1. Sinhala Document Processing (OCR + Preprocessing)

Handles printed and handwritten Sinhala text.
• Image cleaning
• Sinhala OCR
• Text normalization

2. Sinhala Q&A and Summaries (RAG Pipeline)

Takes student questions as text, searches resources, and produces answers tied to teacher notes.
• Embeddings
• Semantic search
• Source-bound answers
• Summaries

3. Voice-Based Q&A (Speech Recognition + Voice Output)

Handles Sinhala voice queries using speech recognition models and generates spoken answers.
• Voice capture
• Sinhala ASR
• Intent detection
• Text-to-speech

4. Automatic Answer Evaluation (IT22003478 – Miyuri)

Grades Sinhala student answers using uploaded resources.
• OCR for answer images if needed
• Semantic comparison
• Rubric-based scoring
• Question-wise and paper-wise feedback


# **👥 Team Responsibilities**

### **1. Sinhala Document Processing (OCR & Cleaning)**

Handles printed and handwritten Sinhala content.

* Image preprocessing
* Sinhala OCR
* Text normalization and cleanup

### **2. Resource-Based Q&A and Summaries (RAG Pipeline)**

Produces accurate, source-bound Sinhala answers.

* Embeddings for resources
* Dense + sparse retrieval
* Question answering
* Summary generation

### **3. Voice-Based Q&A (Speech to Text + TTS)**

Allows students to ask questions through Sinhala voice input.

* Whisper-based Sinhala ASR
* Intent handling
* Sinhala text-to-speech output

### **4. Automatic Answer Evaluation (IT22003478 – Miyuri)**

Grades student answers automatically using teacher-provided material.

* OCR for answer images
* Embedding & semantic comparison
* Rubric-based scoring
* Question-wise and paper-wise feedback

---

# **📘 Component Workflows (Detailed Descriptions)**

This section explains how each major component of the Sinhala Ed Assistant works.
Each workflow focuses on the main steps the system follows when handling a user request.

---

## **1. Sinhala Document Processing Workflow (OCR + Cleaning)**

This component prepares printed or handwritten Sinhala material so it can be used by other modules.

**Workflow Steps**

1. **Image Input**
   The user uploads a textbook page, note, or handwritten answer.

2. **Preprocessing**
   The system improves the image for recognition using operations such as deskewing, noise filtering, and contrast adjustment.

3. **Sinhala OCR Execution**
   The cleaned image is read through a Sinhala-capable OCR model.
   The output is raw Sinhala text containing irregular spacing and characters.

4. **Text Cleaning**
   The OCR text is normalized to a readable and usable form.
   This includes fixing spacing, handling compound characters, and removing noise.

5. **Output Delivery**
   The final text is passed to the RAG pipeline or the answer evaluation module.

---

## **2. Resource-Based Q&A and Summary Workflow (RAG Pipeline)**

This module produces answers tied to teacher resources, preventing unsupported or hallucinated output.

**Workflow Steps**

1. **User Question Input**
   A question typed by the student enters the backend.

2. **Text Normalization**
   The question is standardized so Sinhala variations do not affect processing.

3. **Embedding Generation**
   The system converts the question and teaching materials into semantic vectors.

4. **Retrieval**
   Relevant parts of the teacher resources are located using vector similarity and keyword matching.

5. **Answer Construction**
   The answer is generated using only the retrieved passages.

6. **Summary Generation (when requested)**
   The retrieved passages can also be condensed into a short summary.

7. **Output Delivery**
   The answer or summary returns to the mobile app.

---

## **3. Voice-Based Q&A Workflow (Speech Input + Speech Output)**

This module allows students to ask questions in Sinhala through speech.

**Workflow Steps**

1. **Voice Recording**
   The student speaks through the mobile app.

2. **Speech Recognition (Whisper)**
   The audio is converted to text with accent-aware Sinhala speech recognition.

3. **Query Identification**
   The system determines whether the user wants an answer or a summary.

4. **RAG Processing**
   The recognized text is processed through the resource-based Q&A pipeline.

5. **Sinhala Text Response**
   The answer is produced in Sinhala.

6. **Text-to-Speech (TTS)**
   If requested, the answer is read aloud to the student.

7. **Output Delivery**
   The app displays the text and plays the audio.

---

## **4. Automatic Answer Evaluation Workflow (Developed by Miyuri – IT22003478)**

This component grades student answers using semantic comparison and optional rubric weights.

**Workflow Steps**

1. **Answer Input**
   Students or teachers upload an answer as text or an image.

2. **OCR Handling (if an image)**
   Text is extracted and cleaned through the OCR pipeline.

3. **Text Preparation**
   The answer is segmented into meaningful parts.

4. **Embedding Generation**
   The student answer, teacher material, and key points are converted to vectors using Sinhala-compatible embedding models.

5. **Semantic Matching**
   The system compares student text with expected content.
   It identifies:

   * correct ideas
   * incorrect interpretations
   * missing key points

6. **Rubric-Based Scoring**
   If a rubric is provided, weights for coverage, accuracy, and clarity are applied.

7. **Feedback Generation**
   The module produces:

   * question-level feedback
   * missing points
   * correctness description
   * final score
   * a brief overall feedback note

8. **Output Delivery**
   Results are sent to the mobile app for display.

---

# **🧩 How These Components Work Together**

All modules share three core resources:

* cleaned Sinhala text
* semantic embeddings
* teacher-provided learning materials

This ensures that answers, summaries, voice responses, and grading all remain tied to the same information sources.
The design also allows each module to operate independently while supporting the others.

---


# **🔄 High-Level System Workflow**

```
 Student or Teacher
        |
        V
    Mobile App
        |
        V
    Backend API
        |
        |--- OCR Module ------------------> Clean Sinhala Text
        |--- Embedding Module ------------> Semantic Vectors
        |--- RAG Module ------------------> Source-Based Answers
        |--- Voice Q&A Module ------------> Text + Speech Responses
        |--- Answer Evaluation Module ----> Scores + Feedback
        |
        V
  Mobile App Output
```

All modules work together to support students and teachers in their learning activities.

---

# **📜 Module Workflows**

## **A. Sinhala Document Processing (OCR)**

```
Document Image
      |
      V
Preprocessing
      |
      V
Sinhala OCR
      |
      V
Clean Sinhala Text
```

---

## **B. Sinhala Q&A + Summaries (RAG)**

```
User Question
      |
      V
Normalize Text
      |
      V
Embed Question
      |
      V
Retrieve from Teacher Resources
      |
      V
Generate Sinhala Answer or Summary
```

Answers remain tied to teacher's uploaded content.

---

## **C. Voice-Based Q&A**

```
Sinhala Voice Input
       |
       V
Speech-to-Text (Whisper)
       |
       V
Process Query
       |
       V
RAG Module
       |
       V
Sinhala Answer
       |
       V
Text-to-Speech Output
```

Supports classroom background noise and regional accents.

---

## **D. Automatic Answer Evaluation (Lokuhewage M M – IT22003478)**

```
Student Answer (text or image)
        |
        V
OCR (if image)
        |
        V
Cleaned Sinhala Text
        |
        V
Embed Student Answer
        |
        V
Embed Teacher Notes + Model Answers
        |
        V
Semantic Comparison
        |-- Matched points
        |-- Missing points
        |-- Similarity scores
        |
        V
Rubric-Based Scoring
        |
        V
Question Scores + Overall Feedback
```

Grading is performed strictly based on teacher resources.

---

# **🖥️ Backend Structure (api/)**

```
api/
 ├── app/
 │     ├── ocr/
 │     ├── embeddings/
 │     ├── rag/
 │     ├── voice/
 │     └── answer_evaluation/       # Implementation continues here
 │
 ├── main.py
 ├── SETUP.md
 └── pyproject.toml
```

---

# **📱 Mobile Application (Flutter)**

```
mobile/
 └── <Flutter project files>
```

Features include:

* Sinhala input
* Image upload
* Voice question feature
* Displaying answers and feedback

---

# **⚙️ Technologies Used**

### **Mobile**

* Flutter
* Provider / Riverpod
* Firebase (future enhancement)

### **Backend**

* FastAPI
* Python
* Tesseract OCR
* Whisper ASR
* SinBERT / XLM-R embeddings
* Qdrant / FAISS (vector search)

### **Infrastructure**

* Docker
* Docker Compose

---

# **🌿 Branching Strategy**

Each member maintains their own feature branch:

```
/ocr
/rag
/voice-qa
/answer-evaluation-miyuri
```

Changes are merged into `main` through reviewed Pull Requests.

---

# **▶️ Running the Backend**

```
cd api
pip install -r requirements.txt
uvicorn app.main:app --reload
```

---

# **▶️ Running the Mobile App**

```
cd mobile/sinhala_ed_app
flutter pub get
flutter run
```

---

# **📌 Notes**

All PP1 materials including:

* design report
* mockups
* low-fi and high-fi UI screens
* diagrams
* feedback
* improvements
  are submitted separately following academic guidelines.

They are **not** stored inside this repository to keep the codebase light and organized.

---

# **👤 Authors**

* Sinhala Document Processing: **Ranaweera P.H.K (IT22233452)**
* RAG Q&A Module: **Jayananda L.V.O.R (IT22161406)**
* Voice Q&A Module: **Sathsara T.T.D (IT22362476)**
* Automatic Answer Evaluation: **Lokuhewage M .M (IT22003478)**

---
