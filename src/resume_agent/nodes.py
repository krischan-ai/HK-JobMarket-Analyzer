from __future__ import annotations

from collections import Counter
from typing import Any

from src.analyzer.role_classifier import RoleClassifier
from src.analyzer.rule_engine import RuleBasedSkillExtractor
from src.embeddings.vector_store import VectorStore
from src.knowledge_base.hybrid_search import HybridJobSearch, HybridSearchOptions
from src.logger import get_logger

from .llm import ResumeLLMClient
from .market_insights import compute_market_insights
from .prompts import (
    GAP_ANALYSIS_PROMPT,
    GAP_ANALYSIS_SYSTEM_PROMPT,
    JD_ANALYSIS_PROMPT,
    JD_ANALYSIS_SYSTEM_PROMPT,
    MARKET_JD_SYNTHESIS_PROMPT,
    MARKET_JD_SYNTHESIS_SYSTEM_PROMPT,
    POLISH_PROMPT,
    POLISH_SYSTEM_PROMPT,
    RESUME_PARSE_PROMPT,
    RESUME_PARSE_SYSTEM_PROMPT,
    SCORE_PROMPT,
    SCORE_SYSTEM_PROMPT,
    as_json,
)
from .state import AgentState
from .utils import ResumeAgentError, clamp_score, compact_text, ensure_list, extract_json_objects, parse_llm_json

logger = get_logger(__name__)

# JD 文本达到该长度才视为「用户已提供目标 JD」，否则进入知识库模式。
JD_MIN_LENGTH = 30


def has_target_jd(state: AgentState) -> bool:
    return len((state.get("target_jd_text") or "").strip()) >= JD_MIN_LENGTH


def build_search_query(state: AgentState) -> str:
    """构造知识库检索查询。

    优先级：目标 JD 文本 > 目标职位 > 简历职位/技能 > 简历原文。
    """
    if has_target_jd(state):
        return (state.get("target_jd_text") or "").strip()

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


def analyze_jd(state: AgentState, llm: ResumeLLMClient) -> dict[str, Any]:
    content = llm.chat_json(
        JD_ANALYSIS_SYSTEM_PROMPT,
        JD_ANALYSIS_PROMPT.format(jd_text=compact_text(state["target_jd_text"], 10000)),
    )
    jd_data = parse_llm_json(content)
    if not isinstance(jd_data, dict):
        raise ResumeAgentError("JD analyzer returned non-object JSON")

    role = RoleClassifier().classify(state["target_jd_text"])
    jd_data["role_category"] = role.role_id
    jd_data["role_name"] = role.role_name
    if state.get("target_role"):
        jd_data["target_role"] = state["target_role"]
    for key in ("required_skills", "preferred_skills", "responsibilities", "language_requirements", "key_requirements"):
        jd_data[key] = [str(item) for item in ensure_list(jd_data.get(key)) if item]
    return {"jd": jd_data}


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


def build_market_insights(state: AgentState) -> dict[str, Any]:
    """整库岗位数据分析：需求量最大的岗位方向排名 + 技术栈次数排名。"""
    try:
        return {"market_insights": compute_market_insights(top_n=12)}
    except Exception as exc:
        logger.warning("Market insights skipped: %s", exc)
        return {"market_insights": None}


def build_market_context(state: AgentState) -> dict[str, Any]:
    """基于召回的香港相似岗位，确定性汇总市场上下文（不调用 LLM）。

    产出高频技能、常见职位名、典型岗位措辞，供差距分析与润色参考。
    """
    matched = state.get("matched_jobs") or []
    if not matched:
        return {"market_context": None}

    extractor = RuleBasedSkillExtractor()
    skill_counter: Counter[str] = Counter()
    titles: list[str] = []
    phrases: list[str] = []

    for job in matched:
        title = (job.get("title") or "").strip()
        snippet = (job.get("snippet") or "").strip()
        if title:
            titles.append(title)
        if snippet:
            phrases.append(compact_text(snippet, 240))
        for skill in extractor.extract_flat(f"{title}\n{snippet}"):
            skill_counter[skill] += 1

    context = {
        "job_count": len(matched),
        "top_skills": [{"skill": skill, "count": count} for skill, count in skill_counter.most_common(15)],
        "common_titles": [title for title, _ in Counter(titles).most_common(8)],
        "sample_phrases": phrases[:5],
    }
    return {"market_context": context}


def gap_analysis(state: AgentState, llm: ResumeLLMClient) -> dict[str, Any]:
    content = llm.chat_json(
        GAP_ANALYSIS_SYSTEM_PROMPT,
        GAP_ANALYSIS_PROMPT.format(
            resume=as_json(state.get("resume") or {}),
            jd=as_json(state.get("jd") or {}),
            matched_jobs=as_json(state.get("matched_jobs") or []),
            market_context=as_json(state.get("market_context") or {}),
            market_insights=as_json(state.get("market_insights") or {}),
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
    return {"gap": gap}


def generate_polish(state: AgentState, llm: ResumeLLMClient) -> dict[str, Any]:
    content = llm.chat_json(
        POLISH_SYSTEM_PROMPT,
        POLISH_PROMPT.format(
            resume_text=compact_text(state["resume_text"], 14000),
            resume=as_json(state.get("resume") or {}),
            jd=as_json(state.get("jd") or {}),
            gap=as_json(state.get("gap") or {}),
            market_context=as_json(state.get("market_context") or {}),
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
            "keywords_added": [str(keyword) for keyword in ensure_list(item.get("keywords_added")) if keyword],
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
