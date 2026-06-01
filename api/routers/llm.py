from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Any

router = APIRouter(prefix="/api/llm", tags=["llm"])


class LLMConfig(BaseModel):
    api_key: Optional[str] = ""
    base_url: Optional[str] = "https://api.deepseek.com/v1"
    model: Optional[str] = "deepseek-chat"
    timeout: Optional[int] = 30


class LLMConfigResponse(BaseModel):
    configured: bool
    base_url: str
    model: str
    api_key_set: bool


class LLMTestResult(BaseModel):
    success: bool
    message: str
    latency_ms: Optional[float] = None


def _get_manager():
    from src.llm_config_manager import LLMConfigManager
    return LLMConfigManager()


@router.get("/config", response_model=LLMConfigResponse)
def get_config():
    mgr = _get_manager()
    config = mgr.load()
    return LLMConfigResponse(
        configured=mgr.configured,
        base_url=config.get("base_url", "https://api.deepseek.com/v1"),
        model=config.get("model", "deepseek-chat"),
        api_key_set=bool(config.get("api_key")),
    )


@router.put("/config", response_model=LLMConfigResponse)
def update_config(cfg: LLMConfig):
    mgr = _get_manager()
    mgr.save(
        api_key=cfg.api_key or "",
        base_url=cfg.base_url or "https://api.deepseek.com/v1",
        model=cfg.model or "deepseek-chat",
        timeout=cfg.timeout or 30,
    )
    config = mgr.load()
    return LLMConfigResponse(
        configured=mgr.configured,
        base_url=config.get("base_url", ""),
        model=config.get("model", ""),
        api_key_set=bool(config.get("api_key")),
    )


@router.delete("/config", response_model=dict)
def clear_config():
    mgr = _get_manager()
    mgr.clear()
    return {"message": "LLM 配置已清除", "configured": False}


@router.post("/test", response_model=LLMTestResult)
def test_connection():
    import time
    mgr = _get_manager()
    t0 = time.time()
    success, message = mgr.test_connection(timeout=15)
    elapsed = round((time.time() - t0) * 1000, 1) if success else None
    return LLMTestResult(success=success, message=message, latency_ms=elapsed)


@router.get("/status", response_model=dict)
def status():
    mgr = _get_manager()
    return {"configured": mgr.configured}
