from typing import Optional, Any
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    version: str
    data_count: int


class ErrorResponse(BaseModel):
    detail: str


class SuccessResponse(BaseModel):
    message: str
    count: int = 0


class PaginationParams(BaseModel):
    page: int = 1
    page_size: int = 20


class FilterParams(BaseModel):
    keyword: Optional[str] = None
    location: Optional[str] = None
    source: Optional[str] = None
    skill: Optional[str] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
