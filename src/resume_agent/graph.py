from __future__ import annotations

import queue
import threading
from typing import Any, Callable, Iterator

from src.logger import get_logger

from .llm import ResumeLLMClient
from .nodes import (
    analyze_jd,
    build_interview_prep,
    build_job_research,
    build_market_context,
    build_market_insights,
    conceptualize_market_insights,
    gap_analysis,
    generate_polish,
    has_target_jd,
    llm_match_jobs,
    match_jobs,
    parse_resume,
    run_input_health,
    score_and_verify,
    summarize_tech_stack,
    synthesize_market_jd,
    understand_target_role,
)
from .state import AgentState
from .utils import ResumeAgentError

logger = get_logger(__name__)


def _initial_state(
    *,
    resume_text: str,
    jd_text: str | None,
    jd_url: str | None = None,
    target_role: str | None = None,
    target_role_id: str | None = None,
    target_market: str | None = None,
    application_status: str | None = None,
    max_retries: int = 1,
) -> AgentState:
    return {
        "resume_text": resume_text,
        "target_jd_text": jd_text or "",
        "target_jd_url": jd_url,
        "target_role": target_role,
        "target_role_id": target_role_id,
        "target_role_understanding": None,
        "match_advice": None,
        "target_market": target_market,
        "application_status": application_status,
        "resume": None,
        "jd": None,
        "matched_jobs": None,
        "rerank_used": None,
        "market_context": None,
        "market_insights": None,
        "tech_stack_summary": None,
        "input_health": None,
        "job_research": None,
        "gap": None,
        "polish_suggestions": None,
        "bullet_inventory": None,
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
    target_role_id: str | None = None,
    target_market: str | None = None,
    application_status: str | None = None,
    max_retries: int = 1,
    llm: ResumeLLMClient | None = None,
) -> dict[str, Any]:
    client = llm or ResumeLLMClient()
    state = _initial_state(
        resume_text=resume_text,
        jd_text=jd_text,
        jd_url=jd_url,
        target_role=target_role,
        target_role_id=target_role_id,
        target_market=target_market,
        application_status=application_status,
        max_retries=max_retries,
    )

    state.update(run_input_health(state))
    state.update(parse_resume(state, client))
    state.update(understand_target_role(state, client))
    state.update(match_jobs(state))
    state.update(llm_match_jobs(state, client))
    state.update(build_market_context(state))
    state.update(build_market_insights(state))
    state.update(conceptualize_market_insights(state, client))
    state.update(summarize_tech_stack(state, client))
    _resolve_target(state, client)
    state.update(build_job_research(state))

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
        "target_role_understanding": state.get("target_role_understanding"),
        "match_advice": state.get("match_advice"),
        "input_health": state.get("input_health"),
        "job_research": state.get("job_research"),
        "bullet_inventory": state.get("bullet_inventory") or [],
        "rerank_used": state.get("rerank_used"),
    }


_STREAM_END = object()


def _stream_step(
    step: str, fn: Callable[[], dict[str, Any]], client: ResumeLLMClient
) -> Iterator[dict[str, Any]]:
    """在后台线程运行一个调用 LLM 的节点，并把 token 增量作为 `token` 事件实时产出。

    通过 `yield from` 使用：`update = yield from _stream_step(...)`，返回节点的状态更新。
    """
    q: queue.Queue[Any] = queue.Queue()
    box: dict[str, Any] = {}

    def worker() -> None:
        client.on_delta = q.put
        try:
            box["result"] = fn()
        except BaseException as exc:  # noqa: BLE001 - 在主线程重新抛出
            box["error"] = exc
        finally:
            client.on_delta = None
            q.put(_STREAM_END)

    threading.Thread(target=worker, daemon=True).start()
    while True:
        item = q.get()
        if item is _STREAM_END:
            break
        yield {"stage": "token", "step": step, "delta": item}

    if "error" in box:
        raise box["error"]
    return box["result"]


