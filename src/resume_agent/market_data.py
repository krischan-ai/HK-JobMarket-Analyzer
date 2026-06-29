"""统计分析数据的只读桥接层（v1.2 / 设计文档第 13 章）。

把简历工作流"自己用弱 Prompt 重新解析 JD + 数裸技能词频"替换为
"直接消费统计侧已治理好的结构化标签 + 词库"。

边界：本模块只**读** role_cache.json / data/taxonomy/*.json，不写回，
不触发统计侧缓存失效，两系统单向依赖。用户简历原文仍不持久化。
"""

from __future__ import annotations

import json
from threading import Lock
from typing import Any, Optional

from config.settings import settings
from src.analyzer.role_classifier import RoleClassifier
from src.logger import get_logger

logger = get_logger(__name__)

# tag_profile 真实只有 technical / non_technical 两个桶（experience 类标签归在
# non_technical 下，靠 category 区分），不再假设存在独立 experience 组。
_TAG_GROUPS = ("technical", "non_technical")

_REQUIREMENT_LEVELS = ("required", "preferred", "example", "inferred")

# RoleClassifier 加载 role_cache.json（~2MB）成本不低，进程内复用单例，避免每个
# 节点都重读磁盘。仅用于只读 cache 命中判断，不做分类写入。
_classifier: Optional[RoleClassifier] = None
_classifier_lock = Lock()

# 词库文件按 mtime 缓存，避免每段润色重复读盘。
_taxonomy_cache: dict[str, Any] = {}


def _shared_classifier() -> RoleClassifier:
    global _classifier
    if _classifier is None:
        with _classifier_lock:
            if _classifier is None:
                _classifier = RoleClassifier()
    return _classifier


def load_job_tag_profile(jd_text: str) -> Optional[dict[str, Any]]:
    """命中库内已分类岗位时返回治理后的结构化标签资产，否则返回 None。

    用 RoleClassifier 的缓存键直接命中 role_cache.json；未命中时返回 None，
    调用方应回退到 LLM 解析（analyze_jd 原有逻辑），功能不阻塞。
    """
    text = (jd_text or "").strip()
    if not text:
        return None
    try:
        classifier = _shared_classifier()
        cache_key = classifier._make_cache_key(text)
        cached = classifier._cache.get(cache_key)
    except Exception as exc:  # pragma: no cover - 缓存不可用时安全降级
        logger.warning("load_job_tag_profile fallback (cache unavailable): %s", exc)
        return None
    if not cached:
        return None
    tag_profile = cached.get("tag_profile") or {}
    # 仅在确有治理后的标签时才视为命中，避免空壳缓存误触发"免重解析"。
    if not any(tag_profile.get(group) for group in _TAG_GROUPS):
        return None
    return {
        "tag_profile": tag_profile,
        "soft_skills": cached.get("soft_skills") or {},
        "cross_industry_profile": cached.get("cross_industry_profile") or {},
        "job_context_profile": cached.get("job_context_profile") or {},
        "taxonomy_candidates": cached.get("taxonomy_candidates") or [],
    }


def split_jd_by_requirement(tag_profile: dict[str, Any]) -> dict[str, list[dict]]:
    """把 tag_profile 拆成 required / preferred / example / inferred 四桶。

    example / inferred 不进入硬性技能差距统计（修复§13.1「示例当硬要求」：
    JD 中 "e.g. JavaScript/Go/Java 任一" 的备选语言池不应被当成缺失硬技能）。
    """
    buckets: dict[str, list[dict]] = {level: [] for level in _REQUIREMENT_LEVELS}
    for group in _TAG_GROUPS:
        for tag in tag_profile.get(group, []) or []:
            if not isinstance(tag, dict) or not tag.get("name"):
                continue
            level = str(tag.get("requirement_level") or "required")
            buckets.setdefault(level, []).append(tag)
    return buckets


def tag_names(tags: list[dict]) -> list[str]:
    """提取标签名并去重保序。"""
    seen: set[str] = set()
    out: list[str] = []
    for tag in tags or []:
        name = str(tag.get("name") or "").strip() if isinstance(tag, dict) else ""
        if name and name not in seen:
            seen.add(name)
            out.append(name)
    return out


