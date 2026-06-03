from fastapi import APIRouter, Query
from api.dependencies import load_jobs_df, load_skills_df
import json
from pathlib import Path

router = APIRouter(prefix="/api/stats", tags=["stats"])

# 加载地点中文翻译
_ZH_LOCATION_MAP: dict[str, str] | None = None

def _get_zh_location_map() -> dict[str, str]:
    global _ZH_LOCATION_MAP
    if _ZH_LOCATION_MAP is not None:
        return _ZH_LOCATION_MAP
    path = Path(__file__).resolve().parent.parent.parent / "config" / "i18n" / "locations_zh.json"
    if path.exists():
        with open(path, encoding="utf-8") as f:
            _ZH_LOCATION_MAP = json.load(f)
    else:
        _ZH_LOCATION_MAP = {}
    return _ZH_LOCATION_MAP


def location_to_zh(en: str) -> str:
    """将英文地点名称翻译为中文"""
    if not en or not isinstance(en, str):
        return en or "Hong Kong"
    loc = en.strip()
    loc_lower = loc.lower()
    zh_map = _get_zh_location_map()
    if loc_lower in {k.lower(): v for k, v in zh_map.items()}:
        return {k.lower(): v for k, v in zh_map.items()}[loc_lower]
    if loc_lower == "remote":
        return "遠端工作"
    area_map = {
        "kowloon": "九龍",
        "hong kong island": "香港島",
        "new territories": "新界",
        "hong kong": "香港",
    }
    for suffix, area_zh in area_map.items():
        if loc_lower.endswith(f", {suffix}"):
            core = loc[:-(len(suffix) + 2)].strip()
            core_lower = core.lower()
            core_translated = {k.lower(): v for k, v in zh_map.items()}.get(core_lower, core)
            return f"{core_translated}, {area_zh}"
    return loc


@router.get("/overview")
def overview():
    df = load_jobs_df()
    if df.empty:
        return {"total_jobs": 0, "total_companies": 0, "avg_salary": 0,
                "min_salary": 0, "max_salary": 0, "total_skills": 0,
                "source_count": 0, "location_count": 0}

    total = len(df)
    salary_min = df["salary_min"].dropna()
    companies = df["company"].nunique() if "company" in df.columns else 0
    sources = df["source"].nunique() if "source" in df.columns else 0
    locations = df["location"].nunique() if "location" in df.columns else 0

    skill_df = load_skills_df()
    total_skills = len(skill_df) if not skill_df.empty else 0

    return {
        "total_jobs": total,
        "total_companies": int(companies),
        "avg_salary": round(float(salary_min.mean()), 0) if not salary_min.empty else 0,
        "min_salary": round(float(salary_min.min()), 0) if not salary_min.empty else 0,
        "max_salary": round(float(salary_min.max()), 0) if not salary_min.empty else 0,
        "total_skills": total_skills,
        "source_count": int(sources),
        "location_count": int(locations),
    }


@router.get("/top-skills")
def top_skills(top_n: int = Query(default=15)):
    skill_df = load_skills_df()
    if skill_df.empty:
        return []
    freq = skill_df["skill"].value_counts().head(top_n).reset_index()
    freq.columns = ["skill", "count"]
    freq["category"] = freq["skill"].apply(
        lambda s: skill_df[skill_df["skill"] == s]["category"].iloc[0] if len(skill_df[skill_df["skill"] == s]) > 0 else ""
    )
    return freq.to_dict(orient="records")


@router.get("/categories")
def category_distribution():
    skill_df = load_skills_df()
    if skill_df.empty:
        return []
    freq = skill_df["category"].value_counts().reset_index()
    freq.columns = ["category", "count"]
    return freq.to_dict(orient="records")


@router.get("/salary-by-location")
def salary_by_location():
    df = load_jobs_df()
    if df.empty:
        return []
    g = df.dropna(subset=["salary_min"]).groupby("location")["salary_min"].agg(["min", "max", "mean", "count"])
    g = g.reset_index()
    g.columns = ["location", "min", "max", "avg", "count"]
    g["avg"] = g["avg"].round(0)
    g["location"] = g["location"].apply(location_to_zh)
    return g.to_dict(orient="records")


@router.get("/source-distribution")
def source_distribution():
    df = load_jobs_df()
    if df.empty or "source" not in df.columns:
        return []
    freq = df["source"].value_counts().reset_index()
    freq.columns = ["source", "count"]
    return freq.to_dict(orient="records")


@router.get("/location-distribution")
def location_distribution():
    df = load_jobs_df()
    if df.empty or "location" not in df.columns:
        return []
    freq = df["location"].value_counts().head(30).reset_index()
    freq.columns = ["location", "count"]
    freq["location"] = freq["location"].apply(location_to_zh)
    return freq.to_dict(orient="records")


@router.get("/dashboard")
def dashboard():
    return {
        "overview": overview(),
        "top_skills": top_skills(15),
        "category_distribution": category_distribution(),
        "salary_by_location": salary_by_location(),
        "source_distribution": source_distribution(),
    }
