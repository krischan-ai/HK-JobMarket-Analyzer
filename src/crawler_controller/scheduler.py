from __future__ import annotations

import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from src.crawler_controller.status import CrawlerStatus, StateMachine
from src.crawler_controller.task_manager import CrawlerTask, TaskManager
from src.crawler_controller.post_pipeline import PostCrawlPipeline, PostProcessConfig
from src.crawlers import get_crawler, list_sources
from src.logger import get_logger


class CrawlerScheduler:
    """异步爬虫任务调度器"""

    def __init__(self, manager: Optional[TaskManager] = None, max_workers: int = 3):
        self.manager = manager or TaskManager()
        self.logger = get_logger(self.__class__.__name__)
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._running_tasks: dict[str, threading.Event] = {}  # task_id → cancel event
        self._pause_events: dict[str, threading.Event] = {}  # task_id → pause event

    async def run_task(self, task: CrawlerTask):
        """异步启动爬虫任务执行"""
        cancel_event = threading.Event()
        pause_event = threading.Event()
        self._running_tasks[task.task_id] = cancel_event
        self._pause_events[task.task_id] = pause_event

        loop = asyncio.get_running_loop()
        results: list[dict] = []

        try:
            for source in task.sources:
                if cancel_event.is_set() or task.status == CrawlerStatus.CANCELLED:
                    break
                if pause_event.is_set():
                    task.add_log("info", f"來源 [{source}] 等待恢復...")
                    while pause_event.is_set() and not cancel_event.is_set():
                        await asyncio.sleep(0.5)
                    if cancel_event.is_set():
                        break
                    task.add_log("info", f"來源 [{source}] 已恢復")

                task.add_log("info", f"開始爬取來源: {source}")
                task.update_progress(source, 0, 0)

                try:
                    crawler = get_crawler(source)
                except ValueError:
                    task.add_log("warning", f"未知來源: {source}，已跳過")
                    continue

                for keyword in task.keywords:
                    if cancel_event.is_set():
                        break
                    if pause_event.is_set():
                        while pause_event.is_set() and not cancel_event.is_set():
                            await asyncio.sleep(0.5)
                        if cancel_event.is_set():
                            break

                    try:
                        jobs = await loop.run_in_executor(
                            self._executor, crawler.run, keyword, 3
                        )
                        results.extend(jobs)
                        task.add_log("info", f"[{source}] 關鍵詞 [{keyword}] 採集 {len(jobs)} 條")
                    except Exception as e:
                        task.add_log("error", f"[{source}] 關鍵詞 [{keyword}] 失敗: {e}")

                task.update_progress(source, sum(1 for r in results if r.get("_source") == source), len(results))

            if cancel_event.is_set():
                if task.status != CrawlerStatus.CANCELLED:
                    self.manager.cancel_task(task.task_id)
            else:
                self.manager.complete_task(task.task_id, results)
                # 采集成功后自动触发后处理管线
                if results:
                    await self._run_post_processing(task)

        except Exception as e:
            self.logger.exception("Task %s failed: %s", task.task_id, e)
            self.manager.fail_task(task.task_id, str(e))

        finally:
            self._running_tasks.pop(task.task_id, None)
            self._pause_events.pop(task.task_id, None)

    async def _run_post_processing(self, task: CrawlerTask):
        """在采集完成后执行后处理管线（清洗 → 分类 → 知识库导入）"""
        self.manager.start_post_processing(task.task_id)
        cancel_event = self._running_tasks.get(task.task_id)

        def on_progress(phase: str, pct: float):
            self.manager.update_post_progress(task.task_id, phase, pct)
            phase_labels = {
                "cleaning": "清洗",
                "extraction": "技能提取",
                "classification": "角色分類",
                "kb_import": "知識庫導入",
                "vector_index": "向量索引",
            }
            label = phase_labels.get(phase, phase)
            task.add_log("info", f"[後處理] {label} {pct}%")

        pipeline = PostCrawlPipeline(on_progress=on_progress)
        config = PostProcessConfig.from_dict(task.post_config)

        loop = asyncio.get_running_loop()
        try:
            # 检查是否已被取消
            if cancel_event and cancel_event.is_set():
                pipeline.cancel()

            result = await loop.run_in_executor(
                None, pipeline.run, task.results, config
            )
            # 执行过程中被取消
            if cancel_event and cancel_event.is_set():
                if task.status == CrawlerStatus.POST_PROCESSING:
                    self.manager.cancel_task(task.task_id)
                return

            result_dict = result.to_dict()
            if result.errors and config.fail_on_error:
                self.manager.fail_post_processing(task.task_id, result.errors)
            else:
                self.manager.complete_post_processing(task.task_id, result_dict)
        except Exception as e:
            self.logger.exception("Post-processing failed for task %s: %s", task.task_id, e)
            self.manager.fail_post_processing(task.task_id, [str(e)])

    def cancel_task(self, task_id: str):
        event = self._running_tasks.get(task_id)
        if event:
            event.set()

    def pause_task(self, task_id: str):
        event = self._pause_events.get(task_id)
        if event:
            event.set()

    def resume_task(self, task_id: str):
        event = self._pause_events.get(task_id)
        if event:
            event.clear()
