# Services - Refactored Architecture

## Overview

The evaluation and core services have been refactored into a clean **Service + Repository** pattern, separating data access logic from business logic.

---

## Architecture Pattern

### Repository Layer

Handles all database operations (CRUD) directly with models.

- **`rubric_repository.py`** - `RubricRepository` class

  - `create_rubric()`, `get_rubric()`, `get_rubrics_by_user()`
  - `update_rubric()`, `delete_rubric()`
  - `create_rubric_criterion()`, `get_rubric_criteria()`
  - `get_rubric_with_criteria()`

- **`question_paper_repository.py`** - `QuestionPaperRepository` class

  - `create_question_paper()`, `get_question_paper()`
  - `get_question_papers_by_evaluation_session()`
  - `create_question()`, `get_questions_by_paper()`
  - `create_sub_question()`, `get_sub_questions_by_question()`
  - `create_structured_questions()`
  - `get_question_paper_with_questions()`

- **`answer_evaluation_repository.py`** - `AnswerEvaluationRepository` class

  - `create_answer_document()`, `get_answer_document()`
  - `get_answer_documents_by_evaluation_session()`
  - `create_evaluation_result()`, `get_evaluation_result()`
  - `get_evaluation_result_by_answer_document()`
  - `create_question_score()`, `get_question_scores_by_result()`
  - `update_evaluation_result()`

- **`evaluation_session_repository.py`** - `EvaluationSessionRepository` class
  - `create_evaluation_session()`, `get_evaluation_session()`
  - `get_evaluation_sessions_by_chat_session()`
  - `update_evaluation_status()`
  - `add_evaluation_resource()`, `get_evaluation_resources()`
  - `create_paper_config()`, `get_paper_config()`
  - `update_paper_config()`

#### Core Repositories

- **`chat_session_repository.py`** - `ChatSessionRepository`
  - `create_session()`, `get_session()`, `list_user_sessions()`, `validate_ownership()`
- **`message_repository.py`** - `MessageRepository`
  - `create_user_message()`, `create_system_message()`, `create_assistant_message()`, `list_session_messages()`
- **`message_attachment_repository.py`** - `MessageAttachmentRepository`
  - `attach_resource()`, `get_message_resources()`
- **`message_context_repository.py`** - `MessageContextRepository`
  - `log_used_chunks()`, `get_message_sources()`
- **`message_safety_repository.py`** - `MessageSafetyRepository`
  - `create_safety_report()`, `get_safety_report()`
- **`resource_repository.py`** - `ResourceRepository`
  - `upload_resource()`, `get_resource()`, `list_user_resources()`
- **`resource_chunk_repository.py`** - `ResourceChunkRepository`
  - `create_chunks()`, `get_chunks_by_resource()`, `vector_search()`
- **`session_resource_repository.py`** - `SessionResourceRepository`
  - `attach_resource_to_session()`, `get_session_resources()`
- **`user_repository.py`** - `UserRepository`
  - `get_user()`, `get_user_by_email()`, `create_user()`

### Service Layer

Implements business logic by delegating to repositories.

- **`rubric_service.py`** - `RubricService` class (10 methods)

  - Wraps all repository operations
  - Adds business logic like weight validation
  - `create_evaluation_rubric()` - creates standard rubric with semantic/coverage/BM25 weights

- **`question_paper_service.py`** - `QuestionPaperService` class (9 methods)

  - Orchestrates question paper creation and retrieval
  - Supports structured data import

- **`answer_evaluation_service.py`** - `AnswerEvaluationService` class (11 methods)

  - Manages answer documents and evaluation results
  - `create_complete_evaluation()` - orchestrates complete evaluation creation
  - `get_complete_evaluation_result()` - returns formatted result with scores

- **`evaluation_session_service.py`** - `EvaluationSessionService` class (10 methods)
  - Manages evaluation sessions and their resources
  - Handles paper configuration

#### Core Services

- **`chat_session_service.py`** - `ChatSessionService`
  - Create/list sessions, ownership validation
- **`message_service.py`** - `MessageService`
  - Create user/system/assistant messages, list messages
- **`message_attachment_service.py`** - `MessageAttachmentService`
  - Attach resources to messages, list attachments
- **`message_context_service.py`** - `MessageContextService`
  - Log and read used chunks per message
- **`message_safety_service.py`** - `MessageSafetyService`
  - Create/get safety reports for messages
- **`resource_service.py`** - `ResourceService`
  - Upload and read user resources
