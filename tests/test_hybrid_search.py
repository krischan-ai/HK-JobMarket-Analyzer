from __future__ import annotations

from src.knowledge_base.hybrid_search import HybridJobSearch, HybridSearchOptions
from src.knowledge_base.reranker import RerankResult


class FakeDB:
    is_connected = True

    def search_text(self, query, limit=50):
        return [
            {
                "job_id": "job-1",
                "title": "Python Engineer",
                "company": "Acme",
                "score": 4.0,
                "kb_document_text": "Python backend engineer with FastAPI",
            }
        ]


class DisconnectedDB:
    is_connected = False


class FakeVectorStore:
    def search(self, query, top_k=10):
        return [
            {
                "job_id": "job-2",
                "title": "ML Engineer",
                "company": "Beta",
                "vector_score": 0.9,
                "document": "Machine learning engineer with PyTorch",
                "snippet": "Machine learning engineer",
            },
            {
                "job_id": "job-1",
                "title": "Python Engineer",
                "company": "Acme",
                "vector_score": 0.5,
                "document": "Python backend engineer with FastAPI",
                "snippet": "Python backend engineer",
            },
        ]


class FakeReranker:
    def rerank(self, query, documents, top_n=None):
        return [RerankResult(index=1, relevance_score=0.99), RerankResult(index=0, relevance_score=0.2)]


class EmptyReranker:
    def rerank(self, query, documents, top_n=None):
        return []


def test_hybrid_search_merges_and_weights_without_rerank():
    searcher = HybridJobSearch(db=FakeDB(), vector_store=FakeVectorStore(), reranker=EmptyReranker())
    result = searcher.search("python", HybridSearchOptions(top_k=2, use_rerank=False))

    assert result["rerank_used"] is False
    assert len(result["results"]) == 2
    assert {item["job_id"] for item in result["results"]} == {"job-1", "job-2"}
    assert result["results"][0]["hybrid_score"] >= result["results"][1]["hybrid_score"]


def test_hybrid_search_uses_rerank_when_available():
    searcher = HybridJobSearch(db=FakeDB(), vector_store=FakeVectorStore(), reranker=FakeReranker())
    result = searcher.search("python", HybridSearchOptions(top_k=2, use_rerank=True))

    assert result["rerank_used"] is True
    assert result["results"][0]["rerank_score"] == 0.99


def test_keyword_search_csv_fallback(monkeypatch):
    import pandas as pd

    monkeypatch.setattr(
        "api.dependencies.load_jobs_df",
        lambda: pd.DataFrame([
            {
                "job_id": "csv-1",
                "title": "Data Engineer",
                "company": "CSV Co",
                "kb_document_text": "Airflow data pipeline",
            }
        ]),
    )
    searcher = HybridJobSearch(db=DisconnectedDB(), vector_store=FakeVectorStore(), reranker=EmptyReranker())
    results = searcher._keyword_search("airflow pipeline", 5)

    assert results[0]["job_id"] == "csv-1"
