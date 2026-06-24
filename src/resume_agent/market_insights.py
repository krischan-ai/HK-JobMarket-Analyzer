from __future__ import annotations

import json
from collections import Counter
from typing import Any

from config.settings import settings
from src.analyzer.role_classifier import RoleClassifier
from src.logger import get_logger

logger = get_logger(__name__)

_CSV_PATH = settings.data_dir / "cleaned" / "jobs.csv"
# 软技能不计入"技术栈"次数排名。
_SKILL_SKIP_CATEGORIES = {"soft_skills"}

_cache: dict[str, Any] = {}


def _csv_mtime() -> float:
    try:
        return _CSV_PATH.stat().st_mtime
    except OSError:
        return 0.0


def compute_market_insights(top_n: int = 15) -> dict[str, Any]:
    """基于整库岗位数据计算市场需求洞察（带缓存，CSV 变更时自动失效）。

    - tech_stack_ranking: JD 中技术栈被提及的次数排名。
    - role_demand_ranking: 需求量最大的岗位方向排名（规则分类，全量）。
    """
    signature = (_csv_mtime(), top_n)
    if _cache.get("signature") == signature:
        return _cache["data"]

    data = _build(top_n)
    _cache["signature"] = signature
    _cache["data"] = data
    return data


def _build(top_n: int) -> dict[str, Any]:
    try:
        import pandas as pd

        df = pd.read_csv(_CSV_PATH)
    except Exception as exc:  # pragma: no cover - 数据缺失时的兜底
        logger.warning("Market insights unavailable: %s", exc)
        return {"total_jobs": 0, "tech_stack_ranking": [], "role_demand_ranking": []}

    total = len(df)

    tech_counter: Counter[str] = Counter()
    if "skills" in df.columns:
        for value in df["skills"].dropna():
            try:
                skill_dict = json.loads(value)
            except (TypeError, ValueError):
                continue
            for category, items in (skill_dict or {}).items():
                if category in _SKILL_SKIP_CATEGORIES:
                    continue
                for skill in items or []:
                    if skill:
                        tech_counter[str(skill)] += 1
    tech_ranking = [{"skill": skill, "count": count} for skill, count in tech_counter.most_common(top_n)]

    classifier = RoleClassifier()
    role_counter: Counter[str] = Counter()
    role_names: dict[str, str] = {}
    for _, row in df.iterrows():
        text = f"{row.get('title', '')} {row.get('jd_text', '') or row.get('jd_raw', '')}".strip()
        if not text:
            continue
        result = classifier._classify_with_rules(text)
        if result.role_id and result.role_id != "other":
            role_counter[result.role_id] += 1
            role_names[result.role_id] = result.role_name
    role_ranking = [
        {"role_id": role_id, "role_name": role_names.get(role_id, role_id), "count": count}
        for role_id, count in role_counter.most_common(top_n)
    ]

    return {
        "total_jobs": total,
        "tech_stack_ranking": tech_ranking,
        "role_demand_ranking": role_ranking,
    }
