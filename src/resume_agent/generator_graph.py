from __future__ import annotations

import queue
import threading
from typing import Any, Callable, Iterator

from .generator_models import ResumeGenerateRequest, ResumeGenerateResponse, ResumeGenerationState
from .generator_nodes import (
    apply_selection_policy,
    audit_generated_resume,
    build_capability_match_matrix,
    build_selected_experience_plan,
    build_target_job_profile,
    check_generation_input,
    generate_target_resume,
    parse_resume_profile,
    render_generated_resume_markdown,
    run_quality_gates,
)
from .llm import ResumeLLMClient
from .utils import ResumeAgentError


def _initial_state(request: ResumeGenerateRequest) -> ResumeGenerationState:
    return {
        "resume_text": request.resume_text,
        "target_role": request.target_role,
        "target_role_id": request.target_role_id,
        "target_market": request.target_market or "Hong Kong",
        "language": request.language,
        "style": request.style,
        "narrative_angle": request.narrative_angle,
        "top_k_jobs": request.top_k_jobs,
        "profile_context": request.profile_context,
        "project_context": request.project_context,
        "auto_continue_without_confirmation": request.auto_continue_without_confirmation,
        "confidence": "medium",
        "error": None,
    }


def _response_from_state(state: ResumeGenerationState, *, success: bool = True, error: str | None = None) -> dict[str, Any]:
    return ResumeGenerateResponse(
        success=success,
        generated_resume=state.get("generated_resume"),
        markdown=state.get("markdown") or "",
        target_job_profile=state.get("target_job_profile"),
        capability_matches=state.get("capability_matches") or [],
        selected_experience_plan=state.get("selected_experience_plan"),
        selected_experience=state.get("selected_experience") or [],
        claim_audit=state.get("claim_audit") or [],
        quality_gate=state.get("quality_gate"),
        similar_jobs=state.get("similar_jobs") or [],
        input_health=state.get("input_health"),
        confidence=state.get("confidence") or "medium",
        error=error,
    ).model_dump()


def run_resume_generator(
    request: ResumeGenerateRequest | None = None,
    *,
    resume_text: str | None = None,
    target_role: str | None = None,
    target_role_id: str | None = None,
    target_market: str | None = None,
    language: str = "en",
    style: str = "professional",
    narrative_angle: str | None = None,
    top_k_jobs: int = 8,
    profile_context: dict[str, Any] | None = None,
    project_context: list[dict[str, Any]] | None = None,
    auto_continue_without_confirmation: bool = True,
    llm: ResumeLLMClient | None = None,
) -> dict[str, Any]:
    if request is None:
        request = ResumeGenerateRequest(
            resume_text=resume_text or "",
            target_role=target_role or "",
            target_role_id=target_role_id,
            target_market=target_market,
            language=language,  # type: ignore[arg-type]
            style=style,  # type: ignore[arg-type]
            narrative_angle=narrative_angle,  # type: ignore[arg-type]
            top_k_jobs=top_k_jobs,
            profile_context=profile_context,
            project_context=project_context or [],
            auto_continue_without_confirmation=auto_continue_without_confirmation,
        )
    client = llm or ResumeLLMClient()
    state = _initial_state(request)

    state.update(check_generation_input(state))
    if (state.get("input_health") or {}).get("status") == "blocked":
        return _response_from_state(state, success=False, error="Input is blocked.")

    state.update(parse_resume_profile(state, client))
    state.update(build_target_job_profile(state, client))
    state.update(build_capability_match_matrix(state, client))
    state.update(build_selected_experience_plan(state, client))
    state.update(apply_selection_policy(state))
    state.update(generate_target_resume(state, client))
    state.update(audit_generated_resume(state, client))
    state.update(run_quality_gates(state))
    state.update(render_generated_resume_markdown(state))
    return _response_from_state(state)


