from __future__ import annotations

import re
from collections import Counter
from typing import Any

from src.analyzer.role_prompt import ROLE_DEFINITIONS
from src.analyzer.role_classifier import RoleClassifier
from src.analyzer.rule_engine import RuleBasedSkillExtractor
from src.embeddings.vector_store import VectorStore
from src.knowledge_base.hybrid_search import HybridJobSearch, HybridSearchOptions
from src.logger import get_logger

from .llm import ResumeLLMClient
from .market_data import (
    candidate_capability_hints,
    load_job_tag_profile,
    load_taxonomy,
    normalize_keywords,
    split_jd_by_requirement,
    tag_names,
)
from .market_insights import compute_market_insights
from .prompts import (
    GAP_ANALYSIS_PROMPT,
    GAP_ANALYSIS_SYSTEM_PROMPT,
    INTERVIEW_PREP_PROMPT,
    INTERVIEW_PREP_SYSTEM_PROMPT,
    JD_ANALYSIS_PROMPT,
    JD_ANALYSIS_SYSTEM_PROMPT,
    JOB_MATCH_RERANK_PROMPT,
    JOB_MATCH_RERANK_SYSTEM_PROMPT,
    MARKET_INSIGHTS_SUMMARY_PROMPT,
    MARKET_INSIGHTS_SUMMARY_SYSTEM_PROMPT,
    MARKET_JD_SYNTHESIS_PROMPT,
    MARKET_JD_SYNTHESIS_SYSTEM_PROMPT,
    POLISH_PROMPT,
    POLISH_SYSTEM_PROMPT,
    RESUME_PARSE_PROMPT,
    RESUME_PARSE_SYSTEM_PROMPT,
    SCORE_PROMPT,
    SCORE_SYSTEM_PROMPT,
    TARGET_ROLE_UNDERSTANDING_PROMPT,
    TARGET_ROLE_UNDERSTANDING_SYSTEM_PROMPT,
    TECH_STACK_SUMMARY_PROMPT,
    TECH_STACK_SUMMARY_SYSTEM_PROMPT,
    as_json,
)
from .state import AgentState
from .utils import ResumeAgentError, clamp_score, compact_text, ensure_list, extract_json_objects, parse_llm_json

logger = get_logger(__name__)

# JD 文本达到该长度才视为「用户已提供目标 JD」，否则进入知识库模式。
JD_MIN_LENGTH = 30
TECH_SKILL_CATEGORIES = {"programming_languages", "frameworks_libraries", "ai_concepts", "cloud_devops", "databases"}
OTHER_COMPETENCY_TERMS = (
    "cantonese",
    "english",
    "mandarin",
    "communication",
    "cross-functional",
    "collaboration",
    "stakeholder",
    "leadership",
    "teamwork",
)


def has_target_jd(state: AgentState) -> bool:
    return len((state.get("target_jd_text") or "").strip()) >= JD_MIN_LENGTH


def _role_definition(state: AgentState) -> dict[str, str]:
    role_id = (state.get("target_role_id") or "").strip()
    if role_id in ROLE_DEFINITIONS:
        return {"role_id": role_id, **ROLE_DEFINITIONS[role_id]}
    role_name = (state.get("target_role") or "").strip()
    if role_name:
        for candidate_id, definition in ROLE_DEFINITIONS.items():
            if definition.get("name") == role_name:
                return {"role_id": candidate_id, **definition}
    return {"role_id": "", "name": role_name, "keywords": ""}


def _normalise_theme(item: Any) -> dict[str, Any] | None:
    if not isinstance(item, dict):
        return None
    theme = str(item.get("theme") or "").strip()
    if not theme:
        return None
    return {
        "theme": theme,
        "items": [str(v) for v in ensure_list(item.get("items")) if v],
        "evidence": [str(v) for v in ensure_list(item.get("evidence")) if v][:3],
    }


def _fallback_tech_stack_from_context(context: dict[str, Any] | None) -> dict[str, Any]:
    skills = [str(item.get("skill") or "") for item in ((context or {}).get("top_skills") or []) if item.get("skill")]
    buckets: dict[str, list[str]] = {
        "编程语言与后端开发": [],
        "云平台与交付自动化": [],
        "数据与存储": [],
        "AI / 数据应用": [],
        "工程框架与工具": [],
    }
    for skill in skills:
        lower = skill.lower()
        if lower in {"python", "java", "javascript", "typescript", "go", "c#", "php", "ruby"}:
            buckets["编程语言与后端开发"].append(skill)
        elif lower in {"aws", "azure", "gcp", "docker", "kubernetes", "k8s", "ci/cd", "jenkins", "terraform"}:
            buckets["云平台与交付自动化"].append(skill)
        elif lower in {"sql", "mysql", "postgresql", "mongodb", "redis", "snowflake", "oracle"}:
            buckets["数据与存储"].append(skill)
        elif lower in {"machine learning", "deep learning", "llm", "rag", "tensorflow", "pytorch", "langchain"}:
            buckets["AI / 数据应用"].append(skill)
        else:
            buckets["工程框架与工具"].append(skill)

    themes = [
        {"theme": theme, "items": values[:8], "evidence": []}
        for theme, values in buckets.items()
        if values
    ]
    return {"tech_stack_themes": themes, "other_competencies": [], "core_capabilities": []}


