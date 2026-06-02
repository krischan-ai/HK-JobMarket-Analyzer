from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class RoleDistributionItem(BaseModel):
    role_id: str
    role_name: str
    count: int
    percentage: float


class RoleSalaryItem(BaseModel):
    role_id: str
    role_name: str
    salary_avg: float
    salary_min: float
    salary_max: float
    count: int


class LLMStatus(BaseModel):
    total_jobs: int
    classified: int
    coverage_rate: float
    last_analysis: Optional[str] = None
    llm_available: bool


class ClassificationResult(BaseModel):
    success: bool
    total: int
    classified: int
    duration_ms: float
    message: str = ""
