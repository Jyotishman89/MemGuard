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

    def write(self, text, doc_id, source="owner", trust="trusted"):
        self._col.upsert(
            ids=[doc_id], documents=[text],
            metadatas=[{"source": source, "trust": trust, "sig": provenance.sign(text)}],
        )

    def inject_raw(self, text, doc_id, source="unknown", trust="untrusted", sig=""):
        self._col.upsert(
            ids=[doc_id], documents=[text],
            metadatas=[{"source": source, "trust": trust, "sig": sig}],
        )

    def count(self):
        return self._col.count()

    def scan(self, detector=None):
        """Score every document for anomaly and quarantine the flagged ones.
        Models a periodic integrity sweep over the whole memory store."""
        detector = detector or AnomalyDetector()
        got = self._col.get(include=["documents", "metadatas", "embeddings"])
        ids, texts, metas = got["ids"], got["documents"], got["metadatas"]
        scores = detector.score(texts, got["embeddings"], embed=get_embedding_function())
        flagged = 0
        for i, text, meta, sc in zip(ids, texts, metas, scores):
            meta = dict(meta or {})
            meta["risk"] = sc["risk"]
            meta["quarantined"] = sc["flagged"]
            flagged += sc["flagged"]
            self._col.upsert(ids=[i], documents=[text], metadatas=[meta])
        return flagged

    def retrieve(self, query, k=3):
        res = self._col.query(query_texts=[query], n_results=min(k * 5, max(self._col.count(), 1)))
        docs = zip(res["ids"][0], res["documents"][0], res["metadatas"][0], res["distances"][0])
        kept = []
        for i, text, meta, dist in docs:
            if meta.get("quarantined"):
                continue  
            if self.policy in ("provenance", "both") and not provenance.verify(text, meta.get("sig", "")):
                continue  
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