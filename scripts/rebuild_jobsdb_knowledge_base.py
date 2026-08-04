#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.dependencies import load_jobs_df
from src.analyzer.insurance_reviewer import InsuranceReviewer
from src.analyzer.rule_engine import RuleBasedSkillExtractor
from src.cleaner.pipeline import CleaningPipeline
from src.embeddings.vector_store import VectorStore
from src.logger import get_logger
from src.storage.mongodb import JobDatabase
from scripts.crawl_utils import is_insurance_sales


DEFAULT_RAW_PATH = Path(r"E:\文档\Project\HK-Job-Crawler\data\raw\jobsdb_raw.json")
DEFAULT_CSV_PATH = Path("data/cleaned/jobs.csv")


def load_raw_jobs(path: Path) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("Raw JobsDB data must be a JSON array")
    return [item for item in data if isinstance(item, dict)]


def build_kb_document(job: dict) -> str:
    skills = job.get("skills") or {}
    flat_skills = []
    if isinstance(skills, dict):
        for values in skills.values():
            if isinstance(values, list):
                flat_skills.extend(str(value) for value in values)

    parts = [
        f"Title: {job.get('title', '')}",
        f"Company: {job.get('company', '')}",
        f"Location: {job.get('location', '')}",
        f"Salary: {job.get('salary_raw', '')}",
        f"Employment Type: {job.get('employment_type', '') or job.get('job_type', '')}",
        f"Industry: {job.get('industry_category', '')}",
        f"Work Mode: {job.get('work_mode', '')}",
        f"Education: {job.get('education_required', '')}",
        f"Languages: {', '.join(job.get('languages_required') or [])}",
        f"Skills: {', '.join(sorted(set(flat_skills)))}",
        "Job Description:",
        job.get("jd_text") or job.get("jd_raw") or "",
    ]
    return "\n".join(part for part in parts if part is not None).strip()


def normalize_for_csv(records: list[dict]) -> list[dict]:
    normalized = []
    for record in records:
        item = dict(record)
        for key, value in list(item.items()):
            if isinstance(value, (dict, list)):
                item[key] = json.dumps(value, ensure_ascii=False)
        normalized.append(item)
    return normalized


def clean_jobs(raw_jobs: list[dict], review_insurance: bool = False) -> list[dict]:
    pipeline = CleaningPipeline()
    extractor = RuleBasedSkillExtractor()
    now = datetime.now().isoformat()
    cleaned_jobs = []
    seen_job_ids: dict[str, int] = {}

    for raw in raw_jobs:
        job = dict(raw)
        job.setdefault("source", "jobsdb")
        original_job_id = str(job.get("job_id") or "").strip()
        if original_job_id:
            seen_job_ids[original_job_id] = seen_job_ids.get(original_job_id, 0) + 1
            if seen_job_ids[original_job_id] > 1:
                job["original_job_id"] = original_job_id
                job["job_id"] = f"{original_job_id}__dup{seen_job_ids[original_job_id]}"
        job["crawled_at"] = job.get("crawled_at") or now
        cleaned = pipeline.clean_job(job)
        is_insurance, score, reasons = is_insurance_sales(cleaned)
        cleaned["is_insurance_sales"] = is_insurance
        cleaned["insurance_score"] = score
        cleaned["insurance_reasons"] = reasons
        skills = extractor.extract(cleaned.get("jd_text", ""))
        cleaned["skills"] = {category: list(values) for category, values in skills.items()}
        cleaned["kb_document_text"] = build_kb_document(cleaned)
        cleaned_jobs.append(cleaned)

    if review_insurance:
        suspects = [job for job in cleaned_jobs if job.get("is_insurance_sales")]
        if suspects:
            reviewed_by_id = {
                job.get("job_id"): job
                for job in InsuranceReviewer().review_batch(suspects)
            }
            for idx, job in enumerate(cleaned_jobs):
                if job.get("job_id") in reviewed_by_id:
                    cleaned_jobs[idx].update(reviewed_by_id[job.get("job_id")])

    return cleaned_jobs


def clear_knowledge_base(csv_path: Path, db: JobDatabase, store: VectorStore) -> dict[str, Any]:
    result: dict[str, Any] = {"mongo_deleted": 0, "vector_cleared": False, "csv_cleared": False}
    if db.is_connected:
        result["mongo_deleted"] = db.clear_all()
    store.clear()
    result["vector_cleared"] = True
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame().to_csv(csv_path, index=False, encoding="utf-8-sig")
    result["csv_cleared"] = True
    return result


def import_to_mongodb(records: list[dict], db: JobDatabase) -> int:
    if not db.is_connected:
        return 0
    inserted_or_updated = 0
    for record in records:
        db.insert_job(record)
        inserted_or_updated += 1
    return inserted_or_updated


def rebuild(raw_path: Path, csv_path: Path, confirm_clear: bool, review_insurance: bool = False) -> dict[str, Any]:
    if not confirm_clear:
        raise ValueError("Refusing to clear knowledge base without --confirm-clear")
    if not raw_path.exists():
        raise FileNotFoundError(raw_path)

    logger = get_logger("rebuild_jobsdb_knowledge_base")
    raw_jobs = load_raw_jobs(raw_path)
    logger.info("Loaded %d raw JobsDB records", len(raw_jobs))

    cleaned_jobs = clean_jobs(raw_jobs, review_insurance=review_insurance)
    db = JobDatabase()
    store = VectorStore()
    clear_result = clear_knowledge_base(csv_path, db, store)

    csv_records = normalize_for_csv(cleaned_jobs)
    pd.DataFrame(csv_records).to_csv(csv_path, index=False, encoding="utf-8-sig")
    load_jobs_df.cache_clear()

    mongo_count = import_to_mongodb(cleaned_jobs, db)
    store.rebuild_from_csv(str(csv_path))
    if cleaned_jobs and store.available and store.count() == 0:
        raise RuntimeError("Vector rebuild completed with zero documents")

    return {
        "raw_records": len(raw_jobs),
        "cleaned_records": len(cleaned_jobs),
        "csv_path": str(csv_path),
        "mongo_connected": db.is_connected,
        "mongo_imported": mongo_count,
        "vector_available": store.available,
        "vector_count": store.count(),
        **clear_result,
    }


def main():
    parser = argparse.ArgumentParser(description="Clear and rebuild the JobsDB knowledge base")
    parser.add_argument("--raw", default=str(DEFAULT_RAW_PATH), help="Path to jobsdb_raw.json")
    parser.add_argument("--csv", default=str(DEFAULT_CSV_PATH), help="Output CSV path")
    parser.add_argument("--confirm-clear", action="store_true", help="Required: clear MongoDB, ChromaDB, and jobs.csv")
    parser.add_argument("--review-insurance", action="store_true", help="Run optional LLM review for suspected insurance sales jobs")
    args = parser.parse_args()

    result = rebuild(
        raw_path=Path(args.raw),
        csv_path=Path(args.csv),
        confirm_clear=args.confirm_clear,
        review_insurance=args.review_insurance,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
