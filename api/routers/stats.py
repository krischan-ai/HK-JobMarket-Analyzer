import re
from collections import Counter
from typing import Any

import requests
from fastapi import APIRouter, HTTPException, Query
from api.dependencies import load_jobs_df, load_skills_df
import json
from pathlib import Path
import pandas as pd

from src.llm_config_manager import LLMConfigManager

router = APIRouter(prefix="/api/stats", tags=["stats"])

# 仪表盘技术栈应排除的类别（软技能 + AI 概念/子领域）
_NON_TECH_CATEGORIES = {"soft_skills", "ai_concepts"}

_SKILL_DISPLAY_NAMES = {
    "aws": "亚马逊云（AWS）",
    "azure": "微软云（Azure）",
    "gcp": "谷歌云（GCP）",
    "ci/cd": "持续集成/持续交付（CI/CD）",
    "cicd": "持续集成/持续交付（CI/CD）",
    "api": "应用程序接口（API）",
    "ui": "用户界面（UI）",
    "ux": "用户体验（UX）",
    "qa": "质量保证（QA）",
    "rag": "检索增强生成（RAG）",
    "llm": "大语言模型（LLM）",
    "mlops": "机器学习运维（MLOps）",
    "devops": "开发运维一体化（DevOps）",
    "sre": "站点可靠性工程（SRE）",
    "etl": "抽取/转换/加载（ETL）",
    "sql": "结构化查询语言（SQL）",
    "nlp": "自然语言处理（NLP）",
    "ocr": "光学字符识别（OCR）",
    "mcp": "模型上下文协议（MCP）",
    "uat": "用户验收测试（UAT）",
}

_SPECIFIC_CATEGORY_RULES: list[tuple[str, set[str]]] = [
    ("AI 应用与大模型", {"rag", "llm", "langchain", "llamaindex", "dify", "prompt engineering", "prompt", "embedding", "agent", "mcp", "generative ai", "genai"}),
    ("机器学习与深度学习", {"machine learning", "deep learning", "tensorflow", "pytorch", "scikit-learn", "nlp", "computer vision", "opencv", "model training", "fine-tuning"}),
    ("数据工程与分析", {"sql", "etl", "spark", "hadoop", "airflow", "kafka", "snowflake", "tableau", "power bi", "data pipeline", "data warehouse", "pandas"}),
    ("云平台与基础设施", {"aws", "azure", "gcp", "alicloud", "tencent cloud", "cloud", "linux", "nginx", "cdn", "vpn"}),
    ("容器与编排", {"docker", "kubernetes", "k8s", "openshift", "ecs", "eks"}),
    ("DevOps 与自动化交付", {"ci/cd", "cicd", "devops", "sre", "jenkins", "terraform", "ansible", "argocd", "git", "github actions", "powershell", "bash", "shell"}),
    ("后端语言与服务端开发", {"python", "java", "golang", "go", "node.js", "nodejs", "c#", ".net", "php", "scala", "spring", "spring boot", "django", "fastapi", "flask", "microservices", "rest api"}),
    ("前端与移动开发", {"javascript", "typescript", "react", "vue", "angular", "next.js", "html", "css", "tailwind", "flutter", "react native", "swift", "kotlin"}),
    ("数据库与缓存", {"mysql", "postgresql", "mongodb", "redis", "oracle", "elasticsearch", "nosql", "vector db", "chroma", "faiss"}),
    ("测试与质量工程", {"selenium", "cypress", "test automation", "qa", "junit", "pytest", "uat"}),
    ("安全与合规", {"cybersecurity", "security", "devsecops", "owasp", "iso 27001", "penetration test", "soc"}),
]


def _display_skill_name(skill: Any) -> str:
    name = str(skill or "").strip()
    if not name:
        return ""
    key = name.lower()
    return _SKILL_DISPLAY_NAMES.get(key, name)


def _specific_skill_category(skill: Any, fallback_category: str = "") -> str:
    text = str(skill or "").strip().lower()
    for label, keywords in _SPECIFIC_CATEGORY_RULES:
        if text in keywords or any(keyword in text for keyword in keywords if len(keyword) >= 4):
            return label
    fallback_map = {
        "programming_languages": "编程语言",
        "frameworks_libraries": "框架与开发库",
        "cloud_devops": "云平台与 DevOps",
        "databases": "数据库与数据存储",
        "ai_concepts": "AI 概念与方法",
    }
    return fallback_map.get(str(fallback_category), "其他技术")

# 加载地点中文翻译
_ZH_LOCATION_MAP: dict[str, str] | None = None

def _get_zh_location_map() -> dict[str, str]:
    global _ZH_LOCATION_MAP
    if _ZH_LOCATION_MAP is not None:
        return _ZH_LOCATION_MAP
    path = Path(__file__).resolve().parent.parent.parent / "config" / "i18n" / "locations_zh.json"
    if path.exists():
        with open(path, encoding="utf-8") as f:
            _ZH_LOCATION_MAP = json.load(f)
    else:
        _ZH_LOCATION_MAP = {}
    return _ZH_LOCATION_MAP


# ---- LLM 地名归一化（带磁盘缓存） ----
_LOCATION_NORMALIZATION_VERSION = "v1"
_location_normalization_cache: dict[str, str] | None = None


def _location_normalization_signature(df: pd.DataFrame) -> str:
    csv_path = Path(__file__).resolve().parent.parent.parent / "data" / "cleaned" / "jobs.csv"
    stamp = csv_path.stat().st_mtime if csv_path.exists() else 0
    return f"{_LOCATION_NORMALIZATION_VERSION}:{stamp}:{len(df)}"


def _call_llm_for_location_normalization(locations: list[str]) -> dict[str, str]:
    """调用 LLM 把原始英文地名映射到统一繁体中文地名，合并相同地区的不同写法"""
    manager = LLMConfigManager()
    if not manager.configured:
        return {}
    kwargs = manager.build_kwargs()
    prompt = (
        "你是香港地名翻譯與歸一化助手。請把以下英文地名（可能含拼寫差異、區域後綴 District/SAR 等）"
        "映射到統一的繁體中文地名。相同地區的不同寫法必須合併為同一個中文名稱。\n"
        "規則：\n"
        "1. 輸出 JSON 對象，key 為原始地名（保持原樣），value 為統一中文地名。\n"
        "2. 區域後綴（如 District、SAR）應去掉，歸一到具體地名。例如 Kwun Tong District → 觀塘。\n"
        "3. Central 和 Central and Western District 都映射為 中環。\n"
        "4. Hong Kong SAR 映射為 香港。\n"
        "5. 如果地名已是中文或無法識別，原樣返回。\n"
        f"地名列表：{json.dumps(locations, ensure_ascii=False)}"
    )
    payload = {
        "model": kwargs["model"],
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "max_tokens": 2048,
        "response_format": {"type": "json_object"},
    }
    headers = {"Authorization": f"Bearer {kwargs['api_key']}", "Content-Type": "application/json"}
    resp = requests.post(
        f"{kwargs['api_base'].rstrip('/')}/chat/completions",
        headers=headers,
        json=payload,
        timeout=min(max(int(kwargs.get("timeout", 30) or 30), 30), 60),
        proxies={"http": None, "https": None},
    )
    resp.raise_for_status()
    message = resp.json()["choices"][0]["message"]
    content = (message.get("content") or message.get("reasoning_content") or "").strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    start_obj = content.find("{")
    end_obj = content.rfind("}")
    if start_obj >= 0 and end_obj > start_obj:
        content = content[start_obj:end_obj + 1]
    parsed = json.loads(content)
    mapping: dict[str, str] = {}
    if isinstance(parsed, dict):
        for k, v in parsed.items():
            if isinstance(v, str) and v.strip():
                mapping[str(k)] = v.strip()
    return mapping


