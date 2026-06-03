from __future__ import annotations

import time
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.dependencies import load_jobs_df
from api.schemas.role_stats import ClassificationResult, LLMStatus, RoleDistributionItem
from src.analyzer.role_classifier import ROLE_DEFINITIONS, CACHE_PATH, RoleClassifier
from src.analyzer.role_prompt import ROLE_DEFINITIONS as ROLE_DEFS
from src.logger import get_logger

router = APIRouter(prefix="/api/stats", tags=["role-stats"])
logger = get_logger("api.role_stats")


def _get_classifier() -> RoleClassifier:
    return RoleClassifier()


@router.get("/role-distribution")
def role_distribution():
    classifier = _get_classifier()
    stats = classifier.get_statistics()
    return stats["distribution"]


@router.get("/role-salary")
def role_salary():
    df = load_jobs_df()
    classifier = _get_classifier()

    if df.empty:
        return []

    cache_entries = classifier._cache

    groups: dict[str, dict] = {}
    for _, row in df.iterrows():
        job_id = str(row.get("job_id", ""))
        role_id = "other"

        for cache_key, entry in cache_entries.items():
            if entry.get("_job_id") == job_id:
                role_id = entry.get("role_id", "other")
                break

        if role_id not in ROLE_DEFS:
            role_id = "other"

        salary_min = row.get("salary_min")
        salary_max = row.get("salary_max")
        if salary_min is None or (isinstance(salary_min, float) and salary_min != salary_min):
            continue
        salary_val = float(salary_min)

        if role_id not in groups:
            groups[role_id] = {"role_id": role_id, "role_name": ROLE_DEFS.get(role_id, {}).get("name", "其他"), "values": []}
        groups[role_id]["values"].append(salary_val)

    result = []
    for role_id, gdata in groups.items():
        values = gdata["values"]
        result.append({
            "role_id": role_id,
            "role_name": gdata["role_name"],
            "salary_avg": round(sum(values) / len(values), 0),
            "salary_min": min(values),
            "salary_max": max(values),
            "count": len(values),
        })

    result.sort(key=lambda x: x["count"], reverse=True)
    return result


@router.get("/llm-status")
def llm_status():
    classifier = _get_classifier()
    df = load_jobs_df()
    total = len(df)
    classified = len(classifier._cache)

    last_analysis = None
    if CACHE_PATH.exists():
        last_analysis = datetime.fromtimestamp(CACHE_PATH.stat().st_mtime, tz=timezone.utc).isoformat()

    return {
        "total_jobs": total,
        "classified": classified,
        "coverage_rate": round(classified / total * 100, 1) if total > 0 else 0.0,
        "last_analysis": last_analysis,
        "llm_available": classifier.available,
    }


class RunClassificationRequest(BaseModel):
    mode: str = "full"
    batch_size: int = 5


@router.post("/run-classification")
def run_classification(req: RunClassificationRequest = RunClassificationRequest()):
    df = load_jobs_df()
    if df.empty:
        raise HTTPException(status_code=400, detail="No job data available")

    classifier = _get_classifier()
    if not classifier.available:
        logger.info("LLM not available, using rule-based fallback classification")

    if req.mode == "full":
        classifier.clear_cache()

    jobs = df.to_dict(orient="records")
    start = time.time()
    results = classifier.classify_batch(jobs, text_field="jd_raw", batch_size=req.batch_size)
    elapsed = (time.time() - start) * 1000

    classified_count = sum(1 for j in results if j.get("role_id"))

    for job in results:
        job_id = str(job.get("job_id", ""))
        cache_key = classifier._make_cache_key(job.get("jd_raw", ""))
        if cache_key in classifier._cache:
            classifier._cache[cache_key]["_job_id"] = job_id
    classifier._save_cache()

    return {
        "success": True,
        "total": len(results),
        "classified": classified_count,
        "duration_ms": round(elapsed, 0),
        "message": f"Classified {classified_count}/{len(results)} jobs in {elapsed/1000:.1f}s",
    }