def _taxonomy_dir():
    return settings.data_dir / "taxonomy"


def load_taxonomy() -> dict[str, Any]:
    """加载正式词库 / 别名 / 拒绝列表 / 候选标签，供关键词归一与误判抑制。

    词库文件缺失时返回空结构，关键词归一退化为原样写入（§13.7 兼容策略）。
    按目录 mtime 缓存，避免每段润色重复读盘。
    """
    base = _taxonomy_dir()
    try:
        signature = base.stat().st_mtime
    except OSError:
        signature = 0.0
    if _taxonomy_cache.get("signature") == signature:
        return _taxonomy_cache["data"]

    out: dict[str, Any] = {}
    for name in ("skill_taxonomy", "taxonomy_aliases", "taxonomy_rejections", "taxonomy_candidates"):
        path = base / f"{name}.json"
        try:
            out[name] = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            out[name] = {}

    _taxonomy_cache["signature"] = signature
    _taxonomy_cache["data"] = out
    return out


def _build_alias_index(taxonomy: dict[str, Any]) -> dict[str, str]:
    """构造 alias(lower) -> 规范写法 的映射。

    兼容两种 taxonomy_aliases 结构：
    - {alias: canonical}
    - {canonical: [alias, ...]}
    """
    aliases = taxonomy.get("taxonomy_aliases") or {}
    index: dict[str, str] = {}
    if isinstance(aliases, dict):
        for key, value in aliases.items():
            if isinstance(value, str):
                index[str(key).strip().lower()] = value
            elif isinstance(value, list):
                for alias in value:
                    if alias:
                        index[str(alias).strip().lower()] = str(key)
    return index


def _build_rejection_set(taxonomy: dict[str, Any]) -> set[str]:
    """构造误判词集合（lower），命中者禁止作为"市场要求"写入简历。"""
    rejections = taxonomy.get("taxonomy_rejections") or {}
    result: set[str] = set()
    if isinstance(rejections, dict):
        for key, value in rejections.items():
            result.add(str(key).strip().lower())
            if isinstance(value, dict):
                for alias in value.get("aliases") or []:
                    result.add(str(alias).strip().lower())
    elif isinstance(rejections, list):
        for item in rejections:
            if isinstance(item, dict) and item.get("name"):
                result.add(str(item["name"]).strip().lower())
            elif isinstance(item, str):
                result.add(item.strip().lower())
    result.discard("")
    return result


def normalize_keywords(keywords: list[str], taxonomy: dict[str, Any] | None = None) -> list[str]:
    """用 taxonomy_aliases 归并同义异形、剔除 taxonomy_rejections 误判词。

    词库缺失时退化为去重去空，保证 ATS 关键词一致性而不报错。
    """
    tax = taxonomy if taxonomy is not None else load_taxonomy()
    alias_index = _build_alias_index(tax)
    rejected = _build_rejection_set(tax)

    out: list[str] = []
    seen: set[str] = set()
    for raw in keywords or []:
        keyword = str(raw or "").strip()
        if not keyword:
            continue
        lower = keyword.lower()
        if lower in rejected:
            continue
        canonical = alias_index.get(lower, keyword)
        dedup_key = canonical.lower()
        if dedup_key not in seen:
            seen.add(dedup_key)
            out.append(canonical)
    return out


def candidate_capability_hints(taxonomy_candidates: list[dict], limit: int = 5) -> list[dict]:
    """从 taxonomy_candidates 中挑高置信、非 alias 的新兴场景标签，作为前瞻补强建议。"""
    hints: list[dict] = []
    for cand in taxonomy_candidates or []:
        if not isinstance(cand, dict):
            continue
        if str(cand.get("category") or "") == "alias":
            continue
        name = str(cand.get("name") or "").strip()
        if not name:
            continue
        try:
            confidence = float(cand.get("confidence") or 0)
        except (TypeError, ValueError):
            confidence = 0.0
        if confidence < 0.85:
            continue
        hints.append({
            "name": name,
            "category": str(cand.get("category") or ""),
            "confidence": confidence,
            "evidence": str(cand.get("evidence") or ""),
        })
    hints.sort(key=lambda h: h["confidence"], reverse=True)
    return hints[:limit]
