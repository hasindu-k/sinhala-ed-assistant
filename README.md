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

- Image preprocessing
- Sinhala OCR
- Text normalization and cleanup

### **2. Resource-Based Q&A and Summaries (RAG Pipeline)**

Produces accurate, source-bound Sinhala answers.

- Embeddings for resources
- Dense + sparse retrieval
- Question answering
- Summary generation

### **3. Voice-Based Q&A (Speech to Text + TTS)**

Allows students to ask questions through Sinhala voice input.

- Whisper-based Sinhala ASR
- Intent handling
- Sinhala text-to-speech output

### **4. Automatic Answer Evaluation (IT22003478 – Miyuri)**

Grades student answers automatically using teacher-provided material.

- OCR for answer images
- Embedding & semantic comparison
- Rubric-based scoring
- Question-wise and paper-wise feedback

---

# **📘 Component Workflows (Detailed Descriptions)**

This section explains how each major component of the Sinhala Ed Assistant works.
Each workflow focuses on the main steps the system follows when handling a user request.

---

# **1. Sinhala Document Processing Workflow (OCR + Embeddings)**

This module prepares printed or handwritten Sinhala educational content so the rest of the system can use it.

### **Workflow Steps**

1. **Document Input**
   A student or teacher uploads a scanned page, image, or handwritten note.

2. **Preprocessing**
   The system applies noise removal, resizing, deskewing, and contrast correction to improve recognition quality.

3. **Sinhala OCR Execution**
   The processed image is passed through a Sinhala-trained OCR engine.
   Output: raw Sinhala text.

4. **Text Normalization**
   Cleaning steps include Unicode fixes, spacing correction, and handling compound characters.

5. **Embedding Generation**
   The cleaned text is converted to semantic vectors using Sinhala-compatible embedding models.

6. **Storage in Vector Database**
   The embeddings and metadata are stored for later retrieval during Q&A, summarization, or answer evaluation.

---

# **2. Resource-Based Q&A and Summary Workflow (RAG Pipeline)**

This module retrieves relevant passages from teacher materials and produces source-grounded answers or summaries.

### **Workflow Steps**

1. **User Input (Sinhala Text Query)**
   The student types a question into the mobile app.

2. **Query Normalization**
   The text is standardized to reduce Sinhala spelling and morphology variations.

3. **Query Embedding**
   The normalized question is converted into a semantic vector.

4. **Hybrid Retrieval**
   The system performs:

   - **BM25 retrieval** for keyword-exact passages
   - **Dense retrieval** for semantic matching
   - **Re-ranking** using pseudo-questions (via QuIM-style method)

5. **Context Selection**
   The top-ranked passages from teacher resources are selected.

6. **Answer / Summary Generation**
   The model generates:

   - **Source-bound answer**, or
   - **Condensed summary**, depending on user intent.

7. **Output Delivery**
   The mobile app receives the answer with optional reference indicators.

---

# **3. Voice-Based Q&A Workflow (Speech Input → Text → Answer → Display Output)**

This module handles Sinhala voice questions with accent-aware processing.

### **Workflow Steps**

1. **Voice Capture**
   The user speaks a Sinhala question using the app microphone.

2. **Speech Recognition (ASR)**
   The audio is transcribed into Sinhala text using a fine-tuned Whisper model.

3. **Intent Classification**
   The system identifies whether the user requests:

   - a direct answer
   - or a summary.

4. **RAG Processing**
   The recognized text is forwarded to the RAG module for retrieval and answer generation.

5. **Sinhala Text Response**
   The system produces a source-grounded answer.

6. **Output Delivery**
   The app displays the text response.

---

# **4. Automatic Answer Evaluation Workflow**

This module grades student answers based on semantic similarity to teacher-provided material.

### **Workflow Steps**

1. **Answer Submission**
   A student inputs an answer as typed text or uploads a photo.

2. **OCR (Only for Images)**
   The image is processed and converted into text using the same OCR pipeline used for documents.

3. **Text Preparation**
   The extracted text is cleaned and split into segments.

4. **Embedding Generation**
   Embeddings are produced for:

   - the student answer
   - the expected answer
   - the key points from teacher notes

5. **Semantic Comparison**
   The system checks:

   - matched concepts
   - partially correct ideas
   - missing points
   - irrelevant or incorrect statements

6. **Rubric-Based Evaluation**
   Scores are calculated based on:

   - coverage
   - accuracy
   - clarity
     (or the rubric defined by the teacher)

7. **Feedback Generation**
   The system produces:

   - question-level breakdown
   - suggestions for improvement
   - overall score

8. **Output Delivery**
   Results are displayed in the mobile app.

---

# **🧩 How All Components Work Together**

This combined workflow shows the end-to-end flow of information through the system.

1. **User uploads document → OCR → normalized Sinhala text → embeddings stored**
2. **Student asks question (text or voice) → query processed → relevant passages retrieved**
3. **RAG model generates answer or summary → displayed to user**
4. **Student uploads answer → embeddings compared → grade + feedback sent back**

The modules remain independent but share embeddings and cleaned Sinhala text for consistency.

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
Text Output
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

## 🖥️ Backend Structure (backend/)

