from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

from src.cleaner.text import JDTextCleaner
from src.cleaner.salary import SalaryParser
from src.logger import get_logger
from scripts.crawl_utils import parse_job_fields


_ZH_LOCATION_MAP: dict[str, str] | None = None


def _load_zh_location_map() -> dict[str, str]:
    global _ZH_LOCATION_MAP
    if _ZH_LOCATION_MAP is not None:
        return _ZH_LOCATION_MAP
    path = Path(__file__).resolve().parent.parent.parent / "config" / "i18n" / "locations_zh.json"
    if path.exists():
        with open(path, encoding="utf-8") as f:
            en_to_zh = json.load(f)
        _ZH_LOCATION_MAP = {v.lower(): k for k, v in en_to_zh.items()}
        _ZH_LOCATION_MAP.update({
            "遠程": "Remote",
            "遠程 in hong kong": "Remote",
            "hong kong island": "Hong Kong Island",
            "hong kong": "Hong Kong",
            "new territories": "New Territories",
            "kowloon": "Kowloon",
        })
    else:
        _ZH_LOCATION_MAP = {}
    return _ZH_LOCATION_MAP


def normalize_location(raw: str) -> str:
    if not raw or not isinstance(raw, str):
        return raw or "Hong Kong"
    loc = raw.strip()
    loc_lower = loc.lower()
    zh_map = _load_zh_location_map()
    if loc_lower in zh_map:
        return zh_map[loc_lower]
    area_suffixes = [
        (", kowloon", "Kowloon"),
        (", hong kong island", "Hong Kong Island"),
        (", new territories", "New Territories"),
        (", hong kong", "Hong Kong"),
    ]
    for suffix, area_en in area_suffixes:
        if loc_lower.endswith(suffix):
            core = loc[:-len(suffix)].strip()
            core_lower = core.lower()
            translated = zh_map.get(core_lower, core)
            return f"{translated}, {area_en}"
    if "遠程" in loc:
        return "Remote"
    return loc


class CleaningPipeline:
    """数据清洗管道，组合文本清洗与薪资解析"""

    def __init__(self):
        self.text_cleaner = JDTextCleaner()
        _load_zh_location_map()
        self.logger = get_logger(self.__class__.__name__)

    def clean_job(self, job: dict) -> dict:
        cleaned = dict(job)
        raw_jd = job.get("jd_raw", "")
        cleaned["jd_text"] = self.text_cleaner.clean(raw_jd)
        salary_raw = job.get("salary_raw", "")
        min_sal, max_sal = SalaryParser.parse(salary_raw)
        cleaned["salary_min"] = min_sal
        cleaned["salary_max"] = max_sal
        cleaned["salary_currency"] = "HKD"
        if "location" in cleaned:
            cleaned["location"] = normalize_location(cleaned["location"])
        parse_job_fields(cleaned)
        return cleaned

    def clean_batch(self, jobs: list[dict]) -> list[dict]:
        cleaned = []
        for job in jobs:
            try:
                cleaned.append(self.clean_job(job))
            except Exception as e:
                self.logger.warning("Failed to clean job %s: %s", job.get("job_id", "unknown"), e)
                cleaned.append(job)
        return cleaned