def run_resume_agent_stream(
    *,
    resume_text: str,
    jd_text: str | None = None,
    jd_url: str | None = None,
    target_role: str | None = None,
    target_role_id: str | None = None,
    target_market: str | None = None,
    application_status: str | None = None,
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
        target_role_id=target_role_id,
        target_market=target_market,
        application_status=application_status,
        max_retries=max_retries,
    )

    state.update(run_input_health(state))
    yield {"stage": "input_health", "input_health": state.get("input_health")}

    yield {"stage": "status", "step": "parse_resume", "message": "正在解析简历…"}
    state.update((yield from _stream_step("parse_resume", lambda: parse_resume(state, client), client)))

    yield {"stage": "status", "step": "target_understanding", "message": "正在理解目标职位语义画像…"}
    state.update((yield from _stream_step("target_understanding", lambda: understand_target_role(state, client), client)))
    yield {"stage": "target_understanding", "target_role_understanding": state.get("target_role_understanding")}

    yield {"stage": "status", "step": "match_jobs", "message": "正在混合检索 + rerank 召回相似岗位…"}
    state.update(match_jobs(state))
    yield {"stage": "status", "step": "llm_match_jobs", "message": "正在用大模型理解并排序真实召回岗位…"}
    state.update((yield from _stream_step("llm_match_jobs", lambda: llm_match_jobs(state, client), client)))
    yield {
        "stage": "matched_jobs",
        "matched_jobs": state.get("matched_jobs") or [],
        "rerank_used": state.get("rerank_used"),
        "match_advice": state.get("match_advice"),
    }

    state.update(build_market_context(state))
    yield {"stage": "status", "step": "market_insights", "message": "正在分析整库岗位市场数据…"}
    state.update(build_market_insights(state))
    state.update((yield from _stream_step("market_insights_summary", lambda: conceptualize_market_insights(state, client), client)))
    yield {"stage": "status", "step": "tech_stack", "message": "正在概括岗位技术栈语义主题…"}
    state.update((yield from _stream_step("tech_stack", lambda: summarize_tech_stack(state, client), client)))
    yield {
        "stage": "market_insights",
        "market_insights": state.get("market_insights"),
        "market_context": state.get("market_context"),
        "tech_stack_summary": state.get("tech_stack_summary"),
    }

    yield {"stage": "status", "step": "target", "message": "正在分析目标岗位画像…"}
    yield from _stream_step("target", lambda: (_resolve_target(state, client), {})[1], client)
    yield {"stage": "jd", "jd": state.get("jd")}

    state.update(build_job_research(state))
    yield {"stage": "job_research", "job_research": state.get("job_research")}

    while True:
        yield {"stage": "status", "step": "gap", "message": "正在进行差距分析…"}
        state.update((yield from _stream_step("gap", lambda: gap_analysis(state, client), client)))
        yield {"stage": "gap", "gap_analysis": state.get("gap")}

        yield {"stage": "status", "step": "polish", "message": "正在生成逐段润色建议…"}
        state.update((yield from _stream_step("polish", lambda: generate_polish(state, client), client)))
        yield {"stage": "polish", "polish_suggestions": state.get("polish_suggestions") or []}

        yield {"stage": "status", "step": "score", "message": "正在多维评分…"}
        state.update((yield from _stream_step("score", lambda: score_and_verify(state, client), client)))
        yield {"stage": "score", "score": state.get("score")}

        score_val = (state.get("score") or {}).get("overall_score", 0)
        if score_val >= 7 or state["retry_count"] >= state["max_retries"]:
            break
        state["retry_count"] += 1
        yield {"stage": "status", "step": "retry", "message": "评分未达标，正在重试润色…"}

    yield {"stage": "status", "step": "interview_prep", "message": "正在生成逐 bullet 面试深挖…"}
    try:
        state.update((yield from _stream_step("interview_prep", lambda: build_interview_prep(state, client), client)))
    except ResumeAgentError as exc:
        logger.warning("Interview prep skipped: %s", exc)
        state["bullet_inventory"] = []
    yield {"stage": "interview_prep", "bullet_inventory": state.get("bullet_inventory") or []}

    yield {"stage": "done", "result": _final_payload(state)}


