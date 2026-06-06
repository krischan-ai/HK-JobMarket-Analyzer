from __future__ import annotations

import time
import json as _json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from threading import Lock
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from api.dependencies import load_jobs_df
from api.schemas.role_stats import ClassificationResult, LLMStatus, RoleDistributionItem
from src.analyzer.role_classifier import ROLE_DEFINITIONS, CACHE_PATH, RoleClassifier, RoleResult
from src.analyzer.role_prompt import ROLE_DEFINITIONS as ROLE_DEFS
from src.analyzer.rule_engine import RuleBasedSkillExtractor
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

    if req.mode == "full":
        classifier.clear_cache()

    # 安全转换 NaN 值
    def _safe_str(v) -> str:
        if v is None:
            return ""
        if isinstance(v, float) and v != v:
            return ""
        return str(v)

    jobs = df.to_dict(orient="records")
    # 预处理：将所有 NaN 字段转为安全字符串
    for job in jobs:
        for key in ("jd_raw", "jd_text", "job_id", "title"):
            if key in job:
                job[key] = _safe_str(job.get(key))

    start = time.time()

    try:
        results = classifier.classify_batch(jobs, text_field="jd_raw", batch_size=req.batch_size)
    except Exception as e:
        logger.exception("Classification failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Classification error: {e}")

    elapsed = (time.time() - start) * 1000
    classified_count = sum(1 for j in results if j.get("role_id"))

    for job in results:
        job_id = _safe_str(job.get("job_id"))
        cache_key = classifier._make_cache_key(_safe_str(job.get("jd_raw")))
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


@router.post("/classify-jobs")
def classify_jobs(req: RunClassificationRequest = RunClassificationRequest()):
    """分类岗位并返回带技能标签的详细结果（并发 LLM 调用）"""
    df = load_jobs_df()
    if df.empty:
        raise HTTPException(status_code=400, detail="No job data available")

    classifier = _get_classifier()
    llm_mode = classifier.available
    logger.info("Classify-jobs: LLM=%s, mode=%s, batch=%d, total=%d", llm_mode, req.mode, req.batch_size, len(df))

    if req.mode == "full":
        classifier.clear_cache()

    # 技能提取引擎
    skill_extractor = RuleBasedSkillExtractor()
    skill_extractor.clear_cache()

    jobs = df.to_dict(orient="records")
    total = len(jobs)
    start = time.time()

    cache_lock = Lock()
    classified_count = [0]

    # 安全 float（处理 NaN）
    def _safe_float(v):
        try:
            fv = float(v) if v is not None else 0.0
            return fv if fv == fv else 0.0
        except (ValueError, TypeError):
            return 0.0

    def _safe_int(v, default=0):
        """安全 int 转换（处理 NaN / None）"""
        try:
            if v is None:
                return default
            fv = float(v)
            if fv != fv:  # NaN check
                return default
            return int(fv)
        except (ValueError, TypeError):
            return default

    def _safe_bool(v) -> bool:
        """安全 bool 转换（NaN 视为 False）"""
        if v is None:
            return False
        if isinstance(v, float) and v != v:  # NaN
            return False
        return bool(v)

    def _safe_str(v) -> str:
        """安全 str 转换（NaN / None 视为空字符串）"""
        if v is None:
            return ""
        if isinstance(v, float) and v != v:  # NaN
            return ""
        return str(v)

    def _classify_one(job: dict) -> dict:
        try:
            return _do_classify(job)
        except Exception as e:
            logger.exception("Failed to classify job %s: %s", job.get("job_id", "?"), e)
            # 返回一个最低置信度的 other 结果，避免整个请求失败
            return {
                "job_id": str(job.get("job_id", "")),
                "title": str(job.get("title", "")),
                "company": str(job.get("company", "")),
                "location": str(job.get("location", "")),
                "source": str(job.get("source", "")),
                "role_id": "other",
                "role_name": "其他",
                "role_confidence": "low",
                "salary_min": _safe_float(job.get("salary_min")),
                "salary_max": _safe_float(job.get("salary_max")),
                "skills": [],
                "is_insurance_sales": False,
                "insurance_score": 0,
                "llm_is_insurance": False,
                "llm_confidence": "",
                "llm_explanation": "",
            }

    def _do_classify(job: dict) -> dict:
        jd_text = str(job.get("jd_raw", "") or "")
        # 分类文本：用 JD 文本，若太短则用标题补充
        classify_text = jd_text if len(jd_text) > 20 else str(job.get("title", ""))
        cache_key = classifier._make_cache_key(classify_text)

        # 先检查缓存（加锁）
        with cache_lock:
            if cache_key in classifier._cache:
                cached = classifier._cache[cache_key]
                # 过滤掉内部字段（如 _job_id）
                cls_result = RoleResult(
                    role_id=cached.get("role_id", "other"),
                    role_name=cached.get("role_name", "其他"),
                    confidence=cached.get("confidence", "low"),
                )
                from_cache = True
            else:
                from_cache = False

        if not from_cache:
            # LLM 调用不加锁，允许并发
            if classifier.available:
                try:
                    cls_result = classifier._classify_with_llm(classify_text)
                except Exception:
                    cls_result = classifier._classify_with_rules(classify_text)
            else:
                cls_result = classifier._classify_with_rules(classify_text)

            # 写回缓存（加锁）
            with cache_lock:
                classifier._cache[cache_key] = {
                    "role_id": cls_result.role_id,
                    "role_name": cls_result.role_name,
                    "confidence": cls_result.confidence,
                }
                classifier._save_cache()

        if cls_result.role_id and cls_result.role_id != "other":
            classified_count[0] += 1

        # 提取技术栈（用规则引擎从 JD 文本+标题中提取）
        jd_text_raw = str(job.get("jd_text", "") or job.get("jd_raw", "") or "")
        title_raw = str(job.get("title", ""))
        skill_dict = skill_extractor.extract(jd_text_raw + " " + title_raw)
        flat_skills: list[dict] = []
        for cat, skill_set in skill_dict.items():
            for s in skill_set:
                flat_skills.append({"name": str(s), "category": str(cat)})

        # 保险销售标记（爬虫阶段已计算）
        is_ins = _safe_bool(job.get("is_insurance_sales"))
        ins_score = _safe_int(job.get("insurance_score", 0))

        return {
            "job_id": str(job.get("job_id", "")),
            "title": str(job.get("title", "")),
            "company": str(job.get("company", "")),
            "location": str(job.get("location", "")),
            "source": str(job.get("source", "")),
            "role_id": cls_result.role_id,
            "role_name": cls_result.role_name,
            "role_confidence": cls_result.confidence,
            "salary_min": _safe_float(job.get("salary_min")),
            "salary_max": _safe_float(job.get("salary_max")),
            "skills": flat_skills,
            "is_insurance_sales": is_ins,
            "insurance_score": ins_score,
            "llm_is_insurance": _safe_bool(job.get("llm_is_insurance")),
            "llm_confidence": _safe_str(job.get("llm_confidence")),
            "llm_explanation": _safe_str(job.get("llm_explanation")),
        }

    # 并发分类（max_workers 控制 LLM 并发数）
    workers = min(8, total)
    results_map: dict[int, dict] = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_classify_one, job): idx for idx, job in enumerate(jobs)}
        for future in as_completed(futures):
            idx = futures[future]
            try:
                results_map[idx] = future.result()
            except Exception as e:
                logger.exception("Unexpected error classifying job index %d: %s", idx, e)
                results_map[idx] = {
                    "job_id": str(jobs[idx].get("job_id", "")),
                    "title": str(jobs[idx].get("title", "")),
                    "company": "", "location": "", "source": "",
                    "role_id": "other", "role_name": "其他", "role_confidence": "low",
                    "salary_min": 0.0, "salary_max": 0.0, "skills": [],
                    "is_insurance_sales": False, "insurance_score": 0,
                    "llm_is_insurance": False, "llm_confidence": "", "llm_explanation": "",
                }
            done = len(results_map)
            if done % 50 == 0 or done == total:
                logger.info("Classify progress: %d/%d", done, total)

    # 恢复原始顺序
    results = [results_map[i] for i in range(total) if i in results_map]

    elapsed = (time.time() - start) * 1000

    # Save cache
    for job in jobs:
        cache_key = classifier._make_cache_key(str(job.get("jd_raw", "")))
        if cache_key in classifier._cache:
            classifier._cache[cache_key]["_job_id"] = str(job.get("job_id", ""))
    classifier._save_cache()

    return {
        "success": True,
        "total": total,
        "classified": classified_count[0],
        "duration_ms": round(elapsed, 0),
        "llm_mode": llm_mode,
        "message": f"Classified {classified_count[0]}/{total} jobs in {elapsed/1000:.1f}s ({'LLM' if llm_mode else 'Rules'})",
        "items": results,
    }


