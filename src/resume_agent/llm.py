from __future__ import annotations

from typing import Any

import requests

from config.settings import settings
from src.llm_config_manager import LLMConfigManager

from .utils import ResumeAgentError


class ResumeLLMClient:
    def __init__(self, config_manager: LLMConfigManager | None = None):
        self.config_manager = config_manager or LLMConfigManager()
        cfg = self.config_manager.build_kwargs()
        self.api_key = cfg.get("api_key") or settings.llm_api_key or ""
        self.api_base = (cfg.get("api_base") or settings.llm_base_url or "").rstrip("/")
        self.model = cfg.get("model") or settings.llm_model or "deepseek-chat"
        # 润色步骤输出较长、耗时较高，默认兜底超时取 120s（系统配置可覆盖更大值）。
        self.timeout = max(int(cfg.get("timeout") or 0), 120)

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.api_base)

    def chat_json(self, system_prompt: str, user_prompt: str, temperature: float = 0.2, max_tokens: int = 4096) -> str:
        if not self.configured:
            raise ResumeAgentError("LLM is not configured. Please configure API Key and Base URL first.")

        url = f"{self.api_base}/chat/completions"
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=self.timeout, proxies={"http": None, "https": None})
            resp.raise_for_status()
            data = resp.json()
            msg = data["choices"][0]["message"]
            content = (msg.get("content") or "").strip()
            if not content and msg.get("reasoning_content"):
                content = str(msg["reasoning_content"]).strip()
            if not content:
                raise ResumeAgentError("LLM returned empty content")
            return content
        except ResumeAgentError:
            raise
        except Exception as exc:
            raise ResumeAgentError(f"LLM request failed: {exc}") from exc
