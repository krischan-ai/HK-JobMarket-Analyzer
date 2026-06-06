from __future__ import annotations

import asyncio

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query

from api.schemas.crawler import (
    CrawlResultItem,
    CrawlResultsResponse,
    CrawlTaskCreate,
    CrawlTaskDetailResponse,
    CrawlTaskListResponse,
    CrawlTaskResponse,
)
from src.crawler_controller.scheduler import CrawlerScheduler
from src.crawler_controller.status import CrawlerStatus, StateMachine
from src.crawler_controller.task_manager import TaskManager
from src.crawlers import list_sources

router = APIRouter(prefix="/api/crawler", tags=["crawler"])
manager = TaskManager()
scheduler = CrawlerScheduler(manager=manager)


# 爬取完成后应视为终态（可查看结果但无需轮询）
_CRAWL_DONE_STATUSES = {"completed", "post_processing", "processed", "processing_failed", "failed", "cancelled"}


def _to_response(task) -> CrawlTaskResponse:
    return CrawlTaskResponse(
        task_id=task.task_id,
        keywords=task.keywords,
        sources=task.sources,
        status=task.status.value,
        status_label=StateMachine.label(task.status),
        progress=task.progress,
        total_jobs=task.total_jobs,
        source_progress=task.source_progress,
        created_at=task.created_at,
        completed_at=task.completed_at,
        post_config=task.post_config,
        post_phase=task.post_phase,
        post_phase_pct=task.post_phase_pct,
        post_result=task.post_result,
    )


def _to_detail(task) -> CrawlTaskDetailResponse:
    data = _to_response(task).model_dump()
    data["logs"] = task.logs[-100:]
    return CrawlTaskDetailResponse(**data)


@router.get("/sources")
async def get_sources():
    """获取可用爬虫源列表"""
    return {"sources": list_sources()}


@router.post("/tasks", response_model=CrawlTaskResponse, status_code=201)
async def create_task(body: CrawlTaskCreate, bg: BackgroundTasks):
    """创建爬虫任务"""
    valid_sources = list_sources()
    for s in body.sources:
        if s not in valid_sources:
            raise HTTPException(400, f"Invalid source: {s}. Available: {valid_sources}")

    task = manager.create_task(body.keywords, body.sources)
    # 应用用户自定义后处理配置
    if body.post_config is not None:
        task.post_config = body.post_config.model_dump()
    manager.start_task(task.task_id)
    bg.add_task(scheduler.run_task, task)
    return _to_response(task)


@router.get("/tasks", response_model=CrawlTaskListResponse)
async def list_tasks(status: str = Query(None, description="按状态筛选: idle/running/paused/completed/post_processing/processed/processing_failed/failed/cancelled")):
    """获取任务列表"""
    if status and status not in [s.value for s in CrawlerStatus]:
        raise HTTPException(400, f"Invalid status: {status}")
    tasks = manager.list_tasks(status=status)
    return CrawlTaskListResponse(
        total=len(tasks),
        items=[_to_response(t) for t in tasks],
    )


@router.get("/tasks/{task_id}", response_model=CrawlTaskDetailResponse)
async def get_task(task_id: str):
    """获取任务详情（含日志）"""
    task = manager.get_task(task_id)
    if task is None:
        raise HTTPException(404, f"Task not found: {task_id}")
    return _to_detail(task)


@router.post("/tasks/{task_id}/start", response_model=CrawlTaskResponse)
async def start_task(task_id: str, bg: BackgroundTasks):
    """启动任务"""
    task = manager.get_task(task_id)
    if task is None:
        raise HTTPException(404, f"Task not found: {task_id}")
    if task.status != CrawlerStatus.IDLE:
        raise HTTPException(400, f"Cannot start task in status: {task.status.value}")
    manager.start_task(task_id)
    bg.add_task(scheduler.run_task, task)
    return _to_response(task)


@router.post("/tasks/{task_id}/pause", response_model=CrawlTaskResponse)
async def pause_task(task_id: str):
    """暂停任务"""
    task = manager.get_task(task_id)
    if task is None:
        raise HTTPException(404, f"Task not found: {task_id}")
    if task.status != CrawlerStatus.RUNNING:
        raise HTTPException(400, f"Cannot pause task in status: {task.status.value}")
    scheduler.pause_task(task_id)
    manager.pause_task(task_id)
    return _to_response(task)


@router.post("/tasks/{task_id}/resume", response_model=CrawlTaskResponse)
async def resume_task(task_id: str):
    """恢复任务"""
    task = manager.get_task(task_id)
    if task is None:
        raise HTTPException(404, f"Task not found: {task_id}")
    if task.status != CrawlerStatus.PAUSED:
        raise HTTPException(400, f"Cannot resume task in status: {task.status.value}")
    scheduler.resume_task(task_id)
    manager.resume_task(task_id)
    return _to_response(task)


@router.post("/tasks/{task_id}/cancel", response_model=CrawlTaskResponse)
async def cancel_task(task_id: str):
    """取消任务"""
    task = manager.get_task(task_id)
    if task is None:
        raise HTTPException(404, f"Task not found: {task_id}")
    if task.status not in (CrawlerStatus.RUNNING, CrawlerStatus.PAUSED, CrawlerStatus.IDLE, CrawlerStatus.POST_PROCESSING):
        raise HTTPException(400, f"Cannot cancel task in status: {task.status.value}")
    scheduler.cancel_task(task_id)
    manager.cancel_task(task_id)
    return _to_response(task)


@router.delete("/tasks/{task_id}")
async def delete_task(task_id: str):
    """删除任务"""
    task = manager.get_task(task_id)
    if task is None:
        raise HTTPException(404, f"Task not found: {task_id}")
    if task.status == CrawlerStatus.RUNNING:
        raise HTTPException(400, "Cannot delete running task. Cancel it first.")
    manager.delete_task(task_id)
    return {"message": f"Task {task_id} deleted"}


@router.get("/tasks/{task_id}/results", response_model=CrawlResultsResponse)
async def get_task_results(
    task_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """获取任务爬取结果（分页）"""
    task = manager.get_task(task_id)
    if task is None:
        raise HTTPException(404, f"Task not found: {task_id}")
    data = manager.get_task_results(task_id, page, page_size)
    items = [
        CrawlResultItem(
            job_id=r.get("job_id"),
            title=r.get("title"),
            company=r.get("company"),
            location=r.get("location"),
            salary_raw=r.get("salary_raw"),
            source=r.get("source"),
        )
        for r in data["items"]
    ]
    return CrawlResultsResponse(
        total=data["total"],
        page=data["page"],
        page_size=data["page_size"],
        items=items,
    )