```
backend/
│── app/
│   ├── main.py
│   ├── config/
│   │   ├── settings.py
│   │   └── logging.py
│   │
│   ├── api/
│   │   ├── router.py
│   │   │
│   │   ├── document_processing/     # Sinhala Document Processing & Embedding
│   │   │   ├── routes.py
│   │   │   ├── service.py
│   │   │   ├── ocr/
│   │   │   │   ├── tesseract_engine.py     # printed Sinhala OCR
│   │   │   │   ├── trocr_engine.py         # handwritten OCR
│   │   │   │   └── image_cleaner.py
│   │   │   ├── embedding/
│   │   │       ├── gemini_embedder.py      # embedding-004 / gemini-embedding-001
│   │   │       ├── chunker.py              # PDF->chunks
│   │   │       ├── bm25_engine.py
│   │   │       ├── faiss_store.py
│   │   │       └── retriever.py            # Hybrid BM25 + FAISS retrieval
│   │   │
│   │   ├── text_qa/                        # RAG with Gemini Flash 2.0
│   │   │   ├── routes.py
│   │   │   ├── controller.py
│   │   │   ├── service.py
│   │   │   ├── rag/
│   │   │   │   ├── retriever.py            # connects to document_processing embeddings
│   │   │   │   └── context_builder.py
│   │   │   ├── generation/
│   │   │   │   ├── gemini_flash_client.py  # main Q&A generator (Flash 2.0)
│   │   │   │   ├── safety_checker.py
│   │   │   │   └── summarizer.py           # optional (Gemini grade-level summarization)
│   │   │   └── schemas.py
│   │   │
│   │   ├── voice_qa/
│   │   │   ├── routes.py
│   │   │   ├── whisper_service.py          # converts speech -> Sinhala text
│   │   │   └── qa_pipeline.py              # passes Whisper output to text_qa
│   │   │
│   │   ├── answer_evaluation/
│   │   │   ├── routes.py
│   │   │   ├── service.py
│   │   │   ├── semantic/
│   │   │   │   ├── xlmr_encoder.py         # semantic similarity
│   │   │   │   ├── rubric_checker.py        # syllabus concept validation
│   │   │   │   └── scorer.py               # adaptive scoring
│   │   │   ├── generation/
│   │   │   │   └── gemini_flash_client.py  # natural Sinhala feedback generator
│   │   │   └── schemas.py
│   │   │
│   │   ├── healthcheck/
│   │   │   └── routes.py
│   │   │
│   │   └── users/
│   │       ├── routes.py
│   │       └── auth_service.py
│   │
│   ├── core/
│   │   ├── model_loader.py
│   │   ├── gemini_client.py               # universal Google Generative AI client
│   │   ├── whisper_loader.py
│   │   ├── utils.py
│   │   └── security.py
│   │
│   ├── db/
│   │   ├── embeddings/                   # cached Gemini embeddings
│   │   ├── faiss_indexes/
│   │   ├── bm25/
│   │   └── metadata/
│   │
│   ├── models/                           # Model files (Tesseract, TrOCR)
│   │   ├── trocr/
│   │   ├── tesseract/
│   │   └── whisper/
│   │
│   └── tests/
│       ├── unit/
│       ├── integration/
│       └── e2e/
│
├── scripts/
│   ├── build_embeddings.py
│   ├── build_faiss.py
│   ├── build_bm25.py
│   └── process_documents.py
│
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
│
├── requirements.txt
├── .env
└── README.md
```

---

# **📱 Mobile Application (Flutter)**

```
mobile/
 └── <Flutter project files>
```

Features include:

- Sinhala input
- Image upload
- Voice question feature
- Displaying answers and feedback

---

# **⚙️ Technologies Used**

### **Mobile**

- Flutter
- Provider / Riverpod
- Firebase (future enhancement)

### **Backend**

- FastAPI
- Python
- Tesseract OCR
- Whisper ASR
- SinBERT / XLM-R embeddings
- Qdrant / FAISS (vector search)

### **Infrastructure**

- Docker
- Docker Compose

---

# **🌿 Branching Strategy**

- Main branch for stable releases
- Dev branch for integration
- Feature branches per component developer
- Naming format: /<module-name>, fix/<issue>
- PR required for merging into dev or main
- Each member maintains their own feature branch:

```
/ocr
/rag
/voice-qa
/answer-evaluation-miyuri
```

Changes are merged into `main` through reviewed Pull Requests.

---

# ** Commit & PR Workflow**

- Commit format:
  feat: added OCR preprocessing
  fix: resolved API timeout
  docs: updated setup instructions

- All merges are done through PRs
- PR includes description, reviewer, and merge date
- No direct commits to main

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

- design report
- mockups
- low-fi and high-fi UI screens
- diagrams
- feedback
- improvements
  are submitted separately following academic guidelines.

They are **not** stored inside this repository to keep the codebase light and organized.

---

# **👤 Authors**

- Sinhala Document Processing: **Ranaweera P.H.K (IT22233452)**
- RAG Q&A Module: **Jayananda L.V.O.R (IT22161406)**
- Voice Q&A Module: **Sathsara T.T.D (IT22362476)**
- Automatic Answer Evaluation: **Lokuhewage M .M (IT22003478)**

---
