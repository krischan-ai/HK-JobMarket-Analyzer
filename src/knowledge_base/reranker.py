from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests

from config.settings import settings
from src.llm_config_manager import LLMConfigManager
from src.logger import get_logger


@dataclass
class RerankResult:
    index: int
    relevance_score: float


class SiliconFlowReranker:
    """SiliconFlow rerank client using the /v1/rerank endpoint."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout: int = 30,
    ):
        cfg = LLMConfigManager().load()
        self.api_key = api_key or settings.siliconflow_api_key or cfg.get("rerank_api_key") or cfg.get("api_key") or ""
        self.base_url = (base_url or settings.siliconflow_base_url or cfg.get("rerank_base_url") or "").rstrip("/")
        self.model = model or cfg.get("rerank_model") or settings.rerank_model
        self.timeout = timeout
        self.logger = get_logger(self.__class__.__name__)

    @property
    def available(self) -> bool:
        return bool(self.api_key and self.base_url and self.model)

    def rerank(self, query: str, documents: list[str], top_n: int | None = None) -> list[RerankResult]:
        if not self.available or not query or not documents:
            return []

        payload: dict[str, Any] = {
            "model": self.model,
            "query": query,
            "documents": documents,
            "return_documents": False,
            "top_n": top_n or len(documents),
        }
        if self.model.startswith("Qwen/Qwen3-Reranker"):
            payload["instruction"] = "Rerank Hong Kong job postings by relevance to the user's job-market question."

        try:
            response = requests.post(
                f"{self.base_url}/rerank",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=self.timeout,
                proxies={"http": None, "https": None},
            )
            response.raise_for_status()
            data = response.json()
            results = []
            for item in data.get("results", []):
                results.append(RerankResult(
                    index=int(item.get("index", 0)),
                    relevance_score=float(item.get("relevance_score", 0.0)),
                ))
            return results
        except Exception as e:
            self.logger.warning("Rerank failed: %s", e)
            return []
