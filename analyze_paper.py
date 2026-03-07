import json

with open('student1_dump.json', encoding='utf-8') as f:
    data = json.load(f)

print("Total score:", data["total_score"])
print("Num mapped answers:", len(data["mapped_answers"]))
print("Num score entries:", len(data["scores"]))

# Group by question_id or sub_question_id
scores_by_q = {}
for s in data["scores"]:
    key = str(s["question_id"]) + "_" + str(s["sub_question_id"])
    scores_by_q[key] = s["awarded_marks"]

print("Unique score entries:", len(scores_by_q))
print("Sum of unique score entries:", sum(scores_by_q.values()))
