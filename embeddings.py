"""Embedding backends for Chroma.

By default Chroma downloads all-MiniLM-L6-v2 (ONNX) the first time you index —
best quality, works on any normal machine. On a locked-down box with no model
download (offline, restricted network), set MEMGUARD_EMBED=hashing to use a
dependency-free local embedder instead, so the pipeline still runs.

    MEMGUARD_EMBED=default   (default) Chroma's built-in MiniLM
    MEMGUARD_EMBED=hashing   offline bag-of-words hashing vectors
"""

import hashlib
import os
import re

_TOKEN = re.compile(r"[a-z0-9]+")


class HashingEmbeddingFunction:
    """Deterministic hashed bag-of-words -> L2-normalized vector. No downloads."""

    def __init__(self, dim=512):
        self.dim = dim

    def name(self):  # Chroma >=1.x asks embedding functions to identify themselves
        return f"hashing-{self.dim}"

    def _embed_one(self, text):
        vec = [0.0] * self.dim
        for tok in _TOKEN.findall(text.lower()):
            h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
            idx = h % self.dim
            sign = 1.0 if (h >> 8) & 1 else -1.0
            vec[idx] += sign
        norm = sum(v * v for v in vec) ** 0.5 or 1.0
        return [v / norm for v in vec]

    def __call__(self, input):
        return [self._embed_one(t) for t in input]

    # Chroma >=1.5 calls these two explicitly at index / query time.
    def embed_documents(self, input):
        return self.__call__(input)

    def embed_query(self, input):
        return self.__call__(input)


def get_embedding_function():
    """Return a concrete embedding function used everywhere (store + detector).

    default -> Chroma's built-in MiniLM (ONNX, no torch); hashing -> offline.
    Returning a concrete object (never None) lets the anomaly detector reuse the
    SAME embedder to embed individual sentences.
    """
    if os.environ.get("MEMGUARD_EMBED", "default").lower() == "hashing":
        return HashingEmbeddingFunction()
    from chromadb.utils import embedding_functions
    return embedding_functions.DefaultEmbeddingFunction()