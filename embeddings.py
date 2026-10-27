import hashlib
import os
import re

_TOKEN = re.compile(r"[a-z0-9]+")


class HashingEmbeddingFunction:
    def __init__(self, dim=512):
        self.dim = dim

    def name(self):  
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

    def embed_documents(self, input):
        return self.__call__(input)

    def embed_query(self, input):
        return self.__call__(input)


def get_embedding_function():
    if os.environ.get("MEMGUARD_EMBED", "default").lower() == "hashing":
        return HashingEmbeddingFunction()
    from chromadb.utils import embedding_functions
    return embedding_functions.DefaultEmbeddingFunction()