def build_search_query(state: AgentState) -> str:
    """构造知识库检索查询。

    优先级：目标 JD 文本 > 目标职位 > 简历职位/技能 > 简历原文。
    """
    if has_target_jd(state):
        return (state.get("target_jd_text") or "").strip()

    understanding = state.get("target_role_understanding") or {}
    expanded_query = str(understanding.get("expanded_query") or "").strip()
    if expanded_query:
        return expanded_query

    parts: list[str] = []
    role = (state.get("target_role") or "").strip()
    if role:
        parts.append(role)

    resume = state.get("resume") or {}
    parts.extend(str(title) for title in (resume.get("current_titles") or [])[:3] if title)
    parts.extend(str(skill) for skill in (resume.get("raw_skills") or [])[:15] if skill)

    query = " ".join(parts).strip()
    if query:
        return query
    return compact_text(state.get("resume_text") or "", 2000)


def understand_target_role(state: AgentState, llm: ResumeLLMClient) -> dict[str, Any]:
    """用 LLM 把选定目标职位转成语义检索画像。失败时回退到标准角色定义。"""
    role_def = _role_definition(state)
    role_id = role_def.get("role_id") or ""
    target_role = (state.get("target_role") or role_def.get("name") or "").strip()
    if not role_id and not target_role:
        return {"target_role_understanding": None}

    try:
        content = llm.chat_json(
            TARGET_ROLE_UNDERSTANDING_SYSTEM_PROMPT,
            TARGET_ROLE_UNDERSTANDING_PROMPT.format(
                role_id=role_id or "custom",
                role_name=role_def.get("name") or target_role,
                role_keywords=role_def.get("keywords") or "",
                target_role=target_role or "未填写",
                resume=as_json(state.get("resume") or {}),
            ),
            temperature=0.2,
        )
        parsed = parse_llm_json(content)
        if not isinstance(parsed, dict):
            raise ResumeAgentError("Target role understanding returned non-object JSON")
        understanding = {
            "role_id": str(parsed.get("role_id") or role_id or ""),
            "role_name": str(parsed.get("role_name") or role_def.get("name") or target_role),
            "role_summary": str(parsed.get("role_summary") or ""),
            "expanded_query": str(parsed.get("expanded_query") or ""),
            "core_tech": [str(v) for v in ensure_list(parsed.get("core_tech")) if v],
            "responsibilities": [str(v) for v in ensure_list(parsed.get("responsibilities")) if v],
        }
    except Exception as exc:
        logger.warning("Target role understanding skipped, using role definition fallback: %s", exc)
        keywords = role_def.get("keywords") or ""
        understanding = {
            "role_id": role_id,
            "role_name": role_def.get("name") or target_role,
            "role_summary": role_def.get("name") or target_role,
            "expanded_query": " ".join(part for part in [target_role, role_def.get("name") or "", keywords] if part),
            "core_tech": [item.strip() for item in keywords.split(",") if item.strip()][:8],
            "responsibilities": [],
        }
    return {"target_role_understanding": understanding}


def parse_resume(state: AgentState, llm: ResumeLLMClient) -> dict[str, Any]:
    content = llm.chat_json(
        RESUME_PARSE_SYSTEM_PROMPT,
        RESUME_PARSE_PROMPT.format(resume_text=compact_text(state["resume_text"], 12000)),
        max_tokens=8192,  # 解析结果会回显各段落内容，预留更大额度避免截断
    )
    parsed = parse_llm_json(content)
    if not isinstance(parsed, dict):
        raise ResumeAgentError("Resume parser returned non-object JSON")
    parsed["raw_skills"] = [str(item) for item in ensure_list(parsed.get("raw_skills")) if item]
    parsed["current_titles"] = [str(item) for item in ensure_list(parsed.get("current_titles")) if item]
    if not isinstance(parsed.get("sections"), dict):
        parsed["sections"] = {}
    return {"resume": parsed}


_YEARS_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:\+|＋|以上)?\s*(?:年|years?\b)", re.IGNORECASE)


def _parse_years(*texts: str) -> float | None:
    """从经验类标签名/证据里抽取最小经验年限（取最大命中值，贴近 JD 门槛）。"""
    best: float | None = None
    for text in texts:
        for match in _YEARS_RE.finditer(text or ""):
            try:
                value = float(match.group(1))
            except ValueError:
                continue
            if best is None or value > best:
                best = value
    return best