def _ensure_location_normalization() -> dict[str, str]:
    """惰性载入 LLM 地名归一化映射（优先磁盘缓存，缺失时触发 LLM）"""
    global _location_normalization_cache
    if _location_normalization_cache is not None:
        return _location_normalization_cache

    df = load_jobs_df()
    if df.empty or "location" not in df.columns:
        _location_normalization_cache = {}
        return _location_normalization_cache

    sig = _location_normalization_signature(df)
    cache = _load_analysis_cache()
    cached = cache.get("location_normalization")
    if isinstance(cached, dict) and cached.get("signature") == sig:
        mapping = cached.get("mapping", {})
        if isinstance(mapping, dict) and mapping:
            _location_normalization_cache = mapping
            return mapping

    locations = sorted(df["location"].dropna().unique().tolist())
    try:
        mapping = _call_llm_for_location_normalization(locations)
    except Exception:
        mapping = {}

    _location_normalization_cache = mapping
    if mapping:
        cache["location_normalization"] = {"signature": sig, "mapping": mapping}
        _save_analysis_cache(cache)
    return mapping


def _get_cached_location_normalization() -> dict[str, str]:
    """只读取内存/磁盘缓存，不在普通统计接口中同步触发 LLM。"""
    global _location_normalization_cache
    if _location_normalization_cache is not None:
        return _location_normalization_cache

    df = load_jobs_df()
    if df.empty or "location" not in df.columns:
        _location_normalization_cache = {}
        return _location_normalization_cache

    sig = _location_normalization_signature(df)
    cached = _load_analysis_cache().get("location_normalization")
    if isinstance(cached, dict) and cached.get("signature") == sig:
        mapping = cached.get("mapping", {})
        if isinstance(mapping, dict):
            _location_normalization_cache = mapping
            return mapping

    _location_normalization_cache = {}
    return _location_normalization_cache


def _precompute_location_normalization(df: pd.DataFrame) -> dict[str, str]:
    """在角色分类后台任务中提前调用，把映射写入磁盘缓存供后续统计复用"""
    global _location_normalization_cache
    if df.empty or "location" not in df.columns:
        return {}
    sig = _location_normalization_signature(df)
    cache = _load_analysis_cache()
    cached = cache.get("location_normalization")
    if isinstance(cached, dict) and cached.get("signature") == sig:
        mapping = cached.get("mapping", {})
        if isinstance(mapping, dict) and mapping:
            _location_normalization_cache = mapping
            return mapping

    locations = sorted(df["location"].dropna().unique().tolist())
    try:
        mapping = _call_llm_for_location_normalization(locations)
    except Exception:
        mapping = {}

    _location_normalization_cache = mapping
    if mapping:
        cache["location_normalization"] = {"signature": sig, "mapping": mapping}
        _save_analysis_cache(cache)
    return mapping


def location_to_zh(en: str) -> str:
    """将英文地点名称翻译为中文（优先 LLM 归一化缓存，再查静态映射）"""
    if not en or not isinstance(en, str):
        return en or "Hong Kong"
    loc = en.strip()
    loc_lower = loc.lower()

    # 1. 先查 LLM 归一化缓存
    norm = _get_cached_location_normalization()
    if loc in norm:
        return norm[loc]
    for k, v in norm.items():
        if k.lower() == loc_lower:
            return v

    # 2. 再查静态映射
    zh_map = _get_zh_location_map()
    zh_lower = {k.lower(): v for k, v in zh_map.items()}
    if loc_lower in zh_lower:
        return zh_lower[loc_lower]
    if loc_lower == "remote":
        return "遠端工作"
    area_map = {
        "kowloon": "九龍",
        "hong kong island": "香港島",
        "new territories": "新界",
        "hong kong": "香港",
    }
    for suffix, area_zh in area_map.items():
        if loc_lower.endswith(f", {suffix}"):
            core = loc[:-(len(suffix) + 2)].strip()
            core_translated = zh_lower.get(core.lower(), core)
            return f"{core_translated}, {area_zh}"
    return loc


@router.get("/overview")
def overview():
    df = load_jobs_df()
    if df.empty:
        return {"total_jobs": 0, "total_companies": 0, "avg_salary": 0,
                "min_salary": 0, "max_salary": 0, "total_skills": 0,
                "source_count": 0, "location_count": 0}

    total = len(df)
    salary_min = df["salary_min"].dropna()
    companies = df["company"].nunique() if "company" in df.columns else 0
    sources = df["source"].nunique() if "source" in df.columns else 0
    locations = df["location"].nunique() if "location" in df.columns else 0

    skill_df = load_skills_df()
    # 仅计算技术技能（排除软技能 + AI 概念）
    if not skill_df.empty:
        tech_df = skill_df[~skill_df["category"].isin(_NON_TECH_CATEGORIES)]
        total_skills = len(tech_df) if not tech_df.empty else 0
    else:
        total_skills = 0

    return {
        "total_jobs": total,
        "total_companies": int(companies),
        "avg_salary": round(float(salary_min.mean()), 0) if not salary_min.empty else 0,
        "min_salary": round(float(salary_min.min()), 0) if not salary_min.empty else 0,
        "max_salary": round(float(salary_min.max()), 0) if not salary_min.empty else 0,
        "total_skills": total_skills,
        "source_count": int(sources),
        "location_count": int(locations),
    }

def _get_enriched_skills():
    """获取合并了 CSV + 分类结果的技术技能数据"""
    skill_df = load_skills_df()
    try:
        from api.routers.role_stats import _classify_result
        if _classify_result:
            classify_skills = []
            for item in _classify_result:
                for s in (item.get("skills") or []):
                    classify_skills.append({
                        "skill": s.get("name", ""),
                        "category": s.get("category", ""),
                    })
            if classify_skills:
                classify_df = pd.DataFrame(classify_skills)
                if not skill_df.empty:
                    skill_df = pd.concat([skill_df, classify_df], ignore_index=True)
                else:
                    skill_df = classify_df
    except ImportError:
        pass
    return skill_df


@router.get("/top-skills")
def top_skills(top_n: int = Query(default=15)):
    skill_df = _get_enriched_skills()

    if skill_df.empty:
        return []
    # 过滤掉非技术类别（软技能 + AI 概念）
    tech_df = skill_df[~skill_df["category"].isin(_NON_TECH_CATEGORIES)]
    if tech_df.empty:
        tech_df = skill_df
    freq = tech_df["skill"].value_counts().head(top_n).reset_index()
    freq.columns = ["skill", "count"]
    freq["category"] = freq["skill"].apply(
        lambda s: tech_df[tech_df["skill"] == s]["category"].iloc[0] if len(tech_df[tech_df["skill"] == s]) > 0 else ""
    )
    freq["skill"] = freq["skill"].apply(_display_skill_name)
    return freq.to_dict(orient="records")


@router.get("/categories")
def category_distribution():
    skill_df = _get_enriched_skills()

    if skill_df.empty:
        return []
    # 排除非技术类别（软技能 + AI 概念）
    tech_df = skill_df[~skill_df["category"].isin(_NON_TECH_CATEGORIES)]
    if tech_df.empty:
        tech_df = skill_df
    tech_df = tech_df.copy()
    tech_df["category"] = tech_df.apply(lambda row: _specific_skill_category(row.get("skill"), row.get("category", "")), axis=1)
    freq = tech_df["category"].value_counts().reset_index()
    freq.columns = ["category", "count"]
    return freq.to_dict(orient="records")


