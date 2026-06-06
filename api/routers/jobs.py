from fastapi import APIRouter, Query
from api.dependencies import load_jobs_df, load_skills_df
from api.routers.stats import location_to_zh
import pandas as pd
import math
from pathlib import Path
from datetime import datetime

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("")
def list_jobs(
    keyword: str = Query(default=None),
    location: str = Query(default=None),
    source: str = Query(default=None),
    salary_min: float = Query(default=None),
    salary_max: float = Query(default=None),
    page: int = Query(default=1),
    page_size: int = Query(default=20),
):
    df = load_jobs_df()
    if df.empty:
        return {"total": 0, "page": page, "page_size": page_size, "items": []}

    if keyword:
        mask = df["title"].str.contains(keyword, case=False, na=False)
        if "jd_text" in df.columns:
            mask |= df["jd_text"].str.contains(keyword, case=False, na=False)
        df = df[mask]
    if location:
        df = df[df["location"].str.contains(location, case=False, na=False)]
    if source:
        df = df[df["source"] == source]
    if salary_min is not None and "salary_min" in df.columns:
        df = df[df["salary_min"] >= salary_min]
    if salary_max is not None and "salary_max" in df.columns:
        df = df[df["salary_max"] <= salary_max]

    total = len(df)
    start = (page - 1) * page_size
    df_page = df.iloc[start : start + page_size]

    # 构建来源 → 时间的映射（按来源名匹配 raw 文件的修改时间）
    raw_dir = Path(__file__).resolve().parent.parent.parent / "data" / "raw"
    source_times: dict[str, str] = {}
    if raw_dir.exists():
        for f in raw_dir.glob("*_raw.json"):
            src_name = f.stem.replace("_raw", "").lower()  # "jobsdb_raw" → "jobsdb"
            src_time = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            source_times[src_name] = src_time

    items = []
    for _, row in df_page.iterrows():
        skills = None
        if "skills" in df.columns and pd.notna(row.get("skills")):
            skills = row["skills"]
        src = str(row.get("source", "")).lower().strip()
        import_time = source_times.get(src, None)
        items.append({
            "job_id": str(row.get("job_id", "")),
            "title": str(row.get("title", "")),
            "company": str(row.get("company", "")),
            "location": location_to_zh(str(row.get("location", ""))),
            "salary_min": float(row.get("salary_min", 0)) if pd.notna(row.get("salary_min")) else None,
            "salary_max": float(row.get("salary_max", 0)) if pd.notna(row.get("salary_max")) else None,
            "source": str(row.get("source", "")),
            "skills": skills,
            "import_time": import_time,
        })

    return {"total": total, "page": page, "page_size": page_size, "items": items}


@router.get("/sources")
def list_sources():
    df = load_jobs_df()
    if df.empty or "source" not in df.columns:
        return []
    return sorted(df["source"].dropna().unique().tolist())


@router.get("/locations")
def list_locations():
    df = load_jobs_df()
    if df.empty or "location" not in df.columns:
        return []
    locs = df["location"].dropna().value_counts().reset_index()
    locs.columns = ["name", "count"]
    locs["name"] = locs["name"].apply(location_to_zh)
    return locs.to_dict(orient="records")
