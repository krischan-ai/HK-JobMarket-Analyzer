from __future__ import annotations

import json
from typing import Any, Callable, Optional

import requests

from config.settings import settings
from src.llm_config_manager import LLMConfigManager
from src.logger import get_logger

from .utils import ResumeAgentError

logger = get_logger(__name__)

# 调用方可注入的 token 回调：每收到一个内容增量就被调用一次。
DeltaCallback = Callable[[str], None]


class ResumeLLMClient:
    def __init__(self, config_manager: LLMConfigManager | None = None):
        self.config_manager = config_manager or LLMConfigManager()
        cfg = self.config_manager.build_kwargs()
        self.api_key = cfg.get("api_key") or settings.llm_api_key or ""
        self.api_base = (cfg.get("api_base") or settings.llm_base_url or "").rstrip("/")
        self.model = cfg.get("model") or settings.llm_model or "deepseek-chat"
        # 润色步骤输出较长、耗时较高，默认兜底超时取 120s（系统配置可覆盖更大值）。
        self.timeout = max(int(cfg.get("timeout") or 0), 120)
        # 设置后，chat_json 改走流式接口并对每个内容增量回调，便于前端实时显示模型输出。
        self.on_delta: Optional[DeltaCallback] = None

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.api_base)

    def _payload(self, system_prompt: str, user_prompt: str, temperature: float, max_tokens: int) -> dict[str, Any]:
        return {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

    @property
    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def chat_json(self, system_prompt: str, user_prompt: str, temperature: float = 0.2, max_tokens: int = 4096) -> str:
        if not self.configured:
            raise ResumeAgentError("LLM is not configured. Please configure API Key and Base URL first.")

        # 注入了 token 回调时优先走流式；流式异常则回退到非流式，保证不影响结果产出。
        if self.on_delta is not None:
            try:
                return self._chat_stream(system_prompt, user_prompt, temperature, max_tokens, self.on_delta)
            except ResumeAgentError:
                raise
            except Exception as exc:
                logger.warning("Streaming chat failed, falling back to blocking call: %s", exc)

        return self._chat_blocking(system_prompt, user_prompt, temperature, max_tokens)

    def _chat_blocking(self, system_prompt: str, user_prompt: str, temperature: float, max_tokens: int) -> str:
        url = f"{self.api_base}/chat/completions"
        try:
            resp = requests.post(
                url, headers=self._headers, json=self._payload(system_prompt, user_prompt, temperature, max_tokens),
                timeout=self.timeout, proxies={"http": None, "https": None},
            )
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

    def _chat_stream(
        self, system_prompt: str, user_prompt: str, temperature: float, max_tokens: int, on_delta: DeltaCallback
    ) -> str:
        """流式调用，逐 token 回调内容增量，返回完整内容（供 JSON 解析）。"""
        url = f"{self.api_base}/chat/completions"
        payload = self._payload(system_prompt, user_prompt, temperature, max_tokens)
        payload["stream"] = True

        content_parts: list[str] = []
        reasoning_parts: list[str] = []
        with requests.post(
            url, headers=self._headers, json=payload, stream=True,
            timeout=self.timeout, proxies={"http": None, "https": None},
        ) as resp:
            resp.raise_for_status()
            for raw in resp.iter_lines(decode_unicode=True):
                if not raw or not raw.startswith("data:"):
                    continue
                chunk = raw[5:].strip()
                if chunk == "[DONE]":
                    break
                try:
                    obj = json.loads(chunk)
                except json.JSONDecodeError:
                    continue
                choices = obj.get("choices") or []
                if not choices:
                    continue
                delta = choices[0].get("delta") or {}
                piece = delta.get("content")
                if piece:
                    content_parts.append(piece)
                    try:
                        on_delta(piece)
                    except Exception:  # noqa: BLE001 - 回调失败不应中断模型读取
                        pass
                elif delta.get("reasoning_content"):
                    reasoning_parts.append(str(delta["reasoning_content"]))

        content = "".join(content_parts).strip() or "".join(reasoning_parts).strip()
        if not content:
            raise ResumeAgentError("LLM returned empty content")
        return content
