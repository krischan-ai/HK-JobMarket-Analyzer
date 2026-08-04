"""tag_profile 后处理（v1.2 标签质量治理，doc §11.6）

输入 LLM 原始 tag_profile，输出清洗后的结构化标签：
  标准化 -> 分类纠偏 -> 依证据修正要求层级 -> 负例抑制 -> 多义词消歧 -> 去重。

纯函数、无 I/O，依赖 skill_taxonomy 作为单一数据源，便于单测。
"""

from __future__ import annotations

from typing import Any

from src.analyzer import skill_taxonomy as tax

_LEVEL_RANK = {"required": 3, "preferred": 2, "example": 1, "inferred": 0}
_EVIDENCE_MAX = 160


def _coerce_tag(raw: Any) -> dict | None:
    """把单条标签规整为标准 dict；无法识别名称则返回 None。"""
    if isinstance(raw, str):
        name = raw.strip()
        return {"name": name} if name else None
    if not isinstance(raw, dict):
        return None
    name = str(raw.get("name", "")).strip()
    if not name:
        return None
    return {
        "name": name,
        "category": str(raw.get("category", "") or "").strip(),
        "requirement_level": str(raw.get("requirement_level", "") or "").strip().lower(),
        "source": str(raw.get("source", "") or "llm").strip().lower(),
        "confidence": raw.get("confidence"),
        "evidence": str(raw.get("evidence", "") or "").strip()[:_EVIDENCE_MAX],
    }


def _coerce_confidence(value: Any, default: float = 0.6) -> float:
    try:
        conf = float(value)
    except (TypeError, ValueError):
        return default
    return max(0.0, min(1.0, conf))


def _resolve_level(evidence: str, llm_level: str) -> str:
    marker = tax.infer_requirement_level(evidence)
    if marker is not None:
        # 证据标记词权威；但 LLM 标 inferred 且证据无强标记时保留 inferred
        return marker
    if llm_level in tax.VALID_LEVELS:
        return llm_level
    return "required"


def _correct_category(name: str, llm_category: str) -> str:
    override = tax.NAME_CATEGORY_OVERRIDES.get(name.strip().lower())
    if override:
        return override
    if llm_category in tax.CATEGORY_DISPLAY:
        return llm_category
    return "other"


def _resolve_llama(name: str, evidence: str) -> tuple[str, str] | None:
    """处理独立 llama 歧义（doc §11.4）。返回 (name, category) 或 None 表示丢弃。"""
    ev = evidence.lower()
    if "llamaindex" in ev or "llama index" in ev or "llama-index" in ev:
        return "LlamaIndex", "ai_framework"
    model_ctx = ("llama 2", "llama2", "llama-2", "llama 3", "llama3", "llama-3", "meta llama", "llama model")
    if any(c in ev for c in model_ctx):
        return "LLaMA", "ai_concepts"
    return None


def _disambiguate_domain(name: str, evidence: str, category: str) -> tuple[str, str] | None:
    """domain_knowledge 多义词消歧 + 福利语境抑制。返回 (name, category) 或 None 表示丢弃。"""
    if category != "domain_knowledge":
        return name, category
    ev = evidence.lower()
    for keyword, rules in tax.DISAMBIGUATION.items():
        # 兼容单复数（payment / payments）
        if not (tax.word_boundary_match(keyword, ev) or tax.word_boundary_match(keyword + "s", ev)):
            continue
        for ctx_words, target in rules:
            if any(c in ev for c in ctx_words):
                if target is None:
                    return None  # 福利/非行业语境，丢弃
                return target, "domain_knowledge"
    # 通用福利语境抑制：行业知识标签证据落在福利描述里则丢弃
    if any(w in ev for w in tax.BENEFIT_CONTEXT_WORDS) and not _has_industry_signal(ev):
        return None
    return name, category


def _has_industry_signal(ev: str) -> bool:
    """证据中是否含明确行业/业务语境（避免把所有含 benefit 的证据都误删）。"""
    signals = (
        "industry", "sector", "business", "client", "customer", "domain",
        "ecommerce", "e-commerce", "retail", "banking", "fintech", "logistics",
        "supply chain", "healthcare", "government", "erp", "行業", "業務", "客戶",
    )
    return any(s in ev for s in signals)


def _process_one(raw: Any) -> dict | None:
    tag = _coerce_tag(raw)
    if tag is None:
        return None

    name = tax.normalize_name(tag.get("name", ""))
    evidence = tag.get("evidence", "")
    category = _correct_category(name, tag.get("category", ""))

    # 独立 llama 歧义
    if name.strip().lower() == "llama":
        resolved = _resolve_llama(name, evidence)
        if resolved is None:
            return None
        name, category = resolved

    # domain_knowledge 多义词消歧 / 福利抑制
    disambig = _disambiguate_domain(name, evidence, category)
    if disambig is None:
        return None
    name, category = disambig

    level = _resolve_level(evidence, tag.get("requirement_level", ""))
    confidence = _coerce_confidence(tag.get("confidence"))
    if level == "inferred":
        confidence = min(confidence, tax.INFERRED_MAX_CONFIDENCE)

    source = tag.get("source") or "llm"
    return {
        "name": name,
        "category": category,
        "requirement_level": level,
        "source": source,
        "confidence": round(confidence, 2),
        "evidence": evidence,
    }


def _bucket_for(category: str, original_bucket: str) -> str:
    if category in tax.TECHNICAL_CATEGORIES:
        return "technical"
    if category in tax.NON_TECHNICAL_CATEGORIES:
        return "non_technical"
    return original_bucket