def _jd_from_tag_profile(reused: dict[str, Any]) -> dict[str, Any]:
    """命中库内治理标签时，确定性派生 JDAnalysis，免一次重解析 LLM 调用。

    口径与统计侧统一：required/preferred/example/inferred 直接来自治理后的
    requirement_level；跨行业六维、软技能、标签证据一并透出供下游使用。
    """
    tag_profile = reused.get("tag_profile") or {}
    cross = reused.get("cross_industry_profile") or {}
    soft = reused.get("soft_skills") or {}
    buckets = split_jd_by_requirement(tag_profile)

    tag_evidence: dict[str, str] = {}
    experience_texts: list[str] = []
    for group in ("technical", "non_technical"):
        for tag in tag_profile.get(group, []) or []:
            if not isinstance(tag, dict):
                continue
            name = str(tag.get("name") or "").strip()
            if name and tag.get("evidence"):
                tag_evidence[name] = str(tag.get("evidence"))
            if str(tag.get("category") or "") == "experience":
                experience_texts.append(name)
                if tag.get("evidence"):
                    experience_texts.append(str(tag.get("evidence")))

    # 职责优先用跨行业「交付动作 + 业务场景」表达，回退到 required 标签名。
    responsibilities = tag_names(cross.get("delivery_motion") or [])
    responsibilities += [n for n in tag_names(cross.get("business_scenario") or []) if n not in responsibilities]
    if not responsibilities:
        responsibilities = tag_names(buckets["required"])[:8]

    education = [str(e) for e in (soft.get("education") or []) if e]
    languages = [str(lang) for lang in (soft.get("language") or []) if lang]

    return {
        "required_skills": tag_names(buckets["required"]),
        "preferred_skills": tag_names(buckets["preferred"]),
        "example_skills": tag_names(buckets["example"]),
        "inferred_skills": tag_names(buckets["inferred"]),
        "soft_skills": soft,
        "cross_industry_profile": cross,
        "tag_evidence": tag_evidence,
        "responsibilities": responsibilities[:10],
        "min_experience": _parse_years(*experience_texts),
        "education_required": education[0] if education else None,
        "language_requirements": languages,
        "key_requirements": tag_names(buckets["required"])[:10],
        "reused_from_cache": True,
    }


def _attach_role(jd_data: dict[str, Any], state: AgentState, role_basis: str) -> dict[str, Any]:
    role = RoleClassifier().classify(role_basis)
    jd_data["role_category"] = role.role_id
    jd_data["role_name"] = role.role_name
    if state.get("target_role"):
        jd_data["target_role"] = state["target_role"]
    for key in ("required_skills", "preferred_skills", "example_skills", "inferred_skills",
                "responsibilities", "language_requirements", "key_requirements"):
        jd_data[key] = [str(item) for item in ensure_list(jd_data.get(key)) if item]
    return jd_data


def analyze_jd(state: AgentState, llm: ResumeLLMClient) -> dict[str, Any]:
    jd_text = state["target_jd_text"]

    # 优先复用统计侧已治理的分层标签：命中库内岗位则免重解析，且 example/inferred
    # 备选池被显式分桶，下游差距与评分不再把示例当硬要求（修复§13.1）。
    reused = load_job_tag_profile(jd_text)
    if reused:
        jd_data = _jd_from_tag_profile(reused)
        logger.info("analyze_jd reused governed tag_profile from role cache")
        return {"jd": _attach_role(jd_data, state, jd_text)}

    content = llm.chat_json(
        JD_ANALYSIS_SYSTEM_PROMPT,
        JD_ANALYSIS_PROMPT.format(jd_text=compact_text(jd_text, 10000)),
    )
    jd_data = parse_llm_json(content)
    if not isinstance(jd_data, dict):
        raise ResumeAgentError("JD analyzer returned non-object JSON")
    jd_data["reused_from_cache"] = False
    return {"jd": _attach_role(jd_data, state, jd_text)}


def synthesize_market_jd(state: AgentState, llm: ResumeLLMClient) -> dict[str, Any]:
    """未提供目标 JD 时，基于知识库相似岗位合成「目标市场画像」作为 JD。"""
    matched = state.get("matched_jobs") or []
    target_role = (state.get("target_role") or "").strip()

    content = llm.chat_json(
        MARKET_JD_SYNTHESIS_SYSTEM_PROMPT,
        MARKET_JD_SYNTHESIS_PROMPT.format(
            target_role=target_role or "（未指定，请根据相似岗位推断目标方向）",
            matched_jobs=as_json(matched),
            market_context=as_json(state.get("market_context") or {}),
        ),
    )
    jd_data = parse_llm_json(content)
    if not isinstance(jd_data, dict):
        raise ResumeAgentError("Market JD synthesizer returned non-object JSON")

    role_basis = target_role or " ".join(str(job.get("title") or "") for job in matched)
    role = RoleClassifier().classify(role_basis or "")
    jd_data["role_category"] = role.role_id
    jd_data["role_name"] = role.role_name
    jd_data["source"] = "knowledge_base"
    if target_role:
        jd_data["target_role"] = target_role
    for key in ("required_skills", "preferred_skills", "responsibilities", "language_requirements", "key_requirements"):
        jd_data[key] = [str(item) for item in ensure_list(jd_data.get(key)) if item]
    return {"jd": jd_data}


