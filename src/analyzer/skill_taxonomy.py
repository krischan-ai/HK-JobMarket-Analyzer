"""统一标签词库（v1.2 标签质量治理）

集中维护标签的一级分类、归一展示名、分类纠偏、要求层级标记词、
负例上下文与多义词消歧规则，作为 tag_profile 后处理（skill_postprocessor）
的单一数据源。

设计原则：
- 纯数据 + 小工具函数，无任何 I/O 与第三方依赖，便于单测。
- 与 api/routers/stats.py 中 v1.1 的规则消歧逻辑保持语义一致
  （_word_boundary_match / _industry_keyword_hit / _is_non_industry_context），
  但本模块独立实现，供 LLM tag_profile 链路使用。
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# 一级分类与中文展示名（doc §11.4）
# ---------------------------------------------------------------------------

CATEGORY_DISPLAY: dict[str, str] = {
    # 技术类
    "programming_languages": "編程語言",
    "frameworks_libraries": "框架與庫",
    "databases": "數據庫",
    "cloud_devops": "雲與DevOps",
    "automation_toolkit": "自動化工具",
    "ai_api": "AI API",
    "ai_framework": "AI框架",
    "ai_concepts": "AI概念",
    "infrastructure": "IT基礎設施",
    "security_compliance": "安全與合規",
    "office_tools": "辦公工具",
    # 非技术类
    "business_skill": "業務能力",
    "domain_knowledge": "行業知識",
    "soft_skill": "軟技能",
    "education": "學歷",
    "language": "語言",
    "certification": "證書",
    "experience": "經驗",
    "presales_delivery": "售前交付",
    "other": "其他",
}

TECHNICAL_CATEGORIES: frozenset[str] = frozenset({
    "programming_languages", "frameworks_libraries", "databases", "cloud_devops",
    "automation_toolkit", "ai_api", "ai_framework", "ai_concepts",
    "infrastructure", "security_compliance", "office_tools",
})

NON_TECHNICAL_CATEGORIES: frozenset[str] = frozenset({
    "business_skill", "domain_knowledge", "soft_skill", "education",
    "language", "certification", "experience", "presales_delivery",
})

VALID_LEVELS: tuple[str, ...] = ("required", "preferred", "example", "inferred")
INFERRED_MAX_CONFIDENCE = 0.7

# ---------------------------------------------------------------------------
# 要求层级标记词（doc §11.5 规则 2-5）
#   required 优先于 example；example 优先于 preferred。
# ---------------------------------------------------------------------------

REQUIRED_MARKERS: tuple[str, ...] = (
    "essential", "must have", "must-have", "must ", "required", "requirement",
    "proficiency in", "proficient in", "expertise in", "strong experience",
    "solid experience", "hands-on experience", "hands on experience",
    "experience with", "experience in", "demonstrated", "mandatory",
)

PREFERRED_MARKERS: tuple[str, ...] = (
    "preferred", "nice to have", "nice-to-have", "a plus", "is a plus",
    "advantageous", "an advantage", "bonus", "desirable", "familiarity with",
    "familiar with", "exposure to", "ideally", "good to have", "would be great",
)

EXAMPLE_MARKERS: tuple[str, ...] = (
    "e.g.", "e.g", "such as", "for example", "one of", "at least one",
    "or other major", "including but not limited",
)

# ---------------------------------------------------------------------------
# 归一展示名（小写 -> 官方写法 / 繁体中文）
# ---------------------------------------------------------------------------

NAME_ALIASES: dict[str, str] = {
    "open ai": "OpenAI", "openai": "OpenAI",
    "anthropic": "Anthropic", "claude": "Claude",
    "lang chain": "LangChain", "langchain": "LangChain",
    "llama index": "LlamaIndex", "llamaindex": "LlamaIndex", "llama-index": "LlamaIndex",
    "rag": "RAG", "retrieval augmented generation": "RAG",
    "llm": "LLM", "llms": "LLM",
    "rpa": "RPA", "ci/cd": "CI/CD", "ci cd": "CI/CD",
    "aws": "AWS", "gcp": "GCP", "azure": "Azure",
    "sql": "SQL", "nosql": "NoSQL",
    "javascript": "JavaScript", "typescript": "TypeScript", "python": "Python",
    "vector database": "向量數據庫", "vector databases": "向量數據庫", "vector db": "向量數據庫",
    "web scraping": "Web Scraping", "api integration": "API Integration",
    "ms office": "MS Office", "microsoft office": "MS Office",
    "powerpoint": "PowerPoint", "excel": "Excel",
    "iso 27001": "ISO 27001",
}

# 分类纠偏（小写名 -> 正确一级分类），doc §11.4 调整规则
NAME_CATEGORY_OVERRIDES: dict[str, str] = {
    "openai": "ai_api", "anthropic": "ai_api", "claude": "ai_api",
    "gemini": "ai_api", "llm api": "ai_api", "ai api": "ai_api", "ai apis": "ai_api",
    "langchain": "ai_framework", "llamaindex": "ai_framework", "semantic kernel": "ai_framework",
    "rag": "ai_concepts", "llm": "ai_concepts", "embedding": "ai_concepts",
    "embeddings": "ai_concepts", "向量數據庫": "ai_concepts", "vector database": "ai_concepts",
    "rpa": "automation_toolkit", "web scraping": "automation_toolkit", "cron": "automation_toolkit",
    "api integration": "automation_toolkit", "zapier": "automation_toolkit", "make.com": "automation_toolkit",
    "powerpoint": "office_tools", "excel": "office_tools", "ms office": "office_tools",
    "microsoft office": "office_tools", "word": "office_tools",
    "sql": "databases", "nosql": "databases",
    "iso 27001": "security_compliance", "network security": "security_compliance",
    "docker": "cloud_devops", "kubernetes": "cloud_devops", "ci/cd": "cloud_devops",
    "aws": "cloud_devops", "gcp": "cloud_devops", "azure": "cloud_devops",
}

# ---------------------------------------------------------------------------
# 误判抑制（doc §11.6）
#   命中以下上下文词时，对应标签视为来自福利/地点/公司介绍语境，应删除。
# ---------------------------------------------------------------------------

# 福利/非行业语境词（domain_knowledge 抑制）
BENEFIT_CONTEXT_WORDS: tuple[str, ...] = (
    "coverage", "benefit", "benefits", "pension", "life insurance",
    "medical insurance", "medical and life", "fringe", "scheme",
    "annual leave", "bonus", "allowance", "perks",
)

# 多义行业词：命中后需结合 evidence 上下文判定
POLYSEMY_KEYWORDS: frozenset[str] = frozenset({"insurance", "medical", "health", "payment", "wealth"})

# 多义词消歧（doc §11.6 / §11.10.2）：keyword -> [(上下文词组, 目标domain标签 或 None表示丢弃)]
DISAMBIGUATION: dict[str, list[tuple[tuple[str, ...], str | None]]] = {
    "payment": [
        (("banking", "fintech", "kyc", "aml", "card", "wallet", "settlement", "remittance"), "金融/金融科技知識"),
        (("order", "promotion", "catalog", "ecommerce", "e-commerce", "retail", "pos", "checkout"), "電商/零售業務知識"),
    ],
    "insurance": [
        (("policy", "claims", "underwriting", "broker", "actuarial", "wealth"), "保險/財富管理知識"),
        (("coverage", "benefit", "medical", "life insurance", "fringe", "scheme"), None),
    ],
}

# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------


def has_cjk(text: str) -> bool:
    return any("一" <= ch <= "鿿" for ch in text)


def word_boundary_match(keyword: str, text: str) -> bool:
    """英文关键词用 \\b 词边界，避免子串误判（ai 不命中 Tai、rag 不命中 coverage）；
    中文关键词用子串匹配。text 应已小写。"""
    if not keyword:
        return False
    kw = keyword.strip()
    if not kw:
        return False
    if has_cjk(kw):
        return kw in text
    return re.search(r"\b" + re.escape(kw.lower()) + r"\b", text) is not None


def normalize_name(name: str) -> str:
    key = name.strip().lower()
    return NAME_ALIASES.get(key, name.strip())


def display_category(category: str) -> str:
    return CATEGORY_DISPLAY.get(category, category)


def infer_requirement_level(evidence: str, fallback: str = "required") -> str | None:
    """根据 evidence 推断要求层级。无任何标记词命中时返回 None（表示沿用 LLM 判断）。"""
    if not evidence:
        return None
    low = evidence.lower()
    if any(m in low for m in REQUIRED_MARKERS):
        return "required"
    if any(m in low for m in EXAMPLE_MARKERS):
        return "example"
    if any(m in low for m in PREFERRED_MARKERS):
        return "preferred"
    return None