def analyze_resume_only(
    *,
    resume_text: str,
    jd_text: str | None = None,
    target_role: str | None = None,
    target_role_id: str | None = None,
    llm: ResumeLLMClient | None = None,
) -> dict[str, Any]:
    client = llm or ResumeLLMClient()
    state = _initial_state(resume_text=resume_text, jd_text=jd_text, target_role=target_role, target_role_id=target_role_id)
    state.update(run_input_health(state))
    state.update(parse_resume(state, client))
    state.update(understand_target_role(state, client))
    state.update(match_jobs(state))
    state.update(llm_match_jobs(state, client))
    state.update(build_market_context(state))
    state.update(build_market_insights(state))
    state.update(conceptualize_market_insights(state, client))
    state.update(summarize_tech_stack(state, client))
    _resolve_target(state, client)
    state.update(build_job_research(state))
    state.update(gap_analysis(state, client))
    return dict(state)


def match_jobs_only(jd_text: str, top_k: int = 5) -> list[dict[str, Any]]:
    state = _initial_state(resume_text="", jd_text=jd_text)
    return match_jobs(state, top_k=top_k)["matched_jobs"]


def check_input_health(
    *,
    resume_text: str = "",
    jd_text: str | None = None,
    target_role: str | None = None,
    target_role_id: str | None = None,
    target_market: str | None = None,
    application_status: str | None = None,
) -> dict[str, Any]:
    """Stage 0 输入体检（独立端点用），确定性、不调用 LLM。"""
    state = _initial_state(
        resume_text=resume_text,
        jd_text=jd_text,
        target_role=target_role,
        target_role_id=target_role_id,
        target_market=target_market,
        application_status=application_status,
    )
    return run_input_health(state)["input_health"]


def research_jobs(
    *,
    resume_text: str | None = None,
    jd_text: str | None = None,
    target_role: str | None = None,
    target_role_id: str | None = None,
    top_k: int = 8,
    llm: ResumeLLMClient | None = None,
) -> dict[str, Any]:
    """Stage 1 独立岗位调研：召回 + 市场上下文 + 目标画像 → JobResearchReport。"""
    client = llm or ResumeLLMClient()
    state = _initial_state(resume_text=resume_text or "", jd_text=jd_text, target_role=target_role, target_role_id=target_role_id)
    # 有简历正文时解析以补充检索关键词；否则跳过 LLM 解析。
    if len((resume_text or "").strip()) >= 50:
        state.update(parse_resume(state, client))
    state.update(understand_target_role(state, client))
    state.update(match_jobs(state, top_k=top_k))
    state.update(llm_match_jobs(state, client))
    state.update(build_market_context(state))
    state.update(build_market_insights(state))
    state.update(conceptualize_market_insights(state, client))
    state.update(summarize_tech_stack(state, client))
    _resolve_target(state, client)
    state.update(build_job_research(state))
    return {
        "job_research": state.get("job_research"),
        "matched_jobs": state.get("matched_jobs") or [],
        "rerank_used": state.get("rerank_used"),
    }


def run_interview_prep(
    *,
    resume_text: str,
    polish_suggestions: list[dict[str, Any]],
    jd_text: str | None = None,
    target_role: str | None = None,
    llm: ResumeLLMClient | None = None,
) -> list[dict[str, Any]]:
    """Stage 8 独立面试深挖：基于已有润色建议生成 bullet inventory。"""
    client = llm or ResumeLLMClient()
    state = _initial_state(resume_text=resume_text, jd_text=jd_text, target_role=target_role)
    state["polish_suggestions"] = polish_suggestions
    if jd_text:
        state.update(analyze_jd(state, client))
    return build_interview_prep(state, client)["bullet_inventory"]