def match_jobs(state: AgentState, top_k: int = 5) -> dict[str, Any]:
    """召回相似香港岗位：优先混合检索 + rerank，失败时回退纯向量检索。"""
    query = build_search_query(state)
    if not query.strip():
        return {"matched_jobs": [], "rerank_used": False}

    results: list[dict[str, Any]] = []
    rerank_used = False
    try:
        response = HybridJobSearch().search(
            query,
            HybridSearchOptions(top_k=top_k, candidate_k=max(top_k * 4, 20), use_rerank=True),
        )
        results = response.get("results") or []
        rerank_used = bool(response.get("rerank_used"))
    except Exception as exc:
        logger.warning("Hybrid search failed, falling back to vector search: %s", exc)

    if not results:
        try:
            results = VectorStore().search(query, top_k=top_k)
        except Exception as exc:
            logger.warning("Resume job matching skipped: %s", exc)
            results = []

    matched = []
    for item in results:
        matched.append({
            "job_id": item.get("job_id"),
            "title": item.get("title") or "",
            "company": item.get("company") or "",
            "location": item.get("location") or "",
            "source": item.get("source") or "",
            "url": item.get("url") or "",
            "score": item.get("score"),
            "snippet": item.get("snippet") or "",
        })
    return {"matched_jobs": matched, "rerank_used": rerank_used}


def llm_match_jobs(state: AgentState, llm: ResumeLLMClient) -> dict[str, Any]:
    """在真实召回岗位内用 LLM 做语义排序和定位建议，不新增虚构岗位。"""
    matched = state.get("matched_jobs") or []
    if not matched:
        return {"matched_jobs": matched, "match_advice": None}

    try:
        content = llm.chat_json(
            JOB_MATCH_RERANK_SYSTEM_PROMPT,
            JOB_MATCH_RERANK_PROMPT.format(
                target_role_understanding=as_json(state.get("target_role_understanding") or {}),
                target_role=state.get("target_role") or "",
                resume=as_json(state.get("resume") or {}),
                matched_jobs=as_json(matched),
            ),
            temperature=0.15,
            max_tokens=4096,
        )
        parsed = parse_llm_json(content)
        if not isinstance(parsed, dict):
            raise ResumeAgentError("Job matcher returned non-object JSON")

        by_id = {str(job.get("job_id")): dict(job) for job in matched if job.get("job_id") is not None}
        reasons = parsed.get("match_reasons") if isinstance(parsed.get("match_reasons"), dict) else {}
        ordered: list[dict[str, Any]] = []
        seen: set[str] = set()
        for raw_id in ensure_list(parsed.get("ranked_job_ids")):
            job_id = str(raw_id)
            if job_id in by_id and job_id not in seen:
                item = by_id[job_id]
                if reasons.get(job_id):
                    item["match_reason"] = str(reasons[job_id])
                ordered.append(item)
                seen.add(job_id)
        for job in matched:
            job_id = str(job.get("job_id"))
            if job_id not in seen:
                ordered.append(dict(job))

        advice = parsed.get("match_advice") if isinstance(parsed.get("match_advice"), dict) else {}
        match_advice = {
            "summary": str(advice.get("summary") or ""),
            "suggestions": [str(v) for v in ensure_list(advice.get("suggestions")) if v],
        }
        return {"matched_jobs": ordered[: len(matched)], "match_advice": match_advice}
    except Exception as exc:
        logger.warning("LLM job matching skipped, keeping retrieval order: %s", exc)
        return {"matched_jobs": matched, "match_advice": None}


def build_market_insights(state: AgentState) -> dict[str, Any]:
    """整库岗位数据分析：需求量最大的岗位方向排名 + 技术栈次数排名。"""
    try:
        return {"market_insights": compute_market_insights(top_n=12)}
    except Exception as exc:
        logger.warning("Market insights skipped: %s", exc)
        return {"market_insights": None}