def parse_profile_only(
    *,
    resume_text: str,
    profile_context: dict[str, Any] | None = None,
    project_context: list[dict[str, Any]] | None = None,
    llm: ResumeLLMClient | None = None,
) -> dict[str, Any]:
    request = ResumeGenerateRequest(
        resume_text=resume_text,
        target_role="Profile Parse",
        profile_context=profile_context,
        project_context=project_context or [],
    )
    state = _initial_state(request)
    state.update(parse_resume_profile(state, llm or ResumeLLMClient()))
    return {"success": True, "resume_profile": state.get("resume_profile")}


def build_target_profile_only(
    *,
    resume_text: str = "",
    target_role: str,
    target_role_id: str | None = None,
    target_market: str | None = None,
    top_k_jobs: int = 8,
    llm: ResumeLLMClient | None = None,
) -> dict[str, Any]:
    request = ResumeGenerateRequest(
        resume_text=resume_text or ("target profile " + target_role).ljust(50, "."),
        target_role=target_role,
        target_role_id=target_role_id,
        target_market=target_market,
        top_k_jobs=top_k_jobs,
    )
    state = _initial_state(request)
    state["resume_profile"] = {
        "contact": {},
        "current_titles": [],
        "skills": [],
        "work_experience": [],
        "projects": [],
        "education": [],
        "certifications": [],
    }
    state.update(build_target_job_profile(state, llm or ResumeLLMClient()))
    return {
        "success": True,
        "target_job_profile": state.get("target_job_profile"),
        "similar_jobs": state.get("similar_jobs") or [],
        "confidence": state.get("confidence") or "medium",
    }


_STREAM_END = object()


def _stream_step(
    step: str, fn: Callable[[], dict[str, Any]], client: ResumeLLMClient
) -> Iterator[dict[str, Any]]:
    q: queue.Queue[Any] = queue.Queue()
    box: dict[str, Any] = {}

    def worker() -> None:
        client.on_delta = q.put
        try:
            box["result"] = fn()
        except BaseException as exc:  # noqa: BLE001
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


def run_resume_generator_stream(request: ResumeGenerateRequest, llm: ResumeLLMClient | None = None) -> Iterator[dict[str, Any]]:
    client = llm or ResumeLLMClient()
    state = _initial_state(request)

    try:
        state.update(check_generation_input(state))
        yield {"stage": "input_health", "input_health": state.get("input_health")}
        if (state.get("input_health") or {}).get("status") == "blocked":
            yield {"stage": "error", "error": "Input is blocked.", "result": _response_from_state(state, success=False)}
            return

        for stage, state_key, label, fn in (
            ("profile", "resume_profile", "parse_profile", lambda: parse_resume_profile(state, client)),
            ("target_profile", "target_job_profile", "target_profile", lambda: build_target_job_profile(state, client)),
            ("capability_matches", "capability_matches", "capability_matches", lambda: build_capability_match_matrix(state, client)),
            ("selection_plan", "selected_experience_plan", "selection_plan", lambda: build_selected_experience_plan(state, client)),
            ("generated_resume", "generated_resume", "generated_resume", lambda: generate_target_resume(state, client)),
            ("claim_audit", "claim_audit", "claim_audit", lambda: audit_generated_resume(state, client)),
        ):
            yield {"stage": "status", "step": label, "message": f"Running {label}..."}
            state.update((yield from _stream_step(label, fn, client)))
            if stage == "selection_plan":
                state.update(apply_selection_policy(state))
                yield {"stage": "selection_plan", "selection_plan": state.get("selected_experience_plan"), "selected_experience": state.get("selected_experience")}
            else:
                yield {"stage": stage, stage: state.get(state_key)}

        state.update(run_quality_gates(state))
        yield {"stage": "quality_gate", "quality_gate": state.get("quality_gate")}
        state.update(render_generated_resume_markdown(state))
        yield {"stage": "markdown", "markdown": state.get("markdown")}
        yield {"stage": "done", "result": _response_from_state(state)}
    except ResumeAgentError as exc:
        yield {"stage": "error", "error": str(exc)}
    except Exception as exc:  # noqa: BLE001
        yield {"stage": "error", "error": f"Resume generation failed: {exc}"}
