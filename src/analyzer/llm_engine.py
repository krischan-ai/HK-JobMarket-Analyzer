from __future__ import annotations

import json
import time
from typing import Any, Optional

from config.settings import settings
from src.analyzer.prompt import build_skill_extraction_messages
from src.llm_config_manager import LLMConfigManager
from src.logger import get_logger


class LLMExtractor:
    """大语言模型技能提取引擎，支持 DeepSeek 和 OpenAI 兼容 API

    配置优先级（从高到低）：
    1. 直接传入构造参数（api_key, api_base, model）
    2. 面板持久化配置 (config/llm_config.json)
    3. .env / 环境变量
    """

    def __init__(self, api_key: str = None, api_base: str = None, model: str = None, timeout: int = 30):
        self.logger = get_logger(self.__class__.__name__)

        file_config = LLMConfigManager().build_kwargs()

        self.api_key = api_key if api_key is not None else (file_config.get("api_key") or settings.llm_api_key or "")
        base = api_base if api_base is not None else (file_config.get("api_base") or settings.llm_base_url or "")
        self.api_base = base.rstrip("/")
        self.model = model if model is not None else (file_config.get("model") or settings.llm_model or "deepseek-chat")
        self.timeout = timeout or file_config.get("timeout", 30)

    @property
    def available(self) -> bool:
        return bool(self.api_key) and bool(self.api_base)

    def extract(self, text: str, max_retries: int = 2) -> dict:
        if not self.available:
            self.logger.warning("LLM not configured, returning empty result")
            return {cat: [] for cat in self._default_categories()}

        messages = build_skill_extraction_messages(text)

        for attempt in range(max_retries + 1):
            try:
                response = self._call_api(messages)
                result = self._parse_response(response)
                if result is not None:
                    return result
            except Exception as e:
                self.logger.error("LLM extract attempt %d failed: %s", attempt + 1, e)
                if attempt < max_retries:
                    time.sleep(2 ** attempt)

        self.logger.warning("All LLM retries exhausted, returning empty result")
        return {cat: [] for cat in self._default_categories()}

    def _call_api(self, messages: list[dict]) -> dict:
        import requests
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1,
            "max_tokens": 1024,
        }
        url = f"{self.api_base}/chat/completions"
        resp = requests.post(url, headers=headers, json=payload, timeout=self.timeout, proxies={"http": None, "https": None})
        resp.raise_for_status()
        return resp.json()

    def _parse_response(self, response: dict) -> Optional[dict]:
        try:
            content = response["choices"][0]["message"]["content"]
            content = content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[-1]
                content = content.rsplit("```", 1)[0]
            result = json.loads(content)
            expected = self._default_categories()
            for cat in expected:
                if cat not in result:
                    result[cat] = []
            return result
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            self.logger.error("Failed to parse LLM response: %s", e)
            return None

    def extract_batch(self, jobs: list[dict], text_field: str = "jd_raw", batch_size: int = 5) -> list[dict]:
        results = []
        for i in range(0, len(jobs), batch_size):
            batch = jobs[i : i + batch_size]
            for job in batch:
                text = job.get(text_field, "")
                job["skills_llm"] = self.extract(text)
                results.append(job)
            if i + batch_size < len(jobs):
                self.logger.info("Processed %d/%d jobs, rate limit pause...", i + batch_size, len(jobs))
                time.sleep(1)
        return results

    @staticmethod
    def _default_categories() -> list[str]:
        return [
            "programming_languages",
            "frameworks_libraries",
            "cloud_devops",
            "databases",
            "soft_skills",
        ]
