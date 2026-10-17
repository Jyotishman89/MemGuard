import json
import os
import sys
 
from rag import HERE, RagAgent, load_docs
 
 
def normalize(s):
    return " ".join(s.lower().split())
 
 
def score(agent, eval_set, show=False):
    correct = 0
    rows = []
    for item in eval_set:
        response, hits = agent.answer(item["question"])
        ok = normalize(item["answer"]) in normalize(response)
        correct += ok
        rows.append({"q": item["question"], "expected": item["answer"], "ok": ok})
        if show:
            print(f"  [{'PASS' if ok else 'FAIL'}] {item['question']}  -> expected '{item['answer']}'")
    accuracy = correct / len(eval_set)
    return accuracy, correct, rows
 
 
def main():
    show = "--show" in sys.argv
    print(f"LLM backend: {os.environ.get('MEMGUARD_LLM', 'mock')}")
    print("Indexing clean knowledge base...")
    agent = RagAgent(fresh=True)
    n = agent.index(load_docs())
    print(f"Indexed {n} documents.\n")
 
    eval_set = json.load(open(os.path.join(HERE, "eval_set.json")))
    print(f"Scoring {len(eval_set)} questions...\n")
    accuracy, correct, rows = score(agent, eval_set, show=show)
 
    results_dir = os.path.join(HERE, "results")
    os.makedirs(results_dir, exist_ok=True)
    json.dump(
        {"metric": "clean_accuracy", "accuracy": accuracy, "correct": correct,
         "total": len(eval_set), "rows": rows},
        open(os.path.join(results_dir, "baseline.json"), "w"), indent=2,
    )
 
    print("\n" + "=" * 40)
    print(f"  BASELINE CLEAN ACCURACY: {accuracy:.0%}")
    print(f"  ({correct}/{len(eval_set)} questions correct)")
    print("=" * 40)
    print("Saved -> results/baseline.json")
 
 
if __name__ == "__main__":
    main()
 