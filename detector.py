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