@router.get("/salary-by-location")
def salary_by_location():
    df = load_jobs_df()
    if df.empty:
        return []
    g = df.dropna(subset=["salary_min"]).groupby("location")["salary_min"].agg(["min", "max", "mean", "count"])
    g = g.reset_index()
    g.columns = ["location", "min", "max", "avg", "count"]
    g["avg"] = g["avg"].round(0)
    g["location"] = g["location"].apply(location_to_zh)
    # 翻译后合并同名地区（如 Kwun Tong + Kwun Tong District → 觀塘）
    g = g.groupby("location", as_index=False).agg({"min": "min", "max": "max", "avg": "mean", "count": "sum"})
    g["avg"] = g["avg"].round(0)
    g = g.sort_values("avg", ascending=False)
    return g.to_dict(orient="records")


@router.get("/source-distribution")
def source_distribution():
    df = load_jobs_df()
    if df.empty or "source" not in df.columns:
        return []
    freq = df["source"].value_counts().reset_index()
    freq.columns = ["source", "count"]
    return freq.to_dict(orient="records")


@router.get("/location-distribution")
def location_distribution():
    df = load_jobs_df()
    if df.empty or "location" not in df.columns:
        return []
    # 先翻译再计数，合并同名地区（如 Kwun Tong + Kwun Tong District → 觀塘）
    freq = df["location"].apply(location_to_zh).value_counts().head(30).reset_index()
    freq.columns = ["location", "count"]
    return freq.to_dict(orient="records")


_trend_analysis_cache: dict[str, Any] = {}
_TREND_ANALYSIS_CONTEXT_VERSION = "v8"
_salary_analysis_cache: dict[str, Any] = {}
_SALARY_ANALYSIS_CONTEXT_VERSION = "v3"
_INDUSTRY_DISTRIBUTION_VERSION = "v3"
_SOFT_SKILL_DISTRIBUTION_VERSION = "v1"
_ANALYSIS_CACHE_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "cache" / "ai_analysis_cache.json"


