"""MemGuard's content anomaly detector (Week 3, upgraded).

Provenance stops UNSIGNED poison. This detector inspects content itself, to catch
poison that arrives through a trusted/signed channel. It scores each document on
three unsupervised, explainable signals and flags it if ANY of them trips — so it
defends against more than one attack style:

  1. internal_repetition   -- trigger-stuffed poison repeats tokens. 1 - unique/total.
  2. max_neighbor_sim       -- duplicated poison clusters as near-identical copies.
                               Cosine similarity to the most-similar OTHER document.
  3. intra_doc_incoherence  -- a PoisonedRAG passage is a relevant sentence with a
                               malicious sentence bolted on, so its own sentences
                               don't cohere. 1 - min pairwise sentence similarity.

Signal 3 needs to embed individual sentences, so `score()` takes an `embed` callable
(the same embedder the store uses). Measured margins on the demo corpus:
  repetition  clean <=0.27 vs poison >=0.95
  neighbor    clean <=0.81 vs poison =1.00   (duplicate-style poison)
  incoherence clean  =0.00 vs poison >=0.58   (PoisonedRAG-style poison)

Method note: an off-the-shelf IsolationForest over raw embeddings was tested and
missed the poison, so these targeted signals are used instead.
"""

import re

import numpy as np

_TOKEN = re.compile(r"[a-z0-9]+")
_SENT = re.compile(r"(?<=[.!?])\s+")


def internal_repetition(text: str) -> float:
    toks = _TOKEN.findall(text.lower())
    if not toks:
        return 0.0
    return 1.0 - len(set(toks)) / len(toks)


def _sentences(text):
    return [s for s in _SENT.split(text.strip()) if s]


def _normalize_rows(E):
    E = np.asarray(E, dtype=float)
    n = np.linalg.norm(E, axis=1, keepdims=True)
    n[n == 0] = 1.0
    return E / n


class AnomalyDetector:
    def __init__(self, rep_threshold=0.5, sim_threshold=0.9, incoh_threshold=0.4):
        self.rep_threshold = rep_threshold
        self.sim_threshold = sim_threshold
        self.incoh_threshold = incoh_threshold

    def _neighbor_sim(self, embeddings):
        E = _normalize_rows(embeddings)
        S = E @ E.T
        np.fill_diagonal(S, -1.0)
        return S.max(axis=1)

    def _incoherence(self, text, embed):
        if embed is None:
            return 0.0
        ss = _sentences(text)
        if len(ss) < 2:
            return 0.0
        E = _normalize_rows(embed(ss))
        S = E @ E.T
        return float(1.0 - S[np.triu_indices(len(ss), 1)].min())

    def score(self, texts, embeddings, embed=None):
        """One record per doc: all three signals, a 0-1 risk, and a flag."""
        sims = self._neighbor_sim(embeddings)
        out = []
        for text, sim in zip(texts, sims):
            rep = internal_repetition(text)
            incoh = self._incoherence(text, embed)
            flagged = (rep >= self.rep_threshold or sim >= self.sim_threshold
                       or incoh >= self.incoh_threshold)
            risk = min(1.0, max(rep / self.rep_threshold,
                                sim / self.sim_threshold,
                                incoh / self.incoh_threshold) / 2)
            out.append({"internal_repetition": round(rep, 3),
                        "max_neighbor_sim": round(float(sim), 3),
                        "intra_doc_incoherence": round(incoh, 3),
                        "risk": round(risk, 3), "flagged": bool(flagged)})
        return out