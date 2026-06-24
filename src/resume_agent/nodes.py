from __future__ import annotations

from typing import Any

from src.analyzer.role_classifier import RoleClassifier
from src.embeddings.vector_store import VectorStore
from src.logger import get_logger

from .llm import ResumeLLMClient
from .prompts import (
    GAP_ANALYSIS_PROMPT,
    GAP_ANALYSIS_SYSTEM_PROMPT,
    JD_ANALYSIS_PROMPT,
    JD_ANALYSIS_SYSTEM_PROMPT,
    POLISH_PROMPT,
    POLISH_SYSTEM_PROMPT,
    RESUME_PARSE_PROMPT,
    RESUME_PARSE_SYSTEM_PROMPT,
    SCORE_PROMPT,
    SCORE_SYSTEM_PROMPT,
    as_json,
)
from .state import AgentState
from .utils import ResumeAgentError, clamp_score, compact_text, ensure_list, parse_llm_json

logger = get_logger(__name__)


def parse_resume(state: AgentState, llm: ResumeLLMClient) -> dict[str, Any]:
    content = llm.chat_json(
        RESUME_PARSE_SYSTEM_PROMPT,
        RESUME_PARSE_PROMPT.format(resume_text=compact_text(state["resume_text"], 12000)),
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


def match_jobs(state: AgentState, top_k: int = 5) -> dict[str, Any]:
    try:
        store = VectorStore()
        results = store.search(state["target_jd_text"], top_k=top_k)
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
    return {"matched_jobs": matched}


def gap_analysis(state: AgentState, llm: ResumeLLMClient) -> dict[str, Any]:
    content = llm.chat_json(
        GAP_ANALYSIS_SYSTEM_PROMPT,
        GAP_ANALYSIS_PROMPT.format(
            resume=as_json(state.get("resume") or {}),
            jd=as_json(state.get("jd") or {}),
            matched_jobs=as_json(state.get("matched_jobs") or []),
        ),
    )
    gap = parse_llm_json(content)
    if not isinstance(gap, dict):
        raise ResumeAgentError("Gap analyzer returned non-object JSON")
    for key in ("matched_skills", "missing_skills", "weak_skills"):
        gap[key] = [str(item) for item in ensure_list(gap.get(key)) if item]
    gap["keyword_suggestions"] = [item for item in ensure_list(gap.get("keyword_suggestions")) if isinstance(item, dict)]
    return {"gap": gap}


def generate_polish(state: AgentState, llm: ResumeLLMClient) -> dict[str, Any]:
    content = llm.chat_json(
        POLISH_SYSTEM_PROMPT,
        POLISH_PROMPT.format(
            resume_text=compact_text(state["resume_text"], 14000),
            resume=as_json(state.get("resume") or {}),
            jd=as_json(state.get("jd") or {}),
            gap=as_json(state.get("gap") or {}),
        ),
        temperature=0.25,
    )
    suggestions = parse_llm_json(content)
    if not isinstance(suggestions, list):
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

    normalized = {
        "overall_score": clamp_score(score.get("overall_score")),
        "keyword_coverage": clamp_score(score.get("keyword_coverage")),
        "experience_alignment": clamp_score(score.get("experience_alignment")),
        "skill_relevance": clamp_score(score.get("skill_relevance")),
        "language_quality": clamp_score(score.get("language_quality")),
        "suggestions": [str(item) for item in ensure_list(score.get("suggestions")) if item],
    }
    return {"score": normalized}
