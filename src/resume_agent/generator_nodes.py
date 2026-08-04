from __future__ import annotations

import re
from typing import Any

from src.logger import get_logger

from .generator_models import (
    CapabilityMatch,
    ClaimEvidence,
    EducationItem,
    ExperienceItem,
    GeneratedBullet,
    GeneratedEducation,
    GeneratedExperience,
    GeneratedProject,
    GeneratedResume,
    InputHealthReport,
    ProjectItem,
    QualityGateResult,
    ResumeGenerationState,
    ResumeProfile,
    SelectedExperience,
    SelectedExperiencePlan,
    SkillStat,
    TargetJobProfile,
)
from .generator_prompts import (
    CAPABILITY_MATCH_PROMPT,
    CAPABILITY_MATCH_SYSTEM_PROMPT,
    CLAIM_AUDIT_PROMPT,
    CLAIM_AUDIT_SYSTEM_PROMPT,
    EXPERIENCE_SELECTION_PROMPT,
    EXPERIENCE_SELECTION_SYSTEM_PROMPT,
    PROFILE_PARSE_PROMPT,
    PROFILE_PARSE_SYSTEM_PROMPT,
    RESUME_GENERATION_PROMPT,
    RESUME_GENERATION_SYSTEM_PROMPT,
    TARGET_PROFILE_UNDERSTANDING_PROMPT,
    TARGET_PROFILE_UNDERSTANDING_SYSTEM_PROMPT,
    TARGET_RESPONSIBILITY_SUMMARY_PROMPT,
    TARGET_RESPONSIBILITY_SUMMARY_SYSTEM_PROMPT,
    as_json,
)
from .llm import ResumeLLMClient
from .nodes import (
    build_job_research,
    build_market_context,
    build_market_insights,
    conceptualize_market_insights,
    llm_match_jobs,
    match_jobs,
    summarize_tech_stack,
    synthesize_market_jd,
    understand_target_role,
)
from .utils import ResumeAgentError, compact_text, ensure_list, extract_json_objects, parse_llm_json

logger = get_logger(__name__)

INTERNAL_LABELS = ("迁移句", "迁移说明", "可迁移性", "旧版", "半成品", "draft", "old version", "half-finished")


def _text(value: Any) -> str:
    return str(value or "").strip()


def _strings(value: Any, limit: int | None = None) -> list[str]:
    items = [_text(item) for item in ensure_list(value) if _text(item)]
    return items[:limit] if limit is not None else items


def check_generation_input(state: ResumeGenerationState) -> dict[str, Any]:
    resume_len = len(_text(state.get("resume_text")))
    target_role = _text(state.get("target_role"))
    assumptions: list[str] = []
    gaps: list[str] = []
    blocking_questions: list[str] = []

    if resume_len >= 200:
        resume_status = "provided"
    elif resume_len >= 10:
        resume_status = "partial"
        gaps.append("简历内容偏少，将基于知识库岗位画像补充技能和项目经历，生成内容需用户核实并补充真实经历。")
    else:
        resume_status = "partial"
        gaps.append("简历内容极少，将大量依赖知识库岗位画像生成技能和项目经历，生成内容需用户仔细核实并补充真实经历。")

    target_status = "provided" if target_role else "missing"
    if target_status == "missing":
        blocking_questions.append("请提供目标岗位名称。")
    if not _text(state.get("target_market")):
        assumptions.append("未指定目标市场，默认按 Hong Kong IT 市场生成。")
    if state.get("profile_context") or state.get("project_context"):
        assumptions.append("本次使用临时 profile/project context，但不会持久化保存。")

    status = "blocked" if blocking_questions else ("complete" if resume_status == "provided" else "workable")
    health = InputHealthReport(
        status=status,
        resume_status=resume_status,  # type: ignore[arg-type]
        target_status=target_status,  # type: ignore[arg-type]
        assumptions=assumptions,
        gaps=gaps,
        blocking_questions=blocking_questions,
    )
    return {"input_health": health.model_dump()}


