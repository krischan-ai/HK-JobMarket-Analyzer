from __future__ import annotations

from fastapi import APIRouter, HTTPException

from src.resume_agent import analyze_resume_only, match_jobs_only, run_resume_agent
from src.resume_agent.models import (
    JobMatchRequest,
    JobMatchResponse,
    ResumeAnalyzeRequest,
    ResumeAnalyzeResponse,
    ResumePolishRequest,
    ResumePolishResponse,
)
from src.resume_agent.utils import ResumeAgentError

router = APIRouter(prefix="/api/resume", tags=["resume"])


@router.post("/polish", response_model=ResumePolishResponse)
async def polish_resume(request: ResumePolishRequest):
    try:
        result = run_resume_agent(
            resume_text=request.resume_text,
            jd_text=request.jd_text,
            jd_url=request.jd_url,
            target_role=request.target_role,
            max_retries=request.max_retries,
        )
        return ResumePolishResponse(
            success=True,
            polish_suggestions=result.get("polish_suggestions") or [],
            score=result.get("score"),
            gap_analysis=result.get("gap"),
            matched_jobs=result.get("matched_jobs") or [],
        )
    except ResumeAgentError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Resume polish failed: {exc}") from exc


@router.post("/analyze", response_model=ResumeAnalyzeResponse)
async def analyze_resume(request: ResumeAnalyzeRequest):
    try:
        result = analyze_resume_only(
            resume_text=request.resume_text,
            jd_text=request.jd_text,
            target_role=request.target_role,
        )
        return ResumeAnalyzeResponse(
            success=True,
            resume=result.get("resume"),
            jd=result.get("jd"),
            gap_analysis=result.get("gap"),
            matched_jobs=result.get("matched_jobs") or [],
        )
    except ResumeAgentError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Resume analysis failed: {exc}") from exc


@router.post("/match-jobs", response_model=JobMatchResponse)
async def match_resume_jobs(request: JobMatchRequest):
    try:
        return JobMatchResponse(success=True, matched_jobs=match_jobs_only(request.jd_text, request.top_k))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Job matching failed: {exc}") from exc
