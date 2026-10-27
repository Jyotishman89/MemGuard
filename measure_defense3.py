import json
import os
import sys

from guarded_memory import GuardedMemory
from detector import AnomalyDetector
from rag import HERE, load_docs
from attack import MARKER, make_targeted_poison
from evaluate import normalize


def build_signed_memory():
    eval_set = json.load(open(os.path.join(HERE, "eval_set.json")))
    poison, targets = make_targeted_poison(eval_set)
    mem = GuardedMemory(fresh=True, policy="both")
    for d in load_docs():
        mem.write(d["text"], d["id"], source="owner", trust="trusted")
    for p in poison:                                   # signed poison (trusted channel)
        mem.write(p["text"], p["id"], source="trusted_pipeline", trust="trusted")
    return mem, targets, eval_set, len(poison)


def measure(mem, targets, eval_set):
    hijacked = sum(MARKER in mem.answer(t["question"])[0] for t in targets)
    correct = sum(normalize(e["answer"]) in normalize(mem.answer(e["question"])[0]) for e in eval_set)
    return hijacked / len(targets), correct / len(eval_set)


def main():
    print(f"LLM backend: {os.environ.get('MEMGUARD_LLM', 'mock')}\n")
    mem, targets, eval_set, n_poison = build_signed_memory()
    print(f"Memory: {mem.count()} docs (clean + {n_poison} poison, ALL signed).\n")

    asr_a, clean_a = measure(mem, targets, eval_set)
    print(f"A. Provenance only:       ASR {asr_a:.0%}   clean {clean_a:.0%}   <- signatures don't catch signed poison")

    flagged = mem.scan(AnomalyDetector())
    clean_fp = max(flagged - n_poison, 0)
    print(f"B. Anomaly scan:          flagged {flagged} docs ({min(flagged, n_poison)} poison + {clean_fp} false-positives)")

    asr_c, clean_c = measure(mem, targets, eval_set)
    print(f"C. Provenance + anomaly:  ASR {asr_c:.0%}   clean {clean_c:.0%}\n")

    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    json.dump({"phase": "after_anomaly", "asr": asr_c, "clean_accuracy_retention": clean_c,
               "provenance_only_asr": asr_a, "provenance_only_clean": clean_a,
               "poison_flagged": min(flagged, n_poison), "clean_false_positives": clean_fp,
               "defense": "provenance+anomaly"},
              open(os.path.join(HERE, "results", "attack_after_anomaly.json"), "w"), indent=2)

    print("=" * 52)
    print("  DEFENSE-IN-DEPTH (signed-poison scenario)")
    print(f"    provenance alone:    ASR {asr_a:.0%}")
    print(f"    + anomaly detector:  ASR {asr_c:.0%}   (clean {clean_c:.0%})")
    print("=" * 52)
    print("  Saved -> results/attack_after_anomaly.json")


if __name__ == "__main__":
    main()