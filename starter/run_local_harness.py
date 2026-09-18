import argparse
import json
import os
import sys
import importlib
from datetime import datetime

def main():
    parser = argparse.ArgumentParser(description="Run local evaluation harness for ATLAS.")
    parser.add_argument("--module", default="stage1.atlas", help="Module path to Atlas class")
    parser.add_argument("--data", default="hackathon-data", help="Path to data directory")
    args = parser.parse_args()

    sys.path.insert(0, os.getcwd())
    try:
        mod = importlib.import_module(args.module)
        StudyGraph = getattr(mod, "StudyGraph")
        Atlas = getattr(mod, "Atlas")
    except Exception as e:
        print(f"[FAIL] Could not import {args.module}: {e}")
        sys.exit(1)

    from starter.schemas import Question, Answer, RecordRef

    print("=== Starting Local Harness Evaluation ===")
    print(f"Loading data from: {args.data}")

    t0 = datetime.now()
    graph = StudyGraph(args.data)
    stats = graph.build()
    build_sec = (datetime.now() - t0).total_seconds()

    print(f"[PASS] Graph built in {build_sec:.2f}s ({stats.get('ms', 0)} ms)")
    print(f"       Nodes: {stats.get('nodes')}, Edges: {stats.get('edges')}, Subjects: {stats.get('subjects')}")

    if build_sec > 120.0:
        print(f"[FAIL] Graph build exceeded 120s limit: {build_sec:.2f}s")
        sys.exit(1)

    agent = Atlas(graph)

    test_cases = [
        {"id": "TEST-1", "text": "Which subjects meet potential Hy's law criteria?", "type": "finding"},
        {"id": "TEST-2", "text": "Which subjects at site S01 received a wrong dose?", "type": "trap"},
        {"id": "TEST-3", "text": "How many subjects at site S07 discontinued due to an adverse event?", "type": "count"},
        {"id": "TEST-4", "text": "Which subjects received prohibited concomitant medications?", "type": "finding"}
    ]

    passed = 0
    for tc in test_cases:
        q = Question(id=tc["id"], text=tc["text"])
        t_start = datetime.now()
        ans = agent.answer(q)
        duration = (datetime.now() - t_start).total_seconds()

        assert isinstance(ans.question_id, str)
        assert isinstance(ans.confidence, float)
        assert isinstance(ans.evidence, list)

        if tc["type"] == "trap":
            if ans.answer == [] and len(ans.evidence) == 0:
                print(f"[PASS] {tc['id']} (Trap returned clean [] with 0 citations in {duration:.3f}s)")
                passed += 1
            else:
                print(f"[FAIL] {tc['id']} (Trap produced non-empty output: {ans.answer})")
        else:
            print(f"[PASS] {tc['id']} (Returned {len(ans.evidence)} citations in {duration:.3f}s)")
            passed += 1

    print(f"\nSummary: {passed}/{len(test_cases)} tests completed successfully.")

if __name__ == "__main__":
    main()
