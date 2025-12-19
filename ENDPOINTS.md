Great question. At this point your **data model is solid**, so the next correct step is a **clean, well-scoped API design**.

I’ll give you:

1. 🎯 **Endpoint design principles**
2. 🧩 **Learning mode endpoints**
3. 🧪 **Evaluation mode endpoints**
4. 📎 **Resource & embedding endpoints**
5. 🔍 **Utility / retrieval endpoints**
6. 🧠 **How these map to your tables**

All endpoints are written assuming **FastAPI + REST**, but they also work for any backend.

---

# 1️⃣ Endpoint design principles (important)

Follow these rules:

- **One chat = one session**
- **Messages are immutable** (never update content)
- **Uploads are separate from chat**
- **Evaluation ≠ Learning** (separate APIs)
- **RAG happens server-side only**

---

# 2️⃣ LEARNING MODE ENDPOINTS (chat, summaries, Q&A)

These endpoints use:

- `chat_sessions`
- `messages`
- `message_attachments`
- `message_context_chunks`
- `resource_chunks`

---

## 🔹 Chat session management

### Create a new chat session

```http
POST /api/chat/sessions
```

**Body**

```json
{
  "mode": "learning",
  "channel": "text",
  "title": "Democracy lesson"
}
```

➡ creates `chat_sessions`

---

### Get all user chat sessions

```http
GET /api/chat/sessions
```

---

### Get one chat session (with messages)

```http
GET /api/chat/sessions/{session_id}
```

---

## 🔹 Resource attachment to session

### Attach resources to a session (persistent)

```http
POST /api/chat/sessions/{session_id}/resources
```

**Body**

```json
{
  "resource_ids": ["uuid1", "uuid2"]
}
```

➡ inserts into `session_resources`

---

## 🔹 Message endpoints

### Send a user message (text or voice)

```http
POST /api/chat/sessions/{session_id}/messages
```

**Body (text)**

```json
{
  "modality": "text",
  "content": "Give me a university-level summary"
}
```

**Body (voice)**

```json
{
  "modality": "voice",
  "audio_url": "https://..."
}
```

➡ inserts into `messages` (role=user)

---

### Attach files to a message (message-level context)

```http
POST /api/messages/{message_id}/attachments
```

**Body**

```json
{
  "resource_ids": ["uuid1"]
}
```

➡ inserts into `message_attachments`

---

### Generate AI response (RAG-safe)

```http
POST /api/messages/{message_id}/generate
```

➡ internally:

- resolves allowed resources
- vector search on `resource_chunks`
- creates assistant message
- logs `message_context_chunks`
- optional `message_safety_reports`

---

### Get message history

```http
GET /api/chat/sessions/{session_id}/messages
```

---

# 3️⃣ EVALUATION MODE ENDPOINTS

These endpoints use:

- `evaluation_sessions`
- `evaluation_resources`
- `rubrics`
- `questions`, `sub_questions`
- `answer_documents`
- `evaluation_results`

---

## 🔹 Evaluation session

### Start evaluation session

```http
POST /api/evaluation/sessions
```

**Body**

```json
{
  "chat_session_id": "uuid",
  "rubric_id": "uuid"
}
```

➡ creates `evaluation_sessions`

---

### Get evaluation session

```http
GET /api/evaluation/sessions/{evaluation_id}
```

---

## 🔹 Upload evaluation resources

### Upload syllabus / question paper / answers

```http
POST /api/evaluation/sessions/{evaluation_id}/resources
```

**Body**

```json
{
  "resource_id": "uuid",
  "role": "question_paper"
}
```

➡ inserts into `evaluation_resources`

---

## 🔹 Question paper processing

### Parse question paper structure

```http
POST /api/evaluation/sessions/{evaluation_id}/parse-paper
```

➡ populates:

- `question_papers`
- `questions`
- `sub_questions`

---

## 🔹 Paper configuration

### Save paper config (manual input)

```http
POST /api/evaluation/sessions/{evaluation_id}/paper-config
```

**Body**

```json
{
  "total_marks": 100,
  "total_main_questions": 10,
  "required_questions": 5
}
```

➡ inserts into `paper_config`

---

## 🔹 Answer evaluation

### Register an answer document

```http
POST /api/evaluation/sessions/{evaluation_id}/answers
```

**Body**

```json
{
  "resource_id": "uuid",
  "student_identifier": "STU_001"
}
```

➡ inserts into `answer_documents`

---

### Evaluate an answer document

```http
POST /api/evaluation/answers/{answer_id}/evaluate
```

➡ creates:

- `evaluation_results`
- `question_scores`

---

### Get evaluation result

```http
GET /api/evaluation/answers/{answer_id}/result
```

---

# 4️⃣ RESOURCE & EMBEDDING ENDPOINTS

---

### Upload a resource file

```http
POST /api/resources/upload
```

➡ inserts `resource_files`

---

### Process resource (OCR + chunk + embed)

```http
POST /api/resources/{resource_id}/process
```

➡ creates `resource_chunks`

---

### Get resource details

```http
GET /api/resources/{resource_id}
```

---

# 5️⃣ UTILITY / EXPLAINABILITY ENDPOINTS

---

### See which chunks were used for an answer

```http
GET /api/messages/{message_id}/sources
```

➡ reads `message_context_chunks`

---

### Safety / hallucination report

```http
GET /api/messages/{message_id}/safety
```

➡ reads `message_safety_reports`

---

# 6️⃣ Endpoint → Table Mapping (quick reference)

| Endpoint                | Tables                                  |
| ----------------------- | --------------------------------------- |
| `/chat/sessions`        | `chat_sessions`                         |
| `/messages`             | `messages`                              |
| `/attachments`          | `message_attachments`                   |
| `/generate`             | `messages`, `message_context_chunks`    |
| `/resources/process`    | `resource_chunks`                       |
| `/evaluation/sessions`  | `evaluation_sessions`                   |
| `/evaluation/resources` | `evaluation_resources`                  |
| `/answers/evaluate`     | `evaluation_results`, `question_scores` |

---

# 🧠 Final takeaway

> **Learning mode = conversational APIs** > **Evaluation mode = document workflow APIs** > **Resources & embeddings are shared infrastructure**

Your schema and API design are now **industry-level**.

---