def _dedupe(tags: list[dict]) -> list[dict]:
    best: dict[tuple[str, str], dict] = {}
    for tag in tags:
        key = (tag["name"].lower(), tag["category"])
        cur = best.get(key)
        if cur is None:
            best[key] = tag
            continue
        # 保留更强层级 / 更高置信 / 更长证据
        if (_LEVEL_RANK.get(tag["requirement_level"], 0), tag["confidence"], len(tag["evidence"])) > (
            _LEVEL_RANK.get(cur["requirement_level"], 0), cur["confidence"], len(cur["evidence"])
        ):
            best[key] = tag
    return list(best.values())


def postprocess_tag_profile(raw: Any) -> dict[str, list[dict]]:
    """清洗 LLM 原始 tag_profile，返回 {"technical": [...], "non_technical": [...]}。"""
    result: dict[str, list[dict]] = {"technical": [], "non_technical": []}
    if not isinstance(raw, dict):
        return result

    for bucket in ("technical", "non_technical"):
        items = raw.get(bucket, [])
        if not isinstance(items, list):
            continue
        for item in items:
            processed = _process_one(item)
            if processed is None:
                continue
            target = _bucket_for(processed["category"], bucket)
            result[target].append(processed)

    for bucket in ("technical", "non_technical"):
        result[bucket] = _dedupe(result[bucket])
        result[bucket].sort(
            key=lambda t: (_LEVEL_RANK.get(t["requirement_level"], 0), t["confidence"]),
            reverse=True,
        )
    return result


# ===========================================================================
# 跨行业六维标签治理（v1.3+v1.4，doc §11.10）
# ===========================================================================


def _coerce_dim_tag(raw: Any) -> dict | None:
    if isinstance(raw, str):
        name = raw.strip()
        return {"name": name, "confidence": 0.6, "evidence": ""} if name else None
    if not isinstance(raw, dict):
        return None
    name = str(raw.get("name", "")).strip()
    if not name:
        return None
    return {
        "name": name,
        "confidence": _coerce_confidence(raw.get("confidence")),
        "evidence": str(raw.get("evidence", "") or "").strip()[:_EVIDENCE_MAX],
    }


def _disambiguate_dimension(dim: str, name: str, evidence: str) -> str | None:
    """industry_context/business_scenario 多义词消歧 + 福利语境抑制。
    返回归一后的 name 或 None（丢弃）。"""
    if dim not in ("industry_context", "business_scenario"):
        return name
    ev = evidence.lower()
    for keyword, rules in tax.CROSS_DISAMBIGUATION.items():
        if not (tax.word_boundary_match(keyword, ev) or tax.word_boundary_match(keyword + "s", ev)):
            continue
        for ctx_words, target in rules:
            if any(c in ev for c in ctx_words):
                return target  # None -> 丢弃；否则重新归类
    if any(w in ev for w in tax.BENEFIT_CONTEXT_WORDS) and not _has_industry_signal(ev):
        return None
    return name


def postprocess_cross_industry_profile(raw: Any) -> dict[str, list[dict]]:
    """清洗 LLM 六维原子标签：名称归一 -> 消歧/抑制 -> 去重 -> 按置信排序。"""
    result: dict[str, list[dict]] = {dim: [] for dim in tax.CROSS_INDUSTRY_DIMENSIONS}
    if not isinstance(raw, dict):
        return result
    for dim in tax.CROSS_INDUSTRY_DIMENSIONS:
        items = raw.get(dim, [])
        if not isinstance(items, list):
            continue
        seen: dict[str, dict] = {}
        for item in items:
            tag = _coerce_dim_tag(item)
            if tag is None:
                continue
            name = tax.normalize_dimension_name(tag["name"])
            disamb = _disambiguate_dimension(dim, name, tag["evidence"])
            if disamb is None:
                continue
            name = tax.normalize_dimension_name(disamb)
            entry = {"name": name, "confidence": tag["confidence"], "evidence": tag["evidence"]}
            cur = seen.get(name.lower())
            if cur is None or (entry["confidence"], len(entry["evidence"])) > (cur["confidence"], len(cur["evidence"])):
                seen[name.lower()] = entry
        result[dim] = sorted(seen.values(), key=lambda t: t["confidence"], reverse=True)
    return result


def build_summary_tags(cross_profile: Any) -> list[dict]:
    """确定性组合器：当某规则命中 ≥min_groups 个不同维度信号时产出组合画像（doc §11.10.4）。"""
    if not isinstance(cross_profile, dict):
        return []
    summaries: dict[str, dict] = {}
    for rule in tax.COMBINATION_RULES:
        matched_dims: dict[str, float] = {}
        for dim, keywords in rule["groups"]:
            tags = cross_profile.get(dim, [])
            if not isinstance(tags, list):
                continue
            best: float | None = None
            for t in tags:
                if not isinstance(t, dict):
                    continue
                hay = (str(t.get("name", "")) + " " + str(t.get("evidence", ""))).lower()
                if tax.any_keyword(hay, keywords):
                    conf = _coerce_confidence(t.get("confidence"))
                    best = conf if best is None else max(best, conf)
            if best is not None and (dim not in matched_dims or best > matched_dims[dim]):
                matched_dims[dim] = best
        if len(matched_dims) >= rule.get("min_groups", 2):
            conf = round(sum(matched_dims.values()) / len(matched_dims), 2)
            name = rule["name"]
            existing = summaries.get(name)
            if existing is None or conf > existing["confidence"]:
                summaries[name] = {
                    "name": name,
                    "confidence": conf,
                    "supporting_dimensions": sorted(matched_dims.keys()),
                }
    return sorted(summaries.values(), key=lambda s: s["confidence"], reverse=True)
