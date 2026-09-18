from app import get_stats, get_patient, ask_question, index, QueryRequest

# 1. Stats
stats = get_stats()
print("Stats:", stats)
assert stats["subjects"] == 241
assert stats["nodes"] > 0

# 2. Patient
p = get_patient("042-S07-001")
labs = p.get("lb", p.get("labs", []))
print("Patient 042-S07-001:", p["usubjid"], "Labs:", len(labs))
assert p["usubjid"] == "042-S07-001"

# 3. Ask Hy's Law
ans_hys = ask_question(QueryRequest(question="Hy's law finding", type="hys_law"))
print("Hy's Law answer:", ans_hys["answer"])
assert "042-S07-001" in ans_hys["answer"]

# 4. Ask Trap
ans_trap = ask_question(QueryRequest(question="Site S01 wrong doses", type="trap"))
print("Trap answer:", ans_trap["answer"], "confidence:", ans_trap["confidence"])
assert ans_trap["answer"] == [] and ans_trap["confidence"] == 0.95

# 5. Index HTML
html = index()
assert "Study Sentinel" in html.body.decode("utf-8")

print("All endpoint logic tested and passed!")
