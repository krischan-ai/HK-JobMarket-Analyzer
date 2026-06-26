from fastapi import APIRouter, Query
from api.dependencies import load_jobs_df, load_skills_df
from api.routers.stats import (
    _NON_TECH_CATEGORY_LIMITS,
    _add_label,
    _infer_industry_with_rules,
    _job_industry_record,
    _scan_non_tech_labels_from_text,
    location_to_zh,
)
import pandas as pd
import math
from pathlib import Path
from datetime import datetime
import ast
import json

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

_EMPTY_DOMAIN_LABELS = {"其他", "other", "Others", "未知", "N/A", "na", "none"}


def _safe_str(row, field: str) -> str:
    value = row.get(field, "")
    return str(value) if pd.notna(value) else ""


def _safe_int(row, field: str):
    value = row.get(field, None)
    return int(value) if pd.notna(value) else None


def _safe_bool(row, field: str) -> bool:
    value = row.get(field, False)
    if pd.isna(value):
        return False
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes"}


def _safe_list(row, field: str) -> list[str]:
    value = row.get(field, [])
    if isinstance(value, list):
        return value
    if pd.isna(value):
        return []
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        try:
            parsed = ast.literal_eval(text)
            if isinstance(parsed, list):
                return [str(item) for item in parsed]
        except (ValueError, SyntaxError):
            return [part.strip() for part in text.split(";") if part.strip()]
    return []


def _empty_soft_skills() -> dict[str, list[str]]:
    return {
        "education": [],
        "language": [],
        "soft_skill": [],
        "domain_knowledge": [],
        "certification": [],
        "business_skill": [],
    }


def _normalize_soft_skills(value) -> dict[str, list[str]]:
    if not isinstance(value, dict):
        return _empty_soft_skills()
    result = _empty_soft_skills()
    for key in result:
        result[key] = [str(x).strip() for x in value.get(key, []) if str(x).strip()]
    return result


def _merge_soft_skills_for_row(row, cached_soft_skills, industry_category: str) -> dict[str, list[str]]:
    bucket: dict[str, set[str]] = {category: set() for category in _NON_TECH_CATEGORY_LIMITS}
    normalized = _normalize_soft_skills(cached_soft_skills)

    for category in _NON_TECH_CATEGORY_LIMITS:
        for item in normalized.get(category, []):
            _add_label(bucket, category, item)

    for item in _safe_list(row, "languages_required"):
        _add_label(bucket, "language", item)

    education = _safe_str(row, "education_required")
    if education:
        _add_label(bucket, "education", education)

    jd_text = " ".join([
        _safe_str(row, "title"),
        _safe_str(row, "company"),
        industry_category or _safe_str(row, "industry_category"),
        _safe_str(row, "jd_text"),
        _safe_str(row, "jd_raw"),
        _safe_str(row, "kb_document_text"),
    ])
    scanned = _scan_non_tech_labels_from_text(jd_text)
    for category, labels in scanned.items():
        for label in labels:
            _add_label(bucket, category, label)

    try:
        industry = industry_category or _infer_industry_with_rules(_job_industry_record(row, 0))
        if industry and industry.strip() not in _EMPTY_DOMAIN_LABELS:
            _add_label(bucket, "domain_knowledge", industry)
    except Exception:
        pass

    result = _empty_soft_skills()
    bucket.get("domain_knowledge", set()).difference_update(_EMPTY_DOMAIN_LABELS)
    for category in result:
        result[category] = sorted(bucket.get(category, set()))
    return result


def _soft_skills_by_job_id() -> dict[str, dict[str, list[str]]]:
    try:
        from src.analyzer.role_classifier import CACHE_PATH
        if not CACHE_PATH.exists():
            return {}
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            cache_data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}

    result: dict[str, dict[str, list[str]]] = {}
    if not isinstance(cache_data, dict):
        return result
    for entry in cache_data.values():
        if not isinstance(entry, dict):
            continue
        job_id = str(entry.get("_job_id") or "").strip()
        if job_id:
            result[job_id] = _normalize_soft_skills(entry.get("soft_skills"))
    return result


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

    try:
        from api.routers.role_stats import classified_industry_map
        classified_industries = classified_industry_map()
    except Exception:
        classified_industries = {}
    soft_skills_by_job = _soft_skills_by_job_id()

    items = []
    for _, row in df_page.iterrows():
        skills = None
        if "skills" in df.columns and pd.notna(row.get("skills")):
            skills = row["skills"]
        src = str(row.get("source", "")).lower().strip()
        import_time = source_times.get(src, None)
        job_id = str(row.get("job_id", ""))
        industry_category = classified_industries.get(job_id) or (str(row.get("industry_category", "")) if pd.notna(row.get("industry_category")) else "")
        soft_skills = _merge_soft_skills_for_row(row, soft_skills_by_job.get(job_id), industry_category)
        items.append({
            "job_id": job_id,
            "title": str(row.get("title", "")),
            "company": str(row.get("company", "")),
            "location": location_to_zh(str(row.get("location", ""))),
            "salary_min": float(row.get("salary_min", 0)) if pd.notna(row.get("salary_min")) else None,
            "salary_max": float(row.get("salary_max", 0)) if pd.notna(row.get("salary_max")) else None,
            "source": str(row.get("source", "")),
            "skills": skills,
            "jd_text": str(row.get("jd_text", "")) if pd.notna(row.get("jd_text")) else "",
            "jd_raw": str(row.get("jd_raw", "")) if pd.notna(row.get("jd_raw")) else "",
            "url": str(row.get("url", "")) if pd.notna(row.get("url")) else "",
            "posted_at": str(row.get("posted_at", "")) if pd.notna(row.get("posted_at")) else "",
            "employment_type": str(row.get("employment_type", "")) if pd.notna(row.get("employment_type")) else "",
            "industry_category": industry_category,
            "application_volume": str(row.get("application_volume", "")) if pd.notna(row.get("application_volume")) else "",
            "employer_questions": _safe_list(row, "employer_questions"),
            "is_insurance_sales": _safe_bool(row, "is_insurance_sales"),
            "insurance_score": _safe_int(row, "insurance_score"),
            "insurance_reasons": _safe_list(row, "insurance_reasons"),
            "work_mode": _safe_str(row, "work_mode"),
            "posted_days_ago": _safe_int(row, "posted_days_ago"),
            "company_size": _safe_str(row, "company_size"),
            "education_required": _safe_str(row, "education_required"),
            "languages_required": _safe_list(row, "languages_required"),
            "tech_stack": _safe_list(row, "tech_stack"),
            "soft_skills": soft_skills,
            "job_type": _safe_str(row, "job_type"),
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
    # 先翻译再计数，合并同名地区
    locs = df["location"].apply(location_to_zh).value_counts().reset_index()
    locs.columns = ["name", "count"]
    return locs.to_dict(orient="records")
