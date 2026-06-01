from fastapi import APIRouter, Query
from pydantic import BaseModel

class HealthResponse(BaseModel):
    status: str
    version: str
    data_count: int

router = APIRouter(prefix="/system", tags=["system"])

@router.get("/health", response_model=HealthResponse)
def health_check():
    from api.dependencies import load_jobs_df
    df = load_jobs_df()
    return {"status": "healthy", "version": "1.0.0", "data_count": len(df)}
