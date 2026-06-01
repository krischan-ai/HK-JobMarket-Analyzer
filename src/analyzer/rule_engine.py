from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

from src.logger import get_logger


class RuleBasedSkillExtractor:
    """基于关键词词表 + 正则边界匹配的技能提取引擎"""

    def __init__(self, dict_path: str | Path = "config/tech_dict.json"):
        self.logger = get_logger(self.__class__.__name__)
        with open(dict_path, "r", encoding="utf-8") as f:
            self.tech_dict = json.load(f)
        self._compiled = self._compile_patterns()

    def _compile_patterns(self) -> dict:
        compiled = {}
        for category, keywords in self.tech_dict.items():
            compiled[category] = []
            for kw in keywords:
                pattern = re.compile(r"\b" + kw + r"\b", re.IGNORECASE)
                compiled[category].append((kw, pattern))
        return compiled

    def extract(self, text: str) -> dict:
        if not text:
            return {cat: [] for cat in self.tech_dict}

        result = {}
        for category, patterns in self._compiled.items():
            found = set()
            for raw_kw, pattern in patterns:
                if pattern.search(text):
                    display = (
                        raw_kw
                        .replace("\\+", "+")
                        .replace("\\s+", " ")
                        .replace("\\.", ".")
                        .replace("\\(", "(")
                        .replace("\\)", ")")
                    )
                    if display.lower() == display:
                        display = display.capitalize()
                    found.add(display)
            result[category] = sorted(found)

        return result

    def extract_flat(self, text: str) -> list[str]:
        nested = self.extract(text)
        flat = []
        for skills in nested.values():
            flat.extend(skills)
        return flat

    def analyze_batch(self, jobs: list[dict], text_field: str = "jd_text") -> list[dict]:
        for job in jobs:
            text = job.get(text_field, "")
            job["skills"] = self.extract(text)
        return jobs
