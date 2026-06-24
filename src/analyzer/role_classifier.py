from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import Any, Optional

import requests

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

        self.api_key = api_key if api_key is not None else (file_config.get("api_key") or settings.llm_api_key or "")
        base = api_base if api_base is not None else (file_config.get("api_base") or settings.llm_base_url or "")
        self.api_base = base.rstrip("/")
        self.model = model if model is not None else (file_config.get("model") or settings.llm_model or "deepseek-chat")
        self.timeout = timeout or file_config.get("timeout", 30)

        self._cache: dict[str, dict] = {}
        self._quick_check_result: Optional[bool] = None  # 缓存 API 可用性
        self._quick_check_lock = Lock()
        self._llm_failure_count = 0  # 连续 LLM 调用失败计数
        self._llm_failure_lock = Lock()
        self._max_llm_failures = 5  # 超过此阈值后禁用 LLM
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
        except (OSError, TypeError, ValueError) as e:
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
            return RoleResult(
                role_id=cached.get("role_id", "other"),
                role_name=cached.get("role_name", "其他"),
                confidence=cached.get("confidence", "low"),
            )

        if self.available:
            result = self._classify_with_llm(jd_text)
        else:
            result = self._classify_with_rules(jd_text)

        self._cache[cache_key] = {"role_id": result.role_id, "role_name": result.role_name, "confidence": result.confidence}
        self._save_cache()
        return result

    @staticmethod
    def _extract_json(text: str) -> Optional[dict]:
        """从文本中提取 JSON 对象（兼容推理模型输出）"""
        # 1. 尝试直接解析
        text = text.strip()
        if text.startswith("{"):
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass

        # 2. 查找 ```json ... ``` 包裹
        import re
        m = re.search(r"```(?:json)?\s*(\{.+?\})\s*```", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                pass

        # 3. 查找第一个 { 到最后一个 } 之间的内容
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start:end+1])
            except json.JSONDecodeError:
                pass

        return None

    def _classify_with_llm(self, jd_text: str, max_retries: int = 2) -> RoleResult:
        messages = build_role_classify_messages(jd_text)

        # 快速检测：如果 API 不可达，直接降级到规则引擎
        if not self._quick_check():
            self.logger.warning("API unreachable, falling back to rules immediately")
            return self._classify_with_rules(jd_text)

        for attempt in range(max_retries + 1):
            try:
                response = self._call_api(messages)
                content = response["choices"][0]["message"]["content"]
                content = content.strip()

                if not content:
                    raise ValueError("Empty LLM response content")

                # 从文本中提取 JSON
                parsed = self._extract_json(content)
                if parsed is None:
                    self.logger.warning(
                        "LLM non-JSON response (len=%d, first=%.50s...), using rules",
                        len(content), content
                    )
                    return self._classify_with_rules(jd_text)

                role_id = parsed.get("role_id", "other")
                if role_id not in ROLE_DEFINITIONS:
                    role_id = "other"
                return RoleResult(
                    role_id=role_id,
                    role_name=ROLE_DEFINITIONS.get(role_id, {}).get("name", "其他"),
                    confidence=parsed.get("confidence", "medium"),
                )
            except json.JSONDecodeError:
                self.logger.warning("LLM non-JSON response at attempt %d, using rules", attempt + 1)
                return self._classify_with_rules(jd_text)
            except Exception as e:
                self.logger.error("LLM classify attempt %d failed: %s", attempt + 1, e)
                if isinstance(e, (requests.exceptions.ConnectTimeout, requests.exceptions.ConnectionError,
                                  requests.exceptions.HTTPError)):
                    self.logger.warning("Connection error, falling back to rules")
                    return self._classify_with_rules(jd_text)
                if attempt < max_retries:
                    time.sleep(2 ** attempt)

        self.logger.warning("All LLM classify retries exhausted, falling back to rules")
        return self._classify_with_rules(jd_text)

    def _call_api(self, messages: list[dict]) -> dict:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1,
            "max_tokens": 4096,
        }
        url = f"{self.api_base}/chat/completions"
        resp = requests.post(url, headers=headers, json=payload, timeout=self.timeout, proxies={"http": None, "https": None})
        resp.raise_for_status()
        data = resp.json()
        msg = data["choices"][0]["message"]
        content = msg.get("content", "")
        # 推理模型可能返回空 content + reasoning_content
        if not content or not content.strip():
            reasoning = msg.get("reasoning_content", "")
            if reasoning and reasoning.strip():
                content = reasoning.strip()
            else:
                raise ValueError("Empty response from LLM")
        data["choices"][0]["message"]["content"] = content
        return data

    def _quick_check(self) -> bool:
        """快速检测 API 是否可达（缓存结果，生命周期内只查一次）

        使用最小化的 chat/completions 请求来验证 API 实际可用，
        避免仅检测 /models 端点通过但实际对话接口不可用（如 SSL 错误）。
        """
        if self._quick_check_result is not None:
            return self._quick_check_result
        with self._quick_check_lock:
            # 双重检查：获取锁后再次确认缓存状态
            if self._quick_check_result is not None:
                return self._quick_check_result
            try:
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                }
                # 使用最小 payload 测试 chat/completions 端点
                payload = {
                    "model": self.model,
                    "messages": [{"role": "user", "content": "OK"}],
                    "max_tokens": 5,
                    "temperature": 0.1,
                }
                url = f"{self.api_base}/chat/completions"
                resp = requests.post(
                    url, headers=headers, json=payload,
                    timeout=10, proxies={"http": None, "https": None},
                )
                self._quick_check_result = resp.status_code == 200
            except Exception:
                self._quick_check_result = False
            self.logger.info("LLM quick check: %s", self._quick_check_result)
            return self._quick_check_result

    def _classify_with_rules(self, jd_text: str) -> RoleResult:
        lower = jd_text.lower()
        scores: dict[str, int] = {}

        rules = [
            # AI roles (most specific first)
            ("ai_prompt_engineer", ["prompt engineer", "prompt design", "prompt template", "prompt optimization", "few-shot", "prompting", "creative technologist"]),
            ("ai_model_training", ["model train", "fine-tun", "fine tun", "lora", "peft", "rlhf", "pre-training", "model alignment", "sft", "model developer", "pretrain"]),
            ("ai_agent_dev", ["ai agent", "multi-agent", "agentic", "tool use", "autogpt", "function calling", "react agent", "agent framework", "agent engineer", "agentic engineer", "agent developer", "agent researcher"]),
            ("ai_application", ["rag", "langchain", "llamaindex", "vector db", "llm api", "llm application", "dify", "prompt flow", "embedding", "llm engineer", "llm developer", "llm applied", "ai engineer", "ai developer", "ai programmer", "ai application", "generative ai", "genai", "llm application"]),
            # Data scientist vs ML engineer (split from data_science)
            ("data_scientist", ["data scientist", "data analysis", "statistical", "a/b test", "ab test", "tableau", "data analytics", "business intelligence", "data visualization", "data analyst"]),
            ("ml_engineer", ["ml engineer", "ml pipeline", "mlops", "model deployment", "model serving", "feature store", "distributed training", "model monitoring", "machine learning engineer"]),
            # data_science as fallback for the broad category
            ("data_science", ["machine learning", "deep learning", "tensorflow", "pytorch", "nlp", "computer vision", "cv engineer", "data science"]),
            # Data engineering
            ("data_engineer", ["data engineer", "etl", "spark", "hadoop", "airflow", "data pipeline", "snowflake", "data warehouse", "big data"]),
            # Solution architect (new)
            ("solution_architect", ["solution architect", "system architect", "data architect", "cloud architect", "infrastructure architect", "technology architect", "enterprise architect", "platform architect", "ai architect", "solution lead", "technical architect", "solutions architect", "lead architect", "principal architect"]),
            # Engineering manager (new)
            ("engineering_manager", ["engineering manager", "tech lead", "technical lead", "team lead", "engineering lead", "development manager", "head of engineering", "technical manager", "ai lead", "technical director"]),
            # IT Analyst (new)
            ("it_analyst", ["system analyst", "business analyst", "requirements analysis", "system analysis", "it analyst", "process analyst", "technical analyst"]),
            # Traditional dev roles
            ("fullstack", ["full stack", "full-stack", "mern", "mean", "fullstack"]),
            ("frontend", ["frontend", "front-end", "front end", "web developer", "ui developer", "react", "vue", "angular", "css", "html", "tailwind", "front-end developer", "frontend developer"]),
            ("backend", ["backend", "back-end", "back end", "spring boot", "django", "fastapi", "node.js", "rest api", "restful", "microservices", "api development", "analyst programmer", "java developer", ".net developer", "c# developer", "python developer", "go developer", "software engineer", "software developer", "system developer", "programmer", "back-end developer", "backend developer"]),
            ("mobile", ["swift", "kotlin", "flutter", "react native", "ios developer", "android developer", "objective-c", "mobile developer"]),
            # Infrastructure
            ("devops", ["devops", "sre", "ci/cd", "ci cd", "kubernetes", "k8s", "terraform", "ansible", "jenkins", "docker", "platform engineer", "cloud engineer"]),
            ("qa", ["qa engineer", "test automation", "selenium", "testng", "cypress", "quality assurance", "tester", "qa analyst"]),
            ("security", ["cybersecurity", "security engineer", "penetration test", "soc analyst", "iso 27001", "security analyst", "devsecops", "information security"]),
            # Business roles
            ("product", ["product manager", "product owner", "roadmap", "user story", "prd", "scrum master", "head of product", "product lead"]),
            ("design", ["figma", "sketch", "ui designer", "ux designer", "user research", "prototype", "visual design", "ui/ux", "product design"]),
            ("blockchain", ["solidity", "smart contract", "defi", "web3", "ethereum", "blockchain", "nft", "crypto"]),
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
                try:
                    text = job.get(text_field, "")
                    if not isinstance(text, str):
                        text = str(text) if text and str(text) != "nan" else ""
                    result = self.classify(text)
                    job["role_id"] = result.role_id
                    job["role_name"] = result.role_name
                    job["role_confidence"] = result.confidence
                except Exception as e:
                    self.logger.warning("Failed to classify job %s: %s", job.get("job_id", "?"), e)
                    job["role_id"] = "other"
                    job["role_name"] = "其他"
                    job["role_confidence"] = "low"
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
        self._quick_check_result = None
        if CACHE_PATH.exists():
            os.remove(CACHE_PATH)
        self.logger.info("Role cache cleared")
