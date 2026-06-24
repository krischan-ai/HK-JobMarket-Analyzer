from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class ResumePolishRequest(BaseModel):
    resume_text: str = Field(..., min_length=50, max_length=50000, description="简历原文")
    jd_text: Optional[str] = Field(None, max_length=20000, description="目标 JD 原文（选填，留空则用知识库分析）")
    jd_url: Optional[str] = Field(None, max_length=1000, description="JD 链接（选填）")
    target_role: Optional[str] = Field(None, max_length=200, description="目标职位名称（选填）")
    max_retries: int = Field(1, ge=0, le=5, description="最大重试次数")


class ResumeAnalyzeRequest(BaseModel):
    resume_text: str = Field(..., min_length=50, max_length=50000)
    jd_text: Optional[str] = Field(None, max_length=20000, description="目标 JD 原文（选填）")
    target_role: Optional[str] = Field(None, max_length=200)


class JobMatchRequest(BaseModel):
    jd_text: str = Field(..., min_length=20, max_length=20000)
    top_k: int = Field(5, ge=1, le=20)


class PolishSection(BaseModel):
    section: str
    original: str
    suggested: str
    changes: list[str] = Field(default_factory=list)
    keywords_added: list[str] = Field(default_factory=list)


class ScoreReport(BaseModel):
    overall_score: float = Field(..., ge=0, le=10)
    keyword_coverage: float = Field(..., ge=0, le=10)
    experience_alignment: float = Field(..., ge=0, le=10)
    skill_relevance: float = Field(..., ge=0, le=10)
    language_quality: float = Field(..., ge=0, le=10)
    overall_comment: str = ""
    dimension_reasons: dict[str, str] = Field(default_factory=dict)
    suggestions: list[str] = Field(default_factory=list)


class ResumePolishResponse(BaseModel):
    success: bool
    polish_suggestions: list[PolishSection] = Field(default_factory=list)
    score: Optional[ScoreReport] = None
    gap_analysis: Optional[dict[str, Any]] = None
    matched_jobs: list[dict[str, Any]] = Field(default_factory=list)
    market_context: Optional[dict[str, Any]] = None
    market_insights: Optional[dict[str, Any]] = None
    rerank_used: Optional[bool] = None
    error: Optional[str] = None


class ResumeAnalyzeResponse(BaseModel):
    success: bool
    resume: Optional[dict[str, Any]] = None
    jd: Optional[dict[str, Any]] = None
    gap_analysis: Optional[dict[str, Any]] = None
    matched_jobs: list[dict[str, Any]] = Field(default_factory=list)
    market_context: Optional[dict[str, Any]] = None
    market_insights: Optional[dict[str, Any]] = None
    rerank_used: Optional[bool] = None
    error: Optional[str] = None


class JobMatchResponse(BaseModel):
    success: bool
    matched_jobs: list[dict[str, Any]] = Field(default_factory=list)
    error: Optional[str] = None


class PdfExtractResponse(BaseModel):
    success: bool
    resume_text: str = ""
    char_count: int = 0
    error: Optional[str] = None