def _normalise_profile(raw: Any, state: ResumeGenerationState) -> ResumeProfile:
    if not isinstance(raw, dict):
        raw = {}

    work_items: list[ExperienceItem] = []
    for idx, item in enumerate(ensure_list(raw.get("work_experience")), start=1):
        if not isinstance(item, dict):
            continue
        evidence = _text(item.get("evidence_text")) or "\n".join(_strings(item.get("bullets"), 5)) or _text(item.get("description"))
        work_items.append(ExperienceItem(
            id=_text(item.get("id")) or f"work_{idx}",
            company=_text(item.get("company")),
            title=_text(item.get("title")),
            start_date=_text(item.get("start_date")),
            end_date=_text(item.get("end_date")),
            location=_text(item.get("location")),
            description=_text(item.get("description")),
            bullets=_strings(item.get("bullets")),
            skills=_strings(item.get("skills")),
            evidence_text=evidence,
        ))

    project_items: list[ProjectItem] = []
    for idx, item in enumerate(ensure_list(raw.get("projects")), start=1):
        if not isinstance(item, dict):
            continue
        evidence = _text(item.get("evidence_text")) or "\n".join(_strings(item.get("bullets"), 5)) or _text(item.get("description"))
        project_items.append(ProjectItem(
            id=_text(item.get("id")) or f"project_{idx}",
            name=_text(item.get("name")) or _text(item.get("title")),
            role=_text(item.get("role")),
            period=_text(item.get("period")),
            description=_text(item.get("description")),
            bullets=_strings(item.get("bullets")),
            tech_stack=_strings(item.get("tech_stack") or item.get("skills")),
            evidence_text=evidence,
        ))

    education_items: list[EducationItem] = []
    for idx, item in enumerate(ensure_list(raw.get("education")), start=1):
        if not isinstance(item, dict):
            continue
        education_items.append(EducationItem(
            id=_text(item.get("id")) or f"education_{idx}",
            school=_text(item.get("school")),
            degree=_text(item.get("degree")),
            major=_text(item.get("major")),
            period=_text(item.get("period")),
            evidence_text=_text(item.get("evidence_text")),
        ))

    # If the model cannot parse sections, keep a minimal evidence source so the flow stays inspectable.
    if not work_items and not project_items:
        work_items.append(ExperienceItem(
            id="work_1",
            title="Candidate experience",
            description=compact_text(state.get("resume_text") or "", 1200),
            evidence_text=compact_text(state.get("resume_text") or "", 1200),
        ))

    contact = raw.get("contact") if isinstance(raw.get("contact"), dict) else {}
    return ResumeProfile(
        contact={str(k): _text(v) for k, v in contact.items() if _text(v)},
        current_titles=_strings(raw.get("current_titles")),
        target_preferences=_strings(raw.get("target_preferences")),
        skills=_strings(raw.get("skills") or raw.get("raw_skills")),
        work_experience=work_items,
        projects=project_items,
        education=education_items,
        certifications=_strings(raw.get("certifications")),
        evidence_snippets=_strings(raw.get("evidence_snippets"), 20),
    )


def parse_resume_profile(state: ResumeGenerationState, llm: ResumeLLMClient) -> dict[str, Any]:
    try:
        content = llm.chat_json(
            PROFILE_PARSE_SYSTEM_PROMPT,
            PROFILE_PARSE_PROMPT.format(
                resume_text=compact_text(state.get("resume_text") or "", 16000),
                profile_context=as_json(state.get("profile_context") or {}),
                project_context=as_json(state.get("project_context") or []),
            ),
            temperature=0.1,
            max_tokens=8192,
        )
        parsed = parse_llm_json(content)
    except Exception as exc:
        logger.warning("Profile parse fallback used: %s", exc)
        parsed = _fallback_profile_from_text(state.get("resume_text") or "")
    profile = _normalise_profile(parsed, state)
    return {"resume_profile": profile.model_dump()}


def _fallback_profile_from_text(text: str) -> dict[str, Any]:
    email = ""
    phone = ""
    email_match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text or "")
    if email_match:
        email = email_match.group(0)
    phone_match = re.search(r"(?:\+?852[-\s]?)?[0-9]{4}[-\s]?[0-9]{4}", text or "")
    if phone_match:
        phone = phone_match.group(0)

    common_skills = [
        "Python", "Java", "JavaScript", "TypeScript", "React", "Vue", "FastAPI", "Django",
        "Flask", "SQL", "MySQL", "PostgreSQL", "MongoDB", "Redis", "Docker", "Kubernetes",
        "AWS", "Azure", "GCP", "Machine Learning", "TensorFlow", "PyTorch", "LLM", "RAG",
        "LangChain", "REST API", "Git", "CI/CD",
    ]
    lower = (text or "").lower()
    skills = [skill for skill in common_skills if skill.lower() in lower]
    snippet = compact_text(text, 1800)
    return {
        "contact": {"email": email, "phone": phone},
        "current_titles": [],
        "skills": skills,
        "work_experience": [
            {
                "id": "work_1",
                "title": "Candidate experience",
                "description": snippet,
                "bullets": [snippet],
                "skills": skills,
                "evidence_text": snippet,
            }
        ],
        "projects": [],
        "education": [],
        "certifications": [],
        "evidence_snippets": [snippet],
    }


def _profile_as_legacy_resume(profile: dict[str, Any]) -> dict[str, Any]:
    return {
        "sections": {
            "工作经验": "\n".join(_text(item.get("evidence_text")) for item in profile.get("work_experience") or []),
            "项目经历": "\n".join(_text(item.get("evidence_text")) for item in profile.get("projects") or []),
            "技能": ", ".join(profile.get("skills") or []),
            "教育": "\n".join(
                " ".join(_text(item.get(k)) for k in ("school", "degree", "major", "period"))
                for item in profile.get("education") or []
            ),
        },
        "raw_skills": profile.get("skills") or [],
        "current_titles": profile.get("current_titles") or [],
    }


