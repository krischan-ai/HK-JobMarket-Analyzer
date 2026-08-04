from __future__ import annotations

from typing import Optional
from typing_extensions import TypedDict


class ResumeAnalysis(TypedDict, total=False):
    sections: dict[str, str]
    raw_skills: list[str]
    years_of_experience: Optional[float]
    education_level: Optional[str]
    current_titles: list[str]


class JDAnalysis(TypedDict, total=False):
    required_skills: list[str]
    preferred_skills: list[str]
    example_skills: list[str]          # 备选/示例技能池（e.g. 任一即可），不计入硬性缺口
    inferred_skills: list[str]         # 合理推断技能
    soft_skills: dict[str, list[str]]  # 六类软技能（学历/语言/能力/行业/认证/业务）
    cross_industry_profile: dict       # 跨行业六维（行业/场景/方案/交付/合规/系统资产）
    tag_evidence: dict[str, str]       # 标签名 → JD 原文证据
    reused_from_cache: bool            # 是否复用了统计侧治理好的标签
    responsibilities: list[str]
    min_experience: Optional[float]
    education_required: Optional[str]
    language_requirements: list[str]
    role_category: str
    role_name: str
    key_requirements: list[str]


class GapAnalysis(TypedDict, total=False):
    matched_skills: list[str]
    missing_skills: list[str]
    weak_skills: list[str]
    experience_gap: Optional[str]
    keyword_suggestions: list[dict]
    market_demand_analysis: Optional[str]
    cross_industry_alignment: Optional[str]   # 跨行业能力对齐（业务场景/交付动作/行业知识）
    emerging_suggestions: list[dict]          # 前瞻补强：高置信新兴场景候选标签


class PolishSuggestion(TypedDict, total=False):
    section: str
    original: str
    suggested: str
    changes: list[str]
    keywords_added: list[str]


class ScoreReport(TypedDict, total=False):
    overall_score: float
    keyword_coverage: float
    experience_alignment: float
    skill_relevance: float
    language_quality: float
    overall_comment: str
    dimension_reasons: dict[str, str]
    suggestions: list[str]


class SkillStat(TypedDict, total=False):
    skill: str
    count: int


class TechStackTheme(TypedDict, total=False):
    theme: str
    items: list[str]
    evidence: list[str]


class TargetRoleUnderstanding(TypedDict, total=False):
    role_id: Optional[str]
    role_name: Optional[str]
    role_summary: str
    expanded_query: str
    core_tech: list[str]
    responsibilities: list[str]


class MatchAdvice(TypedDict, total=False):
    summary: str
    suggestions: list[str]


class InputHealth(TypedDict, total=False):
    """Stage 0 输入体检：判断输入是否足够进入后续阶段。"""
    status: str                       # complete | workable | blocked
    target_role: Optional[str]
    target_role_id: Optional[str]
    target_market: Optional[str]
    jd_status: str                    # provided | partial | missing
    resume_status: str                # provided | partial | missing
    application_status: str           # not_applied | applied | unknown
    assumptions: list[str]
    gaps: list[str]
    blocking_questions: list[str]


class JobResearchReport(TypedDict, total=False):
    """Stage 1 岗位调研：把市场上下文/洞察提炼为可见的调研产物。"""
    target_role: Optional[str]
    source: str                       # jd | knowledge_base | mixed
    confidence: str                   # high | medium | low
    sample_count: int
    core_capabilities: list[str]
    high_frequency_skills: list[SkillStat]
    tech_stack_themes: list[TechStackTheme]
    other_competencies: list[str]
    common_titles: list[str]
    common_responsibilities: list[str]
    hidden_requirements: list[str]
    similar_jobs: list[dict]
    resume_positioning_advice: list[str]
    source_coverage_note: str


class ResumeBulletInventory(TypedDict, total=False):
    """Stage 8 面试深挖：把最终简历 bullet 转为可被追问的讲法。"""
    bullet_id: str
    final_text: str
    target_capability: str
    evidence_source: str
    evidence_confidence: str          # strong | medium | weak | risky
    talk_track_30s: str
    follow_up_questions: list[str]
    risk_notes: list[str]
    fallback_answer: str


class AgentState(TypedDict):
    resume_text: str
    target_jd_text: str
    target_jd_url: Optional[str]
    target_role: Optional[str]
    target_role_id: Optional[str]
    target_role_understanding: Optional[TargetRoleUnderstanding]
    match_advice: Optional[MatchAdvice]
    target_market: Optional[str]
    application_status: Optional[str]
    resume: Optional[ResumeAnalysis]
    jd: Optional[JDAnalysis]
    matched_jobs: Optional[list[dict]]
    rerank_used: Optional[bool]
    market_context: Optional[dict]
    market_insights: Optional[dict]
    tech_stack_summary: Optional[dict]
    input_health: Optional[InputHealth]
    job_research: Optional[JobResearchReport]
    gap: Optional[GapAnalysis]
    polish_suggestions: Optional[list[PolishSuggestion]]
    bullet_inventory: Optional[list[ResumeBulletInventory]]
    score: Optional[ScoreReport]
    retry_count: int
    max_retries: int
    error: Optional[str]
