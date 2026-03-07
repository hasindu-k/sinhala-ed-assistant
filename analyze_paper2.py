import json

with open('student1_dump.json', encoding='utf-8') as f:
    data = json.load(f)

scores = {}
for s in data["scores"]:
    key = str(s["question_id"]) + "_" + str(s["sub_question_id"])
    scores[key] = s["awarded_marks"]

print("Dumped scores dictionary:")
for k, v in scores.items():
    if v > 0:
        print(f"Key: {k}, marks: {v}")
print(f"Total: {sum(scores.values())}")
