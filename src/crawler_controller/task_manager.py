from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone
from typing import Optional

from src.crawler_controller.status import CrawlerStatus, StateMachine
from src.logger import get_logger


class CrawlerTask:
    """单个爬虫任务"""

    def __init__(self, keywords: list[str], sources: list[str]):
        self.task_id = uuid.uuid4().hex[:12]
        self.keywords = keywords
        self.sources = sources
        self.status = CrawlerStatus.IDLE
        self.progress = 0.0
        self.total_jobs = 0
        self.source_progress: dict[str, dict] = {}  # source → {total, collected}
        self.logs: list[dict] = []  # [{time, level, message}]
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.completed_at: Optional[str] = None
        self.results: list[dict] = []
        # 后处理字段
        self.post_config: dict = {
            "run_cleaning": True,
            "run_extraction": True,
            "run_classification": True,
            "run_kb_import": True,
            "run_vector_index": True,
            "fail_on_error": False,
        }
        self.post_phase: str = ""           # 当前后处理阶段
        self.post_phase_pct: float = 0.0    # 当前阶段内部进度 0-100
        self.post_result: Optional[dict] = None  # 后处理完成后的结果摘要

    def add_log(self, level: str, message: str):
        self.logs.append({
            "time": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "message": message,
        })
        if len(self.logs) > 500:
            self.logs = self.logs[-300:]

    def set_status(self, new_status: CrawlerStatus):
        self.status = StateMachine.transition(self.status, new_status)
        if StateMachine.is_terminal(new_status):
            self.completed_at = datetime.now(timezone.utc).isoformat()

    def update_progress(self, source: str, collected: int, total: int):
        self.source_progress[source] = {"total": total, "collected": collected}
        self._recalc_progress()

    def _recalc_progress(self):
        totals = sum(s.get("total", 0) for s in self.source_progress.values())
        collected = sum(s.get("collected", 0) for s in self.source_progress.values())
        if totals > 0:
            self.progress = min(round(collected / totals * 100, 1), 100.0)
        self.total_jobs = collected

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "keywords": self.keywords,
            "sources": self.sources,
            "status": self.status.value,
            "status_label": StateMachine.label(self.status),
            "progress": self.progress,
            "total_jobs": self.total_jobs,
            "source_progress": self.source_progress,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "post_config": self.post_config,
            "post_phase": self.post_phase,
            "post_phase_pct": self.post_phase_pct,
            "post_result": self.post_result,
        }


class TaskManager:
    """爬虫任务管理器（线程安全单例）"""

    _instance: Optional[TaskManager] = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._tasks: dict[str, CrawlerTask] = {}
        self.logger = get_logger(self.__class__.__name__)
        self._initialized = True

    def create_task(self, keywords: list[str], sources: list[str]) -> CrawlerTask:
        task = CrawlerTask(keywords, sources)
        with self._lock:
            self._tasks[task.task_id] = task
        task.add_log("info", f"任務創建: 關鍵詞={keywords}, 來源={sources}")
        self.logger.info("Task created: %s", task.task_id)
        return task

    def get_task(self, task_id: str) -> Optional[CrawlerTask]:
        return self._tasks.get(task_id)

    def list_tasks(self, status: Optional[str] = None) -> list[CrawlerTask]:
        tasks = list(self._tasks.values())
        if status:
            tasks = [t for t in tasks if t.status.value == status]
        return sorted(tasks, key=lambda t: t.created_at, reverse=True)

    def start_task(self, task_id: str) -> CrawlerTask:
        task = self._get_or_raise(task_id)
        task.set_status(CrawlerStatus.RUNNING)
        task.add_log("info", "任務開始執行")
        return task

    def pause_task(self, task_id: str) -> CrawlerTask:
        task = self._get_or_raise(task_id)
        task.set_status(CrawlerStatus.PAUSED)
        task.add_log("info", "任務已暫停")
        return task

    def resume_task(self, task_id: str) -> CrawlerTask:
        task = self._get_or_raise(task_id)
        task.set_status(CrawlerStatus.RUNNING)
        task.add_log("info", "任務已恢復")
        return task

    def cancel_task(self, task_id: str) -> CrawlerTask:
        task = self._get_or_raise(task_id)
        target = CrawlerStatus.CANCELLED
        if not StateMachine.can_transition(task.status, target):
            raise ValueError(f"Cannot cancel task in status: {task.status.value}")
        task.set_status(target)
        task.add_log("info", "任務已取消")
        return task

    def complete_task(self, task_id: str, results: list[dict]):
        task = self._get_or_raise(task_id)
        task.results = results
        task.set_status(CrawlerStatus.COMPLETED)
        task.add_log("info", f"任務完成: 共採集 {len(results)} 條數據")

    def fail_task(self, task_id: str, error: str):
        task = self._get_or_raise(task_id)
        task.set_status(CrawlerStatus.FAILED)
        task.add_log("error", f"任務失敗: {error}")

    def start_post_processing(self, task_id: str):
        task = self._get_or_raise(task_id)
        task.set_status(CrawlerStatus.POST_PROCESSING)
        task.post_phase = ""
        task.post_phase_pct = 0
        task.add_log("info", "採集完成，開始後處理管線（清洗 → 分類 → 導入知識庫）")

    def update_post_progress(self, task_id: str, phase: str, pct: float):
        task = self._get_or_raise(task_id)
        task.post_phase = phase
        task.post_phase_pct = pct

    def complete_post_processing(self, task_id: str, result: dict):
        task = self._get_or_raise(task_id)
        task.post_result = result
        task.post_phase = "done"
        task.post_phase_pct = 100
        task.set_status(CrawlerStatus.PROCESSED)
        task.add_log("info",
            f"後處理完成: 清洗={result.get('cleaned_count',0)}, "
            f"分類={result.get('classified_count',0)}, "
            f"MongoDB={result.get('db_inserted',0)}, "
            f"CSV={result.get('csv_exported',0)}, "
            f"向量={result.get('vector_indexed',0)}"
        )

    def fail_post_processing(self, task_id: str, errors: list[str]):
        task = self._get_or_raise(task_id)
        task.set_status(CrawlerStatus.PROCESSING_FAILED)
        task.post_result = {"errors": errors}
        for err in errors:
            task.add_log("error", f"後處理失敗: {err}")

    def delete_task(self, task_id: str):
        with self._lock:
            self._tasks.pop(task_id, None)
        self.logger.info("Task deleted: %s", task_id)

    def get_task_results(self, task_id: str, page: int = 1, page_size: int = 20) -> dict:
        task = self._get_or_raise(task_id)
        total = len(task.results)
        start = (page - 1) * page_size
        end = start + page_size
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": task.results[start:end],
        }

    def _get_or_raise(self, task_id: str) -> CrawlerTask:
        task = self._tasks.get(task_id)
        if task is None:
            raise ValueError(f"Task not found: {task_id}")
        return task
