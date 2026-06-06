"""跨平台爬虫工具模块 — 去重 + 进度追踪 + JD 内容判定"""

import json
import re
from pathlib import Path
from datetime import datetime
from typing import Optional

# ─── JD 内容判定（方案二：基于完整 JD 判断是否 IT 岗位）────────────

# 技术栈关键词 — JD 中命中 >= TECH_MIN_HITS 个即判定为 IT 岗位
TECH_KEYWORDS = [
    # 编程语言
    "python", "java", "javascript", "typescript", "golang", "go",
    "rust", "c++", "c#", "kotlin", "swift", "scala", "ruby", "php",
    # AI / ML 框架
    "tensorflow", "pytorch", "keras", "scikit-learn", "langchain",
    "hugging face", "transformers", "llama", "openai", "rag",
    "deep learning", "machine learning", "neural network",
    "nlp", "computer vision", "reinforcement learning", "llm",
    "large language model", "fine-tuning",
    # 前端框架
    "react", "vue", "angular", "next.js", "nuxt", "svelte",
    "node.js", "express", "django", "flask", "spring boot",
    ".net", "fastapi", "graphql", "redux", "webpack",
    # 数据库 / 数据
    "sql", "mongodb", "postgresql", "redis", "elasticsearch",
    "kafka", "spark", "hadoop", "data pipeline", "etl",
    "tableau", "power bi", "snowflake", "databricks",
    # 云 / 基础设施
    "aws", "azure", "gcp", "docker", "kubernetes", "terraform",
    "jenkins", "ci/cd", "github actions", "linux", "unix",
    # 架构 / 模式
    "microservice", "api", "restful", "soa", "system design",
    "design pattern", "distributed system", "high availability",
    # 工程实践
    "git", "agile", "scrum", "tdd", "unit test",
    "code review", "devops", "sre", "cicd",
    # 安全
    "penetration test", "owasp", "encryption", "firewall",
    # 区块链
    "blockchain", "solidity", "ethereum", "web3", "smart contract",
    # 移动
    "ios", "android", "react native", "flutter",
]

# 非技术排除词 — 仅供后续角色分类使用，不参与收录判定
# 原则：收录阶段只做正向技术关键词匹配，不因 JD 中出现非技术词而排除岗位
# 含混合关键词的岗位（如 "IT Sales"、"Insurance Tech Lead"）由角色分类器区分
NON_TECH_INDICATORS = [
    "sales target", "revenue growth", "cold call",
    "lead generation", "account management", "business development",
    "recruitment", "hiring manager", "talent acquisition",
    "payroll", "compensation", "benefit administration",
    "audit", "tax compliance", "statutory reporting",
    "legal advice", "contract review", "litigation",
    "merchandising", "inventory management", "supply chain",
    "front desk", "reception", "customer service",
    "nursing", "clinical", "patient care",
    "teaching", "curriculum", "classroom",
]

TECH_MIN_HITS = 3  # 最少命中数

# ─── 保险伪装岗位检测（不用于排除，仅标记）────────────

# 保险类公司关键词（用于加分，不是一票否决）
INSURANCE_COMPANY_KEYWORDS = [
    "aia", "axa", "prudential", "manulife", "宏利",
    "友邦", "保诚", "安盛", "富卫", "fwd",
    "中国人寿", "china life", "平安保险", "ping an",
    "aig", "metlife", "chubb", "zurich",
    "amg financial", "family office",
]

# 保险销售标题特征词（标题中出现即加分）
INSURANCE_TITLE_KEYWORDS = [
    "wealth management", "wealth manager", "wealth planner",
    "financial consultant", "financial planner", "financial advisor",
    "family office", "理財顧問", "理c顾问",
    "management trainee", "management associate",
    "wealth management trainee", "financial management trainee",
]

# 保险销售 JD 特征词（JD 中出现即加分，取排名前几个）
INSURANCE_JD_KEYWORDS = [
    # 核心保险销售词
    "wealth management", "wealth planning", "investment planning",
    "financial planning", "portfolio management",
    "client portfolio", "客户理财", "财富管理", "投资规划",
    "insurance product", "insurance plan", "保险产品",
    "retirement planning", "estate planning",
    "risk management", "asset allocation",
    # 低门槛特征
    "fresh graduate", "应届", "iang", "优才", "普通话",
    "no experience", "无需经验", "training provided",
    # 薪酬模式
    "底薪+佣金", "高额佣金", "commission based",
    "package up to", "月入可达", "收入无上限",
    "unlimited income", "快速晋升", "fast track",
    "考试费用", "exam fee", "牌照考试",
    "iiqe", "保险中介人",
    # 职业描述
    "提供培训", "在职培训", "mentorship",
    "弹性工作", "flexible hours", "自主安排",
    "overseas conference", "海外会议", "海外旅游奖励",
]

