# tmp/test_json_repair.py
import json
import re
import sys
import os

# Add app to path to import classifier_service
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.components.document_processing.services.classifier_service import _repair_json

def test_repair():
    test_cases = [
        # 1. Truncated string
        ('{"id1": "This is a long text', '{"id1": "This is a long text"}'),
        # 2. Truncated object
        ('{"id1": "text", "id2": "more', '{"id1": "text", "id2": "more"}'),
        # 3. Missing closing brace
        ('{"id1": "text"', '{"id1": "text"}'),
        # 4. Nested truncated
        ('{"p": {"c": "val', '{"p": {"c": "val"}}'),
        # 5. List truncated
        ('{"list": ["a", "b', '{"list": ["a", "b"]}')
    ]
    
    for corrupted, expected_pattern in test_cases:
        repaired = _repair_json(corrupted)
        print(f"Corrupted: {corrupted}")
        print(f"Repaired:  {repaired}")
        try:
            json.loads(repaired)
            print("Status: ✅ Valid JSON")
        except Exception as e:
            print(f"Status: ❌ Invalid JSON - {e}")
        print("-" * 20)

if __name__ == "__main__":
    test_repair()