def build_target_job_profile(state: ResumeGenerationState, llm: ResumeLLMClient) -> dict[str, Any]:
    """Build a target profile from local retrieval + LLM semantic understanding.

    Uses HybridJobSearch to recall similar jobs, then asks LLM to understand
    core capabilities, high-frequency skills, tech stack and hidden requirements
    from the matched JD samples — not mechanical counting.
    """
    legacy: dict[str, Any] = {
        "resume_text": state.get("resume_text") or "",
        "target_jd_text": "",
        "target_role": state.get("target_role"),
        "target_role_id": state.get("target_role_id"),
        "target_market": state.get("target_market") or "Hong Kong",
        "resume": _profile_as_legacy_resume(state.get("resume_profile") or {}),
        "matched_jobs": None,
        "rerank_used": None,
        "market_context": None,
    }
    legacy["target_role_understanding"] = {
        "role_name": state.get("target_role") or "",
        "expanded_query": state.get("target_role") or "",
        "core_tech": [],
        "responsibilities": [],
    }
    legacy.update(match_jobs(legacy, top_k=int(state.get("top_k_jobs") or 8)))
    legacy.update(build_market_context(legacy))

    matched = legacy.get("matched_jobs") or []
    context = legacy.get("market_context") or {}
    deterministic_skills = [
        SkillStat(skill=_text(item.get("skill")), count=int(item.get("count") or 0))
        for item in ensure_list(context.get("top_skills"))
        if isinstance(item, dict) and _text(item.get("skill"))
    ]
    target_role = _text(state.get("target_role"))

    # LLM semantic understanding of core capabilities, skills, tech stack
    understanding = _understand_target_profile(
        target_role=target_role,
        narrative_angle=state.get("narrative_angle") or "",
        matched_jobs=matched,
        deterministic_stats={"top_skills": [s.model_dump() for s in deterministic_skills[:15]]},
        llm=llm,
    )
    core = understanding.get("core_capabilities") or []
    high_freq = understanding.get("high_frequency_skills") or []
    tech_stack = understanding.get("tech_stack") or []
    hidden = understanding.get("hidden_requirements") or []

    # Fallback: if LLM understanding failed, use deterministic stats
    if not core:
        core = [target_role] if target_role else ["Target role delivery"]
        core.extend(s.skill for s in deterministic_skills[:4])
    if not high_freq:
        high_freq = deterministic_skills[:15]
    if not hidden:
        hidden = []

    responsibilities = summarize_target_responsibilities(
        target_role=target_role,
        matched_jobs=matched,
        skills=[s.get("skill", "") for s in high_freq[:12]] if high_freq else [s.skill for s in deterministic_skills[:12]],
        llm=llm,
    )
    confidence = "medium" if len(matched) >= 2 else ("low" if matched else "low")
    note = (
        f"基于知识库召回的 {len(matched)} 条香港相似岗位，经 LLM 语义理解生成市场画像。"
        if matched
        else "知识库未召回相似岗位，岗位画像仅基于目标岗位名称，置信度较低。"
    )
    profile = TargetJobProfile(
        target_role=target_role,
        source="knowledge_base",
        confidence=confidence,  # type: ignore[arg-type]
        sample_count=len(matched),
        core_capabilities=list(dict.fromkeys(core))[:6],
        high_frequency_skills=[
            SkillStat(skill=_text(s.get("skill")), count=int(s.get("count") or 0))
            for s in high_freq
            if isinstance(s, dict) and _text(s.get("skill"))
        ][:15],
        tech_stack=tech_stack,
        common_titles=_strings(context.get("common_titles"), 10),
        common_responsibilities=responsibilities,
        hidden_requirements=_strings(hidden, 8),
        similar_jobs=[
            {
                "title": job.get("title") or "",
                "company": job.get("company") or "",
                "location": job.get("location") or "",
                "url": job.get("url") or "",
                "match_reason": job.get("match_reason") or "",
            }
            for job in matched[:10]
        ],
        source_coverage_note=note,
    )
    return {
        "target_job_profile": profile.model_dump(),
        "similar_jobs": profile.similar_jobs,
        "confidence": profile.confidence,
    }


