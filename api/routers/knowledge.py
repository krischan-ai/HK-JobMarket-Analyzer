from fastapi import APIRouter, Query
from api.dependencies import load_jobs_df, load_skills_df

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


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