def conceptualize_market_insights(state: AgentState, llm: ResumeLLMClient) -> dict[str, Any]:
    insights = state.get("market_insights") or {}
    if not insights:
        return {"market_insights": insights}
    try:
        content = llm.chat_json(
            MARKET_INSIGHTS_SUMMARY_SYSTEM_PROMPT,
            MARKET_INSIGHTS_SUMMARY_PROMPT.format(market_insights=as_json(insights)),
            temperature=0.15,
            max_tokens=2048,
        )
        parsed = parse_llm_json(content)
        if not isinstance(parsed, dict):
            raise ResumeAgentError("Market insight conceptualizer returned non-object JSON")
        themes = [_normalise_theme(item) for item in ensure_list(parsed.get("tech_stack_themes"))]
        insights = dict(insights)
        insights["tech_stack_themes"] = [item for item in themes if item]
    except Exception as exc:
        logger.warning("Market insight conceptualization skipped: %s", exc)
        fallback = _fallback_tech_stack_from_context({"top_skills": insights.get("tech_stack_ranking") or []})
        insights = dict(insights)
        insights["tech_stack_themes"] = fallback["tech_stack_themes"]
    return {"market_insights": insights}


def build_market_context(state: AgentState) -> dict[str, Any]:
    """基于召回的香港相似岗位，确定性汇总市场上下文（不调用 LLM）。

    产出高频技能、常见职位名、典型岗位措辞，供差距分析与润色参考。
    """
    matched = state.get("matched_jobs") or []
    if not matched:
        return {"market_context": None}

    extractor = RuleBasedSkillExtractor()
    skill_counter: Counter[str] = Counter()
    other_counter: Counter[str] = Counter()
    titles: list[str] = []
    phrases: list[str] = []

    for job in matched:
        title = (job.get("title") or "").strip()
        snippet = (job.get("snippet") or "").strip()
        if title:
            titles.append(title)
        if snippet:
            phrases.append(compact_text(snippet, 240))
        extracted = extractor.extract(f"{title}\n{snippet}")
        for category, skills in extracted.items():
            target = skill_counter if category in TECH_SKILL_CATEGORIES else other_counter
            for skill in skills:
                target[str(skill)] += 1
        for term in OTHER_COMPETENCY_TERMS:
            if term in f"{title}\n{snippet}".lower():
                other_counter[term] += 1

    context = {
        "job_count": len(matched),
        "top_skills": [{"skill": skill, "count": count} for skill, count in skill_counter.most_common(15)],
        "other_competencies": [{"name": name, "count": count} for name, count in other_counter.most_common(12)],
        "common_titles": [title for title, _ in Counter(titles).most_common(8)],
        "sample_phrases": phrases[:5],
    }
    return {"market_context": context}


def summarize_tech_stack(state: AgentState, llm: ResumeLLMClient) -> dict[str, Any]:
    matched = state.get("matched_jobs") or []
    context = state.get("market_context") or {}
    if not matched:
        return {"tech_stack_summary": _fallback_tech_stack_from_context(context)}
    try:
        content = llm.chat_json(
            TECH_STACK_SUMMARY_SYSTEM_PROMPT,
            TECH_STACK_SUMMARY_PROMPT.format(
                target_role_understanding=as_json(state.get("target_role_understanding") or {}),
                market_context=as_json(context),
                matched_jobs=as_json(matched),
            ),
            temperature=0.15,
            max_tokens=4096,
        )
        parsed = parse_llm_json(content)
        if not isinstance(parsed, dict):
            raise ResumeAgentError("Tech stack summarizer returned non-object JSON")
        themes = [_normalise_theme(item) for item in ensure_list(parsed.get("tech_stack_themes"))]
        summary = {
            "tech_stack_themes": [item for item in themes if item],
            "other_competencies": [str(v) for v in ensure_list(parsed.get("other_competencies")) if v],
            "core_capabilities": [str(v) for v in ensure_list(parsed.get("core_capabilities")) if v],
        }
        if not summary["tech_stack_themes"]:
            summary.update(_fallback_tech_stack_from_context(context))
        return {"tech_stack_summary": summary}
    except Exception as exc:
        logger.warning("Tech stack summarization skipped, using filtered rule fallback: %s", exc)
        return {"tech_stack_summary": _fallback_tech_stack_from_context(context)}


# 简历原文达到该长度才视为「完整」，低于则视为「片段」。
RESUME_PROVIDED_LENGTH = 200
RESUME_MIN_LENGTH = 50


