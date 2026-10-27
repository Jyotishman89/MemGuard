import json
import os
 
import chromadb
 
import llm
from embeddings import get_embedding_function
 
HERE = os.path.dirname(os.path.abspath(__file__))
COLLECTION = "memguard_kb"
PERSIST_DIR = os.path.join(HERE, ".chroma")
 
 
def load_docs(path=None):
    if path is None:
        path = os.path.join(HERE, "knowledge_base.json")
    with open(path) as f:
        return json.load(f)
 
 
class RagAgent:
    def __init__(self, fresh=False):
        self._client = chromadb.PersistentClient(path=PERSIST_DIR)
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
 
    def index(self, docs):
        """Upsert docs. Idempotent — safe to run repeatedly."""
        self._col.upsert(
            ids=[d["id"] for d in docs],
            documents=[d["text"] for d in docs],
            metadatas=[{"source": d.get("source", "?"), "trust": d.get("trust", "?")} for d in docs],
        )
        return self._col.count()
 
    def retrieve(self, query, k=3):
        res = self._col.query(query_texts=[query], n_results=k)
        return [
            {"id": i, "text": t, "distance": dist}
            for i, t, dist in zip(res["ids"][0], res["documents"][0], res["distances"][0])
        ]
 
    def answer(self, query, k=3):
        hits = self.retrieve(query, k=k)
        context = "\n".join(f"- {h['text']}" for h in hits)
        prompt = (
            "Answer the question using ONLY the context below. "
            "If the context does not contain the answer, say you don't know.\n\n"
            f"Context:\n{context}\n\nQuestion: {query}\n\nAnswer:"
        )
        return llm.generate(prompt), hits
 
 