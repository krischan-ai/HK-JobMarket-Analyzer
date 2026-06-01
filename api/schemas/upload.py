from typing import Optional, Any
from pydantic import BaseModel


class UploadResult(BaseModel):
    total: int
    success: int
    skipped: int
    new_records: int
    updated_records: int
    errors: list[str]
    duration_ms: float


class FieldMapping(BaseModel):
    fields: dict[str, str]
    source_tag: str


class UploadConfig(BaseModel):
    source_tag: str = "user_upload"
    detect_duplicates: bool = True
    run_cleaning: bool = True
    run_extraction: bool = True
