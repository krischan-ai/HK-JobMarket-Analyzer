from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Optional

from src.analyzer.llm_engine import LLMExtractor
from src.analyzer.rule_engine import RuleBasedSkillExtractor
from src.llm_config_manager import LLMConfigManager
from src.logger import get_logger


class HybridExtractor:
    """双引擎混合技能提取器：规则引擎优先 → LLM 兜底 → 词表更新反馈

    策略说明：
    1. 先用规则引擎提取（< 5ms/条），覆盖 80%+ 的常见技能
    2. 如果规则引擎提取结果为空或置信度低，调用 LLM 兜底
    3. LLM 发现的新关键词可回写到词表（增量更新）

    配置来源（按优先级）：
    - 构造参数 llm_extractor
    - 面板持久化配置 config/llm_config.json
    - .env / 环境变量
    """

    def __init__(self, dict_path: str | Path = "config/tech_dict.json", llm_extractor: Optional[LLMExtractor] = None):
        self.rule_engine = RuleBasedSkillExtractor(dict_path)
        self.llm = llm_extractor or LLMExtractor()
        self.config_mgr = LLMConfigManager()
        self.dict_path = dict_path
        self.logger = get_logger(self.__class__.__name__)

        with open(dict_path, "r", encoding="utf-8") as f:
            self.tech_dict = json.load(f)

    @property
    def llm_configured(self) -> bool:
        return self.config_mgr.configured

    def extract(self, text: str, always_use_llm: bool = False) -> dict:
        rule_result = self.rule_engine.extract(text)

        if not always_use_llm and self._is_sufficient(rule_result):
            rule_result["engine"] = "rule"
            return rule_result

        if not self.llm.available:
            rule_result["engine"] = "rule_only"
            return rule_result

        llm_result = self.llm.extract(text)
        merged = self._merge_results(rule_result, llm_result)
        merged["engine"] = "hybrid"
        return merged

    def extract_batch(self, jobs: list[dict], text_field: str = "jd_raw", always_use_llm: bool = False) -> list[dict]:
        for job in jobs:
            text = job.get(text_field, "")
            result = self.extract(text, always_use_llm=always_use_llm)
            engine = result.pop("engine", "rule")
            job["skills"] = result
            job["extract_engine"] = engine
        return jobs

    def _is_sufficient(self, result: dict) -> bool:
        total = sum(len(v) for v in result.values())
        if total >= 3:
            return True
        tech_skills = sum(len(v) for k, v in result.items() if k != "soft_skills")
        return tech_skills >= 2

    def _merge_results(self, rule_result: dict, llm_result: dict) -> dict:
        merged = {}
        for cat in self.llm._default_categories():
            rule_skills = set(rule_result.get(cat, []))
            llm_skills = set(llm_result.get(cat, []))
            merged[cat] = sorted(rule_skills | llm_skills)
        return merged

    def find_new_terms(self, rule_result: dict, llm_result: dict) -> dict:
        """找出 LLM 提取到但规则引擎未匹配的新词"""
        new_terms = {}
        for cat in self.llm._default_categories():
            rule_skills = set(s.lower() for s in rule_result.get(cat, []))
            llm_skills = set(s.lower() for s in llm_result.get(cat, []))
            diff = llm_skills - rule_skills
            if diff:
                new_terms[cat] = sorted(diff)
        return new_terms

    def suggest_dict_updates(self, jobs: list[dict], text_field: str = "jd_raw", min_occurrences: int = 2) -> dict:
        """扫描一批数据，找出高频出现但词表中未收录的技能词"""
        from collections import Counter
        candidates = {cat: Counter() for cat in self.llm._default_categories()}

        for job in jobs:
            text = job.get(text_field, "")
            if not text:
                continue
            rule_result = self.rule_engine.extract(text)
            if self._is_sufficient(rule_result):
                continue
            llm_result = self.llm.extract(text)
            new_terms = self.find_new_terms(rule_result, llm_result)
            for cat, terms in new_terms.items():
                for term in terms:
                    candidates[cat][term] += 1

        suggestions = {}
        for cat, counter in candidates.items():
            frequent = {k: v for k, v in counter.items() if v >= min_occurrences}
            if frequent:
                suggestions[cat] = dict(sorted(frequent.items(), key=lambda x: -x[1]))
        return suggestions