class InsuranceReviewRequest(BaseModel):
    job_ids: list[str] = []


@router.post("/review-insurance")
def review_insurance(req: InsuranceReviewRequest):
    """LLM 复审疑似保险销售岗位，返回每个岗位的复审结果"""
    if not req.job_ids:
        raise HTTPException(status_code=400, detail="No job IDs provided")

    from src.analyzer.insurance_reviewer import InsuranceReviewer

    reviewer = InsuranceReviewer()
    if not reviewer.available:
        raise HTTPException(status_code=400, detail="LLM 未配置，无法复审")

    df = load_jobs_df()
    if df.empty:
        raise HTTPException(status_code=400, detail="No job data")

    # 筛选出指定 ID 的岗位
    target_jobs = df[df["job_id"].astype(str).isin(req.job_ids)].to_dict(orient="records")
    if not target_jobs:
        raise HTTPException(status_code=404, detail="No matching jobs found")

    start = time.time()
    reviewed = reviewer.review_batch(target_jobs)
    elapsed = (time.time() - start) * 1000

    # 构建返回
    results = []
    for job in reviewed:
        results.append({
            "job_id": str(job.get("job_id", "")),
            "title": str(job.get("title", "")),
            "company": str(job.get("company", "")),
            "is_insurance_sales": bool(job.get("is_insurance_sales", False)),
            "insurance_score": int(job.get("insurance_score", 0)),
            "llm_is_insurance": bool(job.get("llm_is_insurance", False)),
            "llm_confidence": str(job.get("llm_confidence", "")),
            "llm_explanation": str(job.get("llm_explanation", "")),
        })

    insurance_count = sum(1 for r in results if r["llm_is_insurance"])

    return {
        "success": True,
        "total": len(results),
        "insurance_confirmed": insurance_count,
        "duration_ms": round(elapsed, 0),
        "message": f"LLM 复审完成: {insurance_count}/{len(results)} 确认为保险销售 ({elapsed/1000:.1f}s)",
        "items": results,
    }
