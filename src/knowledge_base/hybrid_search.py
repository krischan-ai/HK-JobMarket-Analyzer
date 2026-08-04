from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from config.settings import settings
from src.embeddings.vector_store import VectorStore
from src.knowledge_base.reranker import SiliconFlowReranker
from src.logger import get_logger
from src.storage.mongodb import JobDatabase


@dataclass
class HybridSearchOptions:
    top_k: int = 10
    candidate_k: int = 50
    semantic_weight: float = settings.hybrid_semantic_weight
    keyword_weight: float = settings.hybrid_keyword_weight
    use_rerank: bool = True


class HybridJobSearch:
    """Hybrid retrieval over MongoDB text search and ChromaDB semantic search."""

    def __init__(
        self,
        db: Optional[JobDatabase] = None,
        vector_store: Optional[VectorStore] = None,
        reranker: Optional[SiliconFlowReranker] = None,
    ):
        self.db = db or JobDatabase()
        self.vector_store = vector_store or VectorStore()
        self.reranker = reranker or SiliconFlowReranker()
        self.logger = get_logger(self.__class__.__name__)

    def search(self, query: str, options: Optional[HybridSearchOptions] = None) -> dict:
        options = options or HybridSearchOptions()
        if not query:
            return {"query": query, "results": [], "rerank_used": False}

        keyword_results = self._keyword_search(query, options.candidate_k)
        vector_results = self.vector_store.search(query, top_k=options.candidate_k)
        merged = self._merge(keyword_results, vector_results, options)
        rerank_used = False

        if options.use_rerank and merged:
            docs = [item.get("document") or item.get("snippet") or "" for item in merged]
            reranked = self.reranker.rerank(query, docs, top_n=min(options.top_k, len(docs)))
            if reranked:
                by_index = []
                for result in reranked:
                    if 0 <= result.index < len(merged):
                        item = dict(merged[result.index])
                        item["rerank_score"] = result.relevance_score
                        item["score"] = result.relevance_score
                        by_index.append(item)
                merged = by_index
                rerank_used = True

        return {
            "query": query,
            "results": merged[:options.top_k],
            "rerank_used": rerank_used,
            "semantic_weight": options.semantic_weight,
            "keyword_weight": options.keyword_weight,
        }

    def _keyword_search(self, query: str, limit: int) -> list[dict]:
        if self.db.is_connected:
            records = self.db.search_text(query, limit=limit)
            return self._keyword_records_to_results(records)
        return self._keyword_search_csv(query, limit)

    def _keyword_records_to_results(self, records: list[dict]) -> list[dict]:
        results = []
        for record in records:
            text = record.get("kb_document_text") or record.get("jd_text") or record.get("jd_raw") or ""
            results.append({
                "job_id": record.get("job_id"),
                "title": record.get("title"),
                "company": record.get("company"),
                "location": record.get("location"),
                "source": record.get("source"),
                "url": record.get("url"),
                "keyword_score": float(record.get("score") or 0.0),
                "snippet": text[:300],
                "document": text,
            })
        return results

    def _keyword_search_csv(self, query: str, limit: int) -> list[dict]:
        try:
            from api.dependencies import load_jobs_df

            df = load_jobs_df()
            if df.empty:
                return []
            terms = [term.lower() for term in query.split() if term.strip()]
            if not terms:
                return []
            results = []
            for _, row in df.iterrows():
                text = " ".join(str(row.get(field, "")) for field in ("title", "company", "kb_document_text", "jd_text"))
                lowered = text.lower()
                hits = sum(1 for term in terms if term in lowered)
                if hits:
                    results.append({
                        "job_id": row.get("job_id"),
                        "title": row.get("title"),
                        "company": row.get("company"),
                        "location": row.get("location"),
                        "source": row.get("source"),
                        "url": row.get("url"),
                        "keyword_score": float(hits),
                        "snippet": text[:300],
                        "document": str(row.get("kb_document_text") or row.get("jd_text") or ""),
                    })
            return sorted(results, key=lambda item: item["keyword_score"], reverse=True)[:limit]
        except Exception as e:
            self.logger.warning("CSV keyword search failed: %s", e)
            return []

    def _merge(self, keyword_results: list[dict], vector_results: list[dict], options: HybridSearchOptions) -> list[dict]:
        items: dict[str, dict] = {}
        max_keyword = max((item.get("keyword_score") or 0 for item in keyword_results), default=0.0) or 1.0

        for item in keyword_results:
            job_id = str(item.get("job_id") or "")
            if not job_id:
                continue
            normalized = (item.get("keyword_score") or 0.0) / max_keyword
            merged = dict(item)
            merged["keyword_score"] = round(normalized, 4)
            merged["vector_score"] = 0.0
            items[job_id] = merged

        for item in vector_results:
            job_id = str(item.get("job_id") or "")
            if not job_id:
                continue
            existing = items.get(job_id, {})
            merged = {**item, **existing}
            merged["job_id"] = job_id
            merged["keyword_score"] = existing.get("keyword_score", 0.0)
            merged["vector_score"] = float(item.get("vector_score") or item.get("score") or 0.0)
            merged["document"] = item.get("document") or existing.get("document") or ""
            merged["snippet"] = item.get("snippet") or existing.get("snippet") or ""
            items[job_id] = merged

        weighted = []
        for item in items.values():
            score = (
                options.semantic_weight * float(item.get("vector_score") or 0.0)
                + options.keyword_weight * float(item.get("keyword_score") or 0.0)
            )
            item["hybrid_score"] = round(score, 4)
            item["score"] = item["hybrid_score"]
            weighted.append(item)

        return sorted(weighted, key=lambda item: item.get("hybrid_score", 0.0), reverse=True)
