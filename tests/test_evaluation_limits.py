# tests/test_evaluation_limits.py
import sys
import os
from datetime import datetime, timedelta
from uuid import uuid4

# Add the project root to sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from sqlalchemy import create_engine, text, String, JSON, Integer, DateTime, Column, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, relationship

# We will define a minimal set of models for testing to avoid JSONB/UUID issues
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True)
    email = Column(String)
    tier = Column(String, default="normal")

class ChatSession(Base):
    __tablename__ = "chat_sessions"
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"))

class EvaluationSession(Base):
    __tablename__ = "evaluation_sessions"
    id = Column(String, primary_key=True)
    session_id = Column(String, ForeignKey("chat_sessions.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

# Mock Settings
class MockSettings:
    EVALUATION_LIMIT_NORMAL = 2
    EVALUATION_LIMIT_BASIC = 20
    EVALUATION_LIMIT_CLASSROOM = 60
    EVALUATION_LIMIT_INSTITUTION = -1
    EVALUATION_LIMIT_DURATION_HOURS = 12

mock_settings = MockSettings()

# Import the service logic but we might need to mock its dependencies
from app.services.usage_service import UsageService

# Patch UsageService to use our test models and settings
import app.services.usage_service
app.services.usage_service.User = User
app.services.usage_service.ChatSession = ChatSession
app.services.usage_service.EvaluationSession = EvaluationSession
app.services.usage_service.settings = mock_settings

def setup_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()

def test_evaluation_limits():
    db = setup_db()
    service = UsageService(db)
    
    # 1. Test Tier Mapping
    print("Testing tier mapping...")
    assert service.get_user_tier_limit("normal") == 2
    assert service.get_user_tier_limit("basic") == 20
    print("PASS")

    # 2. Test Normal User Limit
    print("Testing normal user limit...")
    user_id = str(uuid4())
    user = User(id=user_id, email="normal@test.com", tier="normal")
    db.add(user)
    
    chat_id = str(uuid4())
    chat = ChatSession(id=chat_id, user_id=user_id)
    db.add(chat)
    db.commit()

    # Add 2 evaluations (the limit)
    for _ in range(2):
        eval_id = str(uuid4())
        evaluation = EvaluationSession(id=eval_id, session_id=chat_id, created_at=datetime.now())
        db.add(evaluation)
    db.commit()

    # Next one should fail
    try:
        service.check_evaluation_limit(user_id)
        print("FAIL: Should have raised HTTPException")
        return
    except Exception as e:
        if hasattr(e, 'status_code') and e.status_code == 403:
            print("PASS (received 403)")
        else:
            print(f"FAIL: Received unexpected exception: {e}")
            return

    # 3. Test Time Window
    print("Testing time window...")
    # Update old evaluations to be 13 hours ago
    threshold = datetime.now() - timedelta(hours=13)
    db.query(EvaluationSession).update({EvaluationSession.created_at: threshold})
    db.commit()

    # Now it should pass
    try:
        assert service.check_evaluation_limit(user_id) is True
        print("PASS")
    except Exception as e:
        print(f"FAIL: Should have passed but got: {e}")
        return

    # 4. Test Institution Unlimited
    print("Testing institution unlimited...")
    user.tier = "institution"
    db.commit()
    
    # Add 100 evaluations
    for _ in range(100):
        eval_id = str(uuid4())
        evaluation = EvaluationSession(id=eval_id, session_id=chat_id, created_at=datetime.now())
        db.add(evaluation)
    db.commit()

    try:
        assert service.check_evaluation_limit(user_id) is True
        print("PASS")
    except Exception as e:
        print(f"FAIL: Institution should be unlimited but got: {e}")
        return

    print("\nALL EVALUATION LIMIT TESTS PASSED!")

if __name__ == "__main__":
    test_evaluation_limits()
