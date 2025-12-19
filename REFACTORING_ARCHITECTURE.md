# Evaluation Services - Refactored Architecture

## Overview

The evaluation services have been refactored into a clean **Service + Repository** pattern, separating data access logic from business logic.

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

---

## Usage Example

```python
from sqlalchemy.orm import Session
from app.services.evaluation import RubricService, QuestionPaperService
from uuid import UUID

# Initialize services
db: Session  # dependency injection from FastAPI
rubric_service = RubricService(db)
question_service = QuestionPaperService(db)

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

---

## Migration Notes

- Each service class wraps a single repository
- Initialization: `service = ServiceClass(db: Session)`
- All database operations delegated to repository methods
- Services implement business logic and orchestration
