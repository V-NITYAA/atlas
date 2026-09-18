import json
import os
from stage1.atlas import StudyGraph, Atlas
from starter.schemas import Question

print("--- 1. Building StudyGraph ---")
data_path = "hackathon-data/data" if os.path.exists("hackathon-data/data") else "hackathon-data"
g = StudyGraph(data_path)
stats = g.build()

with open("graph_stats.json", "w", encoding="utf-8") as f:
    json.dump(stats, f, indent=2)
print("SUCCESS: graph_stats.json generated successfully!")
print(f"Stats: {stats}")

print("\n--- 2. Generating stage1_public.json ---")
agent = Atlas(g)

test_questions = [
    {"id": "Q1", "text": "Which subjects meet potential Hy's law criteria?"},
    {"id": "Q2", "text": "Which subjects at site S01 received a wrong dose?"},
    {"id": "Q3", "text": "How many subjects at site S07 discontinued due to an adverse event?"},
    {"id": "Q4", "text": "Which subjects received prohibited concomitant medications?"}
]

out = []
for item in test_questions:
    q = Question(id=item["id"], text=item["text"])
    ans = agent.answer(q)
    
    # Serialize safely via Pydantic model_dump if available, else dict
    if hasattr(ans, "model_dump"):
        dumped = ans.model_dump()
    elif hasattr(ans, "dict"):
        dumped = ans.dict()
    else:
        dumped = {
            "question_id": getattr(ans, "question_id", item["id"]),
            "answer": getattr(ans, "answer", []),
            "evidence": [
                {"domain": r.domain, "usubjid": r.usubjid, "seq": r.seq}
                for r in getattr(ans, "evidence", [])
            ],
            "confidence": getattr(ans, "confidence", 0.95)
        }
    out.append(dumped)

with open("stage1_public.json", "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2)
print("SUCCESS: stage1_public.json generated successfully!")
print(f"Evaluated {len(out)} questions cleanly.")
