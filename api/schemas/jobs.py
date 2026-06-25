from typing import Optional, Any
from datetime import datetime
from pydantic import BaseModel


class JobSummary(BaseModel):
    job_id: str
    title: str
    company: str
    location: str
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    source: str
    skills: Optional[dict[str, list[str]]] = None
    posted_at: Optional[str] = None
    employment_type: Optional[str] = None
    industry_category: Optional[str] = None
    application_volume: Optional[str] = None
    is_insurance_sales: Optional[bool] = None
    insurance_score: Optional[int] = None
    work_mode: Optional[str] = None
    posted_days_ago: Optional[int] = None
    company_size: Optional[str] = None
    education_required: Optional[str] = None
    languages_required: Optional[list[str]] = None
    tech_stack: Optional[list[str]] = None
    job_type: Optional[str] = None
    insurance_reasons: Optional[list[str]] = None


class JobDetail(JobSummary):
    jd_raw: Optional[str] = None
    jd_text: Optional[str] = None
    salary_currency: Optional[str] = "HKD"
    url: Optional[str] = None
    employer_questions: Optional[list[str]] = None


class JobListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[JobSummary]


class JobSearchRequest(BaseModel):
    keyword: Optional[str] = None
    location: Optional[str] = None
    source: Optional[str] = None
    skills: Optional[list[str]] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    page: int = 1
    page_size: int = 20
