from __future__ import annotations

import hashlib
from typing import Optional

import chromadb
from chromadb.config import Settings as ChromaSettings

from config.settings import settings
from src.llm_config_manager import LLMConfigManager
from src.logger import get_logger


class VectorStore:
    """ChromaDB vector store for semantic job retrieval."""

    _COLLECTION_NAME = "job_descriptions"

    def __init__(self, persist_path: Optional[str] = None, config_manager: Optional[LLMConfigManager] = None):
        self.persist_path = persist_path or settings.vector_db_path.as_posix()
        self.config = config_manager or LLMConfigManager()
        self.logger = get_logger(self.__class__.__name__)
        self._client: Optional[chromadb.PersistentClient] = None
        self._collection: Optional[chromadb.Collection] = None
        self._init_client()

    def _init_client(self):
        try:
            self._client = chromadb.PersistentClient(
                path=self.persist_path,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            self._collection = self._client.get_or_create_collection(
                name=self._COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )
            self.logger.info("ChromaDB connected: %s (docs=%d)", self.persist_path, self._collection.count())
        except Exception as e:
            self.logger.warning("ChromaDB unavailable: %s. Semantic search disabled.", e)
            self._client = None
            self._collection = None

    @property
    def available(self) -> bool:
        return self._client is not None and self._collection is not None

    def count(self) -> int:
        if not self.available:
            return 0
        return self._collection.count()

    def _embed(self, texts: list[str]) -> list[list[float]]:
        """Call an OpenAI-compatible embedding API."""
        cfg = self.config.load()
        api_key = (
            settings.siliconflow_api_key
            or cfg.get("embedding_api_key")
            or cfg.get("api_key")
            or settings.llm_api_key
        )
        base_url = (
            settings.siliconflow_base_url
            or cfg.get("embedding_base_url")
            or cfg.get("base_url")
            or settings.llm_base_url
        )
        model = cfg.get("embedding_model") or settings.embedding_model
        if not api_key:
            raise RuntimeError("No API key configured for embeddings")

        import openai

        client = openai.OpenAI(api_key=api_key, base_url=base_url, timeout=30)
        kwargs = {"model": model, "input": texts}
        if settings.embedding_dimensions:
            kwargs["dimensions"] = settings.embedding_dimensions
        resp = client.embeddings.create(**kwargs)
        return [d.embedding for d in resp.data]

    def _make_doc_id(self, job_id: str) -> str:
        return hashlib.md5(job_id.encode()).hexdigest()[:16]

    def add_documents(self, documents: list[dict], text_field: str = "jd_text"):
        if not self.available:
            return

        ids = []
        texts = []
        metadatas = []

        for doc in documents:
            text = doc.get(text_field, "")
            if not isinstance(text, str) or len(text.strip()) < 20:
                continue

            job_id = str(doc.get("job_id") or hashlib.md5(text.encode()).hexdigest()[:12])
            ids.append(self._make_doc_id(job_id))
            texts.append(text[:8000])
            metadatas.append({
                "job_id": job_id,
                "title": str(doc.get("title", ""))[:200],
                "company": str(doc.get("company", ""))[:100],
                "location": str(doc.get("location", ""))[:100],
                "source": str(doc.get("source", ""))[:50],
                "url": str(doc.get("url", ""))[:500],
            })

        if not texts:
            return

        try:
            batch_size = max(1, int(settings.embedding_batch_size or 32))
            for start in range(0, len(texts), batch_size):
                end = start + batch_size
                embeddings = self._embed(texts[start:end])
                self._collection.upsert(
                    ids=ids[start:end],
                    embeddings=embeddings,
                    documents=texts[start:end],
                    metadatas=metadatas[start:end],
                )
            self.logger.info("Added %d documents to vector store", len(ids))
        except Exception as e:
            self.logger.warning("Failed to add embeddings: %s", e)

    def search(self, query: str, top_k: int = 10) -> list[dict]:
        if not self.available:
            return []

        try:
            embedding = self._embed([query])[0]
            results = self._collection.query(
                query_embeddings=[embedding],
                n_results=top_k,
                include=["metadatas", "documents", "distances"],
            )
            items = []
            if results["ids"] and results["ids"][0]:
                for i in range(len(results["ids"][0])):
                    meta = results["metadatas"][0][i] if results["metadatas"] else {}
                    items.append({
                        "doc_id": results["ids"][0][i],
                        "job_id": meta.get("job_id"),
                        "title": meta.get("title"),
                        "company": meta.get("company"),
                        "location": meta.get("location"),
                        "source": meta.get("source"),
                        "url": meta.get("url"),
                        "vector_score": round(1 - results["distances"][0][i], 4) if results["distances"] else None,
                        "score": round(1 - results["distances"][0][i], 4) if results["distances"] else None,
                        "snippet": (results["documents"][0][i][:300] if results["documents"] else ""),
                        "document": (results["documents"][0][i] if results["documents"] else ""),
                    })
            return items
        except Exception as e:
            self.logger.warning("Semantic search failed: %s", e)
            return []

    def rebuild_from_csv(self, csv_path: str):
        import pandas as pd

        df = pd.read_csv(csv_path, encoding="utf-8-sig")
        docs = df.to_dict(orient="records")
        self.clear()
        text_field = "kb_document_text" if "kb_document_text" in df.columns else "jd_text"
        self.add_documents(docs, text_field=text_field)
        self.logger.info("Vector store rebuilt: %d documents", self.count())

    def clear(self):
        if not self.available:
            return
        try:
            self._client.delete_collection(self._COLLECTION_NAME)
        except Exception:
            pass
        self._collection = self._client.get_or_create_collection(
            name=self._COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
