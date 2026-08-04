from __future__ import annotations

import json
from collections import Counter
from typing import Any

from config.settings import settings
from src.analyzer.role_classifier import CACHE_PATH as _ROLE_CACHE_PATH, RoleClassifier, RoleResult
from src.logger import get_logger

logger = get_logger(__name__)

_CSV_PATH = settings.data_dir / "cleaned" / "jobs.csv"
# 软技能不计入"技术栈"次数排名。
_SKILL_SKIP_CATEGORIES = {"soft_skills"}
# 技术栈榜单只统计硬性/加分要求，办公工具与示例/推断项不计入（§13.6.1）。
_TECH_RANK_LEVELS = {"required", "preferred"}
_TECH_RANK_SKIP_CATEGORIES = {"office_tools"}

_cache: dict[str, Any] = {}


def _tech_ranking_from_tag_profile(top_n: int) -> list[dict[str, Any]]:
    """优先从 role_cache.json 的治理标签统计技术栈榜单。

    只统计 technical 桶里 requirement_level 为 required/preferred 的标签，
    排除办公工具——口径与统计侧一致，规避裸 skills 词频混入 PowerPoint/Excel。
    缓存为空时返回空列表，调用方回退到 skills 词频。
    """
    try:
        classifier = RoleClassifier()
        cache = classifier._cache or {}
    except Exception as exc:  # pragma: no cover
        logger.warning("Tag-profile tech ranking unavailable: %s", exc)
        return []

    counter: Counter[str] = Counter()
    for entry in cache.values():
        tag_profile = (entry or {}).get("tag_profile") or {}
        for tag in tag_profile.get("technical", []) or []:
            if not isinstance(tag, dict):
                continue
            if str(tag.get("requirement_level") or "required") not in _TECH_RANK_LEVELS:
                continue
            if str(tag.get("category") or "") in _TECH_RANK_SKIP_CATEGORIES:
                continue
            name = str(tag.get("name") or "").strip()
            if name:
                counter[name] += 1
    return [{"skill": skill, "count": count} for skill, count in counter.most_common(top_n)]


def _csv_mtime() -> float:
    try:
        return _CSV_PATH.stat().st_mtime
    except OSError:
        return 0.0


def _role_cache_mtime() -> float:
    try:
        return _ROLE_CACHE_PATH.stat().st_mtime
    except OSError:
        return 0.0


def compute_market_insights(top_n: int = 15) -> dict[str, Any]:
    """基于整库岗位数据计算市场需求洞察（带缓存，CSV 变更时自动失效）。

    - tech_stack_ranking: JD 中技术栈被提及的次数排名。
    - role_demand_ranking: 需求量最大的岗位方向排名（规则分类，全量）。
    """
    signature = (_csv_mtime(), _role_cache_mtime(), top_n)
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

    # 技术栈榜单：优先读治理后的 tag_profile（按 requirement_level 过滤、排除办公工具），
    # 缓存缺失时回退到 jobs.csv 的裸 skills 词频（§13.6.1 + §13.7 降级策略）。
    tech_ranking = _tech_ranking_from_tag_profile(top_n)
    if not tech_ranking:
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
        cache_key = classifier._make_cache_key(text)
        cached = classifier._cache.get(cache_key)
        if cached:
            result = RoleResult(
                role_id=cached.get("role_id", "other"),
                role_name=cached.get("role_name", "其他"),
                confidence=cached.get("confidence", "low"),
            )
        else:
            # 整库洞察在用户请求链路里不能逐条实时调用 LLM；未缓存项使用规则兜底，
            # 后台批量分类写入 role_cache.json 后会自动复用语义结果。
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
