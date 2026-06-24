from __future__ import annotations

from typing import Any, Iterator

from .llm import ResumeLLMClient
from .nodes import (
    analyze_jd,
    build_market_context,
    build_market_insights,
    gap_analysis,
    generate_polish,
    has_target_jd,
    match_jobs,
    parse_resume,
    score_and_verify,
    synthesize_market_jd,
)
from .state import AgentState
from .utils import ResumeAgentError


def _initial_state(
    *,
    resume_text: str,
    jd_text: str | None,
    jd_url: str | None = None,
    target_role: str | None = None,
    max_retries: int = 1,
) -> AgentState:
    return {
        "resume_text": resume_text,
        "target_jd_text": jd_text or "",
        "target_jd_url": jd_url,
        "target_role": target_role,
        "resume": None,
        "jd": None,
        "matched_jobs": None,
        "rerank_used": None,
        "market_context": None,
        "market_insights": None,
        "gap": None,
        "polish_suggestions": None,
        "score": None,
        "retry_count": 0,
        "max_retries": max_retries,
        "error": None,
    }


def _resolve_target(state: AgentState, client: ResumeLLMClient) -> None:
    """有目标 JD 时直接分析；否则用知识库相似岗位合成目标画像。"""
    if has_target_jd(state):
        state.update(analyze_jd(state, client))
        return
    if not state.get("matched_jobs"):
        raise ResumeAgentError(
            "未提供目标 JD，且知识库暂无相似岗位可供分析。请粘贴目标 JD 或填写目标职位后重试。"
        )
    state.update(synthesize_market_jd(state, client))


def run_resume_agent(
    *,
    resume_text: str,
    jd_text: str | None = None,
    jd_url: str | None = None,
    target_role: str | None = None,
    max_retries: int = 1,
    llm: ResumeLLMClient | None = None,
) -> dict[str, Any]:
    client = llm or ResumeLLMClient()
    state = _initial_state(
        resume_text=resume_text,
        jd_text=jd_text,
        jd_url=jd_url,
        target_role=target_role,
        max_retries=max_retries,
    )

    state.update(parse_resume(state, client))
    state.update(match_jobs(state))
    state.update(build_market_context(state))
    state.update(build_market_insights(state))
    _resolve_target(state, client)

    while True:
        state.update(gap_analysis(state, client))
        state.update(generate_polish(state, client))
        state.update(score_and_verify(state, client))

        score = (state.get("score") or {}).get("overall_score", 0)
        if score >= 7 or state["retry_count"] >= state["max_retries"]:
            break
        state["retry_count"] += 1

    return dict(state)


def _final_payload(state: AgentState) -> dict[str, Any]:
    return {
        "success": True,
        "polish_suggestions": state.get("polish_suggestions") or [],
        "score": state.get("score"),
        "gap_analysis": state.get("gap"),
        "matched_jobs": state.get("matched_jobs") or [],
        "market_context": state.get("market_context"),
        "market_insights": state.get("market_insights"),
        "rerank_used": state.get("rerank_used"),
    }


def run_resume_agent_stream(
    *,
    resume_text: str,
    jd_text: str | None = None,
    jd_url: str | None = None,
    target_role: str | None = None,
    max_retries: int = 1,
    llm: ResumeLLMClient | None = None,
) -> Iterator[dict[str, Any]]:
    """逐节点产出事件，支持流式/渐进式展示：先完成的阶段先输出。"""
    client = llm or ResumeLLMClient()
    state = _initial_state(
        resume_text=resume_text,
        jd_text=jd_text,
        jd_url=jd_url,
        target_role=target_role,
        max_retries=max_retries,
    )

    yield {"stage": "status", "step": "parse_resume", "message": "正在解析简历…"}
    state.update(parse_resume(state, client))

    yield {"stage": "status", "step": "match_jobs", "message": "正在混合检索 + rerank 召回相似岗位…"}
    state.update(match_jobs(state))
    yield {
        "stage": "matched_jobs",
        "matched_jobs": state.get("matched_jobs") or [],
        "rerank_used": state.get("rerank_used"),
    }

    state.update(build_market_context(state))
    yield {"stage": "status", "step": "market_insights", "message": "正在分析整库岗位市场数据…"}
    state.update(build_market_insights(state))
    yield {
        "stage": "market_insights",
        "market_insights": state.get("market_insights"),
        "market_context": state.get("market_context"),
    }

    yield {"stage": "status", "step": "target", "message": "正在分析目标岗位画像…"}
    _resolve_target(state, client)
    yield {"stage": "jd", "jd": state.get("jd")}

    while True:
        yield {"stage": "status", "step": "gap", "message": "正在进行差距分析…"}
        state.update(gap_analysis(state, client))
        yield {"stage": "gap", "gap_analysis": state.get("gap")}

        yield {"stage": "status", "step": "polish", "message": "正在生成逐段润色建议…"}
        state.update(generate_polish(state, client))
        yield {"stage": "polish", "polish_suggestions": state.get("polish_suggestions") or []}

        yield {"stage": "status", "step": "score", "message": "正在多维评分…"}
        state.update(score_and_verify(state, client))
        yield {"stage": "score", "score": state.get("score")}

        score_val = (state.get("score") or {}).get("overall_score", 0)
        if score_val >= 7 or state["retry_count"] >= state["max_retries"]:
            break
        state["retry_count"] += 1
        yield {"stage": "status", "step": "retry", "message": "评分未达标，正在重试润色…"}

    yield {"stage": "done", "result": _final_payload(state)}


def analyze_resume_only(
    *,
    resume_text: str,
    jd_text: str | None = None,
    target_role: str | None = None,
    llm: ResumeLLMClient | None = None,
) -> dict[str, Any]:
    client = llm or ResumeLLMClient()
    state = _initial_state(resume_text=resume_text, jd_text=jd_text, target_role=target_role)
    state.update(parse_resume(state, client))
    state.update(match_jobs(state))
    state.update(build_market_context(state))
    state.update(build_market_insights(state))
    _resolve_target(state, client)
    state.update(gap_analysis(state, client))
    return dict(state)


def match_jobs_only(jd_text: str, top_k: int = 5) -> list[dict[str, Any]]:
    state = _initial_state(resume_text="", jd_text=jd_text)
    return match_jobs(state, top_k=top_k)["matched_jobs"]
