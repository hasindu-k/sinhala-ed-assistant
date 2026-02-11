

from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.services.evaluation.evaluation_workflow_service import EvaluationWorkflowService
from uuid import uuid4

client = TestClient(app)

from app.core.security import get_current_user
# Mock the dependency get_current_user to bypass authentication
async def mock_get_current_user():
    user = MagicMock()
    user.id = uuid4()
    return user

app.dependency_overrides[get_current_user] = mock_get_current_user

from app.core.database import get_db
# Mock database session
def mock_get_db():
    return MagicMock()

app.dependency_overrides[get_db] = mock_get_db

def test_evaluate_answer_stream():
    answer_id = uuid4()
    
    # Mock the generator
    mock_generator = [
        ("processing_documents", "Checking answer resource...", 10),
        ("evaluating_answers", "Starting grading process...", 50),
        ("completed", "Evaluation completed.", 100)
    ]

    with patch.object(EvaluationWorkflowService, 'evaluate_answer_generator', return_value=mock_generator) as mock_method:
        response = client.post(f"/api/v1/evaluation/answers/{answer_id}/evaluate/stream")
        
        assert response.status_code == 200
        # Check if content type is text/event-stream; charset=utf-8 (FastAPI default)
        assert "text/event-stream" in response.headers["content-type"]
        
        content = response.text
        lines = content.strip().split('\n')
        
        assert len(lines) == 3
        
        import json
        
        event1 = json.loads(lines[0])
        assert event1["stage"] == "processing_documents"
        assert event1["progress"] == 10
        assert event1["status"] == "processing"
        
        event2 = json.loads(lines[1])
        assert event2["stage"] == "evaluating_answers"
        assert event2["progress"] == 50
        
        event3 = json.loads(lines[2])
        assert event3["stage"] == "completed"
        assert event3["progress"] == 100

if __name__ == "__main__":
    # Manually run the test if executed directly
    try:
        test_evaluate_answer_stream()
        print("Test passed successfully!")
    except AssertionError as e:
        print(f"Test failed: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
