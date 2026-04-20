__all__ = [
    "RubricService",
    "QuestionPaperService",
    "AnswerEvaluationService",
    "EvaluationSessionService",
    "EvaluationResourceService",
    "PaperConfigService",
    "EvaluationWorkflowService",
]


def __getattr__(name):
    if name == "RubricService":
        from app.services.evaluation.rubric_service import RubricService

        return RubricService
    if name == "QuestionPaperService":
        from app.services.evaluation.question_paper_service import QuestionPaperService

        return QuestionPaperService
    if name == "AnswerEvaluationService":
        from app.services.evaluation.answer_evaluation_service import AnswerEvaluationService

        return AnswerEvaluationService
    if name == "EvaluationSessionService":
        from app.services.evaluation.evaluation_session_service import EvaluationSessionService

        return EvaluationSessionService
    if name == "EvaluationResourceService":
        from app.services.evaluation.evaluation_resource_service import EvaluationResourceService

        return EvaluationResourceService
    if name == "PaperConfigService":
        from app.services.evaluation.paper_config_service import PaperConfigService

        return PaperConfigService
    if name == "EvaluationWorkflowService":
        from app.services.evaluation.evaluation_workflow_service import EvaluationWorkflowService

        return EvaluationWorkflowService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
