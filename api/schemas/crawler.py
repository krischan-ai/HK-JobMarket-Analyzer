from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class PostProcessConfigDTO(BaseModel):
    run_cleaning: bool = Field(default=True, description="是否執行數據清洗")
    run_extraction: bool = Field(default=True, description="是否執行技能提取")
    run_classification: bool = Field(default=True, description="是否執行角色分類")
    run_kb_import: bool = Field(default=True, description="是否導入知識庫(MongoDB+CSV)")
    run_vector_index: bool = Field(default=True, description="是否更新向量索引")
    fail_on_error: bool = Field(default=False, description="任一階段失敗是否中止")


class CrawlTaskCreate(BaseModel):
    keywords: list[str] = Field(..., min_length=1, description="爬取關鍵詞列表")
    sources: list[str] = Field(..., min_length=1, description="爬取來源列表")
    post_config: Optional[PostProcessConfigDTO] = Field(default=None, description="後處理配置，不填使用全部啟用的默認值")


class CrawlTaskResponse(BaseModel):
    task_id: str
    keywords: list[str]
    sources: list[str]
    status: str
    status_label: str
    progress: float
    total_jobs: int
    source_progress: dict[str, dict] = {}
    created_at: str
    completed_at: Optional[str] = None
    post_config: dict = {}
    post_phase: str = ""
    post_phase_pct: float = 0.0
    post_result: Optional[dict] = None


class CrawlTaskListResponse(BaseModel):
    total: int
    items: list[CrawlTaskResponse]


class CrawlTaskDetailResponse(CrawlTaskResponse):
    logs: list[dict] = []


class CrawlResultItem(BaseModel):
    job_id: Optional[str] = None
    title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    salary_raw: Optional[str] = None
    source: Optional[str] = None


class CrawlResultsResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[CrawlResultItem]
