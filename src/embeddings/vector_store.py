from __future__ import annotations

import hashlib
import json
from typing import Optional

import chromadb
from chromadb.config import Settings as ChromaSettings

from config.settings import settings
from src.llm_config_manager import LLMConfigManager
from src.logger import get_logger


class VectorStore:
    """ChromaDB 向量存储 — 语义搜索与索引管理"""

    _COLLECTION_NAME = "job_descriptions"

    def __init__(self, persist_path: Optional[str] = None, config_manager: Optional[LLMConfigManager] = None):
        self.persist_path = persist_path or (settings.data_dir / "chromadb").as_posix()
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
        """调用 OpenAI/DeepSeek 兼容 Embedding API"""
        cfg = self.config.load()
        api_key = cfg.get("api_key") or settings.llm_api_key
        base_url = cfg.get("base_url") or settings.llm_base_url
        if not api_key:
            raise RuntimeError("No API key configured for embeddings")

        import openai
        client = openai.OpenAI(api_key=api_key, base_url=base_url, timeout=30)
        resp = client.embeddings.create(
            model="text-embedding-ada-002",
            input=texts,
        )
        return [d.embedding for d in resp.data]

    def _make_doc_id(self, job_id: str) -> str:
        return hashlib.md5(job_id.encode()).hexdigest()[:16]

    def add_documents(self, documents: list[dict], text_field: str = "jd_text"):
        """批量添加文档到向量索引"""
        if not self.available:
            return

        ids = []
        texts = []
        metadatas = []
        embeddings = []

        for doc in documents:
            text = doc.get(text_field, "")
            if not text or len(text.strip()) < 20:
                continue

            job_id = doc.get("job_id", hashlib.md5(text.encode()).hexdigest()[:12])
            doc_id = self._make_doc_id(job_id)
            ids.append(doc_id)

            # 截断长文本
            texts.append(text[:8000])

            metadatas.append({
                "job_id": job_id,
                "title": str(doc.get("title", ""))[:200],
                "company": str(doc.get("company", ""))[:100],
                "location": str(doc.get("location", ""))[:100],
                "source": str(doc.get("source", ""))[:50],
            })

        if not texts:
            return

        try:
            embeddings = self._embed(texts)
            self._collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
            )
            self.logger.info("Added %d documents to vector store", len(ids))
        except Exception as e:
            self.logger.warning("Failed to add embeddings: %s", e)

    def search(self, query: str, top_k: int = 10) -> list[dict]:
        """语义搜索 — 返回最相关的文档"""
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
                        "score": round(1 - results["distances"][0][i], 4) if results["distances"] else None,
                        "snippet": (results["documents"][0][i][:300] if results["documents"] else ""),
                    })
            return items
        except Exception as e:
            self.logger.warning("Semantic search failed: %s", e)
            return []

    def rebuild_from_csv(self, csv_path: str):
        """从 CSV 全量重建向量索引"""
        import pandas as pd
        df = pd.read_csv(csv_path, encoding="utf-8-sig")
        docs = df.to_dict(orient="records")

        if self.available:
            try:
                self._client.delete_collection(self._COLLECTION_NAME)
                self._collection = self._client.create_collection(
                    name=self._COLLECTION_NAME,
                    metadata={"hnsw:space": "cosine"},
                )
            except Exception:
                pass

        self.add_documents(docs)
        self.logger.info("Vector store rebuilt: %d documents", self.count())

    def clear(self):
        """清空向量索引"""
        if self.available:
            try:
                self._client.delete_collection(self._COLLECTION_NAME)
                self._collection = self._client.create_collection(
                    name=self._COLLECTION_NAME,
                    metadata={"hnsw:space": "cosine"},
                )
            except Exception:
                pass