# 保险重灾区位置关键词
INSURANCE_LOCATION_KEYWORDS = [
    "尖沙咀", "tsim sha tsui", "tsimshatsui",
    "铜锣湾", "causeway bay",
    "海港城", "harbour city", "harbourfront",
]

# 疑似薪酬模式
INSURANCE_SALARY_PATTERNS = [
    r"\d{2,3}k\s*[-–~至]\s*\d{2,3}k",     # 17k-50k
    r"\d{2,3},\d{3}\s*[-–~至]\s*\d{2,3},\d{3}", # 17,000-50,000
]

INSURANCE_DETECTION_THRESHOLD = 5  # 综合评分 >= 此值标记为疑似保险销售


def is_insurance_sales(job: dict) -> tuple[bool, int, list[str]]:
    """检测岗位是否为伪装成 IT 的保险销售

    判定逻辑（多指标评分累加）：
      A. 标题命中 INSURANCE_TITLE_KEYWORDS → +3
      B. 公司名命中 INSURANCE_COMPANY_KEYWORDS → +2
      C. JD 中命中 INSURANCE_JD_KEYWORDS → 每个 +1（上限 10）
      D. 位置命中 INSURANCE_LOCATION_KEYWORDS → +2
      E. 薪酬匹配 INSURANCE_SALARY_PATTERNS → +2
      F. 标题含 "trainee" 且公司是保险 → +2

    总评分 >= INSURANCE_DETECTION_THRESHOLD → 疑似保险销售

    注意：
      - 此函数不用于排除岗位，仅供标记
      - 真实保险公司 IT 岗（如 AIA IT Engineer）通常不命中 Title/JD/薪酬特征，评分较低

    Args:
        job: 岗位字典，含 title, company, jd_raw, location, salary_raw

    Returns:
        (is_suspect, score, reasons): 是否疑似、得分、命中原因列表
    """
    score = 0
    reasons = []

    title = (job.get("title") or "").lower()
    company = (job.get("company") or "").lower()
    jd_text = (job.get("jd_raw") or "").lower()
    location = (job.get("location") or "").lower()
    salary = (job.get("salary_raw") or "").lower()

    # A. 标题查 — 最高权重
    for kw in INSURANCE_TITLE_KEYWORDS:
        if kw in title:
            score += 3
            reasons.append(f"标题:{kw}")
            break  # 命中一个就够

    # B. 公司名查
    company_is_insurance = False
    for kw in INSURANCE_COMPANY_KEYWORDS:
        if kw in company:
            score += 2
            reasons.append(f"公司:{kw}")
            company_is_insurance = True
            break

    # C. JD 内容特征累积 — 每个 +1
    jd_hits = 0
    for kw in INSURANCE_JD_KEYWORDS:
        if kw in jd_text:
            jd_hits += 1
            if jd_hits <= 3:  # 最多记录3个原因
                reasons.append(f"JD:{kw}")
    jd_score = min(jd_hits, 10)  # 上限 10 分
    score += jd_score

    # D. 位置查
    for kw in INSURANCE_LOCATION_KEYWORDS:
        if kw in location:
            score += 2
            reasons.append(f"位置:{kw}")
            break

    # E. 薪酬模式
    for pat in INSURANCE_SALARY_PATTERNS:
        if re.search(pat, salary):
            score += 2
            reasons.append("薪酬:大范围")
            break

    # F. Trainee 标题 + 保险公司的组合加重
    if company_is_insurance and "trainee" in title:
        score += 2
        reasons.append("保险Trainee")

    is_suspect = score >= INSURANCE_DETECTION_THRESHOLD
    return is_suspect, score, reasons


