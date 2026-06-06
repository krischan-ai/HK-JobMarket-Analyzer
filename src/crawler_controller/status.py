from __future__ import annotations

from enum import Enum
from typing import Optional


class CrawlerStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    POST_PROCESSING = "post_processing"
    PROCESSED = "processed"
    PROCESSING_FAILED = "processing_failed"
    FAILED = "failed"
    CANCELLED = "cancelled"


_TRANSITIONS: dict[CrawlerStatus, list[CrawlerStatus]] = {
    CrawlerStatus.IDLE: [CrawlerStatus.RUNNING],
    CrawlerStatus.RUNNING: [CrawlerStatus.PAUSED, CrawlerStatus.COMPLETED, CrawlerStatus.FAILED, CrawlerStatus.CANCELLED],
    CrawlerStatus.PAUSED: [CrawlerStatus.RUNNING, CrawlerStatus.CANCELLED],
    CrawlerStatus.COMPLETED: [CrawlerStatus.POST_PROCESSING],
    CrawlerStatus.POST_PROCESSING: [CrawlerStatus.PROCESSED, CrawlerStatus.PROCESSING_FAILED, CrawlerStatus.CANCELLED],
    CrawlerStatus.PROCESSED: [],
    CrawlerStatus.PROCESSING_FAILED: [],
    CrawlerStatus.FAILED: [],
    CrawlerStatus.CANCELLED: [],
}

_TERMINAL = {CrawlerStatus.PROCESSED, CrawlerStatus.PROCESSING_FAILED, CrawlerStatus.FAILED, CrawlerStatus.CANCELLED}


class StateMachine:
    """爬虫任务状态机，确保状态转换合法性"""

    @staticmethod
    def can_transition(current: CrawlerStatus, target: CrawlerStatus) -> bool:
        return target in _TRANSITIONS.get(current, [])

    @staticmethod
    def transition(current: CrawlerStatus, target: CrawlerStatus) -> CrawlerStatus:
        if not StateMachine.can_transition(current, target):
            raise ValueError(f"Invalid transition: {current.value} → {target.value}")
        return target

    @staticmethod
    def is_terminal(status: CrawlerStatus) -> bool:
        return status in _TERMINAL

    @staticmethod
    def label(status: CrawlerStatus) -> str:
        labels = {
            CrawlerStatus.IDLE: "待開始",
            CrawlerStatus.RUNNING: "運行中",
            CrawlerStatus.PAUSED: "已暫停",
            CrawlerStatus.COMPLETED: "採集完成",
            CrawlerStatus.POST_PROCESSING: "後處理中",
            CrawlerStatus.PROCESSED: "已處理完成",
            CrawlerStatus.PROCESSING_FAILED: "後處理失敗",
            CrawlerStatus.FAILED: "失敗",
            CrawlerStatus.CANCELLED: "已取消",
        }
        return labels.get(status, status.value)
