from __future__ import annotations

import threading
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

# 分类状态（全局共享，跨请求持久化）
_classify_progress: dict = {"running": False, "progress": 0, "total": 0, "done": 0, "message": "", "llm_mode": False}
_classify_result: list[dict] = []
_classify_last_at: Optional[str] = None  # 最近一次分类完成时间
_classify_thread: Optional[threading.Thread] = None


def _get_classifier() -> RoleClassifier:
    return RoleClassifier()


def _safe_role_text(row) -> str:
    parts = [
        str(row.get("title", "") or ""),
        str(row.get("jd_text", "") or ""),
        str(row.get("jd_raw", "") or ""),
    ]
    return " ".join(part for part in parts if part and part != "nan").strip()


def _role_from_cache_or_rules(classifier: RoleClassifier, row) -> RoleResult:
    job_id = str(row.get("job_id", "") or "")

    for entry in classifier._cache.values():
        if entry.get("_job_id") == job_id:
            role_id = entry.get("role_id", "other")
            if role_id not in ROLE_DEFS:
                role_id = "other"
            return RoleResult(
                role_id=role_id,
                role_name=ROLE_DEFS.get(role_id, {}).get("name", "其他"),
                confidence=entry.get("confidence", "low"),
            )

    for text in (
        str(row.get("jd_raw", "") or ""),
        str(row.get("jd_text", "") or ""),
        _safe_role_text(row),
    ):
        if not text or text == "nan":
            continue
        cached = classifier._cache.get(classifier._make_cache_key(text))
        if cached:
            role_id = cached.get("role_id", "other")
            if role_id not in ROLE_DEFS:
                role_id = "other"
            return RoleResult(
                role_id=role_id,
                role_name=ROLE_DEFS.get(role_id, {}).get("name", "其他"),
                confidence=cached.get("confidence", "low"),
            )

    text = _safe_role_text(row)
    if not text:
        return RoleResult(role_id="other", role_name="其他", confidence="low")
    return classifier._classify_with_rules(text)


@router.get("/role-distribution")
def role_distribution():
    classifier = _get_classifier()
    df = load_jobs_df()
    if df.empty:
        return []

    distribution: dict[str, dict] = {}
    total = 0
    for _, row in df.iterrows():
        role_result = _role_from_cache_or_rules(classifier, row)
        if role_result.role_id == "other":
            continue
        total += 1
        if role_result.role_id not in distribution:
            distribution[role_result.role_id] = {
                "role_id": role_result.role_id,
                "role_name": ROLE_DEFS.get(role_result.role_id, {}).get("name", role_result.role_name),
                "count": 0,
            }
        distribution[role_result.role_id]["count"] += 1

    result = sorted(distribution.values(), key=lambda x: x["count"], reverse=True)
    for item in result:
        item["percentage"] = round(item["count"] / total * 100, 1) if total > 0 else 0.0
    return result


@router.get("/role-salary")
def role_salary():
    df = load_jobs_df()
    classifier = _get_classifier()

    if df.empty:
        return []

    groups: dict[str, dict] = {}
    for _, row in df.iterrows():
        role_result = _role_from_cache_or_rules(classifier, row)
        role_id = role_result.role_id

        salary_min = row.get("salary_min")
        salary_max = row.get("salary_max")
        if salary_min is None or (isinstance(salary_min, float) and salary_min != salary_min):
            continue
        salary_val = float(salary_min)
        if salary_val <= 0:
            continue

        if role_id == "other":
            continue

        if role_id not in groups:
            groups[role_id] = {"role_id": role_id, "role_name": ROLE_DEFS.get(role_id, {}).get("name", role_result.role_name), "values": []}
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
    use_llm: bool = True  # True=LLM可用时使用LLM, False=强制规则模式


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


