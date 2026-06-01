from fastapi import APIRouter, Query
from api.dependencies import load_jobs_df, load_skills_df
import json

router = APIRouter(prefix="/api/stats", tags=["stats"])


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
