
import sys
import os
import inspect

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Monkeypatch JSONB for SQLite testing
from sqlalchemy.dialects import postgresql
from sqlalchemy import JSON
postgresql.JSONB = JSON

from app.shared.models.answer_evaluation import AnswerDocument, StudentAnswer, QuestionScore
from app.shared.models.question_papers import Question, SubQuestion

def inspect_models():
    models = [AnswerDocument, StudentAnswer, QuestionScore, Question, SubQuestion]
    for m in models:
        print(f"Model: {m.__name__}")
        try:
            # Check __init__ signature
            sig = inspect.signature(m.__init__)
            print(f"  Init Signature: {sig}")
        except Exception as e:
            print(f"  Could not get signature for {m.__name__}: {e}")
            
    # Try to instantiate one with NO args
    try:
        ad = AnswerDocument()
        print("  Instantiated AnswerDocument with NO args successfully.")
    except Exception as e:
        print(f"  Failed to instantiate AnswerDocument with NO args: {e}")

if __name__ == "__main__":
    inspect_models()
