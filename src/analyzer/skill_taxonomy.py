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


def any_keyword(text: str, keywords: tuple[str, ...]) -> bool:
    """text 中是否命中任一关键词（英文词边界 / 中文子串）。text 应已小写。"""
    return any(word_boundary_match(kw, text) for kw in keywords)


# ===========================================================================
# 跨行业六维标签治理模型（v1.3+v1.4，doc §11.10）
# ===========================================================================

CROSS_INDUSTRY_DIMENSIONS: tuple[str, ...] = (
    "industry_context", "business_scenario", "solution_domain",
    "delivery_motion", "compliance_standard", "system_or_asset",
)

DIMENSION_DISPLAY: dict[str, str] = {
    "industry_context": "行業/客戶場景",
    "business_scenario": "業務場景",
    "solution_domain": "技術方案",
    "delivery_motion": "交付動作",
    "compliance_standard": "合規標準",
    "system_or_asset": "系統/設備對象",
}

# 维度内名称归一（英文 / 简体 -> 繁体标准展示名），doc §11.12
CROSS_INDUSTRY_ALIASES: dict[str, str] = {
    "water treatment": "水處理設施", "water treatment facilities": "水處理設施", "水处理": "水處理設施",
    "digital twin": "Digital Twin 解決方案", "数字孪生": "Digital Twin 解決方案",
    "sensor": "傳感器", "sensors": "傳感器", "感測器": "傳感器", "传感器": "傳感器",
    "proof-of-concept": "POC 測試", "proof of concept": "POC 測試", "poc": "POC 測試",
    "tender": "投標", "tender preparation": "投標準備", "tender submission": "投標提交",
    "iso 27001": "ISO 27001", "iso27001": "ISO 27001",
    "it infrastructure": "IT 基礎設施方案設計",
    "government": "政府/公共部門", "public sector": "政府/公共部門",
    "pre-sales": "售前支持", "presales": "售前支持",
    "network security": "網絡安全", "machinery monitoring": "設備狀態監測",
}

# 跨行业上下文消歧（doc §11.10.2）：keyword -> [(上下文词组, 维度, 目标标签 或 None=丢弃)]
# 仅用于 industry_context / business_scenario 维度的多义词判定。
CROSS_DISAMBIGUATION: dict[str, list[tuple[tuple[str, ...], str | None]]] = {
    "payment": [
        (("banking", "fintech", "kyc", "aml", "card", "wallet", "settlement", "sfc", "hkma"), "金融/金融科技業務"),
        (("order", "promotion", "catalog", "ecommerce", "e-commerce", "retail", "pos", "checkout"), "電商/零售業務"),
    ],
    "insurance": [
        (("policy", "claims", "underwriting", "broker", "actuarial", "wealth"), "保險/財富管理業務"),
        (("coverage", "benefit", "medical", "life insurance", "fringe", "scheme"), None),
    ],
    "sensor": [
        (("machinery", "monitoring", "physical condition", "facility", "water treatment", "tracking"), "設備狀態監測"),
    ],
}

# 组合画像规则（doc §11.10.4）：满足 ≥min_groups 个不同维度信号即触发。
# 每个 group = (维度, 关键词集合)，命中标签 name 或 evidence。
COMBINATION_RULES: list[dict] = [
    {
        "name": "政府公用事業 AI/Digital Twin 售前解決方案",
        "groups": [
            ("industry_context", ("政府", "公共部門", "government", "public sector", "公用事業", "utility", "環保", "environmental")),
            ("solution_domain", ("digital twin", "數字孿生", "ai", "人工智能", "人工智慧")),
            ("delivery_motion", ("售前", "pre-sales", "presales", "poc", "proof", "tender", "投標", "技術提案", "proposal", "demo", "presentation")),
            ("business_scenario", ("水處理", "water treatment", "設備狀態", "機械狀態", "monitoring")),
        ],
        "min_groups": 2,
    },
    {
        "name": "零售/電商 ERP 系統集成",
        "groups": [
            ("solution_domain", ("erp", "d365", "dynamics 365", "sap", "middleware", "中間件", "系統集成", "system integration")),
            ("industry_context", ("零售", "電商", "retail", "ecommerce", "e-commerce")),
            ("business_scenario", ("訂單", "促銷", "定價", "order", "promotion", "pricing", "catalog")),
        ],
        "min_groups": 2,
    },
    {
        "name": "電商支付與零售系統開發",
        "groups": [
            ("business_scenario", ("支付", "payment", "pos", "結帳", "checkout")),
            ("industry_context", ("零售", "電商", "retail", "ecommerce", "e-commerce")),
        ],
        "min_groups": 2,
    },
    {
        "name": "金融數據平台與合規場景",
        "groups": [
            ("solution_domain", ("data platform", "數據平台", "data pipeline", "數據管道", "aws")),
            ("industry_context", ("金融", "銀行", "banking", "fintech")),
            ("compliance_standard", ("hkma", "aml", "kyc", "sfc")),
        ],
        "min_groups": 2,
    },
    {
        "name": "物流供應鏈系統集成",
        "groups": [
            ("solution_domain", ("tms", "wms", "api integration", "系統集成", "system integration")),
            ("industry_context", ("物流", "供應鏈", "logistics", "supply chain")),
        ],
        "min_groups": 2,
    },
    {
        "name": "樓宇設施與 IoT 系統方案",
        "groups": [
            ("system_or_asset", ("bms", "樓宇", "building management", "facility", "設施")),
            ("solution_domain", ("iot", "物聯網")),
            ("compliance_standard", ("security", "安全")),
        ],
        "min_groups": 2,
    },
]


def normalize_dimension_name(name: str) -> str:
    return CROSS_INDUSTRY_ALIASES.get(name.strip().lower(), name.strip())