def run_input_health(state: AgentState) -> dict[str, Any]:
    """Stage 0 输入体检：判断输入是否足够、哪些可自动补齐、哪些必须问用户。

    确定性逻辑，不调用 LLM：
    - blocked：简历正文不足，继续会误导，只问最少必要问题。
    - workable：有缺口（如缺 JD）但可用知识库补齐，低置信继续。
    - complete：目标、JD、简历、投递状态都足够明确。
    """
    resume_len = len((state.get("resume_text") or "").strip())
    if resume_len >= RESUME_PROVIDED_LENGTH:
        resume_status = "provided"
    elif resume_len >= RESUME_MIN_LENGTH:
        resume_status = "partial"
    else:
        resume_status = "missing"

    jd_len = len((state.get("target_jd_text") or "").strip())
    if jd_len >= JD_MIN_LENGTH:
        jd_status = "provided"
    elif jd_len > 0:
        jd_status = "partial"
    else:
        jd_status = "missing"

    target_role = (state.get("target_role") or "").strip() or None
    target_market = (state.get("target_market") or "").strip() or None
    application_status = (state.get("application_status") or "").strip() or "unknown"

    assumptions: list[str] = []
    gaps: list[str] = []
    blocking_questions: list[str] = []

    if jd_status != "provided":
        if target_role:
            assumptions.append(f"未提供完整 JD，将基于知识库相似岗位为「{target_role}」合成市场画像。")
        else:
            assumptions.append("未提供 JD 与目标职位，将基于简历技能从知识库召回相似岗位推断目标方向。")
        gaps.append("缺少目标 JD，市场画像为知识库推断结果，置信度有限。")
    if not target_market:
        assumptions.append("未指定目标市场，默认按香港 IT 市场分析。")
    if application_status == "applied":
        assumptions.append("简历已投递，建议聚焦面试准备而非改写已投版本。")

    if resume_status == "missing":
        status = "blocked"
        blocking_questions.append("请粘贴简历正文或上传 PDF 简历后再继续。")
    elif resume_status == "partial":
        status = "workable"
        gaps.append("简历内容偏少，只处理已提供片段，可能影响润色完整度。")
    elif jd_status == "provided" and application_status != "unknown":
        status = "complete"
    else:
        status = "workable"

    health = {
        "status": status,
        "target_role": target_role,
        "target_role_id": (state.get("target_role_id") or "").strip() or None,
        "target_market": target_market,
        "jd_status": jd_status,
        "resume_status": resume_status,
        "application_status": application_status,
        "assumptions": assumptions,
        "gaps": gaps,
        "blocking_questions": blocking_questions,
    }
    return {"input_health": health}


def build_job_research(state: AgentState) -> dict[str, Any]:
    """Stage 1 岗位调研：把召回 + 市场上下文/洞察提炼为可见的调研报告。

    确定性聚合（不额外调用 LLM），复用 matched_jobs / market_context /
    market_insights / jd，作为简历改写与面试准备的共同靶心。
    """
    matched = state.get("matched_jobs") or []
    context = state.get("market_context") or {}
    jd = state.get("jd") or {}
    tech_summary = state.get("tech_stack_summary") or {}

    sample_count = len(matched)
    if sample_count == 0:
        return {"job_research": None}

    top_skills = context.get("top_skills") or []
    high_freq = [
        {"skill": str(item.get("skill")), "count": int(item.get("count") or 0)}
        for item in top_skills
        if item.get("skill")
    ]
    tech_stack_themes = [
        item for item in ensure_list(tech_summary.get("tech_stack_themes"))
        if isinstance(item, dict) and item.get("theme")
    ]
    other_competencies = [str(item) for item in ensure_list(tech_summary.get("other_competencies")) if item]
    if not other_competencies:
        other_competencies = [
            str(item.get("name"))
            for item in ensure_list(context.get("other_competencies"))
            if isinstance(item, dict) and item.get("name")
        ]

    # 核心能力靶心：优先 LLM 语义概括，其次 JD 硬技能，最后回退到市场技术主题/技能。
    core = [str(s) for s in ensure_list(tech_summary.get("core_capabilities")) if s][:5]
    if not core:
        core = [str(s) for s in (jd.get("required_skills") or []) if s][:5]
    if not core:
        for theme in tech_stack_themes[:3]:
            items = theme.get("items") if isinstance(theme, dict) else []
            label = str(theme.get("theme") or "")
            values = [str(v) for v in ensure_list(items) if v]
            if label and values:
                core.append(f"{label}（{', '.join(values[:3])}）")
        core = core[:5]
    if not core:
        core = [item["skill"] for item in high_freq[:5]]

    hidden = [str(s) for s in (jd.get("preferred_skills") or []) if s][:5]
    hidden.extend(str(s) for s in (jd.get("key_requirements") or []) if s)

    source = "jd" if has_target_jd(state) else "knowledge_base"
    if source == "jd":
        confidence = "high"
    else:
        # 知识库模式是市场共性画像而非具体公司 JD，置信度封顶 medium，
        # 避免把市场推断伪装成确定结论。
        confidence = "medium" if sample_count >= 2 else "low"

    advice = []
    if core:
        advice.append("简历置顶突出以下核心能力：" + "、".join(core[:5]) + "。")
    if tech_stack_themes:
        advice.append(
            "围绕目标岗位技术主题组织技能区："
            + "、".join(str(item.get("theme")) for item in tech_stack_themes[:4] if item.get("theme"))
            + "。"
        )
    elif high_freq:
        advice.append(
            "对照市场高频技术线索补齐关键词："
            + "、".join(item["skill"] for item in high_freq[:8])
            + "。"
        )
    if other_competencies:
        advice.append("语言、协作和业务沟通能力单独呈现，不混入技术栈：" + "、".join(other_competencies[:5]) + "。")
    if source == "knowledge_base":
        advice.append("当前为知识库市场画像（非具体公司 JD），定位建议偏共性，拿到真实 JD 后请二次校准。")

    note = (
        f"基于知识库召回的 {sample_count} 条香港相似岗位"
        + ("，并结合用户提供的目标 JD" if source == "jd" else "（未提供具体 JD，为市场共性画像）")
        + f"，置信度 {confidence}。"
    )

    report = {
        "target_role": (state.get("target_role") or jd.get("role_name") or None),
        "source": source,
        "confidence": confidence,
        "sample_count": sample_count,
        "core_capabilities": core,
        "high_frequency_skills": high_freq[:15],
        "tech_stack_themes": tech_stack_themes[:8],
        "other_competencies": other_competencies[:12],
        "common_titles": context.get("common_titles") or [],
        "common_responsibilities": [str(r) for r in (jd.get("responsibilities") or []) if r][:8],
        "hidden_requirements": hidden[:8],
        "similar_jobs": [
            {
                "title": job.get("title") or "",
                "company": job.get("company") or "",
                "location": job.get("location") or "",
                "url": job.get("url") or "",
                "match_reason": job.get("match_reason") or "",
            }
            for job in matched[:10]
        ],
        "resume_positioning_advice": advice,
        "source_coverage_note": note,
    }
    return {"job_research": report}