def _run_classify_in_background(req: RunClassificationRequest):
    """在后台线程中执行分类，结果存入 _classify_result"""
    global _classify_progress, _classify_result, _classify_last_at, _classify_thread

    df = load_jobs_df()
    if df.empty:
        _classify_progress = {"running": False, "progress": 0, "total": 0, "done": 0, "message": "没有数据", "llm_mode": False}
        return

    classifier = _get_classifier()
    llm_mode = classifier.available and req.use_llm
    logger.info("Classify-bg: LLM=%s, total=%d, use_llm=%s", llm_mode, len(df), req.use_llm)

    _classify_progress = {"running": True, "progress": 0, "total": len(df), "done": 0, "message": "正在初始化分類...", "llm_mode": llm_mode}
    _classify_result = []

    if req.mode == "full":
        classifier.clear_cache()

    skill_extractor = RuleBasedSkillExtractor()
    skill_extractor.clear_cache()

    jobs = df.to_dict(orient="records")
    total = len(jobs)
    start = time.time()

    cache_lock = Lock()
    classified_count = [0]

    def _safe_float(v):
        try:
            fv = float(v) if v is not None else 0.0
            return fv if fv == fv else 0.0
        except (ValueError, TypeError):
            return 0.0

    def _safe_int(v, default=0):
        try:
            if v is None: return default
            fv = float(v)
            return default if fv != fv else int(fv)
        except (ValueError, TypeError):
            return default

    def _safe_bool(v) -> bool:
        if v is None: return False
        if isinstance(v, float) and v != v: return False
        return bool(v)

    def _safe_str(v) -> str:
        if v is None: return ""
        if isinstance(v, float) and v != v: return ""
        return str(v)

    def _classify_one(job: dict) -> dict:
        try:
            return _do_classify(job)
        except Exception as e:
            logger.exception("Failed to classify job %s: %s", job.get("job_id", "?"), e)
            return {
                "job_id": _safe_str(job.get("job_id")),
                "title": _safe_str(job.get("title")),
                "company": _safe_str(job.get("company")),
                "location": _safe_str(job.get("location")),
                "source": _safe_str(job.get("source")),
                "role_id": "other", "role_name": "其他", "role_confidence": "low",
                "salary_min": _safe_float(job.get("salary_min")),
                "salary_max": _safe_float(job.get("salary_max")),
                "skills": [], "is_insurance_sales": False, "insurance_score": 0,
                "llm_is_insurance": False, "llm_confidence": "", "llm_explanation": "",
            }

    def _do_classify(job: dict) -> dict:
        jd_text = str(job.get("jd_raw", "") or "")
        classify_text = jd_text if len(jd_text) > 20 else str(job.get("title", ""))
        cache_key = classifier._make_cache_key(classify_text)

        with cache_lock:
            if cache_key in classifier._cache:
                cached = classifier._cache[cache_key]
                cls_result = RoleResult(
                    role_id=cached.get("role_id", "other"),
                    role_name=cached.get("role_name", "其他"),
                    confidence=cached.get("confidence", "low"),
                )
                from_cache = True
            else:
                from_cache = False

        if not from_cache:
            if llm_mode:
                try:
                    cls_result = classifier._classify_with_llm(classify_text)
                except Exception:
                    cls_result = classifier._classify_with_rules(classify_text)
            else:
                cls_result = classifier._classify_with_rules(classify_text)

            with cache_lock:
                classifier._cache[cache_key] = {
                    "role_id": cls_result.role_id,
                    "role_name": cls_result.role_name,
                    "confidence": cls_result.confidence,
                }
                classifier._save_cache()

        if cls_result.role_id and cls_result.role_id != "other":
            classified_count[0] += 1

        jd_text_raw = str(job.get("jd_text", "") or job.get("jd_raw", "") or "")
        title_raw = str(job.get("title", ""))
        skill_dict = skill_extractor.extract(jd_text_raw + " " + title_raw)
        flat_skills: list[dict] = []
        for cat, skill_set in skill_dict.items():
            for s in skill_set:
                flat_skills.append({"name": str(s), "category": str(cat)})

        is_ins = _safe_bool(job.get("is_insurance_sales"))
        ins_score = _safe_int(job.get("insurance_score", 0))

        return {
            "job_id": _safe_str(job.get("job_id")),
            "title": _safe_str(job.get("title")),
            "company": _safe_str(job.get("company")),
            "location": _safe_str(job.get("location")),
            "source": _safe_str(job.get("source")),
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

    # 并发分类
    workers = min(8, total)
    results_map: dict[int, dict] = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_classify_one, job): idx for idx, job in enumerate(jobs)}
        for future in as_completed(futures):
            idx = futures[future]
            try:
                results_map[idx] = future.result()
            except Exception:
                results_map[idx] = {
                    "job_id": _safe_str(jobs[idx].get("job_id")),
                    "role_id": "other", "role_name": "其他", "role_confidence": "low",
                    "salary_min": 0.0, "salary_max": 0.0, "skills": [],
                }
            done_count = len(results_map)
            pct = round(done_count / total * 100, 0)
            _classify_progress = {
                "running": True, "progress": int(pct), "total": total,
                "done": done_count,
                "message": f"正在分類... {done_count}/{total} ({int(pct)}%)",
                "llm_mode": llm_mode,
            }

    results = [results_map[i] for i in range(total) if i in results_map]
    elapsed = (time.time() - start) * 1000

    # Save cache
    for job in jobs:
        cache_key = classifier._make_cache_key(str(job.get("jd_raw", "")))
        if cache_key in classifier._cache:
            classifier._cache[cache_key]["_job_id"] = str(job.get("job_id", ""))
    classifier._save_cache()

    now_ts = datetime.now(timezone.utc).isoformat()
    _classify_result = results
    _classify_last_at = now_ts
    _classify_progress = {
        "running": False, "progress": 100, "total": total, "done": total,
        "message": f"分類完成：{classified_count[0]}/{total} ({ 'LLM' if llm_mode else '規則' } 模式)",
        "llm_mode": llm_mode,
        "duration_ms": round(elapsed, 0),
        "classified": classified_count[0],
    }
    _classify_thread = None
    logger.info("Classify-bg done: %d/%d in %.1fs", classified_count[0], total, elapsed / 1000)


@router.post("/classify-jobs")
def classify_jobs(req: RunClassificationRequest = RunClassificationRequest()):
    """启动后台分类任务，立即返回。进度通过 GET /classify-progress 查询"""
    global _classify_progress, _classify_result, _classify_thread

    # 如果已有任务在运行，拒绝
    if _classify_progress.get("running"):
        raise HTTPException(status_code=409, detail="分类任务正在运行中，请等待完成")

    df = load_jobs_df()
    if df.empty:
        raise HTTPException(status_code=400, detail="No job data available")

    # 重置状态
    _classify_result = []
    _classify_progress = {"running": True, "progress": 0, "total": len(df), "done": 0, "message": "正在啟動...", "llm_mode": False}

    # 启动后台线程
    _classify_thread = threading.Thread(
        target=_run_classify_in_background, args=(req,), daemon=True
    )
    _classify_thread.start()

    return {"started": True, "total": len(df), "message": "分類任務已啟動，請透過 GET /classify-progress 查詢進度"}


@router.get("/classify-progress")
def classify_progress():
    """查询分类进度和结果（供前端轮询）"""
    global _classify_progress, _classify_result, _classify_last_at
    resp = _classify_progress.copy()
    if not _classify_progress.get("running") and _classify_result:
        resp["results"] = _classify_result
    resp["last_classified_at"] = _classify_last_at
    return resp


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
