from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Query

from api.dependencies import load_jobs_df, load_skills_df
from src.embeddings.vector_store import VectorStore

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])

_vector_store: VectorStore | None = None


def _get_vector_store() -> VectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store


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


@router.get("/vector-status")
def vector_status():
    """向量索引狀態"""
    store = _get_vector_store()
    return {
        "available": store.available,
        "doc_count": store.count(),
        "persist_path": store.persist_path,
    }


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