def gap_analysis(state: AgentState, llm: ResumeLLMClient) -> dict[str, Any]:
    jd = state.get("jd") or {}
    content = llm.chat_json(
        GAP_ANALYSIS_SYSTEM_PROMPT,
        GAP_ANALYSIS_PROMPT.format(
            resume=as_json(state.get("resume") or {}),
            jd=as_json(jd),
            matched_jobs=as_json(state.get("matched_jobs") or []),
            market_context=as_json(state.get("market_context") or {}),
            market_insights=as_json(state.get("market_insights") or {}),
            cross_industry_profile=as_json(jd.get("cross_industry_profile") or {}),
            example_skills=as_json(jd.get("example_skills") or []),
        ),
    )
    gap = parse_llm_json(content)
    if not isinstance(gap, dict):
        raise ResumeAgentError("Gap analyzer returned non-object JSON")
    for key in ("matched_skills", "missing_skills", "weak_skills"):
        gap[key] = [str(item) for item in ensure_list(gap.get(key)) if item]
    gap["keyword_suggestions"] = [item for item in ensure_list(gap.get("keyword_suggestions")) if isinstance(item, dict)]
    if gap.get("market_demand_analysis") is not None:
        gap["market_demand_analysis"] = str(gap["market_demand_analysis"])
    if gap.get("cross_industry_alignment") is not None:
        gap["cross_industry_alignment"] = str(gap["cross_industry_alignment"])

    # 守卫（修复§13.1「示例当硬要求」）：备选/推断技能池不计入硬性缺口，
    # 即便 LLM 误把 "e.g. Go/Java 任一" 当成缺失，也在此剔除。
    excluded = {
        str(s).strip().lower()
        for s in (jd.get("example_skills") or []) + (jd.get("inferred_skills") or [])
        if str(s).strip()
    }
    if excluded:
        gap["missing_skills"] = [s for s in gap["missing_skills"] if s.strip().lower() not in excluded]

    # 前瞻补强：接入高置信新兴场景候选标签，作为"市场正在出现、简历尚缺"的建议。
    reused = load_job_tag_profile(state.get("target_jd_text") or "")
    hints = candidate_capability_hints(reused.get("taxonomy_candidates")) if reused else []
    gap["emerging_suggestions"] = [
        {"name": h["name"], "category": h["category"], "evidence": h["evidence"]} for h in hints
    ]
    return {"gap": gap}


