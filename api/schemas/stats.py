from typing import Optional, Any
from pydantic import BaseModel


class StatsOverview(BaseModel):
    total_jobs: int
    total_companies: int
    avg_salary: float
    min_salary: float
    max_salary: float
    total_skills: int
    source_count: int
    location_count: int


class SkillFrequency(BaseModel):
    skill: str
    count: int
    category: Optional[str] = None


class CategoryDistribution(BaseModel):
    category: str
    count: int


class SalaryDistribution(BaseModel):
    location: str
    min: float
    max: float
    avg: float
    count: int


class LocationDistribution(BaseModel):
    location: str
    count: int


class SourceDistribution(BaseModel):
    source: str
    count: int


class DashboardData(BaseModel):
    overview: StatsOverview
    top_skills: list[SkillFrequency]
    category_distribution: list[CategoryDistribution]
    salary_by_location: list[SalaryDistribution]
    source_distribution: list[SourceDistribution]
