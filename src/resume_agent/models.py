from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class ResumePolishRequest(BaseModel):
    resume_text: str = Field(..., min_length=50, max_length=50000, description="简历原文")
    jd_text: Optional[str] = Field(None, max_length=20000, description="目标 JD 原文（选填，留空则用知识库分析）")
    jd_url: Optional[str] = Field(None, max_length=1000, description="JD 链接（选填）")
    target_role: Optional[str] = Field(None, max_length=200, description="目标职位名称（选填）")
    target_role_id: Optional[str] = Field(None, max_length=80, description="标准目标职位 ID（选填）")
    target_market: Optional[str] = Field(None, max_length=100, description="目标市场，如香港/中国大陆（选填）")
    application_status: Optional[str] = Field(None, max_length=40, description="投递状态：not_applied/applied/unknown（选填）")
    max_retries: int = Field(1, ge=0, le=5, description="最大重试次数")


class ResumeAnalyzeRequest(BaseModel):
    resume_text: str = Field(..., min_length=50, max_length=50000)
    jd_text: Optional[str] = Field(None, max_length=20000, description="目标 JD 原文（选填）")
    target_role: Optional[str] = Field(None, max_length=200)
    target_role_id: Optional[str] = Field(None, max_length=80)


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


class InputHealthReport(BaseModel):
    status: str = "workable"
    target_role: Optional[str] = None
    target_role_id: Optional[str] = None
    target_market: Optional[str] = None
    jd_status: str = "missing"
    resume_status: str = "provided"
    application_status: str = "unknown"
    assumptions: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    blocking_questions: list[str] = Field(default_factory=list)


class SkillStat(BaseModel):
    skill: str
    count: int = 0


class TechStackTheme(BaseModel):
    theme: str
    items: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)


class JobResearchReport(BaseModel):
    target_role: Optional[str] = None
    source: str = "knowledge_base"
    confidence: str = "low"
    sample_count: int = 0
    core_capabilities: list[str] = Field(default_factory=list)
    high_frequency_skills: list[SkillStat] = Field(default_factory=list)
    tech_stack_themes: list[TechStackTheme] = Field(default_factory=list)
    other_competencies: list[str] = Field(default_factory=list)
    common_titles: list[str] = Field(default_factory=list)
    common_responsibilities: list[str] = Field(default_factory=list)
    hidden_requirements: list[str] = Field(default_factory=list)
    similar_jobs: list[dict[str, Any]] = Field(default_factory=list)
    resume_positioning_advice: list[str] = Field(default_factory=list)
    source_coverage_note: str = ""


class BulletInventoryItem(BaseModel):
    bullet_id: str
    final_text: str
    target_capability: str = ""
    evidence_source: str = ""
    evidence_confidence: str = "medium"
    talk_track_30s: str = ""
    follow_up_questions: list[str] = Field(default_factory=list)
    risk_notes: list[str] = Field(default_factory=list)
    fallback_answer: str = ""


class ResumePolishResponse(BaseModel):
    success: bool
    polish_suggestions: list[PolishSection] = Field(default_factory=list)
    score: Optional[ScoreReport] = None
    gap_analysis: Optional[dict[str, Any]] = None
    matched_jobs: list[dict[str, Any]] = Field(default_factory=list)
    market_context: Optional[dict[str, Any]] = None
    market_insights: Optional[dict[str, Any]] = None
    target_role_understanding: Optional[dict[str, Any]] = None
    match_advice: Optional[dict[str, Any]] = None
    input_health: Optional[InputHealthReport] = None
    job_research: Optional[JobResearchReport] = None
    bullet_inventory: list[BulletInventoryItem] = Field(default_factory=list)
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
    target_role_understanding: Optional[dict[str, Any]] = None
    match_advice: Optional[dict[str, Any]] = None
    input_health: Optional[InputHealthReport] = None
    job_research: Optional[JobResearchReport] = None
    rerank_used: Optional[bool] = None
    error: Optional[str] = None


class InputHealthRequest(BaseModel):
    resume_text: str = Field("", max_length=50000, description="简历原文（选填）")
    jd_text: Optional[str] = Field(None, max_length=20000)
    target_role: Optional[str] = Field(None, max_length=200)
    target_role_id: Optional[str] = Field(None, max_length=80)
    target_market: Optional[str] = Field(None, max_length=100)
    application_status: Optional[str] = Field(None, max_length=40)


class InputHealthEndpointResponse(BaseModel):
    success: bool
    input_health: Optional[InputHealthReport] = None
    error: Optional[str] = None


class JobResearchRequest(BaseModel):
    resume_text: Optional[str] = Field(None, max_length=50000, description="简历原文（选填，用于补充检索关键词）")
    jd_text: Optional[str] = Field(None, max_length=20000)
    target_role: Optional[str] = Field(None, max_length=200)
    target_role_id: Optional[str] = Field(None, max_length=80)
    top_k: int = Field(8, ge=1, le=20)


class JobResearchEndpointResponse(BaseModel):
    success: bool
    job_research: Optional[JobResearchReport] = None
    matched_jobs: list[dict[str, Any]] = Field(default_factory=list)
    rerank_used: Optional[bool] = None
    error: Optional[str] = None


class InterviewPrepRequest(BaseModel):
    resume_text: str = Field(..., min_length=20, max_length=50000)
    polish_suggestions: list[PolishSection] = Field(..., description="润色后的逐段建议，用于生成面试讲法")
    jd_text: Optional[str] = Field(None, max_length=20000)
    target_role: Optional[str] = Field(None, max_length=200)


class InterviewPrepResponse(BaseModel):
    success: bool
    bullet_inventory: list[BulletInventoryItem] = Field(default_factory=list)
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
