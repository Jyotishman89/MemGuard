"""Day 6: generate the results chart for the README.

Reads the JSON scoreboards in results/ and draws a grouped bar chart:
  - Attack Success Rate (red)  -- lower is better
  - Clean Accuracy      (blue) -- higher is better

Shows a "Before MemGuard" group now. Once Weeks 2-3 write results/attack_after.json,
an "After MemGuard" group appears automatically and the chart becomes the
before/after money chart with no code changes.

    python make_chart.py     ->  results/summary.png
"""

import json
import os

import matplotlib
matplotlib.use("Agg")  # headless / no display needed
import matplotlib.pyplot as plt

from rag import HERE

RESULTS = os.path.join(HERE, "results")
ASSETS = os.path.join(HERE, "assets")   # committed to git; README embeds from here
RED, BLUE = "#c0483b", "#2f6fed"   # validated CVD-safe categorical pair
INK, MUTED, SURFACE = "#1a1a1a", "#6b6b6b", "#fcfcfb"


def load(name):
    path = os.path.join(RESULTS, name)
    return json.load(open(path)) if os.path.exists(path) else None


def main():
    before = load("attack_before.json")
    after = load("attack_after.json")
    if before is None:
        raise SystemExit("Run measure_attack.py first to create results/attack_before.json")

    # Always show two columns so the before/after story reads at a glance.
    # If "after" isn't measured yet, its slot is a faint "pending" placeholder.
    w = 0.32
    fig, ax = plt.subplots(figsize=(7, 4.6), dpi=150)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)

    def draw_group(pos, data):
        a = data["asr"] * 100
        c = data["clean_accuracy_retention"] * 100
        ba = ax.bar(pos - w / 2, a, w, color=RED)
        bc = ax.bar(pos + w / 2, c, w, color=BLUE)
        for bar in list(ba) + list(bc):
            ax.annotate(f"{bar.get_height():.0f}%",
                        (bar.get_x() + bar.get_width() / 2, bar.get_height()),
                        textcoords="offset points", xytext=(0, 4),
                        ha="center", fontsize=10, color=INK)

    draw_group(0, before)
    if after is not None:
        draw_group(1, after)
    else:
        # ghost placeholder bars for the not-yet-measured "after"
        ax.bar(1 - w / 2, 100, w, facecolor="none", edgecolor="#d6d6d6", hatch="//", linewidth=1)
        ax.bar(1 + w / 2, 100, w, facecolor="none", edgecolor="#d6d6d6", hatch="//", linewidth=1)
        ax.text(1, 50, "pending\n(Week 2-3)", ha="center", va="center",
                fontsize=9, color=MUTED, style="italic")

    # legend proxies (color = identity)
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=RED, label="Attack Success Rate (lower = better)"),
                       Patch(color=BLUE, label="Clean Accuracy (higher = better)")],
              loc="lower center", bbox_to_anchor=(0.5, -0.30), ncol=1, frameon=False, fontsize=9)

    ax.set_ylim(0, 108)
    ax.set_xlim(-0.6, 1.6)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["Before MemGuard", "After MemGuard"], fontsize=11, color=INK)
    ax.set_ylabel("%", color=MUTED)
    ax.set_title("MemGuard — poisoning attack, before vs after defense", color=INK, fontsize=12)
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color(MUTED)
    ax.tick_params(colors=MUTED)
    ax.yaxis.grid(True, color="#e6e6e6", linewidth=0.8)
    ax.set_axisbelow(True)

    fig.subplots_adjust(bottom=0.22)
    fig.tight_layout()
    os.makedirs(ASSETS, exist_ok=True)
    out = os.path.join(ASSETS, "summary.png")
    fig.savefig(out, facecolor=SURFACE, bbox_inches="tight")
    print(f"Saved -> {out}")


if __name__ == "__main__":
    main()