def jd_contains_tech(jd_text: str) -> bool:
    """基于完整 JD 文本判断是否为 IT 技术岗位

    判定逻辑（纯正向匹配，不用排除词）：
      技术关键词命中 >= TECH_MIN_HITS → IT 岗位
      否则 → 非 IT 岗位

    注意：不因 JD 中出现非技术词（如 sales、insurance）而排除岗位，
    这类混合岗位由后续角色分类器进一步区分。

    Args:
        jd_text: 完整 JD 文本（通常 1000-5000 字）

    Returns:
        True 表示 IT 技术岗位，False 表示非 IT 岗位
    """
    if not jd_text:
        return False

    jd_lower = jd_text.lower()

    # 技术关键词命中数累计
    hits = 0
    for kw in TECH_KEYWORDS:
        if kw in jd_lower:
            hits += 1
            if hits >= TECH_MIN_HITS:
                return True

    return False


# ─── 去重 ───────────────────────────────────────────────


def normalize_url(url: str) -> str:
    """提取 URL 的基础部分用于去重（去掉 query/hash）"""
    if not url:
        return ""
    # 去掉 hash
    url = url.split("#")[0]
    # 去掉尾部 query（保留部分平台需要的 query 参数）
    # JobsDB: /job/123?type=standard → /job/123
    # Indeed: /viewjob?jk=abc123 → /viewjob?jk=abc123 （jk 是唯一标识）
    # LinkedIn: /jobs/view/123 → /jobs/view/123
    return url.split("?")[0].rstrip("/")


def build_dedup_key(job: dict) -> str:
    """构建跨平台去重键
    优先级: URL > (source, title, company)
    """
    url = job.get("url", "")
    base_url = normalize_url(url)
    if base_url:
        return f"url::{base_url}"

    # 无 URL 时用 (source, title_lower, company_lower) 兜底
    source = job.get("source", "unknown")
    title = job.get("title", "").lower().strip()
    company = job.get("company", "").lower().strip()
    return f"{source}::{title}||{company}"


def deduplicate(
    jobs: list[dict],
    existing_keys: Optional[set] = None,
) -> list[dict]:
    """跨平台去重

    去重优先级：
      1. URL（去掉 query/hash）— 最精确
      2. (source, title_lower, company_lower) — 无 URL 时兜底

    Args:
        jobs: 待去重岗位列表
        existing_keys: 已有的去重键集合（用于跳过已收集岗位）

    Returns:
        去重后的新增岗位列表
    """
    seen = set(existing_keys) if existing_keys else set()
    unique = []

    for j in jobs:
        key = build_dedup_key(j)
        if key not in seen:
            seen.add(key)
            unique.append(j)

    return unique


def build_existing_keys(jobs: list[dict]) -> set:
    """从已有数据构建去重键集合"""
    keys = set()
    for j in jobs:
        keys.add(build_dedup_key(j))
    return keys


# ─── 进度追踪 ───────────────────────────────────────────

PROGRESS_FILE = Path("data/progress/crawl_progress.json")


def load_progress() -> dict:
    """加载进度文件"""
    if PROGRESS_FILE.exists():
        try:
            return json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {
        "completed_keywords": [],
        "last_completed": None,
        "last_completed_at": None,
        "total_jobs": 0,
    }


def save_progress(progress: dict):
    """保存进度文件"""
    PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
    PROGRESS_FILE.write_text(
        json.dumps(progress, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def mark_keyword_completed(progress: dict, keyword: str, total_jobs: int):
    """标记一个关键词为已完成"""
    if keyword not in progress["completed_keywords"]:
        progress["completed_keywords"].append(keyword)
    progress["last_completed"] = keyword
    progress["last_completed_at"] = datetime.now().isoformat()
    progress["total_jobs"] = total_jobs
    save_progress(progress)


def get_remaining_keywords(all_keywords: list[str]) -> list[str]:
    """获取尚未爬取的关键词列表（不修改进度文件）"""
    progress = load_progress()
    completed = set(progress.get("completed_keywords", []))
    return [kw for kw in all_keywords if kw not in completed]


def print_progress_status(all_keywords: list[str]):
    """打印进度状态"""
    progress = load_progress()
    completed = set(progress.get("completed_keywords", []))
    remaining = [kw for kw in all_keywords if kw not in completed]

    print(f"  进度: {len(completed)}/{len(all_keywords)} 个关键词已完成")
    print(f"  总岗位数: {progress.get('total_jobs', 0)}")
    if progress.get("last_completed"):
        print(f"  最后完成: {progress['last_completed']} ({progress.get('last_completed_at', '')[:19]})")
    if remaining:
        print(f"  剩余 {len(remaining)} 个: {', '.join(remaining[:5])}{'...' if len(remaining) > 5 else ''}")
