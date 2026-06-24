from __future__ import annotations

from typing import Any

from .llm import ResumeLLMClient
from .nodes import analyze_jd, gap_analysis, generate_polish, match_jobs, parse_resume, score_and_verify
from .state import AgentState


def _initial_state(
    *,
    resume_text: str,
    jd_text: str,
    jd_url: str | None = None,
    target_role: str | None = None,
    max_retries: int = 1,
) -> AgentState:
    return {
        "resume_text": resume_text,
        "target_jd_text": jd_text,
        "target_jd_url": jd_url,
        "target_role": target_role,
        "resume": None,
        "jd": None,
        "matched_jobs": None,
        "gap": None,
        "polish_suggestions": None,
        "score": None,
        "retry_count": 0,
        "max_retries": max_retries,
        "error": None,
    }


def run_resume_agent(
    *,
    resume_text: str,
    jd_text: str,
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
    state.update(analyze_jd(state, client))
    state.update(match_jobs(state))

    while True:
        state.update(gap_analysis(state, client))
        state.update(generate_polish(state, client))
        state.update(score_and_verify(state, client))

        score = (state.get("score") or {}).get("overall_score", 0)
        if score >= 7 or state["retry_count"] >= state["max_retries"]:
            break
        state["retry_count"] += 1

    return dict(state)


def analyze_resume_only(
    *,
    resume_text: str,
    jd_text: str,
    target_role: str | None = None,
    llm: ResumeLLMClient | None = None,
) -> dict[str, Any]:
    client = llm or ResumeLLMClient()
    state = _initial_state(resume_text=resume_text, jd_text=jd_text, target_role=target_role)
    state.update(parse_resume(state, client))
    state.update(analyze_jd(state, client))
    state.update(match_jobs(state))
    state.update(gap_analysis(state, client))
    return dict(state)


def match_jobs_only(jd_text: str, top_k: int = 5) -> list[dict[str, Any]]:
    state = _initial_state(resume_text="", jd_text=jd_text)
    return match_jobs(state, top_k=top_k)["matched_jobs"]