def _load_analysis_cache() -> dict[str, Any]:
    if not _ANALYSIS_CACHE_PATH.exists():
        return {}
    try:
        with open(_ANALYSIS_CACHE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _save_analysis_cache(cache: dict[str, Any]) -> None:
    try:
        _ANALYSIS_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(_ANALYSIS_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


def _get_disk_cached_analysis(kind: str, signature: str) -> dict[str, Any] | None:
    item = _load_analysis_cache().get(kind)
    if not isinstance(item, dict) or item.get("signature") != signature:
        return None
    data = item.get("data")
    if not isinstance(data, dict):
        return None
    data = dict(data)
    # 旧缓存里 evidence 可能是字符串，规整成列表后再返回，避免前端对字符串调用 .map 出错。
    if isinstance(data.get("sections"), list):
        data["sections"] = _normalize_sections(data["sections"])
    data["from_cache"] = True
    data["analysis_status"] = "cached"
    return data


def _set_disk_cached_analysis(kind: str, signature: str, data: dict[str, Any]) -> None:
    if not data.get("llm_used"):
        return
    cache = _load_analysis_cache()
    payload = dict(data)
    payload["from_cache"] = False
    payload["analysis_status"] = "completed"
    cache[kind] = {"signature": signature, "data": payload}
    _save_analysis_cache(cache)


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value != value:
        return ""
    return str(value).strip()


def _counter_from_column(df: pd.DataFrame, column: str, top_n: int = 10) -> list[dict[str, Any]]:
    if column not in df.columns:
        return []
    counter = Counter()
    for value in df[column].dropna():
        text = _safe_text(value)
        if text:
            counter[text] += 1
    return [{"name": name, "count": count} for name, count in counter.most_common(top_n)]


def _collect_skill_stats(df: pd.DataFrame, top_n: int = 20) -> list[dict[str, Any]]:
    skill_df = load_skills_df()
    if skill_df.empty:
        return []
    skill_df = skill_df[~skill_df["category"].isin(_NON_TECH_CATEGORIES)].copy()
    if skill_df.empty:
        return []
    skill_df["display_skill"] = skill_df["skill"].apply(_display_skill_name)
    skill_df["specific_category"] = skill_df.apply(
        lambda row: _specific_skill_category(row.get("skill"), row.get("category", "")),
        axis=1,
    )
    grouped = (
        skill_df.groupby(["display_skill", "specific_category"])
        .size()
        .sort_values(ascending=False)
        .head(top_n)
        .reset_index(name="count")
    )
    return [
        {"skill": row["display_skill"], "category": row["specific_category"], "count": int(row["count"])}
        for _, row in grouped.iterrows()
    ]


def _collect_responsibility_stats(df: pd.DataFrame) -> list[dict[str, Any]]:
    rules: list[tuple[str, tuple[str, ...]]] = [
        ("系统开发与功能交付", ("develop", "development", "implement", "build", "enhance", "application", "backend", "frontend")),
        ("AI/数据能力落地", ("ai", "llm", "rag", "model", "machine learning", "data", "analytics", "pipeline")),
        ("云基础设施与部署", ("cloud", "aws", "azure", "gcp", "deploy", "infrastructure", "kubernetes", "docker")),
        ("自动化与运维监控", ("ci/cd", "automation", "monitor", "devops", "sre", "reliability", "terraform")),
        ("需求分析与项目协作", ("requirement", "stakeholder", "coordinate", "collaborate", "project", "vendor", "uat")),
        ("安全合规与质量保障", ("security", "compliance", "risk", "quality", "testing", "qa", "audit")),
        ("团队带领与技术指导", ("lead", "mentor", "manage", "guide", "supervise", "team")),
    ]
    counter = Counter()
    for _, row in df.iterrows():
        text = " ".join([
            _safe_text(row.get("title")),
            _safe_text(row.get("jd_text")),
            _safe_text(row.get("kb_document_text")),
        ]).lower()
        if not text:
            continue
        for label, keywords in rules:
            if any(keyword in text for keyword in keywords):
                counter[label] += 1
    return [{"name": name, "count": count} for name, count in counter.most_common()]


_INDUSTRY_LABELS = [
    "金融服务/金融科技",
    "保险/财富管理",
    "互联网/软件服务",
    "人工智能/数据服务",
    "电信/云与基础设施",
    "教育/科研",
    "政府/公共机构",
    "零售/电商",
    "物流/供应链",
    "医疗健康",
    "房地产/物业",
    "咨询/专业服务",
    "酒店/旅游",
    "媒体/娱乐",
    "制造/硬件",
    "其他",
]

_INDUSTRY_KEYWORD_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("金融服务/金融科技", ("bank", "banking", "finance", "financial", "fintech", "trading", "securities", "payment", "wealth")),
    ("保险/财富管理", ("insurance", "insurtech", "actuarial", "underwriting", "claims", "broker")),
    ("互联网/软件服务", ("software", "saas", "platform", "application", "web", "mobile app", "product company")),
    ("人工智能/数据服务", ("artificial intelligence", "ai ", " ai/", "machine learning", "data science", "analytics", "big data", "llm", "rag")),
    ("电信/云与基础设施", ("telecom", "telecommunication", "cloud", "infrastructure", "data centre", "data center", "network", "hosting")),
    ("教育/科研", ("education institution", "school", "university", "college", "academy")),
    ("政府/公共机构", ("government", "public sector", "authority", "department", "bureau", "council")),
    ("零售/电商", ("retail", "e-commerce", "ecommerce", "commerce", "mall", "shop", "customer loyalty")),
    ("物流/供应链", ("logistics", "supply chain", "shipping", "freight", "warehouse", "transport")),
    ("医疗健康", ("health", "medical", "hospital", "clinic", "pharma", "biotech")),
    ("房地产/物业", ("property", "real estate", "facility management", "facilities management")),
    ("咨询/专业服务", ("consulting", "consultancy", "professional service", "outsourcing", "solution provider", "vendor")),
    ("酒店/旅游", ("hospitality", "hotel", "travel", "tourism", "airline")),
    ("媒体/娱乐", ("media", "advertising", "entertainment", "gaming", "game")),
    ("制造/硬件", ("manufacturing", "hardware", "semiconductor", "electronics", "iot", "device")),
]


def _industry_cache_signature(df: pd.DataFrame) -> str:
    csv_path = Path(__file__).resolve().parent.parent.parent / "data" / "cleaned" / "jobs.csv"
    stamp = csv_path.stat().st_mtime if csv_path.exists() else 0
    return f"{_INDUSTRY_DISTRIBUTION_VERSION}:{stamp}:{len(df)}"


def _job_industry_record(row: pd.Series, idx: int) -> dict[str, str | int]:
    jd = _safe_text(row.get("kb_document_text")) or _safe_text(row.get("jd_text")) or _safe_text(row.get("jd_raw"))
    return {
        "idx": idx,
        "title": _safe_text(row.get("title"))[:120],
        "company": _safe_text(row.get("company"))[:120],
        "provided_industry": _safe_text(row.get("industry_category"))[:80],
        "jd_excerpt": jd[:320],
    }


def _infer_industry_with_rules(record: dict[str, Any]) -> str:
    provided = _safe_text(record.get("provided_industry"))
    if provided and provided not in {"-", "None", "null"}:
        text = provided.lower()
        for label, keywords in _INDUSTRY_KEYWORD_RULES:
            if any(keyword in text for keyword in keywords):
                return label
    business_text = " ".join([
        _safe_text(record.get("company")),
        _safe_text(record.get("title")),
        provided,
    ]).lower()
    for label, keywords in _INDUSTRY_KEYWORD_RULES:
        if any(keyword in business_text for keyword in keywords):
            return label
    jd_text = _safe_text(record.get("jd_excerpt")).lower()
    for label, keywords in _INDUSTRY_KEYWORD_RULES:
        if any(keyword in jd_text for keyword in keywords):
            return label
    return "其他"


def _call_llm_for_industry_batch(records: list[dict[str, Any]]) -> dict[int, str]:
    manager = LLMConfigManager()
    if not manager.configured:
        raise HTTPException(status_code=400, detail="LLM 未配置，无法生成行业分类")
    kwargs = manager.build_kwargs()
    prompt = (
        "你是香港招聘市场行业分类助手。请根据每条岗位的公司名称、岗位标题、已有行业字段和 JD 摘要，"
        "判断该岗位所属行业。必须只从给定行业标签中选择一个，不能输出公司名称。\n"
        f"行业标签：{json.dumps(_INDUSTRY_LABELS, ensure_ascii=False)}\n"
        "请输出 JSON 对象，格式严格为：{\"items\":[{\"idx\":0,\"industry\":\"金融服务/金融科技\"}]}。\n"
        f"岗位数据：{json.dumps(records, ensure_ascii=False)}"
    )
    payload = {
        "model": kwargs["model"],
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "max_tokens": 2048,
        "response_format": {"type": "json_object"},
    }
    headers = {"Authorization": f"Bearer {kwargs['api_key']}", "Content-Type": "application/json"}
    resp = requests.post(
        f"{kwargs['api_base'].rstrip('/')}/chat/completions",
        headers=headers,
        json=payload,
        timeout=min(max(int(kwargs.get("timeout", 30) or 30), 30), 60),
        proxies={"http": None, "https": None},
    )
    resp.raise_for_status()
    message = resp.json()["choices"][0]["message"]
    content = (message.get("content") or message.get("reasoning_content") or "").strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    start_obj = content.find("{")
    end_obj = content.rfind("}")
    if start_obj >= 0 and end_obj > start_obj:
        content = content[start_obj:end_obj + 1]
    parsed = json.loads(content)
    items = parsed.get("items", []) if isinstance(parsed, dict) else []
    result: dict[int, str] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        try:
            idx = int(item.get("idx"))
        except (TypeError, ValueError):
            continue
        industry = _safe_text(item.get("industry"))
        result[idx] = industry if industry in _INDUSTRY_LABELS else "其他"
    return result


def _collect_llm_industry_distribution(df: pd.DataFrame, top_n: int = 10, use_llm: bool = True) -> list[dict[str, Any]]:
    if df.empty:
        return []
    signature = _industry_cache_signature(df)
    cached = _get_disk_cached_analysis("industry_distribution", signature)
    if cached and isinstance(cached.get("items"), list):
        return cached["items"][:top_n]

    records = [_job_industry_record(row, idx) for idx, (_, row) in enumerate(df.iterrows())]
    assigned: dict[int, str] = {}
    llm_used = False
    if use_llm:
        batch_size = 50
        llm_records = records[:50]
        for start in range(0, len(llm_records), batch_size):
            batch = llm_records[start:start + batch_size]
            try:
                assigned.update(_call_llm_for_industry_batch(batch))
                llm_used = True
            except Exception:
                for record in batch:
                    assigned[int(record["idx"])] = _infer_industry_with_rules(record)

    counter = Counter()
    for record in records:
        idx = int(record["idx"])
        industry = assigned.get(idx) or _infer_industry_with_rules(record)
        counter[industry] += 1
    ranked = [(name, count) for name, count in counter.most_common() if name != "其他"]
    if counter.get("其他"):
        ranked.append(("其他", counter["其他"]))
    items = [{"name": name, "count": count} for name, count in ranked[:top_n]]
    cache = _load_analysis_cache()
    cache["industry_distribution"] = {"signature": signature, "data": {"llm_used": llm_used, "items": items}}
    _save_analysis_cache(cache)
    return items


def _soft_skill_cache_signature(df: pd.DataFrame) -> str:
    csv_path = Path(__file__).resolve().parent.parent.parent / "data" / "cleaned" / "jobs.csv"
    stamp = csv_path.stat().st_mtime if csv_path.exists() else 0
    return f"{_SOFT_SKILL_DISTRIBUTION_VERSION}:{stamp}:{len(df)}"


def _job_soft_skill_record(row: pd.Series, idx: int) -> dict[str, Any]:
    jd = _safe_text(row.get("kb_document_text")) or _safe_text(row.get("jd_text")) or _safe_text(row.get("jd_raw"))
    return {
        "idx": idx,
        "title": _safe_text(row.get("title"))[:120],
        "jd_excerpt": jd[:600],
    }


def _call_llm_for_soft_skill_batch(records: list[dict[str, Any]]) -> dict[int, dict[str, list[str]]]:
    manager = LLMConfigManager()
    if not manager.configured:
        raise HTTPException(status_code=400, detail="LLM 未配置，无法生成软技能分析")
    kwargs = manager.build_kwargs()
    prompt = (
        "你是香港 IT 招聘市場軟技能分析師。請閱讀下面每條崗位的標題和 JD 文本，"
        "理解後提取該崗位提到的軟技能要求，嚴格分為三類：\n"
        "1. education: 學歷要求（例如 學士學位、碩士優先、計算機相關學歷、大專或以上 等）\n"
        "2. language: 語言要求（例如 英語、粵語、普通話、中文 等）\n"
        "3. soft_skill: 個人能力（例如 溝通能力、團隊合作、組織能力、領導力、問題解決、抗壓能力、跨團隊協作 等）\n"
        "規則：\n"
        "- 必須基於 JD 實際內容理解後提取，不要憑空編造。\n"
        "- 學歷統一用中文表達，歸併同義寫法（如 Bachelor's degree / 学士学位 都寫成「學士學位」）。\n"
        "- 語言統一用中文，歸併同義寫法（如 English / 英语 都寫成「英語」，Cantonese 寫成「粵語」，Mandarin 寫成「普通話」，Chinese 寫成「中文」）。\n"
        "- 個人能力統一用中文，歸併同義寫法（如 communication → 溝通能力，teamwork → 團隊合作，organizational skills → 組織能力，problem-solving → 問題解決）。\n"
        "- 每條崗位的三類各輸出若干項，JD 中沒有明確提到的輸出空數組。\n"
        "請輸出 JSON 對象，格式嚴格為："
        "{\"items\":[{\"idx\":0,\"education\":[\"學士學位\"],\"language\":[\"英語\",\"粵語\"],\"soft_skill\":[\"溝通能力\",\"團隊合作\"]}]}。\n"
        f"崗位數據：{json.dumps(records, ensure_ascii=False)}"
    )
    payload = {
        "model": kwargs["model"],
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "max_tokens": 3072,
        "response_format": {"type": "json_object"},
    }
    headers = {"Authorization": f"Bearer {kwargs['api_key']}", "Content-Type": "application/json"}
    resp = requests.post(
        f"{kwargs['api_base'].rstrip('/')}/chat/completions",
        headers=headers,
        json=payload,
        timeout=min(max(int(kwargs.get("timeout", 30) or 30), 30), 90),
        proxies={"http": None, "https": None},
    )
    resp.raise_for_status()
    message = resp.json()["choices"][0]["message"]
    content = (message.get("content") or message.get("reasoning_content") or "").strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    start_obj = content.find("{")
    end_obj = content.rfind("}")
    if start_obj >= 0 and end_obj > start_obj:
        content = content[start_obj:end_obj + 1]
    parsed = json.loads(content)
    items = parsed.get("items", []) if isinstance(parsed, dict) else []
    result: dict[int, dict[str, list[str]]] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        try:
            idx = int(item.get("idx"))
        except (TypeError, ValueError):
            continue
        result[idx] = {
            "education": [str(x) for x in (item.get("education") or []) if str(x).strip()],
            "language": [str(x) for x in (item.get("language") or []) if str(x).strip()],
            "soft_skill": [str(x) for x in (item.get("soft_skill") or []) if str(x).strip()],
        }
    return result


def _collect_llm_soft_skill_distribution(df: pd.DataFrame, use_llm: bool = True) -> list[dict[str, Any]]:
    """讓 LLM 閱讀全庫 JD 後提取學歷、語言、個人能力三類軟技能並聚計排名。

    與規則匹配不同，這裡由大模型理解 JD 語義後歸併同義表達並輸出標準化中文標籤。
    """
    if df.empty:
        return []
    signature = _soft_skill_cache_signature(df)
    cached = _get_disk_cached_analysis("soft_skill_distribution", signature)
    if cached and isinstance(cached.get("items"), list):
        return cached["items"]

    records = [_job_soft_skill_record(row, idx) for idx, (_, row) in enumerate(df.iterrows())]
    assigned: dict[int, dict[str, list[str]]] = {}
    llm_used = False
    if use_llm:
        batch_size = 20
        for start in range(0, len(records), batch_size):
            batch = records[start:start + batch_size]
            try:
                assigned.update(_call_llm_for_soft_skill_batch(batch))
                llm_used = True
            except Exception:
                pass

    edu_counter: Counter[str] = Counter()
    lang_counter: Counter[str] = Counter()
    skill_counter: Counter[str] = Counter()
    for record in records:
        idx = int(record["idx"])
        extracted = assigned.get(idx)
        if not extracted:
            continue
        for item in extracted.get("education", []):
            edu_counter[item] += 1
        for item in extracted.get("language", []):
            lang_counter[item] += 1
        for item in extracted.get("soft_skill", []):
            skill_counter[item] += 1

    items: list[dict[str, Any]] = []
    for name, count in skill_counter.most_common(10):
        items.append({"name": name, "category": "soft_skill", "count": count})
    for name, count in edu_counter.most_common(6):
        items.append({"name": name, "category": "education", "count": count})
    for name, count in lang_counter.most_common(6):
        items.append({"name": name, "category": "language", "count": count})

    cache = _load_analysis_cache()
    cache["soft_skill_distribution"] = {"signature": signature, "data": {"llm_used": llm_used, "items": items}}
    _save_analysis_cache(cache)
    return items


def _sample_jobs_for_analysis(df: pd.DataFrame, limit: int = 12) -> list[dict[str, str]]:
    if df.empty:
        return []
    rows = df.head(limit)
    samples = []
    for _, row in rows.iterrows():
        jd = _safe_text(row.get("kb_document_text")) or _safe_text(row.get("jd_text")) or _safe_text(row.get("jd_raw"))
        samples.append({
            "title": _safe_text(row.get("title")),
            "company": _safe_text(row.get("company")),
            "industry": _safe_text(row.get("industry_category")),
            "location": _safe_text(row.get("location")),
            "jd_excerpt": jd[:300],
        })
    return samples


def _build_trend_context(df: pd.DataFrame, use_llm: bool = True) -> dict[str, Any]:
    from src.resume_agent.market_insights import compute_market_insights
    from api.routers.role_stats import role_distribution, role_salary

    market = compute_market_insights(top_n=12)
    return {
        "total_jobs": len(df),
        "role_demand_ranking": market.get("role_demand_ranking", []),
        "role_distribution": role_distribution(),
        "role_salary": role_salary(),
        "tech_stack_ranking": _collect_skill_stats(df, top_n=20),
        "skill_category_distribution": category_distribution(),
        "responsibility_distribution": _collect_responsibility_stats(df),
        "industry_distribution": _collect_llm_industry_distribution(df, top_n=10, use_llm=use_llm),
        "soft_skill_demand": _collect_llm_soft_skill_distribution(df, use_llm=use_llm),
        "company_distribution": _counter_from_column(df, "company", top_n=10),
        "location_distribution": [
            {"name": name, "count": count}
            for name, count in df["location"].apply(location_to_zh).value_counts().head(10).items()
        ],
        "education_distribution": _counter_from_column(df, "education_required", top_n=8),
        "language_distribution": _counter_from_column(df, "languages_required", top_n=8),
        "knowledge_base_samples": _sample_jobs_for_analysis(df),
    }


def _compact_trend_context(context: dict[str, Any]) -> dict[str, Any]:
    return {
        "total_jobs": context.get("total_jobs", 0),
        "role_demand_ranking": context.get("role_demand_ranking", [])[:8],
        "role_distribution": context.get("role_distribution", [])[:8],
        "role_salary": context.get("role_salary", [])[:8],
        "tech_stack_ranking": context.get("tech_stack_ranking", [])[:12],
        "skill_category_distribution": context.get("skill_category_distribution", [])[:10],
        "responsibility_distribution": context.get("responsibility_distribution", [])[:8],
        "industry_distribution": context.get("industry_distribution", [])[:8],
        "soft_skill_demand": context.get("soft_skill_demand", [])[:14],
        "company_distribution": context.get("company_distribution", [])[:8],
        "location_distribution": context.get("location_distribution", [])[:8],
        "education_distribution": context.get("education_distribution", [])[:6],
        "language_distribution": context.get("language_distribution", [])[:6],
        "knowledge_base_samples": [
            {
                "title": item.get("title"),
                "company": item.get("company"),
                "industry": item.get("industry"),
                "jd_excerpt": item.get("jd_excerpt", "")[:180],
            }
            for item in context.get("knowledge_base_samples", [])[:6]
        ],
    }


def _fallback_trend_sections(context: dict[str, Any]) -> list[dict[str, Any]]:
    roles = "、".join([f"{x.get('role_name')}({x.get('count')})" for x in context.get("role_demand_ranking", [])[:5]]) or "暂无明确角色分类"
    role_dist = "、".join([f"{x.get('role_name')}({x.get('percentage')}%)" for x in context.get("role_distribution", [])[:5]]) or "暂无角色分布统计"
    skills = "、".join([f"{x.get('skill')}({x.get('count')})" for x in context.get("tech_stack_ranking", [])[:8]]) or "暂无技能统计"
    categories = "、".join([f"{x.get('category')}({x.get('count')})" for x in context.get("skill_category_distribution", [])[:6]]) or "暂无类别统计"
    industries = "、".join([f"{x.get('name')}({x.get('count')})" for x in context.get("industry_distribution", [])[:5]]) or "行业字段较少，需结合公司名称和 JD 判断"
    soft_skills = "、".join([f"{x.get('name')}({x.get('count')})" for x in context.get("soft_skill_demand", [])[:6]]) or "暂无软技能统计，点击「重新生成分析」调用 LLM 提取"
    return [
        {"key": "tech_stack_demand", "title": "技术栈需求分析", "summary": f"技术栈榜单显示：{skills}。这些高频技术说明香港 IT 岗位更偏向云平台、后端工程、数据处理与自动化交付的组合能力，单一工具会被放在完整交付链路里评估。", "evidence": context.get("tech_stack_ranking", [])[:8]},
        {"key": "tech_category", "title": "细分技能类别分析", "summary": f"细分类别占比中较突出的方向包括：{categories}。相比原始大类，这些类别更能反映岗位真实能力结构，适合用来判断候选人技能组合是否均衡。", "evidence": context.get("skill_category_distribution", [])[:6]},
        {"key": "role_classification", "title": "角色分类分析", "summary": f"角色分类显示市场需求集中在：{roles}。求职定位时应先选择主角色，再围绕该角色补齐最常见技术栈和职责表达，避免简历只堆工具名。", "evidence": context.get("role_demand_ranking", [])[:5]},
        {"key": "role_distribution", "title": "角色分布分析", "summary": f"角色分布占比靠前的是：{role_dist}。这说明岗位供给并非均匀分散，热门方向竞争更强，但也意味着 JD 表达更标准、可对标样本更多。", "evidence": context.get("role_distribution", [])[:6]},
        {"key": "soft_skill_demand", "title": "软技能需求分析", "summary": f"基于知识库 JD 的语义分析，软技能需求排名前列：{soft_skills}。学历与语言要求体现岗位门槛，个人能力（沟通、团队协作、组织等）反映雇主对综合素质的偏好；求职者应在简历中用具体事例佐证这些能力，而非仅罗列形容词。", "evidence": context.get("soft_skill_demand", [])[:8]},
        {"key": "responsibility", "title": "岗位职责分析", "summary": "从样本 JD 看，职责通常围绕系统开发、AI/数据能力落地、云基础设施交付、跨团队协作和质量/安全要求展开。技术型岗位不只看工具名，还强调端到端交付和业务场景理解。", "evidence": context.get("knowledge_base_samples", [])[:5]},
        {"key": "company_industry", "title": "公司行业分析", "summary": f"基于公司名称、岗位标题和 JD 业务语境归类后，行业集中在：{industries}。行业排名反映的是岗位需求来自哪些业务场景，而不是公司名称出现次数；求职时应结合目标行业补充对应业务词汇、监管语境和项目案例。", "evidence": context.get("industry_distribution", [])[:5]},
        {"key": "tech_direction", "title": "技术方向分析", "summary": f"技术栈高频项包括：{skills}。整体方向偏向云平台、AI 应用、数据工程、DevOps 自动化和全栈开发能力组合，简称类技术名已在图表中补充中文全称。", "evidence": context.get("tech_stack_ranking", [])[:8]},
    ]


def _trend_section_specs(context: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"key": "tech_stack_demand", "title": "技术栈需求分析", "evidence": context.get("tech_stack_ranking", [])[:8]},
        {"key": "tech_category", "title": "细分技能类别分析", "evidence": context.get("skill_category_distribution", [])[:8]},
        {"key": "role_classification", "title": "角色分类分析", "evidence": context.get("role_demand_ranking", [])[:8]},
        {"key": "role_distribution", "title": "角色分布分析", "evidence": context.get("role_distribution", [])[:8]},
        {"key": "soft_skill_demand", "title": "软技能需求分析", "evidence": context.get("soft_skill_demand", [])[:10]},
        {"key": "responsibility", "title": "岗位职责分析", "evidence": context.get("responsibility_distribution", [])[:8]},
        {"key": "company_industry", "title": "公司行业分析", "evidence": context.get("industry_distribution", [])[:8]},
        {"key": "tech_direction", "title": "技术方向分析", "evidence": context.get("tech_stack_ranking", [])[:8]},
    ]


