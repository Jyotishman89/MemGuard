"""Week 3 chart: defense-in-depth against SIGNED poison.

Three scenarios, showing why one layer isn't enough:
  No defense           -> attack works
  Provenance only      -> still works (poison is signed)
  Provenance + Anomaly -> stopped

    python make_chart_depth.py  ->  assets/defense_in_depth.png
"""

import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

from rag import HERE

RESULTS, ASSETS = os.path.join(HERE, "results"), os.path.join(HERE, "assets")
RED, BLUE = "#c0483b", "#2f6fed"
INK, MUTED, SURFACE = "#1a1a1a", "#6b6b6b", "#fcfcfb"


def main():
    path = os.path.join(RESULTS, "attack_after_anomaly.json")
    if not os.path.exists(path):
        raise SystemExit("Run `python measure_defense3.py` first — it creates "
                         "results/attack_after_anomaly.json, which this chart reads.")
    depth = json.load(open(path))
    # All bars come from MEASURED data (no hardcoding). Against SIGNED poison,
    # "no defense" and "provenance only" are the same run, so we show the two
    # meaningful states: provenance alone vs. provenance + the ML detector.
    prov_clean = depth.get("provenance_only_clean", depth["clean_accuracy_retention"])
    scenarios = [
        ("Provenance only\n(signed poison)", round(depth["provenance_only_asr"] * 100), round(prov_clean * 100)),
        ("Provenance +\nAnomaly (ML)", round(depth["asr"] * 100), round(depth["clean_accuracy_retention"] * 100)),
    ]
    labels = [s[0] for s in scenarios]
    asr = [s[1] for s in scenarios]
    clean = [s[2] for s in scenarios]

    x = range(len(scenarios))
    w = 0.34
    fig, ax = plt.subplots(figsize=(7.6, 4.6), dpi=150)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)

    b1 = ax.bar([i - w / 2 for i in x], asr, w, color=RED)
    b2 = ax.bar([i + w / 2 for i in x], clean, w, color=BLUE)
    for bars in (b1, b2):
        for bar in bars:
            ax.annotate(f"{bar.get_height():.0f}%",
                        (bar.get_x() + bar.get_width() / 2, bar.get_height()),
                        textcoords="offset points", xytext=(0, 4),
                        ha="center", fontsize=10, color=INK)

    ax.set_ylim(0, 108)
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontsize=10.5, color=INK)
    ax.set_ylabel("%", color=MUTED)
    ax.set_title("MemGuard defense-in-depth — signed poison (the hard case)", color=INK, fontsize=12)
    ax.legend(handles=[Patch(color=RED, label="Attack Success Rate (lower = better)"),
                       Patch(color=BLUE, label="Clean Accuracy (higher = better)")],
              loc="lower center", bbox_to_anchor=(0.5, -0.30), ncol=1, frameon=False, fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color(MUTED)
    ax.tick_params(colors=MUTED)
    ax.yaxis.grid(True, color="#e6e6e6", linewidth=0.8)
    ax.set_axisbelow(True)

    fig.subplots_adjust(bottom=0.24)
    fig.tight_layout()
    os.makedirs(ASSETS, exist_ok=True)
    out = os.path.join(ASSETS, "defense_in_depth.png")
    fig.savefig(out, facecolor=SURFACE, bbox_inches="tight")
    print(f"Saved -> {out}")


if __name__ == "__main__":
    main()