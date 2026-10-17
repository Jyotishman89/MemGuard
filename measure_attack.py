"""The "before" scoreboard for the targeted attack (no defense).

  ASR (on targeted queries) -- % of target questions whose answer carries the payload
  Clean accuracy (all)      -- % of ALL questions still answered correctly
  Poison rate               -- poison passages / corpus

Writes results/attack_before.json.

    python measure_attack.py [--show]
"""

import json
import os
import sys

from rag import HERE, RagAgent, load_docs
from attack import MARKER, build_files
from evaluate import normalize


def load_or_build():
    kb = os.path.join(HERE, "poisoned_kb.json")
    tg = os.path.join(HERE, "targets.json")
    if os.path.exists(kb) and os.path.exists(tg):
        return json.load(open(kb)), json.load(open(tg))
    return build_files()


def main():
    show = "--show" in sys.argv
    print(f"LLM backend: {os.environ.get('MEMGUARD_LLM', 'mock')}\n")
    poisoned_kb, targets = load_or_build()
    n_poison = sum(1 for d in poisoned_kb if str(d["id"]).startswith("p"))

    agent = RagAgent(fresh=True)
    agent.index(poisoned_kb)
    print(f"Indexed {len(poisoned_kb)} docs ({n_poison} poison).\n")

    # ASR on the targeted questions
    hijacked = 0
    for t in targets:
        ans, _ = agent.answer(t["question"])
        hit = MARKER in ans
        hijacked += hit
        if show:
            print(f"  ASR={'HIT' if hit else '---'}  {t['question']}")
    asr = hijacked / len(targets)

    # Clean accuracy across ALL questions (targets counted as wrong if hijacked)
    eval_set = json.load(open(os.path.join(HERE, "eval_set.json")))
    correct = 0
    for e in eval_set:
        ans, _ = agent.answer(e["question"])
        correct += normalize(e["answer"]) in normalize(ans)
    clean_acc = correct / len(eval_set)
    poison_rate = n_poison / len(poisoned_kb)

    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    json.dump({"phase": "before_defense", "asr": asr, "clean_accuracy_retention": clean_acc,
               "poison_rate": poison_rate, "n_targets": len(targets), "n_poison": n_poison},
              open(os.path.join(HERE, "results", "attack_before.json"), "w"), indent=2)

    print("=" * 50)
    print("  BEFORE MEMGUARD (targeted attack, no defense)")
    print(f"    Attack Success Rate (targeted): {asr:.0%}")
    print(f"    Clean accuracy (all queries):   {clean_acc:.0%}")
    print(f"    Corpus poison rate:             {poison_rate:.1%}")
    print("=" * 50)
    print("  Saved -> results/attack_before.json")


if __name__ == "__main__":
    main()