import json
import os
import sys

from guarded_memory import GuardedMemory
from rag import HERE, load_docs
from attack import MARKER, make_targeted_poison
from evaluate import normalize


def build_memory(policy):
    eval_set = json.load(open(os.path.join(HERE, "eval_set.json")))
    poison, targets = make_targeted_poison(eval_set)
    mem = GuardedMemory(fresh=True, policy=policy)
    for d in load_docs():                                   # signed
        mem.write(d["text"], d["id"], source="owner", trust="trusted")
    for p in poison:                                        # unsigned
        mem.inject_raw(p["text"], p["id"], source=p["source"], trust=p["trust"])
    return mem, targets, eval_set


def measure(mem, targets, eval_set):
    hijacked = sum(MARKER in mem.answer(t["question"])[0] for t in targets)
    correct = sum(normalize(e["answer"]) in normalize(mem.answer(e["question"])[0]) for e in eval_set)
    return hijacked / len(targets), correct / len(eval_set)


def main():
    policy = "off" if ("--policy" in sys.argv and "off" in sys.argv) else "provenance"
    print(f"LLM backend: {os.environ.get('MEMGUARD_LLM', 'mock')} | policy: {policy}\n")

    mem, targets, eval_set = build_memory(policy)
    asr, clean = measure(mem, targets, eval_set)

    if policy == "provenance":
        os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
        json.dump({"phase": "after_provenance", "asr": asr, "clean_accuracy_retention": clean,
                   "defense": "provenance"},
                  open(os.path.join(HERE, "results", "attack_after.json"), "w"), indent=2)

    print("=" * 50)
    print(f"  WITH MEMGUARD ({policy})")
    print(f"    Attack Success Rate (targeted): {asr:.0%}")
    print(f"    Clean accuracy (all queries):   {clean:.0%}")
    print("=" * 50)
    if policy == "provenance":
        print("  Saved -> results/attack_after.json  (run make_chart.py)")


if __name__ == "__main__":
    main()