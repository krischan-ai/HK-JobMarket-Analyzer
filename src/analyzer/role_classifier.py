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
from src.analyzer.skill_postprocessor import (
    build_summary_tags,
    postprocess_cross_industry_profile,
    postprocess_tag_profile,
)
from src.analyzer.skill_taxonomy import CROSS_INDUSTRY_DIMENSIONS
from src.llm_config_manager import LLMConfigManager
from src.logger import get_logger

CACHE_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "role_cache.json"


@dataclass
class RoleResult:
    role_id: str
    role_name: str
    confidence: str
    soft_skills: dict[str, list[str]] = field(default_factory=lambda: {
        "education": [],
        "language": [],
        "soft_skill": [],
        "domain_knowledge": [],
        "certification": [],
        "business_skill": [],
    })
    tag_profile: dict[str, list[dict]] = field(default_factory=lambda: {
        "technical": [],
        "non_technical": [],
    })
    cross_industry_profile: dict[str, list[dict]] = field(default_factory=lambda: {
        dim: [] for dim in CROSS_INDUSTRY_DIMENSIONS
    })
    job_context_profile: dict[str, list[dict]] = field(default_factory=lambda: {
        "summary_tags": [],
    })
    taxonomy_candidates: list[dict] = field(default_factory=list)


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
        self._force_reclassify: bool = False  # full 模式跳过缓存命中、强制重新分类（不删除磁盘缓存）
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

    @staticmethod
    def _normalize_soft_skills(value: Any) -> dict[str, list[str]]:
        result = {
            "education": [],
            "language": [],
            "soft_skill": [],
            "domain_knowledge": [],
            "certification": [],
            "business_skill": [],
        }
        if not isinstance(value, dict):
            return result
        for key in result:
            raw_items = value.get(key, [])
            if isinstance(raw_items, list):
                result[key] = [str(item).strip() for item in raw_items if str(item).strip()]
        return result

    @staticmethod
    def _empty_tag_profile() -> dict[str, list[dict]]:
        return {"technical": [], "non_technical": []}

    @staticmethod
    def _normalize_tag_profile(value: Any, run_postprocess: bool = False) -> dict[str, list[dict]]:
        """规整 tag_profile。run_postprocess=True 时对 LLM 原始输出执行后处理治理；
        从缓存读取已治理结果时按原样校验结构。"""
        if run_postprocess:
            return postprocess_tag_profile(value)
        result = {"technical": [], "non_technical": []}
        if not isinstance(value, dict):
            return result
        for bucket in result:
            items = value.get(bucket, [])
            if isinstance(items, list):
                result[bucket] = [item for item in items if isinstance(item, dict) and item.get("name")]
        return result

    @staticmethod
    def _empty_cross_industry_profile() -> dict[str, list[dict]]:
        return {dim: [] for dim in CROSS_INDUSTRY_DIMENSIONS}

    @staticmethod
    def _empty_job_context_profile() -> dict[str, list[dict]]:
        return {"summary_tags": []}

    @classmethod
    def _normalize_cross_industry_profile(cls, value: Any, run_postprocess: bool = False) -> dict[str, list[dict]]:
        if run_postprocess:
            return postprocess_cross_industry_profile(value)
        result = cls._empty_cross_industry_profile()
        if not isinstance(value, dict):
            return result
        for dim in result:
            items = value.get(dim, [])
            if isinstance(items, list):
                result[dim] = [item for item in items if isinstance(item, dict) and item.get("name")]
        return result

    @classmethod
    def _normalize_job_context_profile(cls, value: Any) -> dict[str, list[dict]]:
        result = cls._empty_job_context_profile()
        if isinstance(value, dict) and isinstance(value.get("summary_tags"), list):
            result["summary_tags"] = [t for t in value["summary_tags"] if isinstance(t, dict) and t.get("name")]
        return result

    @staticmethod
    def _normalize_taxonomy_candidates(candidates: Any, alias_updates: Any = None) -> list[dict]:
        """规整 candidate_taxonomy_updates，并把 candidate_alias_updates 折叠为 category=='alias' 候选。"""
        result: list[dict] = []
        if isinstance(candidates, list):
            for c in candidates:
                if isinstance(c, dict) and str(c.get("name", "")).strip() and str(c.get("evidence", "")).strip():
                    result.append(c)
        if isinstance(alias_updates, list):
            for a in alias_updates:
                if not isinstance(a, dict):
                    continue
                alias = str(a.get("alias", "")).strip()
                canonical = str(a.get("canonical", "")).strip()
                evidence = str(a.get("evidence", "")).strip()
                if alias and canonical and evidence:
                    result.append({
                        "name": alias,
                        "category": "alias",
                        "aliases": [canonical],
                        "evidence": evidence,
                        "reason": f"alias of {canonical}",
                        "confidence": a.get("confidence", 0.8),
                        "requirement_level": "",
                        "status": "candidate",
                    })
        return result

    def classify(self, jd_text: str) -> RoleResult:
        if not jd_text or not isinstance(jd_text, str):
            return RoleResult(role_id="other", role_name="其他", confidence="low")

        cache_key = self._make_cache_key(jd_text)
        if not self._force_reclassify and cache_key in self._cache:
            cached = self._cache[cache_key]
            return RoleResult(
                role_id=cached.get("role_id", "other"),
                role_name=cached.get("role_name", "其他"),
                confidence=cached.get("confidence", "low"),
                soft_skills=self._normalize_soft_skills(cached.get("soft_skills")),
                tag_profile=self._normalize_tag_profile(cached.get("tag_profile")),
                cross_industry_profile=self._normalize_cross_industry_profile(cached.get("cross_industry_profile")),
                job_context_profile=self._normalize_job_context_profile(cached.get("job_context_profile")),
                taxonomy_candidates=self._normalize_taxonomy_candidates(cached.get("taxonomy_candidates")),
            )

        if self.available:
            result = self._classify_with_llm(jd_text)
        else:
            result = self._classify_with_rules(jd_text)

        self._cache[cache_key] = {
            "role_id": result.role_id,
            "role_name": result.role_name,
            "confidence": result.confidence,
            "soft_skills": result.soft_skills,
            "tag_profile": result.tag_profile,
            "cross_industry_profile": result.cross_industry_profile,
            "job_context_profile": result.job_context_profile,
            "taxonomy_candidates": result.taxonomy_candidates,
        }
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
                cross_profile = self._normalize_cross_industry_profile(
                    parsed.get("cross_industry_profile"), run_postprocess=True
                )
                return RoleResult(
                    role_id=role_id,
                    role_name=ROLE_DEFINITIONS.get(role_id, {}).get("name", "其他"),
                    confidence=parsed.get("confidence", "medium"),
                    soft_skills=self._normalize_soft_skills(parsed.get("soft_skills")),
                    tag_profile=self._normalize_tag_profile(parsed.get("tag_profile"), run_postprocess=True),
                    cross_industry_profile=cross_profile,
                    job_context_profile={"summary_tags": build_summary_tags(cross_profile)},
                    taxonomy_candidates=self._normalize_taxonomy_candidates(
                        parsed.get("candidate_taxonomy_updates"), parsed.get("candidate_alias_updates")
                    ),
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
            # 16384：长 JD（售前/架构/管理岗）结构化输出可达 6000-9700 字符，
            # 8192 token 上限会截断响应导致 JSON 解析失败、静默降级到规则引擎。
            "max_tokens": 16384,
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

        enriched = self._classify_cross_industry_solution_rules(jd_text)
        if enriched is not None:
            return enriched

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

    @staticmethod
    def _evidence(text: str, needle: str, fallback: str = "") -> str:
        """Return a compact quote around a matched phrase for rule-generated tags."""
        if not text:
            return fallback[:160]
        lower = text.lower()
        pos = lower.find(needle.lower())
        if pos < 0:
            return (fallback or text[:160]).strip()[:160]
        start = pos
        end = min(len(text), pos + len(needle))
        return " ".join(text[start:end].split())[:160]

    @classmethod
    def _rule_tag(
        cls,
        text: str,
        name: str,
        category: str,
        requirement_level: str,
        needle: str,
        confidence: float = 0.9,
        fallback: str = "",
    ) -> dict:
        return {
            "name": name,
            "category": category,
            "requirement_level": requirement_level,
            "source": "rules",
            "confidence": confidence,
            "evidence": cls._evidence(text, needle, fallback),
        }

    @classmethod
    def _dim_tag(
        cls,
        text: str,
        name: str,
        needle: str,
        confidence: float = 0.9,
        fallback: str = "",
    ) -> dict:
        return {
            "name": name,
            "confidence": confidence,
            "evidence": cls._evidence(text, needle, fallback),
        }

    @classmethod
    def _classify_cross_industry_solution_rules(cls, jd_text: str) -> RoleResult | None:
        """Evidence-backed fallback for pre-sales solution / cross-industry JDs.

        This keeps acceptance-critical structure available when the LLM times out.
        The rules intentionally require multiple co-occurring signals so ordinary
        engineering-manager or security postings are not pulled into this path.
        """
        lower = jd_text.lower()
        solution_signals = (
            "solution design", "solution designs", "technical proposals",
            "solution demonstrations", "proof-of-concept", "poc",
            "tender preparation", "presales", "pre-sales",
            "it infrastructure solutions", "digital twin solutions",
        )
        signal_count = sum(1 for sig in solution_signals if sig in lower)
        if signal_count < 3:
            return None

        tag_raw = {"technical": [], "non_technical": []}
        cross_raw = {dim: [] for dim in CROSS_INDUSTRY_DIMENSIONS}
        soft = {
            "education": [],
            "language": [],
            "soft_skill": [],
            "domain_knowledge": [],
            "certification": [],
            "business_skill": [],
        }
        candidates: list[dict] = []

        def has(phrase: str) -> bool:
            return phrase in lower

        def add_tech(name: str, category: str, level: str, needle: str, confidence: float = 0.9):
            if has(needle.lower()):
                tag_raw["technical"].append(cls._rule_tag(jd_text, name, category, level, needle, confidence))

        def add_nontech(name: str, category: str, level: str, needle: str, confidence: float = 0.9):
            if has(needle.lower()):
                tag_raw["non_technical"].append(cls._rule_tag(jd_text, name, category, level, needle, confidence))

        def add_cross(dim: str, name: str, needle: str, confidence: float = 0.9):
            if has(needle.lower()):
                cross_raw[dim].append(cls._dim_tag(jd_text, name, needle, confidence))

        add_tech("AI", "ai_concepts", "required", "AI and Digital Twin solutions", 0.94)
        add_tech("Digital Twin", "ai_concepts", "required", "Digital Twin solutions", 0.95)
        add_tech("IT Infrastructure", "infrastructure", "required", "IT infrastructure solutions", 0.95)
        add_tech("Networking", "infrastructure", "required", "networking", 0.9)
        add_tech("Hardware", "infrastructure", "required", "hardware", 0.9)
        add_tech("Software", "infrastructure", "required", "software", 0.9)
        add_tech("Network Security", "security_compliance", "required", "network security", 0.94)
        add_tech("Sensors", "infrastructure", "required", "suitable sensors brands", 0.92)
        add_tech("ISO 27001", "security_compliance", "required", "ISO 27001", 0.98)
        add_tech("PowerPoint", "office_tools", "required", "PowerPoint", 0.86)
        add_tech("Excel", "office_tools", "required", "Excel", 0.86)
        add_tech("MS Office", "office_tools", "required", "MS Office", 0.86)

        add_nontech("需求分析", "business_skill", "required", "Understand client requirement", 0.92)
        add_nontech("痛点分析", "business_skill", "required", "analyze their pain points", 0.92)
        add_nontech("业务成果导向", "business_skill", "required", "achieve business outcomes", 0.9)
        add_nontech("方案设计", "presales_delivery", "required", "solution designs", 0.93)
        add_nontech("技术提案", "presales_delivery", "required", "technical proposals", 0.93)
        add_nontech("方案演示", "presales_delivery", "required", "solution demonstrations", 0.93)
        add_nontech("POC 测试", "presales_delivery", "required", "Proof-Of-Concept (POC) tests", 0.94)
        add_nontech("投标准备", "presales_delivery", "required", "tender preparation", 0.92)
        add_nontech("投标提交", "presales_delivery", "required", "submission for tender bidding", 0.9)
        add_nontech("业务拓展支持", "presales_delivery", "required", "business development manager", 0.88)
        add_nontech("售前到交付衔接", "presales_delivery", "required", "presales to project delivery", 0.92)
        add_nontech("供应商沟通", "business_skill", "required", "vendors", 0.86)
        add_nontech("客户沟通", "business_skill", "required", "client", 0.84)
        add_nontech("4 年以上 IT 行业经验", "experience", "required", "At least 4 years", 0.94)
        add_nontech("售前经验", "experience", "preferred", "pre-sales or engineering background being preferred", 0.9)
        add_nontech("工程背景", "experience", "preferred", "engineering background being preferred", 0.9)
        add_nontech("AI / Environmental / Computer Science Engineering 相关学位", "education", "required", "Degree holder", 0.9)
        add_nontech("英语", "language", "required", "spoken & written English", 0.92)
        add_nontech("中文", "language", "required", "Chinese", 0.9)
        add_nontech("独立工作能力", "soft_skill", "required", "work independently", 0.9)
        add_nontech("团队合作", "soft_skill", "required", "part of a team", 0.9)

        add_cross("industry_context", "政府/公共部门", "government and public sector clients", 0.94)
        add_cross("industry_context", "公用事业/环保工程", "Environmental", 0.72)
        add_cross("business_scenario", "水处理设施监测", "water treatment facilities", 0.96)
        add_cross("business_scenario", "设备状态监测", "monitoring and tracking the physical condition", 0.95)
        add_cross("solution_domain", "AI 解决方案", "AI and Digital Twin solutions", 0.94)
        add_cross("solution_domain", "Digital Twin 解决方案", "Digital Twin solutions", 0.95)
        add_cross("solution_domain", "IT 基础设施方案设计", "IT infrastructure solutions", 0.95)
        add_cross("solution_domain", "网络安全", "network security", 0.9)
        add_cross("delivery_motion", "需求分析", "Understand client requirement", 0.92)
        add_cross("delivery_motion", "方案设计", "solution designs", 0.93)
        add_cross("delivery_motion", "技术提案", "technical proposals", 0.93)
        add_cross("delivery_motion", "方案演示", "solution demonstrations", 0.93)
        add_cross("delivery_motion", "POC 测试", "Proof-Of-Concept (POC) tests", 0.94)
        add_cross("delivery_motion", "投标", "tender preparation", 0.92)
        add_cross("delivery_motion", "售前到项目交付衔接", "presales to project delivery", 0.92)
        add_cross("compliance_standard", "ISO 27001", "ISO 27001", 0.98)
        add_cross("compliance_standard", "政府合规", "government standards", 0.9)
        add_cross("compliance_standard", "信息安全合规", "network security", 0.86)
        add_cross("system_or_asset", "传感器", "suitable sensors brands", 0.94)
        add_cross("system_or_asset", "机械设备", "physical condition of machinery", 0.94)

        if has("spoken & written english"):
            soft["language"].append("英语")
        if has("chinese"):
            soft["language"].append("中文")
        if has("work independently"):
            soft["soft_skill"].append("独立工作能力")
        if has("part of a team"):
            soft["soft_skill"].append("团队合作")
        if has("government and public sector clients"):
            soft["domain_knowledge"].append("政府/公共部门业务知识")
        for name, needle in (
            ("需求分析", "Understand client requirement"),
            ("演示/汇报", "presentations"),
            ("客户沟通", "client"),
            ("供应商沟通", "vendors"),
            ("投标准备", "tender preparation"),
        ):
            if has(needle.lower()):
                soft["business_skill"].append(name)
        if has("degree holder"):
            soft["education"].append("相关学位")
        if has("iso 27001"):
            soft["certification"].append("ISO 27001")

        if has("water treatment facilities"):
            candidates.append({
                "name": "水处理设施知识",
                "category": "domain_knowledge",
                "aliases": ["water treatment facilities"],
                "evidence": cls._evidence(jd_text, "water treatment facilities"),
                "reason": "domain-specific reusable label not fully covered by existing taxonomy",
                "confidence": 0.96,
                "requirement_level": "required",
                "status": "candidate",
            })
        if has("suitable sensors brands"):
            candidates.append({
                "name": "传感器品牌选型",
                "category": "industrial_iot",
                "aliases": ["suitable sensors brands"],
                "evidence": cls._evidence(jd_text, "suitable sensors brands"),
                "reason": "asset-selection capability should be discoverable as a reusable taxonomy candidate",
                "confidence": 0.92,
                "requirement_level": "required",
                "status": "candidate",
            })
        if has("proof-of-concept"):
            candidates.append({
                "name": "Proof-Of-Concept",
                "category": "alias",
                "aliases": ["POC 测试"],
                "evidence": cls._evidence(jd_text, "Proof-Of-Concept"),
                "reason": "alias of POC 测试",
                "confidence": 0.95,
                "requirement_level": "",
                "status": "candidate",
            })

        cross_profile = postprocess_cross_industry_profile(cross_raw)
        return RoleResult(
            role_id="solution_architect",
            role_name=ROLE_DEFINITIONS["solution_architect"]["name"],
            confidence="high" if signal_count >= 5 else "medium",
            soft_skills=soft,
            tag_profile=postprocess_tag_profile(tag_raw),
            cross_industry_profile=cross_profile,
            job_context_profile={"summary_tags": build_summary_tags(cross_profile)},
            taxonomy_candidates=candidates,
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
                    job["soft_skills"] = result.soft_skills
                    job["tag_profile"] = result.tag_profile
                    job["cross_industry_profile"] = result.cross_industry_profile
                    job["job_context_profile"] = result.job_context_profile
                    job["taxonomy_candidates"] = result.taxonomy_candidates
                except Exception as e:
                    self.logger.warning("Failed to classify job %s: %s", job.get("job_id", "?"), e)
                    job["role_id"] = "other"
                    job["role_name"] = "其他"
                    job["role_confidence"] = "low"
                    job["soft_skills"] = self._normalize_soft_skills({})
                    job["tag_profile"] = self._empty_tag_profile()
                    job["cross_industry_profile"] = self._empty_cross_industry_profile()
                    job["job_context_profile"] = self._empty_job_context_profile()
                    job["taxonomy_candidates"] = []
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