def _parse_plain_trend_sections(content: str, specs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    import re

    sections: list[dict[str, Any]] = []
    for idx, spec in enumerate(specs):
        title = spec["title"]
        next_titles = [re.escape(s["title"]) for s in specs[idx + 1:]]
        next_pattern = "|".join(next_titles)
        if next_pattern:
            pattern = rf"(?:^|\n)#+\s*{re.escape(title)}\s*\n(?P<body>.*?)(?=\n#+\s*(?:{next_pattern})\s*\n|$)"
        else:
            pattern = rf"(?:^|\n)#+\s*{re.escape(title)}\s*\n(?P<body>.*)$"
        match = re.search(pattern, content, flags=re.S)
        body = match.group("body").strip() if match else ""
        body = re.sub(r"\n{3,}", "\n\n", body)
        body = body.strip("- \n")
        if not body:
            body = "本段模型输出为空，请点击“重新生成分析”重试。"
        sections.append({
            "key": spec["key"],
            "title": title,
            "summary": body,
            "evidence": spec.get("evidence", []),
        })
    return sections


def _call_llm_for_trend_analysis(context: dict[str, Any]) -> list[dict[str, Any]]:
    manager = LLMConfigManager()
    if not manager.configured:
        raise HTTPException(status_code=400, detail="LLM 未配置，无法生成知识库趋势总结")
    kwargs = manager.build_kwargs()
    section_specs = _trend_section_specs(context)
    prompt = (
        "你是香港 IT 招聘市场分析师。请只基于下面的岗位知识库统计和样本 JD，"
        "按下面 8 个标题输出纯文本分析。每个标题必须单独成行，格式为：### 标题。"
        "每个标题下写 3-5 句中文，不能只复述出现次数；"
        "必须解释这些数据对香港 IT 行情的意义、对候选人技能组合/简历关键词/求职优先级的建议、以及样本局限。"
        "技术简称必须补充中文解释，例如 持续集成/持续交付（CI/CD）。不要输出 JSON。\n\n"
        "特别注意：「软技能需求分析」一节必须覆盖学历要求、语言要求、个人能力（如沟通能力、团队合作、组织能力、领导力等）三类，"
        "分别说明每类的高频项及其对求职者简历表达与能力准备的启示，不要只谈岗位数量。\n\n"
        "标题顺序：\n"
        + "\n".join([f"### {spec['title']}" for spec in section_specs]) +
        "\n\n"
        f"知识库上下文：\n{json.dumps(_compact_trend_context(context), ensure_ascii=False)[:5200]}"
    )
    payload = {
        "model": kwargs["model"],
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "max_tokens": 4096,
    }
    headers = {"Authorization": f"Bearer {kwargs['api_key']}", "Content-Type": "application/json"}
    resp = requests.post(
        f"{kwargs['api_base'].rstrip('/')}/chat/completions",
        headers=headers,
        json=payload,
        timeout=max(int(kwargs.get("timeout", 30) or 30), 120),
        proxies={"http": None, "https": None},
    )
    resp.raise_for_status()
    message = resp.json()["choices"][0]["message"]
    content = (message.get("content") or "").strip()
    if not content:
        content = (message.get("reasoning_content") or "").strip()
    return _parse_plain_trend_sections(content, section_specs)


def _normalize_evidence(value: Any) -> list[Any]:
    """把 LLM 返回的 evidence 统一成列表。

    LLM 有时会把 evidence 写成一整段文字而不是数组，前端对字符串调用 .map 会抛错导致整块消失，
    因此在写入缓存前就规整：列表原样保留；字符串按 、；; 换行符拆分；其它类型丢弃为空列表。
    """
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        parts = re.split(r"[、；;\n]+", value)
        return [part.strip() for part in parts if part.strip()]
    return []


def _normalize_sections(sections: list[Any]) -> list[dict[str, Any]]:
    """规整 LLM 返回的 sections：只保留字典项，并把 evidence 统一成列表。"""
    normalized: list[dict[str, Any]] = []
    for section in sections:
        if not isinstance(section, dict):
            continue
        section = dict(section)
        section["evidence"] = _normalize_evidence(section.get("evidence"))
        normalized.append(section)
    return normalized


def _call_llm_sections(prompt: str) -> list[dict[str, Any]]:
    manager = LLMConfigManager()
    if not manager.configured:
        raise HTTPException(status_code=400, detail="LLM 未配置，无法生成智能总结")
    kwargs = manager.build_kwargs()
    payload = {
        "model": kwargs["model"],
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "max_tokens": 4096,
        "response_format": {"type": "json_object"},
    }
    headers = {"Authorization": f"Bearer {kwargs['api_key']}", "Content-Type": "application/json"}
    resp = requests.post(
        f"{kwargs['api_base'].rstrip('/')}/chat/completions",
        headers=headers,
        json=payload,
        timeout=max(int(kwargs.get("timeout", 30) or 30), 120),
        proxies={"http": None, "https": None},
    )
    resp.raise_for_status()
    message = resp.json()["choices"][0]["message"]
    content = (message.get("content") or message.get("reasoning_content") or "").strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    start_obj = content.find("{")
    end_obj = content.rfind("}")
    if start_obj >= 0 and end_obj > start_obj:
        content = content[start_obj:end_obj + 1]
    parsed = json.loads(content)
    sections = parsed.get("sections", []) if isinstance(parsed, dict) else parsed
    if not isinstance(sections, list):
        raise ValueError("LLM response does not contain sections list")
    return _normalize_sections(sections)


@router.get("/tech-trend-analysis")
def tech_trend_analysis(refresh: bool = Query(default=False)):
    df = load_jobs_df()
    if df.empty:
        return {"llm_used": False, "sections": [], "context": {"total_jobs": 0}}

    csv_path = Path(__file__).resolve().parent.parent.parent / "data" / "cleaned" / "jobs.csv"
    signature = f"{_TREND_ANALYSIS_CONTEXT_VERSION}:{csv_path.stat().st_mtime if csv_path.exists() else 0}:{len(df)}"
    if not refresh and _trend_analysis_cache.get("signature") == signature:
        data = dict(_trend_analysis_cache["data"])
        data["from_cache"] = True
        data["analysis_status"] = "cached"
        return data
    if not refresh:
        cached = _get_disk_cached_analysis("tech_trend", signature)
        if cached:
            _trend_analysis_cache["signature"] = signature
            _trend_analysis_cache["data"] = cached
            return cached

    context = _build_trend_context(df, use_llm=refresh)
    if not refresh:
        result = {
            "llm_used": False,
            "from_cache": False,
            "analysis_status": "fallback",
            "warning": "未命中 AI 分析缓存，已先返回本地知识库摘要；点击“重新生成分析”可调用 LLM 生成完整总结。",
            "sections": _fallback_trend_sections(context),
            "context": context,
        }
        _trend_analysis_cache["signature"] = signature
        _trend_analysis_cache["data"] = result
        return result

    try:
        sections = _call_llm_for_trend_analysis(context)
        result = {"llm_used": True, "from_cache": False, "analysis_status": "completed", "sections": sections, "context": context}
    except HTTPException:
        raise
    except Exception as exc:
        result = {
            "llm_used": False,
            "from_cache": False,
            "analysis_status": "fallback",
            "warning": f"LLM 趋势总结失败，已返回本地知识库兜底摘要：{exc}",
            "sections": _fallback_trend_sections(context),
            "context": context,
        }

    _trend_analysis_cache["signature"] = signature
    _trend_analysis_cache["data"] = result
    _set_disk_cached_analysis("tech_trend", signature, result)
    return result


def _salary_overview_stats(df: pd.DataFrame) -> dict[str, Any]:
    values = []
    if "salary_min" in df.columns:
        values = [float(v) for v in df["salary_min"].dropna().tolist() if float(v) > 0]
    if not values:
        return {"avg": 0, "min": 0, "max": 0, "median": 0, "count": 0}
    series = pd.Series(values)
    return {
        "avg": round(float(series.mean()), 0),
        "min": round(float(series.min()), 0),
        "max": round(float(series.max()), 0),
        "median": round(float(series.median()), 0),
        "count": len(values),
    }


def _list_from_maybe_string(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    text = _safe_text(value)
    if not text:
        return []
    try:
        parsed = json.loads(text.replace("'", '"'))
        if isinstance(parsed, list):
            return [str(item) for item in parsed if str(item).strip()]
    except Exception:
        pass
    return [part.strip() for part in text.replace(";", ",").split(",") if part.strip()]


def _call_llm_for_job_display_names(jobs: list[dict[str, Any]]) -> dict[int, str]:
    """调用 LLM 为高薪岗位生成简洁中文显示名称，用于图表标签避免英文重叠"""
    manager = LLMConfigManager()
    if not manager.configured:
        return {}
    kwargs = manager.build_kwargs()
    items = [
        {"idx": i, "title": j.get("title", ""), "role": j.get("role_name", ""), "industry": j.get("industry_category", "")}
        for i, j in enumerate(jobs)
    ]
    prompt = (
        "你是香港 IT 招聘市場崗位名稱翻譯助手。請為以下每個英文崗位標題生成一個簡潔的中文顯示名稱（不超過10個字），"
        "用於圖表標籤展示。名稱應體現崗位核心方向，避免過長導致標籤重疊。\n"
        "規則：\n"
        '1. 輸出 JSON 對象，格式為 {"items":[{"idx":0,"display_name":"AI應用工程師"}]}。\n'
        "2. 優先使用角色名稱和行業信息輔助翻譯。\n"
        "3. 如果標題已是中文，可以精簡後返回。\n"
        "4. 相同方向的崗位可以合併為同一名稱。\n"
        f"崗位數據：{json.dumps(items, ensure_ascii=False)}"
    )
    payload = {
        "model": kwargs["model"],
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "max_tokens": 2048,
        "response_format": {"type": "json_object"},
    }
    headers = {"Authorization": f"Bearer {kwargs['api_key']}", "Content-Type": "application/json"}
    resp = requests.post(
        f"{kwargs['api_base'].rstrip('/')}/chat/completions",
        headers=headers,
        json=payload,
        timeout=min(max(int(kwargs.get("timeout", 30) or 30), 30), 60),
        proxies={"http": None, "https": None},
    )
    resp.raise_for_status()
    message = resp.json()["choices"][0]["message"]
    content = (message.get("content") or message.get("reasoning_content") or "").strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    start_obj = content.find("{")
    end_obj = content.rfind("}")
    if start_obj >= 0 and end_obj > start_obj:
        content = content[start_obj:end_obj + 1]
    parsed = json.loads(content)
    result: dict[int, str] = {}
    items_out = parsed.get("items", []) if isinstance(parsed, dict) else []
    for item in items_out:
        if not isinstance(item, dict):
            continue
        idx = item.get("idx")
        name = item.get("display_name", "")
        if isinstance(idx, int) and isinstance(name, str) and name.strip():
            result[idx] = name.strip()
    return result


def _top_salary_jobs(df: pd.DataFrame, top_n: int = 15, use_llm: bool = True) -> list[dict[str, Any]]:
    if df.empty or "salary_min" not in df.columns:
        return []
    from api.routers.role_stats import _get_classifier, _role_from_cache_or_rules

    classifier = _get_classifier()
    rows = df.dropna(subset=["salary_min"]).copy()
    rows = rows[rows["salary_min"].astype(float) > 0]
    rows = rows.sort_values("salary_min", ascending=False).head(top_n)
    result = []
    for idx, row in rows.iterrows():
        role = _role_from_cache_or_rules(classifier, row)
        industry = _infer_industry_with_rules(_job_industry_record(row, int(idx)))
        jd = _safe_text(row.get("jd_text")) or _safe_text(row.get("jd_raw")) or _safe_text(row.get("kb_document_text"))
        result.append({
            "title": _safe_text(row.get("title")),
            "company": _safe_text(row.get("company")),
            "location": location_to_zh(_safe_text(row.get("location"))),
            "industry_category": industry,
            "role_name": role.role_name,
            "role_id": role.role_id,
            "tech_stack": _list_from_maybe_string(row.get("tech_stack"))[:10],
            "work_summary": jd[:220],
            "salary_min": float(row.get("salary_min") or 0),
            "salary_max": float(row.get("salary_max") or 0) if _safe_text(row.get("salary_max")) else 0,
        })

    # 调用 LLM 生成简洁中文显示名称，避免英文标题在图表中重叠
    display_names = {}
    if use_llm:
        try:
            display_names = _call_llm_for_job_display_names(result)
        except Exception:
            display_names = {}
    for i, item in enumerate(result):
        item["display_name"] = display_names.get(i) or item.get("role_name") or item.get("title", "")

    return result

def _build_salary_context(df: pd.DataFrame, use_llm: bool = True) -> dict[str, Any]:
    from api.routers.role_stats import role_salary

    return {
        "total_jobs": len(df),
        "salary_overview": _salary_overview_stats(df),
        "salary_by_location": salary_by_location(),
        "salary_by_role": role_salary(),
        "top_salary_jobs": _top_salary_jobs(df, use_llm=use_llm),
    }


def _fallback_salary_sections(context: dict[str, Any]) -> list[dict[str, Any]]:
    overview = context.get("salary_overview", {})
    locations = "、".join([f"{x.get('location')}({x.get('avg')})" for x in context.get("salary_by_location", [])[:5]]) or "暂无地区薪资统计"
    roles = "、".join([f"{x.get('role_name')}({x.get('salary_avg')})" for x in context.get("salary_by_role", [])[:5]]) or "暂无角色薪资统计"
    top_jobs = "、".join([f"{x.get('title')}({x.get('salary_min')})" for x in context.get("top_salary_jobs", [])[:5]]) or "暂无高薪岗位统计"
    return [
        {"key": "salary_overview", "title": "薪资总体分析", "summary": f"当前可用薪资样本 {overview.get('count', 0)} 条，平均月薪约 HKD {overview.get('avg', 0)}，中位数约 HKD {overview.get('median', 0)}。最高与最低值差距较大，说明岗位 seniority 与技术方向对薪资影响明显。", "evidence": [overview]},
        {"key": "salary_location", "title": "地区薪资分析", "summary": f"地区均薪较高的样本包括：{locations}。地区薪资应结合样本数一起看，样本少的区域不宜单独作为市场结论。", "evidence": context.get("salary_by_location", [])[:6]},
        {"key": "salary_role", "title": "角色薪资分析", "summary": f"角色均薪较突出的方向包括：{roles}。高薪角色通常更强调架构、AI 应用、DevOps 与后端交付能力。", "evidence": context.get("salary_by_role", [])[:6]},
        {"key": "top_salary_jobs", "title": "高薪岗位分析", "summary": f"高薪岗位样本包括：{top_jobs}。建议结合行业、角色方向、工作内容、技术栈和地域判断高薪来源；不要只追逐薪资数字，应优先选择能积累行业知识与可迁移技术能力的岗位。", "evidence": context.get("top_salary_jobs", [])[:6]},
    ]


@router.get("/salary-analysis")
def salary_analysis(refresh: bool = Query(default=False)):
    df = load_jobs_df()
    if df.empty:
        return {"llm_used": False, "sections": [], "context": {"total_jobs": 0}}

    csv_path = Path(__file__).resolve().parent.parent.parent / "data" / "cleaned" / "jobs.csv"
    signature = f"{_SALARY_ANALYSIS_CONTEXT_VERSION}:{csv_path.stat().st_mtime if csv_path.exists() else 0}:{len(df)}"
    if not refresh and _salary_analysis_cache.get("signature") == signature:
        data = dict(_salary_analysis_cache["data"])
        data["from_cache"] = True
        data["analysis_status"] = "cached"
        return data
    if not refresh:
        cached = _get_disk_cached_analysis("salary", signature)
        if cached:
            _salary_analysis_cache["signature"] = signature
            _salary_analysis_cache["data"] = cached
            return cached

    context = _build_salary_context(df, use_llm=refresh)
    if not refresh:
        result = {
            "llm_used": False,
            "from_cache": False,
            "analysis_status": "fallback",
            "warning": "未命中 AI 分析缓存，已先返回本地薪资摘要；点击“重新生成分析”可调用 LLM 生成完整总结。",
            "sections": _fallback_salary_sections(context),
            "context": context,
        }
        _salary_analysis_cache["signature"] = signature
        _salary_analysis_cache["data"] = result
        return result

    prompt = (
        "你是香港 IT 招聘市场薪资分析师。请只基于下面的薪资知识库统计，"
        "用中文输出合法 JSON 对象，顶层字段为 sections。sections 必须包含四个对象："
        "薪资总体分析、地区薪资分析、角色薪资分析、高薪岗位分析。"
        "每个对象字段为 key、title、summary、evidence。summary 写 2-4 句，"
        "必须提到 HKD/月，避免空泛，指出样本数或异常值风险。高薪岗位分析必须说明高薪岗位集中在什么行业、什么岗位方向、主要从事什么工作、用了什么技术栈、位于什么地域，并总结对就业市场的意义和求职者建议。\n\n"
        f"薪资知识库上下文：\n{json.dumps(context, ensure_ascii=False)[:7000]}"
    )
    try:
        sections = _call_llm_sections(prompt)
        result = {"llm_used": True, "from_cache": False, "analysis_status": "completed", "sections": sections, "context": context}
    except HTTPException:
        raise
    except Exception as exc:
        result = {
            "llm_used": False,
            "from_cache": False,
            "analysis_status": "fallback",
            "warning": f"LLM 薪资总结失败，已返回本地知识库兜底摘要：{exc}",
            "sections": _fallback_salary_sections(context),
            "context": context,
        }
    _salary_analysis_cache["signature"] = signature
    _salary_analysis_cache["data"] = result
    _set_disk_cached_analysis("salary", signature, result)
    return result


@router.get("/dashboard")
def dashboard():
    return {
        "overview": overview(),
        "top_skills": top_skills(15),
        "category_distribution": category_distribution(),
        "salary_by_location": salary_by_location(),
        "source_distribution": source_distribution(),
    }
