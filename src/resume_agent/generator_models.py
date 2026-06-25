from __future__ import annotations

from typing import Any, Literal, Optional, TypedDict

from pydantic import BaseModel, Field


Language = Literal["en", "zh-Hant", "zh-Hans"]
EvidenceConfidence = Literal["strong", "medium", "weak", "risky"]


class ResumeGenerateRequest(BaseModel):
    resume_text: str = Field(..., min_length=1, max_length=50000)
    target_role: str = Field(..., min_length=2, max_length=200)
    target_role_id: Optional[str] = Field(None, max_length=80)
    target_market: Optional[str] = Field("Hong Kong", max_length=100)
    language: Language = "en"
    style: Literal["professional", "technical", "management"] = "professional"
    narrative_angle: Optional[str] = Field(None, max_length=200)
    top_k_jobs: int = Field(8, ge=1, le=20)
    profile_context: Optional[dict[str, Any]] = None
    project_context: list[dict[str, Any]] = Field(default_factory=list)
    auto_continue_without_confirmation: bool = True


class InputHealthReport(BaseModel):
    status: Literal["complete", "workable", "blocked"] = "workable"
    resume_status: Literal["provided", "partial", "missing"] = "provided"
    target_status: Literal["provided", "missing"] = "provided"
    assumptions: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    blocking_questions: list[str] = Field(default_factory=list)


class ExperienceItem(BaseModel):
    id: str
    company: str = ""
    title: str = ""
    start_date: str = ""
    end_date: str = ""
    location: str = ""
    description: str = ""
    bullets: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    evidence_text: str = ""


class ProjectItem(BaseModel):
    id: str
    name: str = ""
    role: str = ""
    period: str = ""
    description: str = ""
    bullets: list[str] = Field(default_factory=list)
    tech_stack: list[str] = Field(default_factory=list)
    evidence_text: str = ""


class EducationItem(BaseModel):
    id: str
    school: str = ""
    degree: str = ""
    major: str = ""
    period: str = ""
    evidence_text: str = ""


class ResumeProfile(BaseModel):
    contact: dict[str, str] = Field(default_factory=dict)
    current_titles: list[str] = Field(default_factory=list)
    target_preferences: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    work_experience: list[ExperienceItem] = Field(default_factory=list)
    projects: list[ProjectItem] = Field(default_factory=list)
    education: list[EducationItem] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    evidence_snippets: list[str] = Field(default_factory=list)


class SkillStat(BaseModel):
    skill: str
    count: int = 0


class TargetJobProfile(BaseModel):
    target_role: str
    source: Literal["knowledge_base", "jd", "mixed"] = "knowledge_base"
    confidence: Literal["high", "medium", "low"] = "medium"
    sample_count: int = 0
    core_capabilities: list[str] = Field(default_factory=list)
    high_frequency_skills: list[SkillStat] = Field(default_factory=list)
    tech_stack: list[dict[str, Any]] = Field(default_factory=list)
    common_titles: list[str] = Field(default_factory=list)
    common_responsibilities: list[str] = Field(default_factory=list)
    hidden_requirements: list[str] = Field(default_factory=list)
    similar_jobs: list[dict[str, Any]] = Field(default_factory=list)
    source_coverage_note: str = ""


class CapabilityMatch(BaseModel):
    capability: str
    job_basis: str = ""
    matched_sources: list[str] = Field(default_factory=list)
    evidence_strength: Literal["strong", "medium", "weak", "missing"] = "missing"
    resume_angle: str = ""
    risk_note: str = ""


class SelectedExperience(BaseModel):
    source_type: Literal["work", "project", "education", "skill", "knowledge_base"]
    source_id: str
    source_title: str = ""
    target_capability: str
    evidence_text: str
    selection_reason: str
    evidence_confidence: EvidenceConfidence


class SelectedExperiencePlan(BaseModel):
    selected: list[SelectedExperience] = Field(default_factory=list)
    excluded: list[dict[str, str]] = Field(default_factory=list)
    selection_summary: str = ""
    user_confirmation_required: list[str] = Field(default_factory=list)


class GeneratedBullet(BaseModel):
    bullet_id: str
    text: str
    evidence_id: str = ""
    target_capability: str = ""
    interview_risk: Literal["low", "medium", "high"] = "medium"


class GeneratedExperience(BaseModel):
    company: str = ""
    title: str = ""
    start_date: str = ""
    end_date: str = ""
    location: str = ""
    bullets: list[GeneratedBullet] = Field(default_factory=list)


class GeneratedProject(BaseModel):
    name: str = ""
    role: str = ""
    period: str = ""
    bullets: list[GeneratedBullet] = Field(default_factory=list)


class GeneratedEducation(BaseModel):
    school: str = ""
    degree: str = ""
    major: str = ""
    period: str = ""


class GeneratedResume(BaseModel):
    language: Language
    headline: str
    positioning_statement: str
    summary: str
    skills: list[str] = Field(default_factory=list)
    work_experience: list[GeneratedExperience] = Field(default_factory=list)
    projects: list[GeneratedProject] = Field(default_factory=list)
    education: list[GeneratedEducation] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)


class ClaimEvidence(BaseModel):
    claim: str
    claim_type: Literal["number", "role", "skill", "achievement", "education", "company", "time", "other"]
    source: Literal["resume", "selected_experience", "knowledge_base", "inferred", "user_confirmed"]
    confidence: EvidenceConfidence
    action: Literal["keep", "soften", "remove", "ask_user"]
    reason: str = ""
    suggested_revision: str = ""


class QualityGateResult(BaseModel):
    status: Literal["pass", "pass_with_gaps", "blocked"]
    p0_violations: list[str] = Field(default_factory=list)
    p1_gaps: list[str] = Field(default_factory=list)
    suggested_fixes: list[str] = Field(default_factory=list)


class ResumeGenerateResponse(BaseModel):
    success: bool
    generated_resume: Optional[GeneratedResume] = None
    markdown: str = ""
    target_job_profile: Optional[TargetJobProfile] = None
    capability_matches: list[CapabilityMatch] = Field(default_factory=list)
    selected_experience_plan: Optional[SelectedExperiencePlan] = None
    selected_experience: list[SelectedExperience] = Field(default_factory=list)
    claim_audit: list[ClaimEvidence] = Field(default_factory=list)
    quality_gate: Optional[QualityGateResult] = None
    similar_jobs: list[dict[str, Any]] = Field(default_factory=list)
    input_health: Optional[InputHealthReport] = None
    confidence: Literal["high", "medium", "low"] = "medium"
    error: Optional[str] = None


class ResumeGenerationState(TypedDict, total=False):
    resume_text: str
    target_role: str
    target_role_id: Optional[str]
    target_market: Optional[str]
    language: Language
    style: str
    narrative_angle: Optional[str]
    top_k_jobs: int
    profile_context: Optional[dict[str, Any]]
    project_context: list[dict[str, Any]]
    auto_continue_without_confirmation: bool
    input_health: dict[str, Any]
    resume_profile: dict[str, Any]
    target_job_profile: dict[str, Any]
    capability_matches: list[dict[str, Any]]
    selected_experience_plan: dict[str, Any]
    selected_experience: list[dict[str, Any]]
    generated_resume: dict[str, Any]
    claim_audit: list[dict[str, Any]]
    quality_gate: dict[str, Any]
    markdown: str
    similar_jobs: list[dict[str, Any]]
    confidence: str
    error: Optional[str]