def generate_polish(state: AgentState, llm: ResumeLLMClient) -> dict[str, Any]:
    jd = state.get("jd") or {}
    taxonomy = load_taxonomy()
    content = llm.chat_json(
        POLISH_SYSTEM_PROMPT,
        POLISH_PROMPT.format(
            resume_text=compact_text(state["resume_text"], 14000),
            resume=as_json(state.get("resume") or {}),
            jd=as_json(jd),
            gap=as_json(state.get("gap") or {}),
            market_context=as_json(state.get("market_context") or {}),
            cross_industry_profile=as_json(jd.get("cross_industry_profile") or {}),
        ),
        temperature=0.25,
        max_tokens=8192,  # 逐段润色输出较长，避免 JSON 被截断
    )
    try:
        suggestions = parse_llm_json(content)
    except ResumeAgentError:
        suggestions = None
    if not isinstance(suggestions, list):
        # 数组被截断时，抢救已完整生成的段落，避免整条工作流失败。
        salvaged = extract_json_objects(content)
        if salvaged:
            logger.warning("Polish JSON not a clean array; salvaged %d segment(s)", len(salvaged))
            suggestions = salvaged
        else:
            raise ResumeAgentError("Polish generator returned non-array JSON")

    normalized = []
    for item in suggestions:
        if not isinstance(item, dict):
            continue
        normalized.append({
            "section": str(item.get("section") or "其他"),
            "original": str(item.get("original") or ""),
            "suggested": str(item.get("suggested") or ""),
            "changes": [str(change) for change in ensure_list(item.get("changes")) if change],
            # 词库归一：同义异形统一规范写法、剔除误判负例（福利里的 insurance、
            # 地点 Tai Po 误命中 ai 等），保证 ATS 关键词一致（§13.5.3）。
            "keywords_added": normalize_keywords(
                [str(keyword) for keyword in ensure_list(item.get("keywords_added")) if keyword],
                taxonomy,
            ),
        })
    return {"polish_suggestions": normalized}


def score_and_verify(state: AgentState, llm: ResumeLLMClient) -> dict[str, Any]:
    content = llm.chat_json(
        SCORE_SYSTEM_PROMPT,
        SCORE_PROMPT.format(
            resume_text=compact_text(state["resume_text"], 12000),
            jd=as_json(state.get("jd") or {}),
            suggestions=as_json(state.get("polish_suggestions") or []),
        ),
        temperature=0.1,
    )
    score = parse_llm_json(content)
    if not isinstance(score, dict):
        raise ResumeAgentError("Score verifier returned non-object JSON")

    raw_reasons = score.get("dimension_reasons")
    dimension_reasons = {}
    if isinstance(raw_reasons, dict):
        for key in ("keyword_coverage", "experience_alignment", "skill_relevance", "language_quality"):
            if raw_reasons.get(key):
                dimension_reasons[key] = str(raw_reasons[key])

    normalized = {
        "overall_score": clamp_score(score.get("overall_score")),
        "keyword_coverage": clamp_score(score.get("keyword_coverage")),
        "experience_alignment": clamp_score(score.get("experience_alignment")),
        "skill_relevance": clamp_score(score.get("skill_relevance")),
        "language_quality": clamp_score(score.get("language_quality")),
        "overall_comment": str(score.get("overall_comment") or ""),
        "dimension_reasons": dimension_reasons,
        "suggestions": [str(item) for item in ensure_list(score.get("suggestions")) if item],
    }
    return {"score": normalized}


def build_interview_prep(state: AgentState, llm: ResumeLLMClient) -> dict[str, Any]:
    """Stage 8 面试深挖：把润色后的每条 bullet 转为可被追问的讲法。"""
    suggestions = state.get("polish_suggestions") or []
    if not suggestions:
        return {"bullet_inventory": []}

    content = llm.chat_json(
        INTERVIEW_PREP_SYSTEM_PROMPT,
        INTERVIEW_PREP_PROMPT.format(
            jd=as_json(state.get("jd") or {}),
            suggestions=as_json(suggestions),
        ),
        temperature=0.3,
        max_tokens=8192,  # 逐条讲法输出较长，避免 JSON 被截断
    )
    try:
        items = parse_llm_json(content)
    except ResumeAgentError:
        items = None
    if not isinstance(items, list):
        # 数组被截断时抢救已完整生成的条目，不让整个面试准备失败。
        salvaged = extract_json_objects(content)
        if salvaged:
            logger.warning("Interview prep JSON not a clean array; salvaged %d item(s)", len(salvaged))
            items = salvaged
        else:
            raise ResumeAgentError("Interview prep returned non-array JSON")

    inventory = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        inventory.append({
            "bullet_id": str(item.get("bullet_id") or f"b{index + 1}"),
            "final_text": str(item.get("final_text") or ""),
            "target_capability": str(item.get("target_capability") or ""),
            "evidence_source": str(item.get("evidence_source") or ""),
            "evidence_confidence": str(item.get("evidence_confidence") or "medium"),
            "talk_track_30s": str(item.get("talk_track_30s") or ""),
            "follow_up_questions": [str(q) for q in ensure_list(item.get("follow_up_questions")) if q],
            "risk_notes": [str(r) for r in ensure_list(item.get("risk_notes")) if r],
            "fallback_answer": str(item.get("fallback_answer") or ""),
        })
    return {"bullet_inventory": inventory}
