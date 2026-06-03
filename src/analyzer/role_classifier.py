from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from config.settings import settings
from src.analyzer.role_prompt import ROLE_DEFINITIONS, build_role_classify_messages
from src.llm_config_manager import LLMConfigManager
from src.logger import get_logger

CACHE_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "role_cache.json"


@dataclass
class RoleResult:
    role_id: str
    role_name: str
    confidence: str


class RoleClassifier:
    """基于 LLM 的岗位角色分类引擎

    自动分析 JD 工作内容，将岗位归类到 14 种标准技术角色。
    LLM 不可用时降级为关键词规则匹配。
    分类结果缓存到 data/role_cache.json，避免重复调用 API。
    """

    def __init__(self, api_key: str = None, api_base: str = None, model: str = None, timeout: int = 30):
        self.logger = get_logger(self.__class__.__name__)

        file_config = LLMConfigManager().build_kwargs()

        self.api_key = api_key or file_config.get("api_key") or settings.llm_api_key or ""
        self.api_base = (api_base or file_config.get("api_base") or settings.llm_base_url or "").rstrip("/")
        self.model = model or file_config.get("model") or settings.llm_model or "deepseek-chat"
        self.timeout = timeout or file_config.get("timeout", 30)

        self._cache: dict[str, dict] = {}
        self._load_cache()

    @property
    def available(self) -> bool:
        return bool(self.api_key) and bool(self.api_base)

    def _load_cache(self):
        if CACHE_PATH.exists():
            try:
                with open(CACHE_PATH, "r", encoding="utf-8") as f:
                    self._cache = json.load(f)
                self.logger.info("Loaded %d role cache entries", len(self._cache))
            except (json.JSONDecodeError, OSError):
                self._cache = {}

    def _save_cache(self):
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(CACHE_PATH, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, ensure_ascii=False, indent=2)
        except OSError as e:
            self.logger.warning("Failed to save role cache: %s", e)

    def _make_cache_key(self, text: str) -> str:
        import hashlib
        text = str(text) if text and str(text) != "nan" else ""
        return hashlib.md5(text[:500].encode("utf-8")).hexdigest()

    def classify(self, jd_text: str) -> RoleResult:
        if not jd_text or not isinstance(jd_text, str):
            return RoleResult(role_id="other", role_name="其他", confidence="low")

        cache_key = self._make_cache_key(jd_text)
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            return RoleResult(**cached)

        if self.available:
            result = self._classify_with_llm(jd_text)
        else:
            result = self._classify_with_rules(jd_text)

        self._cache[cache_key] = {"role_id": result.role_id, "role_name": result.role_name, "confidence": result.confidence}
        self._save_cache()
        return result

    def _classify_with_llm(self, jd_text: str, max_retries: int = 2) -> RoleResult:
        messages = build_role_classify_messages(jd_text)

        for attempt in range(max_retries + 1):
            try:
                response = self._call_api(messages)
                content = response["choices"][0]["message"]["content"]
                content = content.strip()
                if content.startswith("```"):
                    content = content.split("\n", 1)[-1]
                    content = content.rsplit("```", 1)[0]
                parsed = json.loads(content)
                role_id = parsed.get("role_id", "other")
                if role_id not in ROLE_DEFINITIONS:
                    role_id = "other"
                return RoleResult(
                    role_id=role_id,
                    role_name=ROLE_DEFINITIONS.get(role_id, {}).get("name", "其他"),
                    confidence=parsed.get("confidence", "medium"),
                )
            except Exception as e:
                self.logger.error("LLM classify attempt %d failed: %s", attempt + 1, e)
                if attempt < max_retries:
                    time.sleep(2 ** attempt)

        self.logger.warning("All LLM classify retries exhausted, falling back to rules")
        return self._classify_with_rules(jd_text)

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
            "max_tokens": 256,
        }
        url = f"{self.api_base}/chat/completions"
        resp = requests.post(url, headers=headers, json=payload, timeout=self.timeout, proxies={"http": None, "https": None})
        resp.raise_for_status()
        return resp.json()

    def _classify_with_rules(self, jd_text: str) -> RoleResult:
        lower = jd_text.lower()
        scores: dict[str, int] = {}

        rules = [
            ("frontend", ["react", "vue", "angular", "frontend", "front-end", "ui developer", "css ", "html ", "tailwind"]),
            ("backend", ["spring boot", "django", "fastapi", "backend", "back-end", "rest api", "restful", "microservices", "api development"]),
            ("fullstack", ["full stack", "full-stack", "mern", "mean"]),
            ("mobile", ["swift", "kotlin", "flutter", "react native", "ios developer", "android developer", "objective-c"]),
            ("data_science", ["machine learning", "deep learning", "tensorflow", "pytorch", "nlp", "data scientist", "computer vision", "ml engineer"]),
            ("data_engineer", ["data engineer", "etl", "spark", "hadoop", "airflow", "data pipeline", "snowflake", "data warehouse"]),
            ("devops", ["devops", "sre", "ci/cd", "ci cd", "kubernetes", "k8s", "terraform", "ansible", "jenkins", "docker"]),
            ("qa", ["qa engineer", "test automation", "selenium", "testng", "cypress", "quality assurance", "tester"]),
            ("security", ["cybersecurity", "security engineer", "penetration test", "soc analyst", "iso 27001", "security analyst"]),
            ("product", ["product manager", "roadmap", "user story", "prd", "scrum master"]),
            ("design", ["figma", "sketch", "ui designer", "ux designer", "user research", "prototype", "visual design"]),
            ("blockchain", ["solidity", "smart contract", "defi", "web3", "ethereum", "blockchain", "nft"]),
            ("ai_engineer", ["llm", "langchain", "rag", "prompt engineering", "ai agent", "fine-tun", "generative ai"]),
        ]

        for role_id, keywords in rules:
            score = 0
            for kw in keywords:
                if kw in lower:
                    score += 1
            if score > 0:
                scores[role_id] = score

        if not scores:
            return RoleResult(role_id="other", role_name="其他", confidence="low")

        best_role = max(scores, key=lambda k: scores[k])
        best_score = scores[best_role]

        confidence = "high" if best_score >= 3 else "medium" if best_score >= 2 else "low"
        return RoleResult(
            role_id=best_role,
            role_name=ROLE_DEFINITIONS[best_role]["name"],
            confidence=confidence,
        )

    def classify_batch(self, jobs: list[dict], text_field: str = "jd_raw", batch_size: int = 5) -> list[dict]:
        results = []
        for i in range(0, len(jobs), batch_size):
            batch = jobs[i : i + batch_size]
            for job in batch:
                text = job.get(text_field, "")
                if not isinstance(text, str):
                    text = str(text) if text and str(text) != "nan" else ""
                result = self.classify(text)
                job["role_id"] = result.role_id
                job["role_name"] = result.role_name
                job["role_confidence"] = result.confidence
                results.append(job)
            if i + batch_size < len(jobs):
                self.logger.info("Classified %d/%d jobs", i + batch_size, len(jobs))
                time.sleep(0.5)
        return results

    def get_statistics(self) -> dict:
        distribution: dict[str, dict] = {}
        for cache_entry in self._cache.values():
            role_id = cache_entry.get("role_id", "other")
            if role_id not in distribution:
                distribution[role_id] = {
                    "role_id": role_id,
                    "role_name": ROLE_DEFINITIONS.get(role_id, {}).get("name", "其他"),
                    "count": 0,
                }
            distribution[role_id]["count"] += 1

        total = len(self._cache)
        result = sorted(distribution.values(), key=lambda x: x["count"], reverse=True)
        for item in result:
            item["percentage"] = round(item["count"] / total * 100, 1) if total > 0 else 0.0
        return {
            "distribution": result,
            "total_classified": total,
        }

    def clear_cache(self):
        self._cache = {}
        if CACHE_PATH.exists():
            os.remove(CACHE_PATH)
        self.logger.info("Role cache cleared")
