from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Query
from pydantic import BaseModel

from api.dependencies import load_jobs_df, load_skills_df
from config.settings import settings
from src.embeddings.vector_store import VectorStore
from src.knowledge_base.hybrid_search import HybridJobSearch, HybridSearchOptions
from src.storage.mongodb import JobDatabase

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])

_vector_store: VectorStore | None = None
_hybrid_search: HybridJobSearch | None = None


class JobsDBRebuildRequest(BaseModel):
    raw_path: str = r"E:\文档\Project\HK-Job-Crawler\data\raw\jobsdb_raw.json"
    confirm_clear: bool = False
    review_insurance: bool = False


def _get_vector_store() -> VectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store


def _get_hybrid_search() -> HybridJobSearch:
    global _hybrid_search
    if _hybrid_search is None:
        _hybrid_search = HybridJobSearch(vector_store=_get_vector_store())
    return _hybrid_search


@router.get("/skill-frequency")
def skill_frequency(top_n: int = Query(default=30)):
    skill_df = load_skills_df()
    if skill_df.empty:
        return []
    freq = skill_df["skill"].value_counts().head(top_n).reset_index()
    freq.columns = ["skill", "count"]
    return freq.to_dict(orient="records")


@router.get("/trends")
def tech_trends(skill: str = Query(default=None)):
    df = load_jobs_df()
    if df.empty or "skills" not in df.columns:
        return []

    import pandas as pd
    skill_list = []
    for _, row in df.iterrows():
        s = row.get("skills")
        if isinstance(s, dict):
            flat = []
            for v in s.values():
                if isinstance(v, list):
                    flat.extend(v)
            skill_list.append({"job_id": row.get("job_id"), "title": row.get("title"), "skills": flat})

    trends_df = pd.DataFrame(skill_list)
    if trends_df.empty:
        return []

    trends_df = trends_df.explode("skills")
    freq = trends_df["skills"].value_counts().head(30).reset_index()
    freq.columns = ["skill", "count"]
    return freq.to_dict(orient="records")


@router.get("/companies")
def company_stats():
    df = load_jobs_df()
    if df.empty or "company" not in df.columns:
        return []
    freq = df["company"].value_counts().head(20).reset_index()
    freq.columns = ["company", "count"]
    return freq.to_dict(orient="records")


@router.get("/search")
def search(kw: str = Query(default=None)):
    df = load_jobs_df()
    if df.empty:
        return []

    mask = df["title"].str.contains(kw, case=False, na=False)
    if "jd_text" in df.columns:
        mask |= df["jd_text"].str.contains(kw, case=False, na=False)
    if "company" in df.columns:
        mask |= df["company"].str.contains(kw, case=False, na=False)
    result = df[mask].head(20)

    items = []
    for _, row in result.iterrows():
        items.append({"job_id": str(row.get("job_id")), "title": str(row.get("title")), "company": str(row.get("company")), "location": str(row.get("location"))})
    return items


@router.get("/versions")
def versions():
    return [
        {"version": "v1.0", "records": "15", "date": "2026-06-01", "description": "初始 JobsDB 数据"},
    ]


# ── 向量語義搜索 ──

@router.get("/semantic-search")
def semantic_search(q: str = Query(..., description="搜索查詢文本")):
    """語義搜索 — 使用 ChromaDB 向量檢索相關崗位"""
    store = _get_vector_store()
    if not store.available:
        return {"available": False, "results": [], "message": "ChromaDB 未初始化或不可用"}
    results = store.search(q, top_k=15)
    return {"available": True, "results": results, "query": q}


@router.get("/hybrid-search")
def hybrid_search(
    q: str = Query(..., description="Search query"),
    top_k: int = Query(default=10, ge=1, le=100),
    candidate_k: int = Query(default=50, ge=1, le=200),
    semantic_weight: float = Query(default=settings.hybrid_semantic_weight, ge=0, le=1),
    keyword_weight: float = Query(default=settings.hybrid_keyword_weight, ge=0, le=1),
    use_rerank: bool = Query(default=True),
):
    searcher = _get_hybrid_search()
    options = HybridSearchOptions(
        top_k=top_k,
        candidate_k=candidate_k,
        semantic_weight=semantic_weight,
        keyword_weight=keyword_weight,
        use_rerank=use_rerank,
    )
    return searcher.search(q, options)


@router.get("/vector-status")
def vector_status():
    """向量索引狀態"""
    store = _get_vector_store()
    return {
        "available": store.available,
        "doc_count": store.count(),
        "persist_path": store.persist_path,
        "embedding_model": settings.embedding_model,
        "rerank_model": settings.rerank_model,
    }


@router.get("/index-status")
def index_status():
    store = _get_vector_store()
    db = JobDatabase()
    return {
        "mongo_connected": db.is_connected,
        "mongo_count": db.count() if db.is_connected else 0,
        "vector_available": store.available,
        "vector_count": store.count(),
        "csv_records": len(load_jobs_df()),
        "embedding_model": settings.embedding_model,
        "rerank_model": settings.rerank_model,
        "hybrid_semantic_weight": settings.hybrid_semantic_weight,
        "hybrid_keyword_weight": settings.hybrid_keyword_weight,
    }


@router.post("/rebuild-jobsdb")
def rebuild_jobsdb(req: JobsDBRebuildRequest):
    from scripts.rebuild_jobsdb_knowledge_base import rebuild

    if not req.confirm_clear:
        return {"success": False, "message": "confirm_clear=true is required"}
    try:
        result = rebuild(
            raw_path=Path(req.raw_path),
            csv_path=Path(__file__).resolve().parent.parent.parent / "data" / "cleaned" / "jobs.csv",
            confirm_clear=req.confirm_clear,
            review_insurance=req.review_insurance,
        )
        global _hybrid_search
        _hybrid_search = None
        return {"success": True, **result}
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.post("/vector-rebuild")
def vector_rebuild():
    """從 CSV 全量重建向量索引"""
    store = _get_vector_store()
    csv_path = Path(__file__).resolve().parent.parent.parent / "data" / "cleaned" / "jobs.csv"
    if not csv_path.exists():
        return {"success": False, "message": f"CSV not found: {csv_path}"}
    try:
        store.rebuild_from_csv(str(csv_path))
        return {"success": True, "doc_count": store.count()}
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.delete("/vector-clear")
def vector_clear():
    """清空向量索引"""
    store = _get_vector_store()
    store.clear()
    return {"success": True, "doc_count": store.count()}
