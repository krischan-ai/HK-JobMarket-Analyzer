from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

from src.crawler_controller.scheduler import CrawlerScheduler
from src.crawler_controller.scheduler_config import SchedulerConfig
from src.crawler_controller.task_manager import TaskManager
from src.crawlers import list_sources
from src.logger import get_logger

router = APIRouter(prefix="/api/scheduler", tags=["scheduler"])
logger = get_logger(__name__)
cfg = SchedulerConfig()
manager = TaskManager()
scheduler = CrawlerScheduler(manager=manager)


class CronJobCreate(BaseModel):
    name: str = Field(..., description="任務名稱")
    keywords: list[str] = Field(..., min_length=1)
    sources: list[str] = Field(..., min_length=1)
    cron: str = Field(default="0 6 * * 1", description="Cron 表達式")
    enabled: bool = Field(default=True)


class CronJobResponse(BaseModel):
    id: str
    name: str
    keywords: list[str]
    sources: list[str]
    cron: str
    enabled: bool
    last_run: Optional[str] = None
    created_at: str


def _job_to_response(j: dict) -> CronJobResponse:
    return CronJobResponse(
        id=j.get("id", ""),
        name=j.get("name", ""),
        keywords=j.get("keywords", []),
        sources=j.get("sources", []),
        cron=j.get("cron", "0 6 * * 1"),
        enabled=j.get("enabled", True),
        last_run=j.get("last_run"),
        created_at=j.get("created_at", ""),
    )


@router.get("/jobs", response_model=list[CronJobResponse])
def list_jobs():
    """獲取所有定時任務"""
    return [_job_to_response(j) for j in cfg.load_all()]


@router.post("/jobs", response_model=CronJobResponse, status_code=201)
def create_job(body: CronJobCreate):
    """創建定時任務"""
    valid = list_sources()
    for s in body.sources:
        if s not in valid:
            raise HTTPException(400, f"Invalid source: {s}. Available: {valid}")

    job = {
        "id": uuid.uuid4().hex[:12],
        "name": body.name,
        "keywords": body.keywords,
        "sources": body.sources,
        "cron": body.cron,
        "enabled": body.enabled,
        "last_run": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    cfg.add_job(job)
    logger.info("Cron job created: %s", job["id"])
    return _job_to_response(job)


@router.put("/jobs/{job_id}", response_model=CronJobResponse)
def update_job(job_id: str, body: CronJobCreate):
    """更新定時任務"""
    updated = cfg.update_job(job_id, {
        "name": body.name,
        "keywords": body.keywords,
        "sources": body.sources,
        "cron": body.cron,
        "enabled": body.enabled,
    })
    if not updated:
        raise HTTPException(404, f"Job not found: {job_id}")
    return _job_to_response(updated)


@router.delete("/jobs/{job_id}")
def delete_job(job_id: str):
    """刪除定時任務"""
    if not cfg.delete_job(job_id):
        raise HTTPException(404, f"Job not found: {job_id}")
    return {"message": f"Job {job_id} deleted"}


@router.post("/jobs/{job_id}/run")
async def run_job_now(job_id: str, bg: BackgroundTasks):
    """手動觸發執行定時任務"""
    jobs = cfg.load_all()
    job = next((j for j in jobs if j.get("id") == job_id), None)
    if not job:
        raise HTTPException(404, f"Job not found: {job_id}")

    task = manager.create_task(job["keywords"], job["sources"])
    manager.start_task(task.task_id)
    bg.add_task(scheduler.run_task, task)

    cfg.update_job(job_id, {"last_run": datetime.now(timezone.utc).isoformat()})

    return {"task_id": task.task_id, "message": f"Job {job_id} started as task {task.task_id}"}