def _understand_target_profile(
    *,
    target_role: str,
    narrative_angle: str,
    matched_jobs: list[dict[str, Any]],
    deterministic_stats: dict[str, Any],
    llm: ResumeLLMClient,
) -> dict[str, Any]:
    """Use LLM to semantically understand core capabilities, skills, tech stack from matched jobs."""
    if not matched_jobs:
        return {}
    compact_jobs = [
        {
            "title": item.get("title") or "",
            "snippet": (item.get("snippet") or "")[:500],
            "match_reason": item.get("match_reason") or "",
        }
        for item in matched_jobs[:8]
    ]
    try:
        content = llm.chat_json(
            TARGET_PROFILE_UNDERSTANDING_SYSTEM_PROMPT,
            TARGET_PROFILE_UNDERSTANDING_PROMPT.format(
                target_role=target_role or "目标岗位",
                narrative_angle=narrative_angle or "未指定",
                matched_jobs=as_json(compact_jobs),
                deterministic_stats=as_json(deterministic_stats),
            ),
            temperature=0.2,
            max_tokens=4096,
        )
        parsed = parse_llm_json(content)
        if not isinstance(parsed, dict):
            raise ResumeAgentError("Target profile understanding returned non-object JSON")
        return {
            "core_capabilities": _strings(parsed.get("core_capabilities"), 6),
            "high_frequency_skills": [
                item for item in ensure_list(parsed.get("high_frequency_skills"))
                if isinstance(item, dict) and _text(item.get("skill"))
            ][:15],
            "tech_stack": [
                item for item in ensure_list(parsed.get("tech_stack"))
                if isinstance(item, dict)
            ][:10],
            "hidden_requirements": _strings(parsed.get("hidden_requirements"), 8),
        }
    except Exception as exc:
        logger.warning("Target profile understanding fallback used: %s", exc)
        return {}


def summarize_target_responsibilities(
    *,
    target_role: str,
    matched_jobs: list[dict[str, Any]],
    skills: list[str],
    llm: ResumeLLMClient,
) -> list[str]:
    """Use LLM to turn raw JD snippets into readable Chinese responsibility summaries."""
    if not matched_jobs:
        return [f"围绕 {target_role or '目标岗位'} 的核心职责组织技术能力与项目表达。"]

    compact_jobs = [
        {
            "title": item.get("title") or "",
            "snippet": item.get("snippet") or "",
            "match_reason": item.get("match_reason") or "",
        }
        for item in matched_jobs[:8]
    ]
    try:
        content = llm.chat_json(
            TARGET_RESPONSIBILITY_SUMMARY_SYSTEM_PROMPT,
            TARGET_RESPONSIBILITY_SUMMARY_PROMPT.format(
                target_role=target_role,
                skills=", ".join(skills),
                matched_jobs=as_json(compact_jobs),
            ),
            temperature=0.15,
            max_tokens=2048,
        )
        parsed = parse_llm_json(content)
        if isinstance(parsed, list):
            cleaned = [_clean_responsibility(item) for item in _strings(parsed, 8)]
            cleaned = [item for item in cleaned if item]
            if cleaned:
                return cleaned[:8]
    except Exception as exc:
        logger.warning("Target responsibility summary fallback used: %s", exc)

    fallback: list[str] = []
    if skills:
        fallback.append("围绕 " + "、".join(skills[:5]) + " 等技术栈完成系统开发、集成或数据处理任务。")
    fallback.append("根据目标岗位要求参与需求理解、方案实现、测试交付和跨团队协作。")
    return fallback


