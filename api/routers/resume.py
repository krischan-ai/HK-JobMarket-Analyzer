from __future__ import annotations

import json

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from src.resume_agent import analyze_resume_only, match_jobs_only, run_resume_agent
from src.resume_agent.graph import run_resume_agent_stream
from src.resume_agent.models import (
    JobMatchRequest,
    JobMatchResponse,
    PdfExtractResponse,
    ResumeAnalyzeRequest,
    ResumeAnalyzeResponse,
    ResumePolishRequest,
    ResumePolishResponse,
)
from src.resume_agent.pdf_parser import extract_resume_text_from_pdf
from src.resume_agent.utils import ResumeAgentError

# 上传 PDF 体积上限（10 MB），避免超大文件占用内存。
_MAX_PDF_BYTES = 10 * 1024 * 1024

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
            market_context=result.get("market_context"),
            market_insights=result.get("market_insights"),
            rerank_used=result.get("rerank_used"),
        )
    except ResumeAgentError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Resume polish failed: {exc}") from exc


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


@router.post("/polish-stream")
async def polish_resume_stream(request: ResumePolishRequest):
    """流式润色：逐阶段产出结果（SSE），先完成的阶段先返回。"""

    def event_gen():
        try:
            for event in run_resume_agent_stream(
                resume_text=request.resume_text,
                jd_text=request.jd_text,
                jd_url=request.jd_url,
                target_role=request.target_role,
                max_retries=request.max_retries,
            ):
                yield _sse(event)
        except ResumeAgentError as exc:
            yield _sse({"stage": "error", "error": str(exc)})
        except Exception as exc:  # noqa: BLE001 - 兜底，确保错误也能流式返回
            yield _sse({"stage": "error", "error": f"Resume polish failed: {exc}"})

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


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
            market_context=result.get("market_context"),
            market_insights=result.get("market_insights"),
            rerank_used=result.get("rerank_used"),
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


@router.post("/extract-pdf", response_model=PdfExtractResponse)
async def extract_pdf(file: UploadFile = File(...)):
    """从上传的文本型 PDF 抽取简历文本，文件仅在内存处理、不落盘。"""
    filename = (file.filename or "").lower()
    if not filename.endswith(".pdf") and (file.content_type or "") != "application/pdf":
        raise HTTPException(status_code=400, detail="仅支持 PDF 文件")

    data = await file.read()
    if len(data) > _MAX_PDF_BYTES:
        raise HTTPException(status_code=400, detail="PDF 文件过大，请上传 10 MB 以内的文件")

    try:
        text = extract_resume_text_from_pdf(data)
    except ResumeAgentError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"PDF extraction failed: {exc}") from exc

    return PdfExtractResponse(success=True, resume_text=text, char_count=len(text))
