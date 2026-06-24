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


class AgentState(TypedDict):
    resume_text: str
    target_jd_text: str
    target_jd_url: Optional[str]
    target_role: Optional[str]
    resume: Optional[ResumeAnalysis]
    jd: Optional[JDAnalysis]
    matched_jobs: Optional[list[dict]]
    rerank_used: Optional[bool]
    market_context: Optional[dict]
    market_insights: Optional[dict]
    gap: Optional[GapAnalysis]
    polish_suggestions: Optional[list[PolishSuggestion]]
    score: Optional[ScoreReport]
    retry_count: int
    max_retries: int
    error: Optional[str]