def _clean_responsibility(value: Any) -> str:
    text = _text(value)
    text = re.sub(
        r"\b(Title|Company|Location|Salary|Employment Type|Industry|Work Mode|Education|Languages|Skills)\s*:",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\s+", " ", text).strip(" -:；;，,")
    if len(text) > 220:
        text = text[:220].rstrip() + "..."
    return text


def _source_lookup(profile: dict[str, Any]) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for source_type, key in (("work", "work_experience"), ("project", "projects"), ("education", "education")):
        for item in profile.get(key) or []:
            if isinstance(item, dict) and item.get("id"):
                lookup[str(item["id"])] = {"source_type": source_type, **item}
    for skill in profile.get("skills") or []:
        sid = f"skill_{re.sub(r'[^a-zA-Z0-9]+', '_', str(skill).lower()).strip('_')}"
        lookup[sid] = {"source_type": "skill", "id": sid, "name": str(skill), "evidence_text": str(skill)}
    return lookup


def _fallback_capability_matches(state: ResumeGenerationState) -> list[CapabilityMatch]:
    profile = state.get("resume_profile") or {}
    target = state.get("target_job_profile") or {}
    sources = _source_lookup(profile)
    haystacks = {sid: as_json(item).lower() for sid, item in sources.items()}
    matches: list[CapabilityMatch] = []
    for capability in (target.get("core_capabilities") or [])[:5]:
        words = [w.lower() for w in re.findall(r"[A-Za-z][A-Za-z0-9+#./-]{1,}", str(capability))]
        matched = [sid for sid, text in haystacks.items() if any(word in text for word in words)]
        strength = "medium" if matched else "missing"
        matches.append(CapabilityMatch(
            capability=str(capability),
            job_basis="来自目标岗位画像中的核心能力要求。",
            matched_sources=matched[:3],
            evidence_strength=strength,  # type: ignore[arg-type]
            resume_angle="可使用匹配到的真实经历作为简历表达支撑。" if matched else "",
            risk_note="" if matched else "原始简历中没有找到直接证据，不能写成强经历。",
        ))
    return matches


def build_capability_match_matrix(state: ResumeGenerationState, llm: ResumeLLMClient) -> dict[str, Any]:
    try:
        content = llm.chat_json(
            CAPABILITY_MATCH_SYSTEM_PROMPT,
            CAPABILITY_MATCH_PROMPT.format(
                target_job_profile=as_json(state.get("target_job_profile") or {}),
                resume_profile=as_json(state.get("resume_profile") or {}),
            ),
            temperature=0.15,
            max_tokens=4096,
        )
        parsed = parse_llm_json(content)
        if not isinstance(parsed, list):
            raise ResumeAgentError("Capability matcher returned non-array JSON")
        matches = [CapabilityMatch.model_validate(item) for item in parsed if isinstance(item, dict)]
    except Exception as exc:
        logger.warning("Capability matching fallback used: %s", exc)
        matches = _fallback_capability_matches(state)
    return {"capability_matches": [item.model_dump() for item in matches]}


def _normalise_selection_plan(raw: Any, state: ResumeGenerationState) -> SelectedExperiencePlan:
    if not isinstance(raw, dict):
        raw = {}
    lookup = _source_lookup(state.get("resume_profile") or {})
    selected: list[SelectedExperience] = []
    for item in ensure_list(raw.get("selected")):
        if not isinstance(item, dict):
            continue
        source_id = _text(item.get("source_id"))
        source_type = item.get("source_type") or "work"
        source = lookup.get(source_id, {})

        # Allow knowledge_base items that are not in the profile lookup
        if source_type == "knowledge_base":
            if not source_id:
                source_id = f"kb_{len(selected) + 1}"
            selected.append(SelectedExperience(
                source_type="knowledge_base",
                source_id=source_id,
                source_title=_text(item.get("source_title")) or "知识库岗位素材",
                target_capability=_text(item.get("target_capability")) or "Target role capability",
                evidence_text=_text(item.get("evidence_text")) or "来源于知识库岗位画像",
                selection_reason=_text(item.get("selection_reason")) or "简历素材不足，基于知识库岗位画像生成补充素材。",
                evidence_confidence=item.get("evidence_confidence") or "weak",
            ))
            continue

        if not source_id or source_id not in lookup:
            continue
        selected.append(SelectedExperience(
            source_type=source_type,
            source_id=source_id,
            source_title=_text(item.get("source_title")) or _source_title(source),
            target_capability=_text(item.get("target_capability")) or "Target role capability",
            evidence_text=_text(item.get("evidence_text")) or _text(source.get("evidence_text")) or _source_title(source),
            selection_reason=_text(item.get("selection_reason")) or "该素材与目标岗位能力存在关联，可作为保守表达依据。",
            evidence_confidence=item.get("evidence_confidence") or "medium",
        ))

    if not selected:
        for match in ensure_list(state.get("capability_matches")):
            if not isinstance(match, dict):
                continue
            for source_id in _strings(match.get("matched_sources"), 2):
                source = lookup.get(source_id)
                if not source:
                    continue
                selected.append(SelectedExperience(
                    source_type=source["source_type"],
                    source_id=source_id,
                    source_title=_source_title(source),
                    target_capability=_text(match.get("capability")) or "Target role capability",
                    evidence_text=_text(source.get("evidence_text")) or _source_title(source),
                    selection_reason=_text(match.get("resume_angle")) or "该素材能够映射到目标岗位能力，因此被选入生成依据。",
                    evidence_confidence="medium" if match.get("evidence_strength") != "strong" else "strong",
                ))
        selected = selected[:6]

    excluded = [item for item in ensure_list(raw.get("excluded")) if isinstance(item, dict)]
    selected_ids = {item.source_id for item in selected}
    for source_id, source in lookup.items():
        if source_id not in selected_ids and source.get("source_type") in {"work", "project"}:
            excluded.append({
                "source_id": source_id,
                "source_title": _source_title(source),
                "reason": "与本次目标岗位核心能力关联较弱，优先级低于已选素材。",
            })

    confirmation = _strings(raw.get("user_confirmation_required"))
    confirmation.extend(
        f"{item.source_title or item.source_id}: evidence is {item.evidence_confidence}"
        for item in selected
        if item.evidence_confidence in {"weak", "risky"}
    )
    return SelectedExperiencePlan(
        selected=selected,
        excluded=excluded[:20],
        selection_summary=_text(raw.get("selection_summary")) or f"Selected {len(selected)} evidence item(s) for the target role.",
        user_confirmation_required=list(dict.fromkeys(confirmation)),
    )


def _source_title(source: dict[str, Any]) -> str:
    if source.get("source_type") == "work":
        return " - ".join(part for part in [_text(source.get("company")), _text(source.get("title"))] if part) or source.get("id", "")
    if source.get("source_type") == "project":
        return _text(source.get("name")) or source.get("id", "")
    if source.get("source_type") == "education":
        return " - ".join(part for part in [_text(source.get("school")), _text(source.get("degree"))] if part) or source.get("id", "")
    return _text(source.get("name")) or source.get("id", "")


def build_selected_experience_plan(state: ResumeGenerationState, llm: ResumeLLMClient) -> dict[str, Any]:
    try:
        content = llm.chat_json(
            EXPERIENCE_SELECTION_SYSTEM_PROMPT,
            EXPERIENCE_SELECTION_PROMPT.format(
                input_health=as_json(state.get("input_health") or {}),
                target_job_profile=as_json(state.get("target_job_profile") or {}),
                resume_profile=as_json(state.get("resume_profile") or {}),
                capability_matches=as_json(state.get("capability_matches") or []),
            ),
            temperature=0.15,
            max_tokens=6144,
        )
        parsed = parse_llm_json(content)
    except Exception as exc:
        logger.warning("Selection plan fallback used: %s", exc)
        parsed = {}
    plan = _normalise_selection_plan(parsed, state)
    return {
        "selected_experience_plan": plan.model_dump(),
        "selected_experience": [item.model_dump() for item in plan.selected],
    }


def apply_selection_policy(state: ResumeGenerationState) -> dict[str, Any]:
    plan = SelectedExperiencePlan.model_validate(state.get("selected_experience_plan") or {})
    for item in plan.selected:
        if item.evidence_confidence == "risky":
            plan.user_confirmation_required.append(
                f"{item.source_title or item.source_id}: risky evidence was not allowed as a strong claim."
            )
    plan.user_confirmation_required = list(dict.fromkeys(plan.user_confirmation_required))
    return {
        "selected_experience_plan": plan.model_dump(),
        "selected_experience": [item.model_dump() for item in plan.selected],
    }


def _normalise_generated_resume(raw: Any, state: ResumeGenerationState) -> GeneratedResume:
    if not isinstance(raw, dict):
        raw = {}
    profile = state.get("resume_profile") or {}
    plan = SelectedExperiencePlan.model_validate(state.get("selected_experience_plan") or {})
    lookup = _source_lookup(profile)

    allowed_ids = {item.source_id for item in plan.selected}
    work_items: list[GeneratedExperience] = []
    for idx, item in enumerate(ensure_list(raw.get("work_experience")), start=1):
        if not isinstance(item, dict):
            continue
        bullets = _normalise_bullets(item.get("bullets"), allowed_ids, idx)
        work_items.append(GeneratedExperience(
            company=_text(item.get("company")),
            title=_text(item.get("title")),
            start_date=_text(item.get("start_date")),
            end_date=_text(item.get("end_date")),
            location=_text(item.get("location")),
            bullets=bullets,
        ))

    project_items: list[GeneratedProject] = []
    for idx, item in enumerate(ensure_list(raw.get("projects")), start=1):
        if not isinstance(item, dict):
            continue
        project_items.append(GeneratedProject(
            name=_text(item.get("name")),
            role=_text(item.get("role")),
            period=_text(item.get("period")),
            bullets=_normalise_bullets(item.get("bullets"), allowed_ids, idx + 100),
        ))

    if not work_items and not project_items:
        for idx, selected in enumerate(plan.selected, start=1):
            source = lookup.get(selected.source_id, {})
            bullet = GeneratedBullet(
                bullet_id=f"b{idx}",
                text=_safe_bullet_from_evidence(selected),
                evidence_id=selected.source_id,
                target_capability=selected.target_capability,
                interview_risk="high" if selected.evidence_confidence in {"weak", "risky"} else "medium",
            )
            if selected.source_type == "project" or selected.source_type == "knowledge_base":
                project_items.append(GeneratedProject(name=selected.source_title, bullets=[bullet]))
            else:
                work_items.append(GeneratedExperience(
                    company=_text(source.get("company")),
                    title=_text(source.get("title")) or selected.source_title,
                    start_date=_text(source.get("start_date")),
                    end_date=_text(source.get("end_date")),
                    location=_text(source.get("location")),
                    bullets=[bullet],
                ))

    education = [
        GeneratedEducation(
            school=_text(item.get("school")),
            degree=_text(item.get("degree")),
            major=_text(item.get("major")),
            period=_text(item.get("period")),
        )
        for item in ensure_list(raw.get("education") or profile.get("education"))
        if isinstance(item, dict)
    ]

    target = state.get("target_job_profile") or {}
    headline = _text(raw.get("headline")) or _text(target.get("target_role")) or "IT Professional"
    return GeneratedResume(
        language=raw.get("language") or state.get("language") or "en",
        headline=headline,
        positioning_statement=_text(raw.get("positioning_statement")) or f"Targeting {headline} roles in Hong Kong.",
        summary=_text(raw.get("summary")) or f"IT candidate with experience aligned to {headline}.",
        skills=_strings(raw.get("skills") or profile.get("skills"), 30),
        work_experience=work_items,
        projects=project_items,
        education=education,
        certifications=_strings(raw.get("certifications") or profile.get("certifications")),
    )


def _normalise_bullets(raw: Any, allowed_ids: set[str], offset: int = 0) -> list[GeneratedBullet]:
    bullets: list[GeneratedBullet] = []
    for idx, item in enumerate(ensure_list(raw), start=1):
        if isinstance(item, str):
            item = {"text": item}
        if not isinstance(item, dict):
            continue
        evidence_id = _text(item.get("evidence_id"))
        bullets.append(GeneratedBullet(
            bullet_id=_text(item.get("bullet_id")) or f"b{offset}_{idx}",
            text=_text(item.get("text")),
            evidence_id=evidence_id if evidence_id in allowed_ids else evidence_id,
            target_capability=_text(item.get("target_capability")),
            interview_risk=item.get("interview_risk") or "medium",
        ))
    return [bullet for bullet in bullets if bullet.text]


def _safe_bullet_from_evidence(selected: SelectedExperience) -> str:
    text = selected.evidence_text.strip()
    first = re.split(r"(?<=[.!?。！？])\s+", text)[0] if text else selected.source_title
    first = first.strip("-• \n\t") or selected.source_title
    return compact_text(first, 260)


def generate_target_resume(state: ResumeGenerationState, llm: ResumeLLMClient) -> dict[str, Any]:
    try:
        content = llm.chat_json(
            RESUME_GENERATION_SYSTEM_PROMPT,
            RESUME_GENERATION_PROMPT.format(
                language=state.get("language") or "en",
                style=state.get("style") or "professional",
                narrative_angle=state.get("narrative_angle") or "",
                input_health=as_json(state.get("input_health") or {}),
                target_job_profile=as_json(state.get("target_job_profile") or {}),
                resume_profile=as_json(state.get("resume_profile") or {}),
                selected_experience_plan=as_json(state.get("selected_experience_plan") or {}),
            ),
            temperature=0.25,
            max_tokens=8192,
        )
        parsed = parse_llm_json(content)
    except Exception as exc:
        logger.warning("Resume generation fallback used: %s", exc)
        parsed = {}
    generated = _normalise_generated_resume(parsed, state)
    return {"generated_resume": generated.model_dump()}


def audit_generated_resume(state: ResumeGenerationState, llm: ResumeLLMClient) -> dict[str, Any]:
    try:
        content = llm.chat_json(
            CLAIM_AUDIT_SYSTEM_PROMPT,
            CLAIM_AUDIT_PROMPT.format(
                input_health=as_json(state.get("input_health") or {}),
                generated_resume=as_json(state.get("generated_resume") or {}),
                selected_experience_plan=as_json(state.get("selected_experience_plan") or {}),
                target_job_profile=as_json(state.get("target_job_profile") or {}),
            ),
            temperature=0.1,
            max_tokens=4096,
        )
        parsed = parse_llm_json(content)
    except Exception as exc:
        logger.warning("Claim audit fallback used: %s", exc)
        parsed = []
    if not isinstance(parsed, list):
        parsed = extract_json_objects(str(parsed))

    audit: list[ClaimEvidence] = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        try:
            audit.append(ClaimEvidence.model_validate(item))
        except Exception:
            continue
    if not audit:
        for bullet in _iter_generated_bullets(state.get("generated_resume") or {}):
            audit.append(ClaimEvidence(
                claim=bullet.get("text") or "",
                claim_type="achievement",
                source="selected_experience" if bullet.get("evidence_id") else "inferred",
                confidence="medium" if bullet.get("evidence_id") else "risky",
                action="keep" if bullet.get("evidence_id") else "ask_user",
                reason="Fallback audit based on bullet evidence_id.",
            ))
    return {"claim_audit": [item.model_dump() for item in audit]}


def _iter_generated_bullets(generated: dict[str, Any]) -> list[dict[str, Any]]:
    bullets: list[dict[str, Any]] = []
    for section in ("work_experience", "projects"):
        for item in generated.get(section) or []:
            if isinstance(item, dict):
                bullets.extend(b for b in ensure_list(item.get("bullets")) if isinstance(b, dict))
    return bullets


def run_quality_gates(state: ResumeGenerationState) -> dict[str, Any]:
    p0: list[str] = []
    p1: list[str] = []
    fixes: list[str] = []
    plan = state.get("selected_experience_plan") or {}
    selected_ids = {
        str(item.get("source_id"))
        for item in plan.get("selected") or []
        if isinstance(item, dict) and item.get("source_id")
    }
    generated = state.get("generated_resume") or {}
    markdownish = as_json(generated)

    # Check if resume is sparse — allows knowledge_base claims as supplementary material
    input_health = state.get("input_health") or {}
    resume_is_sparse = input_health.get("resume_status") in {"partial", "missing"}

    for bullet in _iter_generated_bullets(generated):
        text = _text(bullet.get("text"))
        evidence_id = _text(bullet.get("evidence_id"))
        if not evidence_id:
            p0.append(f"Bullet lacks evidence_id: {compact_text(text, 80)}")
        elif evidence_id not in selected_ids:
            p0.append(f"Bullet evidence_id not found in selected experience: {evidence_id}")
        if any(label.lower() in text.lower() for label in INTERNAL_LABELS):
            p0.append(f"Internal label leaked in bullet: {compact_text(text, 80)}")

    if any(label.lower() in markdownish.lower() for label in INTERNAL_LABELS):
        p0.append("Generated resume contains internal workflow labels.")

    for item in state.get("claim_audit") or []:
        if not isinstance(item, dict):
            continue
        # When resume is sparse, knowledge_base claims are allowed as supplementary material
        if item.get("source") == "knowledge_base" and item.get("action") == "keep" and not resume_is_sparse:
            p0.append(f"Knowledge-base claim kept as candidate experience: {_text(item.get('claim'))}")
        if item.get("source") == "knowledge_base" and item.get("action") == "keep" and resume_is_sparse:
            p1.append(f"知识库补充内容需用户核实：{_text(item.get('claim'))}")
        if item.get("confidence") == "risky" and item.get("action") == "keep":
            p0.append(f"Risky claim kept: {_text(item.get('claim'))}")
        if item.get("confidence") in {"weak", "risky"} and item.get("action") in {"soften", "ask_user", "remove"}:
            p1.append(f"低置信 claim 需要复核：{_text(item.get('claim'))}")

    for match in state.get("capability_matches") or []:
        if isinstance(match, dict) and match.get("evidence_strength") == "missing":
            p1.append(f"目标能力缺少真实经历证据：{_text(match.get('capability'))}")

    if p0:
        fixes.append("删除缺少证据的 bullet，或只基于已选真实素材重新生成。")
    if p1:
        fixes.append("正式投递前请复核弱证据 / 缺失能力，必要时补充真实项目或降低表达强度。")

    status = "blocked" if p0 else ("pass_with_gaps" if p1 else "pass")
    result = QualityGateResult(status=status, p0_violations=list(dict.fromkeys(p0)), p1_gaps=list(dict.fromkeys(p1)), suggested_fixes=fixes)
    return {"quality_gate": result.model_dump()}


def render_generated_resume_markdown(state: ResumeGenerationState) -> dict[str, Any]:
    resume = GeneratedResume.model_validate(state.get("generated_resume") or {})
    contact = (state.get("resume_profile") or {}).get("contact") or {}
    lines: list[str] = [f"# {contact.get('name') or resume.headline}", ""]
    contact_line = " | ".join(_text(contact.get(k)) for k in ("location", "email", "phone", "linkedin", "github") if _text(contact.get(k)))
    if contact_line:
        lines.extend([contact_line, ""])
    lines.extend(["## Professional Summary", "", resume.positioning_statement, "", resume.summary, ""])
    if resume.skills:
        lines.extend(["## Key Skills", ""])
        lines.extend(f"- {skill}" for skill in resume.skills)
        lines.append("")
    if resume.work_experience:
        lines.extend(["## Work Experience", ""])
        for item in resume.work_experience:
            title = " - ".join(part for part in (item.company, item.title) if part) or item.title or item.company
            if title:
                lines.append(f"### {title}")
            dates = " - ".join(part for part in (item.start_date, item.end_date) if part)
            meta = " | ".join(part for part in (dates, item.location) if part)
            if meta:
                lines.append(meta)
            lines.append("")
            lines.extend(f"- {bullet.text}" for bullet in item.bullets)
            lines.append("")
    if resume.projects:
        lines.extend(["## Projects", ""])
        for item in resume.projects:
            lines.append(f"### {item.name or item.role or 'Project'}")
            if item.period:
                lines.append(item.period)
            lines.append("")
            lines.extend(f"- {bullet.text}" for bullet in item.bullets)
            lines.append("")
    if resume.education:
        lines.extend(["## Education", ""])
        for item in resume.education:
            heading = " - ".join(part for part in (item.school, item.degree, item.major) if part)
            lines.append(heading or item.school or item.degree)
            if item.period:
                lines.append(item.period)
            lines.append("")
    if resume.certifications:
        lines.extend(["## Certifications", ""])
        lines.extend(f"- {cert}" for cert in resume.certifications)
        lines.append("")
    return {"markdown": "\n".join(lines).strip() + "\n"}


