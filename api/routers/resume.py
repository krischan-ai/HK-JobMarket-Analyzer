from __future__ import annotations

import json

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from src.resume_agent import (
    analyze_resume_only,
    build_target_profile_only,
    check_input_health,
    match_jobs_only,
    parse_profile_only,
    research_jobs,
    run_interview_prep,
    run_resume_agent,
    run_resume_generator,
    run_resume_generator_stream,
)
from src.resume_agent.graph import run_resume_agent_stream
from src.resume_agent.generator_models import ResumeGenerateRequest, ResumeGenerateResponse
from src.resume_agent.models import (
    InputHealthEndpointResponse,
    InputHealthRequest,
    InterviewPrepRequest,
    InterviewPrepResponse,
    JobMatchRequest,
    JobMatchResponse,
    JobResearchEndpointResponse,
    JobResearchRequest,
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

@router.post("/generate", response_model=ResumeGenerateResponse)
async def generate_resume(request: ResumeGenerateRequest):
    """知识库驱动的目标岗位简历生成。"""
    try:
        return run_resume_generator(request)
    except ResumeAgentError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Resume generation failed: {exc}") from exc


@router.post("/generate-stream")
async def generate_resume_stream(request: ResumeGenerateRequest):
    """流式简历生成：逐阶段输出岗位画像、选材、简历与质量闸门。"""

    def event_gen():
        try:
            for event in run_resume_generator_stream(request):
                yield _sse(event)
        except ResumeAgentError as exc:
            yield _sse({"stage": "error", "error": str(exc)})
        except Exception as exc:  # noqa: BLE001
            yield _sse({"stage": "error", "error": f"Resume generation failed: {exc}"})

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/profile-parse")
async def parse_resume_profile_endpoint(request: ResumeGenerateRequest):
    """只解析个人资料，便于生成前预览。"""
    try:
        return parse_profile_only(
            resume_text=request.resume_text,
            profile_context=request.profile_context,
            project_context=request.project_context,
        )
    except ResumeAgentError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Resume profile parse failed: {exc}") from exc


@router.post("/target-profile")
async def target_profile_endpoint(request: ResumeGenerateRequest):
    """只生成目标岗位画像，便于确认目标方向。"""
    try:
        return build_target_profile_only(
            resume_text=request.resume_text,
            target_role=request.target_role,
            target_role_id=request.target_role_id,
            target_market=request.target_market,
            top_k_jobs=request.top_k_jobs,
        )
    except ResumeAgentError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Target profile generation failed: {exc}") from exc


@router.post("/polish", response_model=ResumePolishResponse)
async def polish_resume(request: ResumePolishRequest):
    try:
        result = run_resume_agent(
            resume_text=request.resume_text,
            jd_text=request.jd_text,
            jd_url=request.jd_url,
            target_role=request.target_role,
            target_role_id=request.target_role_id,
            target_market=request.target_market,
            application_status=request.application_status,
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
            target_role_understanding=result.get("target_role_understanding"),
            match_advice=result.get("match_advice"),
            input_health=result.get("input_health"),
            job_research=result.get("job_research"),
            bullet_inventory=result.get("bullet_inventory") or [],
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
                target_role_id=request.target_role_id,
                target_market=request.target_market,
                application_status=request.application_status,
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
            target_role_id=request.target_role_id,
        )
        return ResumeAnalyzeResponse(
            success=True,
            resume=result.get("resume"),
            jd=result.get("jd"),
            gap_analysis=result.get("gap"),
            matched_jobs=result.get("matched_jobs") or [],
            market_context=result.get("market_context"),
            market_insights=result.get("market_insights"),
            target_role_understanding=result.get("target_role_understanding"),
            match_advice=result.get("match_advice"),
            input_health=result.get("input_health"),
            job_research=result.get("job_research"),
            rerank_used=result.get("rerank_used"),
        )
    except ResumeAgentError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Resume analysis failed: {exc}") from exc


@router.post("/input-health", response_model=InputHealthEndpointResponse)
async def input_health(request: InputHealthRequest):
    """Stage 0 输入体检：确定性判断输入是否足够、缺口与必须追问的问题。"""
    try:
        health = check_input_health(
            resume_text=request.resume_text or "",
            jd_text=request.jd_text,
            target_role=request.target_role,
            target_role_id=request.target_role_id,
            target_market=request.target_market,
            application_status=request.application_status,
        )
        return InputHealthEndpointResponse(success=True, input_health=health)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Input health check failed: {exc}") from exc


@router.post("/job-research", response_model=JobResearchEndpointResponse)
async def job_research(request: JobResearchRequest):
    """Stage 1 岗位调研：知识库混合检索 + 市场画像 → 岗位调研报告。"""
    try:
        result = research_jobs(
            resume_text=request.resume_text,
            jd_text=request.jd_text,
            target_role=request.target_role,
            target_role_id=request.target_role_id,
            top_k=request.top_k,
        )
        return JobResearchEndpointResponse(
            success=True,
            job_research=result.get("job_research"),
            matched_jobs=result.get("matched_jobs") or [],
            rerank_used=result.get("rerank_used"),
        )
    except ResumeAgentError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Job research failed: {exc}") from exc


@router.post("/interview-prep", response_model=InterviewPrepResponse)
async def interview_prep(request: InterviewPrepRequest):
    """Stage 8 面试深挖：把润色后的每条 bullet 转为可被追问的讲法。"""
    try:
        inventory = run_interview_prep(
            resume_text=request.resume_text,
            polish_suggestions=[item.model_dump() for item in request.polish_suggestions],
            jd_text=request.jd_text,
            target_role=request.target_role,
        )
        return InterviewPrepResponse(success=True, bullet_inventory=inventory)
    except ResumeAgentError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Interview prep failed: {exc}") from exc


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



