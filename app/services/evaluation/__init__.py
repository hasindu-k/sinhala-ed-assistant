# app/services/evaluation/__init__.py

from app.services.evaluation.evaluation_session_service import (
    create_evaluation_session,
    get_evaluation_session,
    get_evaluation_sessions_by_chat_session,
    update_evaluation_status,
    add_evaluation_resource,
    get_evaluation_resources,
    create_paper_config,
    get_paper_config,
    update_paper_config,
)

from app.services.evaluation.question_paper_service import (
    create_question_paper,
    get_question_paper,
    get_question_papers_by_evaluation_session,
    create_question,
    get_questions_by_paper,
    create_sub_question,
    get_sub_questions_by_question,
    create_structured_questions,
    get_question_paper_with_questions,
)

from app.services.evaluation.answer_evaluation_service import (
    create_answer_document,
    get_answer_document,
    get_answer_documents_by_evaluation_session,
    create_evaluation_result,
    get_evaluation_result,
    get_evaluation_result_by_answer_document,
    create_question_score,
    get_question_scores_by_result,
    update_evaluation_result,
    create_complete_evaluation,
    get_complete_evaluation_result,
)

from app.services.evaluation.rubric_service import (
    create_rubric,
    get_rubric,
    get_rubrics_by_user,
    update_rubric,
    delete_rubric,
    create_rubric_criterion,
    get_rubric_criteria,
    update_rubric_criterion,
    delete_rubric_criterion,
    create_rubric_with_criteria,
    get_rubric_with_criteria,
    create_evaluation_rubric,
)

__all__ = [
    # Evaluation Session
    "create_evaluation_session",
    "get_evaluation_session",
    "get_evaluation_sessions_by_chat_session",
    "update_evaluation_status",
    "add_evaluation_resource",
    "get_evaluation_resources",
    "create_paper_config",
    "get_paper_config",
    "update_paper_config",
    
    # Question Paper
    "create_question_paper",
    "get_question_paper",
    "get_question_papers_by_evaluation_session",
    "create_question",
    "get_questions_by_paper",
    "create_sub_question",
    "get_sub_questions_by_question",
    "create_structured_questions",
    "get_question_paper_with_questions",
    
    # Answer Evaluation
    "create_answer_document",
    "get_answer_document",
    "get_answer_documents_by_evaluation_session",
    "create_evaluation_result",
    "get_evaluation_result",
    "get_evaluation_result_by_answer_document",
    "create_question_score",
    "get_question_scores_by_result",
    "update_evaluation_result",
    "create_complete_evaluation",
    "get_complete_evaluation_result",
    
    # Rubric
    "create_rubric",
    "get_rubric",
    "get_rubrics_by_user",
    "update_rubric",
    "delete_rubric",
    "create_rubric_criterion",
    "get_rubric_criteria",
    "update_rubric_criterion",
    "delete_rubric_criterion",
    "create_rubric_with_criteria",
    "get_rubric_with_criteria",
    "create_evaluation_rubric",
]
