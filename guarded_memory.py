"""GuardedMemory — MemGuard's public library API.

A drop-in wrapper around a vector store that enforces provenance at retrieval time.
Two ways content enters the store:

    mem.write(text)          # OWNER path: content is signed and trusted
    mem.inject_raw(text, …)  # ATTACKER path: no valid signature (simulates poisoning)

and one way it leaves:

    mem.answer(question)     # retrieves, but drops anything that fails provenance

The `policy` controls the gate:
    "provenance" (default) — only docs with a valid signature reach the answer
    "off"                  — no filtering (reproduces the undefended baseline)

Week 3 will add an "anomaly" policy (ML) on top of this, for content that must be
accepted without a signature.
"""

import chromadb

import llm
import provenance
from embeddings import get_embedding_function
from detector import AnomalyDetector

COLLECTION = "memguard_guarded"
PERSIST_DIR = ".chroma_guarded"


class GuardedMemory:
    def __init__(self, fresh=False, policy="provenance", persist_dir=PERSIST_DIR):
        self.policy = policy
        self._client = chromadb.PersistentClient(path=persist_dir)
        if fresh:
            try:
                self._client.delete_collection(COLLECTION)
            except Exception:
                pass
        embed_fn = get_embedding_function()
        kwargs = {"name": COLLECTION}
        if embed_fn is not None:
            kwargs["embedding_function"] = embed_fn
        self._col = self._client.get_or_create_collection(**kwargs)

    # ---- writing ----
    def write(self, text, doc_id, source="owner", trust="trusted"):
        """Owner path: sign the content so it can later be verified."""
        self._col.upsert(
            ids=[doc_id], documents=[text],
            metadatas=[{"source": source, "trust": trust, "sig": provenance.sign(text)}],
        )

    def inject_raw(self, text, doc_id, source="unknown", trust="untrusted", sig=""):
        """Attacker path: content enters WITHOUT a valid signature."""
        self._col.upsert(
            ids=[doc_id], documents=[text],
            metadatas=[{"source": source, "trust": trust, "sig": sig}],
        )

    def count(self):
        return self._col.count()

    # ---- Week 3: content anomaly scan (quarantines poison that slipped past provenance) ----
    def scan(self, detector=None):
        """Score every document for anomaly and quarantine the flagged ones.
        Models a periodic integrity sweep over the whole memory store."""
        detector = detector or AnomalyDetector()
        got = self._col.get(include=["documents", "metadatas", "embeddings"])
        ids, texts, metas = got["ids"], got["documents"], got["metadatas"]
        # Pass the same embedder so the detector can embed sentences (incoherence signal).
        scores = detector.score(texts, got["embeddings"], embed=get_embedding_function())
        flagged = 0
        for i, text, meta, sc in zip(ids, texts, metas, scores):
            meta = dict(meta or {})
            meta["risk"] = sc["risk"]
            meta["quarantined"] = sc["flagged"]
            flagged += sc["flagged"]
            self._col.upsert(ids=[i], documents=[text], metadatas=[meta])
        return flagged

    # ---- retrieval with the provenance + anomaly gates ----
    def retrieve(self, query, k=3):
        # Over-fetch, then filter, so we can still return k good docs after dropping poison.
        res = self._col.query(query_texts=[query], n_results=min(k * 5, max(self._col.count(), 1)))
        docs = zip(res["ids"][0], res["documents"][0], res["metadatas"][0], res["distances"][0])
        kept = []
        for i, text, meta, dist in docs:
            if meta.get("quarantined"):
                continue  # flagged by the anomaly scan
            if self.policy in ("provenance", "both") and not provenance.verify(text, meta.get("sig", "")):
                continue  # unsigned / forged
            kept.append({"id": i, "text": text, "distance": dist, "meta": meta})
            if len(kept) >= k:
                break
        return kept

    def answer(self, query, k=3):
        hits = self.retrieve(query, k=k)
        if not hits:
            return "I don't know.", hits
        context = "\n".join(f"- {h['text']}" for h in hits)
        prompt = (
            "Answer the question using ONLY the context below. "
            "If the context does not contain the answer, say you don't know.\n\n"
            f"Context:\n{context}\n\nQuestion: {query}\n\nAnswer:"
        )
        return llm.generate(prompt), hits