- **`resource_chunk_service.py`** - `ResourceChunkService`
  - Persist chunks and perform vector search via pgvector
- **`session_resource_service.py`** - `SessionResourceService`
  - Link resources to chat sessions
- **`user_service.py`** - `UserService`
  - Basic user CRUD helpers
- **`rag_service.py`** - `RAGService`
  - Orchestrates retrieval, logs sources, and creates assistant messages

---

## Usage Example

```python
from sqlalchemy.orm import Session
from app.services.evaluation import RubricService, QuestionPaperService
from app.services import MessageService, ChatSessionService, RAGService
from uuid import UUID

# Initialize services
db: Session  # dependency injection from FastAPI
rubric_service = RubricService(db)
question_service = QuestionPaperService(db)
message_service = MessageService(db)
chat_session_service = ChatSessionService(db)
rager = RAGService(db)

# Create evaluation rubric
user_id = UUID("...")
rubric = rubric_service.create_evaluation_rubric(
    user_id=user_id,
    name="Math Exam Rubric"
)

# Create question paper
eval_session_id = UUID("...")
resource_id = UUID("...")
paper = question_service.create_question_paper(
    evaluation_session_id=eval_session_id,
    resource_id=resource_id,
    extracted_text="Question text here"
)

# Get complete paper with questions
full_paper = question_service.get_question_paper_with_questions(paper.id)

# Create a user message and generate an assistant response via RAG
user_msg = message_service.create_user_message(
  session_id=eval_session_id,
  content="Explain the main idea of question 1",
  modality="text",
)
resp = rager.generate_response(
  session_id=eval_session_id,
  user_message_id=user_msg.id,
  user_query=user_msg.content,
  resource_ids=[resource_id],
  query_embedding=None,  # supply embedding to enable vector search
)
print(resp["assistant_message_id"], len(resp["sources"]))
```

---

## Benefits

1. **Separation of Concerns**

   - Repositories handle persistence
   - Services handle business logic
   - Routers handle HTTP

2. **Testability**

   - Easy to mock repositories for unit testing services
   - Clear dependencies

3. **Reusability**

   - Services can be used from different routers, CLI, background jobs
   - Repositories can be swapped with different implementations

4. **Maintainability**
   - Single responsibility principle
   - Clear code organization
   - Easy to locate and fix issues

---

## File Structure

```
app/services/evaluation/
├── __init__.py                          # Exports service classes
├── rubric_repository.py                 # RubricRepository
├── rubric_service.py                    # RubricService
├── question_paper_repository.py         # QuestionPaperRepository
├── question_paper_service.py            # QuestionPaperService
├── answer_evaluation_repository.py      # AnswerEvaluationRepository
├── answer_evaluation_service.py         # AnswerEvaluationService
├── evaluation_session_repository.py     # EvaluationSessionRepository
├── evaluation_session_service.py        # EvaluationSessionService
├── evaluation_resource_service.py       # (legacy - to be migrated)
└── paper_config_service.py              # (legacy - to be migrated)
```

```
app/services/
├── __init__.py                          # Exports core + evaluation services
├── chat_session_repository.py           # ChatSessionRepository
├── chat_session_service.py              # ChatSessionService
├── message_repository.py                # MessageRepository
├── message_service.py                   # MessageService
├── message_attachment_repository.py     # MessageAttachmentRepository
├── message_attachment_service.py        # MessageAttachmentService
├── message_context_repository.py        # MessageContextRepository
├── message_context_service.py           # MessageContextService
├── message_safety_repository.py         # MessageSafetyRepository
├── message_safety_service.py            # MessageSafetyService
├── resource_repository.py               # ResourceRepository
├── resource_service.py                  # ResourceService
├── resource_chunk_repository.py         # ResourceChunkRepository
├── resource_chunk_service.py            # ResourceChunkService
├── session_resource_repository.py       # SessionResourceRepository
├── session_resource_service.py          # SessionResourceService
├── user_repository.py                   # UserRepository
└── user_service.py                      # UserService
```

---

## Migration Notes

- Each service class wraps a single repository
- Initialization: `service = ServiceClass(db: Session)`
- All database operations delegated to repository methods
- Services implement business logic and orchestration

### Import Aggregation

- Core and evaluation services are re-exported from `app/services/__init__.py` for convenience.

```python
from app.services import (
  ChatSessionService,
  MessageService,
  ResourceService,
  RubricService,
  EvaluationSessionService,
)
```
