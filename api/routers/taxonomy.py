"""候选词库审核与晋升接口（v1.5 第二/三期，doc §11.11.6）。

消费 TaxonomyDiscoveryAgent 沉淀的候选池：
- GET  /api/taxonomy/candidates   候选池 + 已晋升 + 别名 + 拒绝列表汇总
- POST /api/taxonomy/confirm       人工确认候选 → 正式词库
- POST /api/taxonomy/reject        人工拒绝候选 → 拒绝列表（永久抑制）
- POST /api/taxonomy/merge-alias   候选/术语 → 正式标签别名
- POST /api/taxonomy/auto-promote  按 support/公司数/置信度自动晋升低风险候选

晋升或确认后会失效趋势/场景/软技能派生缓存（taxonomy stamp，见 stats._taxonomy_stamp）。
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from api.dependencies import load_jobs_df
from src.analyzer.taxonomy_discovery_agent import TaxonomyDiscoveryAgent
from src.logger import get_logger

router = APIRouter(prefix="/api/taxonomy", tags=["taxonomy"])
logger = get_logger("api.taxonomy")


def _agent() -> TaxonomyDiscoveryAgent:
    return TaxonomyDiscoveryAgent()


def _company_by_job() -> dict[str, str]:
    """job_id -> company 映射，用于自动晋升的「不同公司数」判定。"""
    try:
        df = load_jobs_df()
    except Exception:
        return {}
    if df.empty or "job_id" not in df.columns or "company" not in df.columns:
        return {}
    mapping: dict[str, str] = {}
    for _, row in df.iterrows():
        job_id = str(row.get("job_id", "") or "").strip()
        company = str(row.get("company", "") or "").strip()
        if job_id and company:
            mapping[job_id] = company
    return mapping


class ConfirmRequest(BaseModel):
    name: str
    by: str = "manual"


class RejectRequest(BaseModel):
    name: str
    reason: str = ""


class MergeAliasRequest(BaseModel):
    alias: str
    canonical: str
    category: str = ""
    evidence: str = ""


class AutoPromoteRequest(BaseModel):
    min_support: int = 3
    min_companies: int = 2
    min_confidence: float = 0.85
    dry_run: bool = False


@router.get("/candidates")
def list_candidates():
    return _agent().review_overview()


@router.post("/confirm")
def confirm_candidate(req: ConfirmRequest):
    return _agent().confirm_candidate(req.name, by=req.by)


@router.post("/reject")
def reject_candidate(req: RejectRequest):
    return _agent().reject_candidate(req.name, reason=req.reason)


@router.post("/merge-alias")
def merge_alias(req: MergeAliasRequest):
    return _agent().merge_alias(req.alias, req.canonical, category=req.category, evidence=req.evidence)


@router.post("/auto-promote")
def auto_promote(req: AutoPromoteRequest):
    return _agent().promote_candidates(
        company_by_job=_company_by_job(),
        min_support=req.min_support,
        min_companies=req.min_companies,
        min_confidence=req.min_confidence,
        dry_run=req.dry_run,
    )
