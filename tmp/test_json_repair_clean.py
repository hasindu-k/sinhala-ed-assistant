# tmp/test_json_repair_clean.py
import json

def _repair_json(text: str) -> str:
    """Basic recovery for truncated JSON (unterminated strings/objects)."""
    text = text.strip()
    if not text: return "{}"
    
    # 1. Close unterminated string if it ends abruptly
    if text.count('"') % 2 != 0:
        text += '"'
    
    # 2. Add closing markers in reverse order of opening
    stack = []
    # Skip counting within strings to be more accurate
    in_string = False
    escaped = False
    
    for char in text:
        if escaped:
            escaped = False
            continue
        if char == '\\':
            escaped = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        
        if not in_string:
            if char == '{': stack.append('}')
            elif char == '[': stack.append(']')
            elif char == '}': 
                if stack and stack[-1] == '}': stack.pop()
            elif char == ']':
                if stack and stack[-1] == ']': stack.pop()
    
    # Append missing closers
    while stack:
        text += stack.pop()
        
    return text

def test_repair():
    test_cases = [
        ('{"id1": "This is a long text', '{"id1": "This is a long text"}'),
        ('{"id1": "text", "id2": "more', '{"id1": "text", "id2": "more"}'),
        ('{"id1": "text"', '{"id1": "text"}'),
        ('{"p": {"c": "val', '{"p": {"c": "val"}}'),
        ('{"list": ["a", "b', '{"list": ["a", "b"]}')
    ]
    
    success_count = 0
    for corrupted, _ in test_cases:
        repaired = _repair_json(corrupted)
        print(f"Corrupted: {corrupted}")
        print(f"Repaired:  {repaired}")
        try:
            json.loads(repaired)
            print("Status: [PASS] Valid JSON")
            success_count += 1
        except Exception as e:
            print(f"Status: [FAIL] Invalid JSON - {e}")
        print("-" * 20)
    
    if success_count == len(test_cases):
        print("ALL TESTS PASSED")
    else:
        print(f"PASSED {success_count}/{len(test_cases)}")

if __name__ == "__main__":
    test_repair()
