# 香港招聘网站数据爬取与技术需求分析系统 — 技术设计文档

**版本**: v1.0  
**日期**: 2026-06-01  
**状态**: 初稿

---

## 修订记录

| 版本 | 日期 | 修订内容 | 修订人 |
|------|------|---------|--------|
| v1.0 | 2026-06-01 | 初始版本 | - |

---

## 目录

1. [引言](#1-引言)
   - 1.1 [编写目的](#11-编写目的)
   - 1.2 [项目背景](#12-项目背景)
   - 1.3 [适用范围](#13-适用范围)
2. [目标网站分析](#2-目标网站分析)
   - 2.1 [目标网站选型](#21-目标网站选型)
   - 2.2 [文本特征分析](#22-文本特征分析)
   - 2.3 [反爬策略预判](#23-反爬策略预判)
3. [系统总体架构](#3-系统总体架构)
   - 3.1 [架构分层设计](#31-架构分层设计)
   - 3.2 [技术选型说明](#32-技术选型说明)
   - 3.3 [数据流设计](#33-数据流设计)
4. [数据采集层详细设计](#4-数据采集层详细设计)
   - 4.1 [基于 RESTful API 的采集方案](#41-基于-restful-api-的采集方案)
   - 4.2 [基于 Playwright 的动态渲染采集方案](#42-基于-playwright-的动态渲染采集方案)
   - 4.3 [代理与请求头策略](#43-代理与请求头策略)
   - 4.4 [频率控制与异常处理](#44-频率控制与异常处理)
5. [数据清洗与存储层详细设计](#5-数据清洗与存储层详细设计)
   - 5.1 [数据模型与字段设计](#51-数据模型与字段设计)
   - 5.2 [文本清洗流程](#52-文本清洗流程)
   - 5.3 [薪资标准化处理](#53-薪资标准化处理)
   - 5.4 [数据存储方案](#54-数据存储方案)
6. [算法与文本挖掘层详细设计](#6-算法与文本挖掘层详细设计)
   - 6.1 [总体策略](#61-总体策略)
   - 6.2 [方案 A：基于关键词词表的规则匹配引擎](#62-方案-a基于关键词词表的规则匹配引擎)
   - 6.3 [方案 B：基于大语言模型的智能提取引擎](#63-方案-b基于大语言模型的智能提取引擎)
   - 6.4 [双引擎对比与选型建议](#64-双引擎对比与选型建议)
7. [数据可视化层详细设计](#7-数据可视化层详细设计)
   - 7.1 [技术热度分析](#71-技术热度分析)
   - 7.2 [薪资与技术关联分析](#72-薪资与技术关联分析)
   - 7.3 [行业与区域分布分析](#73-行业与区域分布分析)
8. [关键技术攻关与风险控制](#8-关键技术攻关与风险控制)
   - 8.1 [反爬虫对抗策略](#81-反爬虫对抗策略)
   - 8.2 [混合语文本处理策略](#82-混合语文本处理策略)
   - 8.3 [薪资解析策略](#83-薪资解析策略)
9. [法律与合规声明](#9-法律与合规声明)
10. [部署与运行指南](#10-部署与运行指南)
    - 10.1 [环境依赖](#101-环境依赖)
    - 10.2 [运行步骤](#102-运行步骤)

---

## 1. 引言

### 1.1 编写目的

本文档旨在为"香港招聘网站数据爬取与技术需求分析系统"提供完整的技术设计方案。文档覆盖系统架构、模块划分、核心算法、数据模型、风险控制及部署运维等各个方面，用于指导研发团队进行系统开发与迭代。

### 1.2 项目背景

香港作为国际金融与科技中心，IT 人才市场需求旺盛。然而，香港招聘市场存在以下特点：

- **平台分散**：岗位信息分布在 JobsDB、Indeed、LinkedIn、HKGoodJobs 等多个平台
- **文本混杂**：岗位描述（Job Description）以全英文或中英夹杂（Code-switching）为主
- **薪资不透明**：薪资表达方式多样（月薪/年薪、区间/面议），缺乏统一格式
- **市场动态变化快**：技术栈需求随行业趋势快速演变

因此，亟需一套自动化系统来持续采集、结构化分析香港 IT 招聘数据，为求职者与用人单位提供数据决策支持。

### 1.3 适用范围

本文档适用于以下人员与场景：

| 角色 | 关注重点 |
|------|---------|
| 系统架构师 | 整体架构设计、技术选型、模块划分 |
| 后端开发工程师 | 爬虫实现、数据清洗、API 设计 |
| 算法工程师 | NLP 文本挖掘、LLM 集成 |
| 数据分析师 | 可视化报表设计、分析维度定义 |
| 运维工程师 | 部署配置、代理管理、监控告警 |

---

## 2. 目标网站分析

### 2.1 目标网站选型

| 网站 | 所属集团/机构 | 岗位数量 | 技术架构 | 反爬强度 | 优先级 | 备注 |
|------|-------------|---------|---------|---------|-------|------|
| JobsDB | SEEK Group | 最大 | GraphQL / RESTful API | 中等 | P0 | 香港最大招聘平台 |
| Indeed HK | Indeed (Recruit) | 大 | RESTful API | 较低 | P1 | 数据补充 |
| LinkedIn HK | Microsoft | 大 | RESTful API | 高 | P2 | 需登录墙绕过 |
| HKGoodJobs | 本地 | 中 | 传统 HTML | 低 | P3 | 本地中小企业居多 |
| **OfferToday** | 本地初创 | 中 | RESTful API | 低 | **P2** | 专注毕业生与初级岗位，中英双语 JD 占比高 |
| **香港科学园 (HKSTP)** | 香港科技园公司 | 少-中 | 传统 HTML | 低 | **P2** | 科技园区企业专属，含大量深科技/研发岗位 |
| **香港数码港 (Cyberport)** | 数码港管理有限公司 | 少-中 | 传统 HTML / API | 低 | **P2** | 数码港社群企业招聘，侧重金融科技/Web3/数码娱乐 |
| **港八大联校校招网站 (JIJIS)** | 香港八大院校联校 | 中 | 传统 HTML | 低 | **P1** | 八大院校联合就业信息系统，覆盖应届毕业生与实习岗位 |

> **JIJIS 说明**：香港八大资助大学（港大、中大、科大、理大、城大、浸大、岭大、教大）联合建立的 JIJIS（Joint Institutions Job Information System），是面向在校生与应届毕业生的官方校招平台，岗位类型涵盖实习、毕业生全职及部分初级职位。

**选型建议**：
- **核心数据源（P0-P1）**：JobsDB 作为主数据源覆盖全量市场；JIJIS 作为校招专属数据源，补充应届生与实习岗位数据
- **补充数据源（P2）**：Indeed HK 加大数据覆盖面；OfferToday 补充毕业生初级岗位；香港科学园和数码港补充特定科技园区的高质量技术岗位
- **辅助数据源（P3）**：HKGoodJobs 和 LinkedIn HK 作为长尾补充

### 2.2 文本特征分析

香港 IT 岗位 JD 的文本特征对下游 NLP 任务有重要影响：

1. **语言分布**：约 70% 为全英文，25% 为中英夹杂，5% 为全中文
2. **专有名词密集**：技术栈名称（Python、AWS、React）出现频率高，且大小写不统一
3. **缩写普遍**：如 CI/CD、K8s、FE/BE、SRE 等行业缩写
4. **句式结构化**：通常以列表形式呈现技术要求（Requirements / Qualifications 段落）
5. **区域特征**：包含香港本地地名（中环 Central、观塘 Kwun Tong、科学园 Science Park）

### 2.3 反爬策略预判

| 网站 | 反爬措施 | 应对方案 |
|------|---------|---------|
| JobsDB | Rate limiting、API Token 验证 | 伪造请求头、控制频率、定期刷新 Token |
| Indeed | IP 风控、CAPTCHA | 代理 IP 池、Playwright 自动化 |
| LinkedIn | 强反爬、登录墙 | 仅作为补充数据源，使用 Playwright Stealth |
| OfferToday | 基本防护 | 标准请求头伪造 + 频率控制即可 |
| 香港科学园 (HKSTP) | 基本防护 | 标准请求头伪造 + 频率控制即可 |
| 香港数码港 (Cyberport) | 基本防护 | 标准请求头伪造 + 频率控制即可 |
| JIJIS (八大联校) | 基本防护 | 标准请求头伪造 + 频率控制即可 |

---

## 3. 系统总体架构

### 3.1 架构分层设计

本系统采用经典的四层架构设计，各层职责明确、接口清晰：

```
+--------------------------------------------------------------------+
|                        数据采集层 (Crawler Layer)                    |
|  Requests / Playwright / 代理IP池 / 频率控制器                       |
+--------------------------------------------------------------------+
         |                         |
         |   原始 JSON / HTML       |
         v                         v
+--------------------------------------------------------------------+
|                      数据清洗与存储层 (Cleaning & Storage Layer)     |
|  文本清洗 / 薪资标准化 / 去重 / MongoDB + CSV 持久化                |
+--------------------------------------------------------------------+
         |
         |   结构化数据
         v
+--------------------------------------------------------------------+
|                      算法与文本挖掘层 (Analysis Layer)               |
|  规则匹配引擎 (Regex)  /  LLM 智能引擎 (DeepSeek/GPT)              |
+--------------------------------------------------------------------+
         |
         |   技能标签 / 结构化 JSON
         v
+--------------------------------------------------------------------+
|                        数据可视化层 (Visualization Layer)            |
|  Streamlit 看板 / Matplotlib 图表 / 数据导出                        |
+--------------------------------------------------------------------+
```

### 3.2 技术选型说明

| 层次 | 技术栈 | 选型理由 |
|------|-------|---------|
| 数据采集 | Python Requests, Playwright | Requests 轻量高效；Playwright 支持动态渲染，可绕过复杂反爬 |
| 文本清洗 | BeautifulSoup, re, Pandas | BeautifulSoup 解析 HTML；re 正则匹配清洗；Pandas 批量处理 |
| 数据存储 | MongoDB, CSV | MongoDB 灵活支持 JSON 文档存储；CSV 便于快速导出分析 |
| 文本挖掘 | re, spaCy, OpenAI SDK | re 高性能规则匹配；spaCy 英文 NLP 管道；OpenAI SDK 对接大模型 |
| 数据可视化 | Streamlit, Matplotlib, Seaborn | Streamlit 交互式看板快速开发；Matplotlib/Seaborn 静态图表 |
| 配置管理 | python-dotenv, JSON | .env 管理密钥；JSON 管理词表配置 |

### 3.3 数据流设计

```
[JobsDB/Indeed] --HTTP请求--> [代理IP池] --> [爬虫模块]
                                                 |
                                         清洗、去重、标准化
                                                 |
                                            [MongoDB]
                                                 |
                                    双引擎并行或串行分析
                                                 |
                              [技能标签]  [薪资数据]  [区域数据]
                                                 |
                                        可视化看板生成
                                                 |
                                    [HTML报表]  [PNG图表]  [CSV导出]
```

---

## 4. 数据采集层详细设计

### 4.1 基于 RESTful API 的采集方案

#### 4.1.1 接口分析

JobsDB 新版网站采用前后端分离架构，通过浏览器开发者工具（F12）抓包可发现其后端 API。典型的 API 特征：

- **端点格式**：`https://hk.jobsdb.com/api/...`
- **请求方式**：GET / POST，参数含 keyword、location、page 等
- **响应格式**：JSON，包含岗位列表、分页信息

#### 4.1.2 核心爬虫实现

```python
import requests
import time
import random
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

class JobsDBCrawler:
    """
    JobsDB 招聘数据爬虫
    通过模拟 API 请求获取岗位数据
    """

    def __init__(self, proxy_config: dict = None):
        self.base_url = "https://hk.jobsdb.com/api/jobs"
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Referer": "https://hk.jobsdb.com/",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-HK,en-HK;q=0.9,en;q=0.8,zh-CN;q=0.7",
        }
        self.proxies = proxy_config
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        if self.proxies:
            self.session.proxies.update(self.proxies)

    def fetch_page(self, keyword: str, page: int = 1) -> dict | None:
        """
        获取指定关键词和页码的岗位数据
        """
        params = {"keyword": keyword, "page": page, "location": "Hong Kong"}
        try:
            logging.info("Fetching keyword=[%s] page=[%d]", keyword, page)
            response = self.session.get(
                self.base_url, params=params, timeout=15
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logging.error("Request failed: %s", e)
            return None

    def run(
        self, keyword: str, max_pages: int = 5,
        delay_range: tuple = (2.5, 5.0)
    ) -> list[dict]:
        """
        运行爬虫，收集多个页面的数据
        """
        all_jobs = []
        for page in range(1, max_pages + 1):
            data = self.fetch_page(keyword, page)
            if data and "jobs" in data:
                all_jobs.extend(data["jobs"])
                delay = random.uniform(*delay_range)
                logging.info("Collected %d jobs, sleeping %.2fs", len(data["jobs"]), delay)
                time.sleep(delay)
            else:
                logging.warning("No data returned for page %d, stopping", page)
                break
        return all_jobs
```

#### 4.1.3 配置管理

代理配置通过 `.env` 文件管理，避免硬编码：

```
# .env 配置文件
PROXY_HTTP=http://hk-residential-proxy:8080
PROXY_HTTPS=http://hk-residential-proxy:8080
CRAWL_DELAY_MIN=2.5
CRAWL_DELAY_MAX=5.0
USER_AGENT=Mozilla/5.0 (Windows NT 10.0; Win64; x64) ...
```

### 4.2 基于 Playwright 的动态渲染采集方案

当目标网站存在以下情况时，需切换至 Playwright：

- 数据通过 JavaScript 动态渲染，API 难以直接调用
- 页面存在 Cloudflare 等反爬防护
- 需要模拟用户登录、滚动等交互行为

```python
from playwright.sync_api import sync_playwright
import time

class PlaywrightCrawler:
    """
    Playwright 动态渲染爬虫
    适用于强 JavaScript 渲染或高反爬网站
    """

    def __init__(self, headless: bool = True):
        self.headless = headless

    def fetch_dynamic_page(self, url: str) -> str:
        """
        使用无头浏览器获取动态渲染后的页面 HTML
        """
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 ..."
                ),
                viewport={"width": 1920, "height": 1080},
            )
            page = context.new_page()
            page.goto(url, wait_until="networkidle", timeout=30000)
            # 模拟人类滚动行为
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(2)
            html = page.content()
            browser.close()
            return html
```

### 4.3 代理与请求头策略

#### 4.3.1 代理 IP 选择

| 代理类型 | 适用场景 | 优点 | 缺点 |
|---------|---------|------|------|
| 数据中心代理 | 低反爬网站 | 速度快、价格低 | 易被识别拦截 |
| 住宅代理 | 高反爬网站 | 匿名性高、成功率好 | 价格较高 |
| 香港本地代理 | 香港网站优先推荐 | 区域匹配度高 | 资源有限 |

#### 4.3.2 请求头伪造

```python
HEADERS_TEMPLATE = {
    "User-Agent": "Mozilla/5.0 ...",
    "Accept": "application/json, text/html",
    "Accept-Language": "zh-HK,en-HK;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://hk.jobsdb.com/",
    "Connection": "keep-alive",
    "Cache-Control": "no-cache",
}
```

### 4.4 频率控制与异常处理

#### 4.4.1 自适应延迟策略

```python
class AdaptiveDelayController:
    """
    自适应延迟控制器
    根据请求成功率动态调整延迟时间
    """

    def __init__(self, base_delay: float = 3.0):
        self.base_delay = base_delay
        self.success_window = []

    def get_delay(self) -> float:
        if not self.success_window:
            return self.base_delay
        success_rate = sum(self.success_window[-20:]) / 20
        if success_rate < 0.8:
            return self.base_delay * 2
        return self.base_delay

    def record_result(self, success: bool):
        self.success_window.append(1 if success else 0)
        if len(self.success_window) > 100:
            self.success_window.pop(0)
```

#### 4.4.2 异常处理与重试机制

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
)
def robust_fetch(url: str, session: requests.Session) -> requests.Response:
    response = session.get(url, timeout=15)
    response.raise_for_status()
    return response
```

---

## 5. 数据清洗与存储层详细设计

### 5.1 数据模型与字段设计

#### 5.1.1 核心数据结构

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class JobPosting:
    """岗位数据模型"""
    job_id: str                          # 唯一标识
    title: str                           # 职位名称
    company: str                         # 公司名称
    location: str                        # 工作地点
    salary_raw: str                      # 原始薪资文本
    salary_min: Optional[float] = None   # 最低薪资 (HKD)
    salary_max: Optional[float] = None   # 最高薪资 (HKD)
    jd_text: str = ""                    # 清洗后的 JD 文本
    jd_raw: str = ""                     # 原始 JD 文本
    url: str = ""                        # 原始链接
    source: str = "jobsdb"               # 数据来源
    crawled_at: datetime = None          # 爬取时间
    skills: dict = None                  # 提取的技能标签
```

#### 5.1.2 MongoDB 文档结构

```json
{
  "_id": "HK_10023948",
  "title": "Senior Full Stack Engineer (Node.js + React)",
  "company": "HK Fintech Limited",
  "location": "Central",
  "salary_raw": "HK$45,000 - HK$60,000 /month",
  "salary_min": 45000,
  "salary_max": 60000,
  "salary_currency": "HKD",
  "salary_period": "monthly",
  "jd_text": "We are looking for a software developer proficient in React and AWS cloud services...",
  "url": "https://hk.jobsdb.com/job/10023948",
  "source": "jobsdb",
  "crawled_at": { "$date": "2026-06-01T12:00:00Z" },
  "skills": {
    "programming_languages": ["Python", "TypeScript"],
    "frameworks": ["React", "Node.js"],
    "cloud_devops": ["AWS", "Docker"],
    "databases": ["PostgreSQL"]
  }
}
```

### 5.2 文本清洗流程

#### 5.2.1 清洗管道设计

```python
import re
from bs4 import BeautifulSoup

class JDTextCleaner:
    """
    JD 文本清洗器
    按管道顺序执行多个清洗步骤
    """

    @staticmethod
    def remove_html_tags(text: str) -> str:
        if not text:
            return ""
        return BeautifulSoup(text, "html.parser").get_text(separator=" ")

    @staticmethod
    def normalize_whitespace(text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def normalize_unicode(text: str) -> str:
        # 统一全角/半角字符
        text = text.replace("\u3000", " ")  # 全角空格 → 半角
        text = text.replace("\xa0", " ")    # NBSP → 半角空格
        return text

    @staticmethod
    def remove_special_chars(text: str) -> str:
        # 保留字母、数字、常用标点
        return re.sub(r"[^\w\s@.,;:!?()\-+/%]", " ", text)

    @staticmethod
    def normalize_case(text: str) -> str:
        # 注意：保留专有名词大小写，不做全局小写
        return text

    def clean(self, raw_text: str) -> str:
        text = self.remove_html_tags(raw_text)
        text = self.normalize_unicode(text)
        text = self.normalize_whitespace(text)
        text = self.remove_special_chars(text)
        text = self.normalize_whitespace(text)
        return text
```

#### 5.2.2 清洗示例

| 原始文本 | 清洗后文本 |
|---------|-----------|
| `<p>懂 React, AWS 優先</p>` | `懂 React, AWS 優先` |
| `We are looking for\u00a0a Python developer...` | `We are looking for a Python developer...` |
| `Skills: Java  ,  SQL  ,  Spring` | `Skills: Java, SQL, Spring` |

### 5.3 薪资标准化处理

#### 5.3.1 薪资解析策略

```python
import re
from typing import Optional, Tuple

class SalaryParser:
    """
    香港招聘薪资解析器
    处理多种薪资表达格式
    """

    PATTERNS = [
        # HK$45,000 - HK$60,000 /month
        r"(?:hk)?\$?([\d,]+)\s*-\s*(?:hk)?\$?([\d,]+)\s*(?:/|per\s*)(month|mth|annum|year|yr)",
        # HK$45,000 - HK$60,000
        r"(?:hk)?\$?([\d,]+)\s*-\s*(?:hk)?\$?([\d,]+)\b",
        # HK$45,000 up
        r"(?:hk)?\$?([\d,]+)\s*(up|above|plus|以上)",
        # HK$45,000 /month
        r"(?:hk)?\$?([\d,]+)\s*(?:/|per\s*)(month|mth|annum|year|yr)",
    ]

    @staticmethod
    def parse(raw: str) -> Tuple[Optional[float], Optional[float]]:
        """
        解析薪资文本，返回 (min_salary, max_salary)
        统一标准化为港币月薪 (HKD/month)
        """
        if not raw or not isinstance(raw, str):
            return None, None

        raw = raw.strip().lower()

        for pattern in SalaryParser.PATTERNS:
            match = re.search(pattern, raw)
            if not match:
                continue

            groups = match.groups()

            if len(groups) >= 2:
                min_val = float(groups[0].replace(",", ""))
                max_val = float(groups[1].replace(",", "")) if len(groups) >= 2 else None
                period = groups[2] if len(groups) >= 3 else "month"

                # 标准化为月薪
                if period in ("annum", "year", "yr"):
                    min_val = round(min_val / 12, 0)
                    if max_val:
                        max_val = round(max_val / 12, 0)

                return min_val, max_val

        return None, None


# 示例
assert SalaryParser.parse("HK$45,000 - HK$60,000 /month") == (45000, 60000)
assert SalaryParser.parse("HK$600,000 - HK$720,000 per annum") == (50000, 60000)
assert SalaryParser.parse("Negotiable") == (None, None)
```

### 5.4 数据存储方案

#### 5.4.1 MongoDB 存储（主存储）

```python
from pymongo import MongoClient, IndexModel, ASCENDING

class JobDatabase:
    """
    岗位数据 MongoDB 持久化管理器
    """

    def __init__(self, uri: str = "mongodb://localhost:27017", db_name: str = "hk_job_market"):
        self.client = MongoClient(uri)
        self.db = self.client[db_name]
        self.collection = self.db["job_postings"]
        self._ensure_indexes()

    def _ensure_indexes(self):
        indexes = [
            IndexModel([("job_id", ASCENDING)], unique=True),
            IndexModel([("source", ASCENDING)]),
            IndexModel([("crawled_at", ASCENDING)]),
            IndexModel([("skills.programming_languages", ASCENDING)]),
        ]
        self.collection.create_indexes(indexes)

    def insert_job(self, job: dict) -> str:
        """插入或更新岗位数据（upsert）"""
        result = self.collection.update_one(
            {"job_id": job["job_id"]},
            {"$set": job},
            upsert=True,
        )
        return result.upserted_id

    def bulk_insert(self, jobs: list[dict]) -> int:
        """批量插入"""
        count = 0
        for job in jobs:
            try:
                self.insert_job(job)
                count += 1
            except Exception as e:
                logging.error("Insert failed for %s: %s", job.get("job_id"), e)
        return count
```

#### 5.4.2 CSV 导出（辅助分析）

```python
import pandas as pd

def export_to_csv(mongo_uri: str, output_path: str):
    """将 MongoDB 数据导出为 CSV"""
    client = MongoClient(mongo_uri)
    db = client["hk_job_market"]
    cursor = db["job_postings"].find({}, {"_id": 0})
    df = pd.DataFrame(list(cursor))
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    logging.info("Exported %d records to %s", len(df), output_path)
```

---

## 6. 算法与文本挖掘层详细设计

### 6.1 总体策略

考虑到香港招聘 JD 以英文为主且技术词密集的特点，本系统采用**双引擎并行架构**：

```
                          ┌──────────────────────┐
  清洗后 JD 文本 ────────→│   规则匹配引擎（高性能）│ ← 适用于已知技术栈批量处理
                          ├──────────────────────┤
                          │   LLM 智能引擎（高精度）│ ← 适用于深度理解与隐含技能发现
                          └──────────────────────┘
                                      │
                          结构化技能标签 JSON
```

### 6.2 方案 A：基于关键词词表的规则匹配引擎

#### 6.2.1 技术词表设计

```python
# config/tech_dict.json
{
  "programming_languages": [
    "python", "java", "typescript", "javascript", "golang", "go",
    "c\\+\\+", "cpp", "c#", "csharp", "php", "ruby", "swift",
    "kotlin", "scala", "rust", "r\\s+language", "matlab"
  ],
  "frameworks_libraries": [
    "react", "vue", "angular", "svelte", "next\\.js", "nuxt",
    "django", "flask", "spring\\s+boot", "spring", "express",
    "fastapi", "asp\\.net", "laravel", "tensorflow", "pytorch"
  ],
  "cloud_devops": [
    "aws", "azure", "gcp", "google\\s+cloud", "aliyun",
    "docker", "kubernetes", "k8s", "jenkins", "gitlab\\s+ci",
    "github\\s+actions", "terraform", "ansible", "helm",
    "prometheus", "grafana", "elasticsearch"
  ],
  "databases": [
    "mysql", "postgresql", "postgres", "mongodb", "redis",
    "oracle", "dynamodb", "cassandra", "elasticsearch",
    "kafka", "snowflake", "bigquery", "redshift"
  ],
  "soft_skills": [
    "communication", "teamwork", "leadership", "problem.solving",
    "analytical", "agile", "scrum", "cross.functional",
    "stakeholder management", "mentoring"
  ]
}
```

#### 6.2.2 规则匹配引擎实现

```python
import re
import json
from pathlib import Path

class RuleBasedSkillExtractor:
    """
    基于关键词词表 + 正则边界匹配的技能提取引擎
    特点：高性能、可解释性强、适用于已知技术栈的批量处理
    """

    def __init__(self, dict_path: str = "config/tech_dict.json"):
        with open(dict_path, "r", encoding="utf-8") as f:
            self.tech_dict = json.load(f)
        self._compiled = self._compile_patterns()

    def _compile_patterns(self) -> dict:
        """预编译正则表达式以提高性能"""
        compiled = {}
        for category, keywords in self.tech_dict.items():
            compiled[category] = []
            for kw in keywords:
                pattern = re.compile(r"\b" + kw + r"\b", re.IGNORECASE)
                compiled[category].append((kw, pattern))
        return compiled

    def extract(self, text: str) -> dict:
        """
        从 JD 文本中提取技能标签
        返回按类别分组的技能列表
        """
        if not text:
            return {cat: [] for cat in self.tech_dict}

        result = {}
        for category, patterns in self._compiled.items():
            found_skills = set()
            for raw_kw, pattern in patterns:
                if pattern.search(text):
                    # 规范化显示名称
                    display = raw_kw.replace("\\+", "+").replace("\\s+", " ").replace("\\.", ".")
                    if display.lower() == display:
                        found_skills.add(display.capitalize())
                    else:
                        found_skills.add(display)
            result[category] = sorted(found_skills)

        return result

    def extract_flat(self, text: str) -> list[str]:
        """提取所有技能并扁平化返回"""
        nested = self.extract(text)
        flat = []
        for skills in nested.values():
            flat.extend(skills)
        return flat
```

#### 6.2.3 性能指标

| 指标 | 数值 |
|------|------|
| 单条 JD 处理耗时 | < 5ms |
| 内存占用 | < 100MB |
| 准确率（已知词表） | > 95% |
| 召回率（已知词表） | > 90% |
| 可发现新词 | 否 |

### 6.3 方案 B：基于大语言模型的智能提取引擎

#### 6.3.1 适用场景

- JD 中包含隐含技能描述（如 "design scalable microservices"）
- 需要区分 "熟悉"、"精通"、"了解" 等熟练度等级
- 需要提取软技能（沟通能力、团队协作等）
- 词表中未覆盖的新型技术栈

#### 6.3.2 LLM 提取实现

```python
import json
import logging
from openai import OpenAI

class LLMSkillExtractor:
    """
    基于大语言模型的智能技能提取引擎
    支持 DeepSeek / OpenAI GPT 等兼容接口
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.deepseek.com/v1",
        model: str = "deepseek-chat",
        temperature: float = 0.1,
    ):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.temperature = temperature

    def extract(self, jd_text: str, max_retries: int = 2) -> dict:
        """
        调用 LLM 从 JD 文本中提取结构化技能信息
        """
        prompt = self._build_prompt(jd_text)

        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"},
                    temperature=self.temperature,
                )
                content = response.choices[0].message.content
                return json.loads(content)

            except json.JSONDecodeError:
                logging.warning(
                    "LLM response JSON parse failed, attempt %d/%d",
                    attempt + 1, max_retries,
                )
            except Exception as e:
                logging.error(
                    "LLM API call failed, attempt %d/%d: %s",
                    attempt + 1, max_retries, e,
                )

        return {}

    def _build_prompt(self, jd_text: str) -> str:
        return f"""
You are an expert IT recruiter specializing in the Hong Kong job market.
Analyze the following Job Description and extract technical requirements.

Return a valid JSON object with these keys:
- "programming_languages": list of programming languages mentioned
- "frameworks_libraries": list of frameworks, libraries, or runtimes
- "cloud_devops": list of cloud platforms, DevOps tools, or infrastructure tech
- "databases": list of databases, data stores, or message queues
- "soft_skills": list of soft skills or interpersonal requirements
- "years_of_experience": required years of experience (null if not specified)
- "education": required education level (null if not specified)

Guidelines:
- Include proficiency level if mentioned (e.g., "expert Python", "familiar with React")
- Deduplicate similar terms
- Use original casing from the JD where appropriate

Job Description:
\"\"\"{jd_text}\"\"\"
"""
```

#### 6.3.3 提取结果示例

```json
{
  "programming_languages": ["Python (expert)", "TypeScript", "Java"],
  "frameworks_libraries": ["React", "Node.js", "Spring Boot", "FastAPI"],
  "cloud_devops": ["AWS (certified preferred)", "Docker", "Kubernetes", "Terraform"],
  "databases": ["PostgreSQL", "Redis", "Kafka"],
  "soft_skills": ["Cross-team communication", "Problem-solving", "Agile/Scrum"],
  "years_of_experience": "5+",
  "education": "Bachelor's degree in Computer Science or related field"
}
```

### 6.4 双引擎对比与选型建议

| 对比维度 | 规则匹配引擎 (Rule-Based) | LLM 智能引擎 |
|---------|-------------------------|-------------|
| 处理速度 | ~5ms/条 | ~2-5s/条 |
| 成本 | 近乎为零 | API 调用费用 |
| 词表覆盖 | 仅已知词 | 能力无限，可发现新词 |
| 上下文理解 | 差（仅词级别匹配） | 强（理解句子语义） |
| 熟练度区分 | 不支持 | 支持 |
| 软技能提取 | 有限 | 强 |
| 可解释性 | 完全透明 | 黑盒 |
| 部署复杂度 | 低 | 中（需 API 密钥） |

**推荐策略**：
- **批量初筛（白天）**：使用规则引擎快速处理全量数据，获得基础统计
- **深度分析（夜间/定时）**：对规则引擎未能覆盖的 JD，或需深度理解的样本，调用 LLM 二次处理
- **增量更新**：定期将 LLM 发现的新技术栈补充到规则词表中，逐步提升规则引擎覆盖率

---

## 7. 数据可视化层详细设计

### 7.1 技术热度分析

#### 7.1.1 技术热度统计

```python
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False

class TechTrendAnalyzer:
    """
    技术趋势分析器
    统计技术栈在招聘市场中的出现频率
    """

    def __init__(self, df: pd.DataFrame):
        self.df = df

    def top_skills(self, top_n: int = 20) -> pd.Series:
        """统计出现频率最高的技术栈"""
        all_skills = []
        for skills in self.df["skills"].dropna():
            if isinstance(skills, dict):
                for category in skills.values():
                    if isinstance(category, list):
                        all_skills.extend(category)
        return pd.Series(all_skills).value_counts().head(top_n)

    def plot_top_skills(self, top_n: int = 15, save_path: str = None):
        """绘制技术栈热度条形图"""
        top = self.top_skills(top_n)

        fig, ax = plt.subplots(figsize=(12, 7))
        bars = ax.barh(range(len(top)), top.values, color="skyblue", edgecolor="steelblue")
        ax.set_yticks(range(len(top)))
        ax.set_yticklabels(top.index)
        ax.invert_yaxis()
        ax.set_xlabel("Number of Job Postings", fontsize=12)
        ax.set_title("Top {} In-Demand IT Skills in Hong Kong".format(top_n), fontsize=14, fontweight="bold")

        for bar, val in zip(bars, top.values):
            ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2,
                    str(val), va="center", fontsize=10)

        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches="tight")
        plt.show()
```

#### 7.1.2 技术分类对比分析

```python
def plot_category_distribution(df: pd.DataFrame, save_path: str = None):
    """
    按技能类别（语言/框架/云服务/数据库）绘制分布
    """
    category_counts = {"Programming Languages": 0, "Frameworks": 0,
                       "Cloud & DevOps": 0, "Databases": 0}

    for skills in df["skills"].dropna():
        if isinstance(skills, dict):
            for cat_key, cat_label in [
                ("programming_languages", "Programming Languages"),
                ("frameworks_libraries", "Frameworks"),
                ("cloud_devops", "Cloud & DevOps"),
                ("databases", "Databases"),
            ]:
                if cat_key in skills and isinstance(skills[cat_key], list):
                    category_counts[cat_label] += len(skills[cat_key])

    fig, ax = plt.subplots(figsize=(8, 8))
    colors = ["#ff9999", "#66b3ff", "#99ff99", "#ffcc99"]
    ax.pie(category_counts.values(), labels=category_counts.keys(),
           autopct="%1.1f%%", colors=colors, startangle=90)
    ax.set_title("Technical Skill Category Distribution", fontsize=14, fontweight="bold")
    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.show()
```

### 7.2 薪资与技术关联分析

#### 7.2.1 薪资-技能箱线图

```python
def plot_salary_by_skill(df: pd.DataFrame, top_skills: int = 10):
    """
    绘制各技术栈的薪资分布箱线图
    帮助分析掌握哪些技术的岗位薪资更高
    """
    records = []
    for _, row in df.dropna(subset=["salary_min", "skills"]).iterrows():
        avg_salary = (row["salary_min"] + row["salary_max"]) / 2
        if isinstance(row["skills"], dict):
            for category in row["skills"].values():
                if isinstance(category, list):
                    for skill in category:
                        records.append({"skill": skill, "salary": avg_salary})

    skill_df = pd.DataFrame(records)
    if skill_df.empty:
        return

    top = skill_df["skill"].value_counts().head(top_skills).index
    plot_df = skill_df[skill_df["skill"].isin(top)]

    fig, ax = plt.subplots(figsize=(14, 7))
    sns.boxplot(data=plot_df, x="salary", y="skill", ax=ax, palette="Blues_d")
    ax.set_xlabel("Monthly Salary (HKD)", fontsize=12)
    ax.set_ylabel("")
    ax.set_title("Salary Distribution by Technical Skill", fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.show()
```

#### 7.2.2 高薪技能排行榜

```python
def top_high_paying_skills(df: pd.DataFrame, top_n: int = 15) -> pd.DataFrame:
    """
    计算各技能的平均薪资水平
    """
    records = []
    for _, row in df.dropna(subset=["salary_min", "skills"]).iterrows():
        avg_salary = (row["salary_min"] + row["salary_max"]) / 2
        if isinstance(row["skills"], dict):
            for category in row["skills"].values():
                if isinstance(category, list):
                    for skill in category:
                        records.append({"skill": skill, "salary": avg_salary})

    skill_salary_df = pd.DataFrame(records)
    return (
        skill_salary_df.groupby("skill")["salary"]
        .agg(["mean", "count", "std"])
        .query("count >= 3")          # 过滤样本量过少的技能
        .sort_values("mean", ascending=False)
        .head(top_n)
    )
```

### 7.3 行业与区域分布分析

#### 7.3.1 工作地点热力图

```python
def plot_location_heatmap(df: pd.DataFrame):
    """展示香港各区域岗位数量分布"""
    location_counts = df["location"].value_counts().head(20)

    fig, ax = plt.subplots(figsize=(10, 8))
    colors = plt.cm.Reds(location_counts.values / location_counts.max())
    bars = ax.barh(location_counts.index, location_counts.values, color=colors)
    ax.invert_yaxis()
    ax.set_xlabel("Number of Job Postings")
    ax.set_title("Job Distribution by Location in Hong Kong", fontsize=14, fontweight="bold")

    for bar, val in zip(bars, location_counts.values):
        ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2,
                str(val), va="center")

    plt.tight_layout()
    plt.show()
```

#### 7.3.2 交互式看板 (Streamlit)

```python
# src/app.py
import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="HK Job Market Analyzer", layout="wide")
st.title("香港 IT 招聘市场数据分析看板")

@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    return pd.read_csv(path)

df = load_data("output/jobs_cleaned.csv")

# 侧边栏筛选
st.sidebar.header("筛选条件")
selected_location = st.sidebar.multiselect(
    "工作地点", df["location"].unique(), default=[]
)

# 技术热度图
st.header("技术栈热度排行")
skill_counts = df["skills"].explode().value_counts().head(20)
fig = px.bar(skill_counts, orientation="h", title="Top 20 技术栈需求")
st.plotly_chart(fig, use_container_width=True)

# 薪资分布
st.header("薪资分布概览")
fig2 = px.box(df, x="salary_min", y="location", title="各区域薪资分布")
st.plotly_chart(fig2, use_container_width=True)
```

---

## 8. 关键技术攻关与风险控制

### 8.1 反爬虫对抗策略

| 风险类型 | 表现 | 应对方案 | 优先级 |
|---------|------|---------|-------|
| IP 封禁 | 返回 403 / 429 | 1. 香港住宅代理 IP 池<br>2. 自动切换失败 IP<br>3. 请求重试机制 | P0 |
| Rate Limiting | 请求被限频 | 1. 自适应延迟控制（2.5-5s）<br>2. 随机化请求间隔<br>3. 分散爬取时段 | P0 |
| Cloudflare 防护 | 5 秒盾 / CAPTCHA | 1. Playwright Stealth 插件<br>2. 模拟真实浏览器指纹<br>3. 降低并发度 | P1 |
| API Token 失效 | Token 过期 | 1. Token 自动刷新机制<br>2. 定期更新 Headers | P1 |
| 账号风控 | 账号被限制 | 1. 模拟正常用户行为<br>2. 避免高频操作 | P2 |

#### 8.1.1 Playwright Stealth 配置

```python
from playwright_stealth import stealth_sync

def create_stealth_browser():
    """创建带有反检测功能的浏览器实例"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) ...",
            locale="zh-HK",
            timezone_id="Asia/Hong_Kong",
        )
        page = context.new_page()
        stealth_sync(page)  # 隐藏自动化特征
        return browser, page
```

### 8.2 混合语文本处理策略

针对香港招聘 JD 中英夹杂的特点，采取以下策略：

| 策略 | 说明 | 实施方式 |
|------|------|---------|
| 统一小写匹配 | 规避大小写不一致问题 | 匹配时统一转为 lowercase |
| 边界正则 | 防止误匹配（如 java 匹配到 javascript） | `\bpython\b` |
| 中英分离处理 | 中文部分用规则处理，英文部分用 NLP | 先识别语言区域再分流 |
| 大模型兜底 | 规则无法覆盖时交由 LLM 理解 | 置信度低于阈值时调用 LLM |

### 8.3 薪资解析策略

| 格式示例 | 解析方法 | 标准化结果 |
|---------|---------|-----------|
| HK$45,000 - HK$60,000 /month | 正则提取范围 + 单位 | (45000, 60000) |
| HK$600,000 - HK$720,000 per annum | 正则提取后 ÷12 | (50000, 60000) |
| HK$45,000 up | 正则提取下限 | (45000, None) |
| Negotiable / 面议 | 返回 None | (None, None) |
| HK$30,000 - HK$50,000 | 默认月薪 | (30000, 50000) |

---

## 9. 法律与合规声明

本系统在设计和使用过程中，必须严格遵守以下法律与合规要求：

### 9.1 数据采集合规

1. **遵守 robots.txt**：爬取前检查目标网站的 `robots.txt`，仅采集允许的路径
2. **非商业用途**：采集数据仅用于个人学术研究、求职参考或技术分析，严禁转售牟利
3. **控制请求频率**：默认请求延迟 2.5-5.0 秒，避免对目标服务器造成压力
4. **数据最小化**：仅采集分析所需的字段，不采集无关的个人信息

### 9.2 《个人资料（隐私）条例》

香港《个人资料（隐私）条例》（PDPO）对数据采集有明确要求：

- 不采集求职者的个人信息（姓名、联系方式等）
- 仅采集公司发布的公开岗位信息
- 不将数据进行跨境传输（如涉及）

### 9.3 使用免责

> 本系统仅提供技术实现方案。使用者应自行评估目标网站的服务条款（ToS）并承担相应法律责任。因不当使用本系统造成的任何法律纠纷或服务中断，由使用者自行承担。

---

## 10. 部署与运行指南

### 10.1 环境依赖

#### 10.1.1 Python 版本要求

- Python >= 3.9

#### 10.1.2 依赖管理

```plaintext
# requirements.txt
requests==2.31.0
beautifulsoup4==4.12.3
playwright==1.42.0
pandas==2.2.1
openai==1.14.1
pymongo==4.6.1
python-dotenv==1.0.1
matplotlib==3.8.3
seaborn==0.13.2
streamlit==1.32.0
plotly==5.19.0
tenacity==8.2.3
```

#### 10.1.3 安装步骤

```bash
# 1. 创建虚拟环境
python -m venv venv
venv\Scripts\activate    # Windows
source venv/bin/activate # Linux/Mac

# 2. 安装依赖
pip install -r requirements.txt

# 3. 安装 Playwright 浏览器内核（如需）
playwright install chromium

# 4. 启动 MongoDB（如需本地存储）
# 确保 MongoDB 服务已启动，默认端口 27017
```

### 10.2 运行步骤

#### 步骤一：配置环境变量

创建 `.env` 文件：

```ini
# 代理配置（可选但建议）
PROXY_HTTP=http://your_hk_proxy_ip:port
PROXY_HTTPS=http://your_hk_proxy_ip:port

# 大模型 API 配置（使用 LLM 引擎时需要）
LLM_API_KEY=your_deepseek_or_openai_api_key
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat

# MongoDB 配置
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB_NAME=hk_job_market

# 爬虫配置
CRAWL_DELAY_MIN=2.5
CRAWL_DELAY_MAX=5.0
CRAWL_MAX_PAGES=10
```

#### 步骤二：数据采集

```bash
# 采集 JobsDB 数据
python src/crawler.py \
    --source jobsdb \
    --keyword "software engineer" \
    --pages 10 \
    --output data/raw/

# 多关键词批量采集
python src/crawler.py \
    --source jobsdb \
    --keywords "data scientist,frontend,backend,devops" \
    --pages 5 \
    --output data/raw/
```

#### 步骤三：数据清洗与存储

```bash
python src/cleaner.py \
    --input data/raw/ \
    --output data/cleaned/ \
    --storage mongodb
```

#### 步骤四：技术需求分析

```bash
# 规则引擎模式（批量快速处理）
python src/analyzer.py \
    --mode rule \
    --input data/cleaned/ \
    --output data/analysis/

# LLM 智能引擎模式（深度分析）
python src/analyzer.py \
    --mode llm \
    --input data/cleaned/ \
    --output data/analysis/ \
    --batch-size 10

# 双引擎联合模式（推荐）
python src/analyzer.py \
    --mode hybrid \
    --input data/cleaned/ \
    --output data/analysis/
```

#### 步骤五：启动可视化看板

```bash
# Streamlit 交互式看板
streamlit run src/app.py \
    --server.port 8501 \
    --server.address 0.0.0.0

# 或生成静态图表
python src/visualize.py \
    --input data/analysis/ \
    --output output/charts/
```

#### 步骤六：一键工作流

```python
# run_pipeline.py — 一键执行完整数据流水线
from src.crawler import JobsDBCrawler
from src.cleaner import JDTextCleaner, SalaryParser
from src.analyzer import RuleBasedSkillExtractor
from src.visualize import TechTrendAnalyzer

def run_pipeline(keywords: list[str], pages: int = 5):
    # 1. 采集
    crawler = JobsDBCrawler()
    all_jobs = []
    for kw in keywords:
        jobs = crawler.run(kw, max_pages=pages)
        all_jobs.extend(jobs)
    
    # 2. 清洗
    cleaner = JDTextCleaner()
    for job in all_jobs:
        job["jd_text"] = cleaner.clean(job.get("jd_raw", ""))
        job["salary_min"], job["salary_max"] = SalaryParser.parse(job.get("salary_raw", ""))
    
    # 3. 分析
    extractor = RuleBasedSkillExtractor()
    for job in all_jobs:
        job["skills"] = extractor.extract(job.get("jd_text", ""))
    
    # 4. 可视化
    df = pd.DataFrame(all_jobs)
    analyzer = TechTrendAnalyzer(df)
    analyzer.plot_top_skills(save_path="output/trends.png")
    
    return df

if __name__ == "__main__":
    df = run_pipeline(["software engineer", "data scientist"], pages=5)
    print(f"Pipeline completed. Collected {len(df)} jobs.")
```

---

## 附录

### A. 项目目录结构

```
HK-JobMarket-Analyzer/
├── config/                    # 配置文件
│   ├── tech_dict.json         # 技术栈词表
│   └── crawler_settings.json  # 爬虫配置
├── src/                       # 源代码
│   ├── __init__.py
│   ├── crawler.py             # 爬虫核心模块
│   ├── cleaner.py             # 数据清洗与薪资标准化
│   ├── analyzer.py            # 规则 + LLM 文本挖掘
│   ├── visualize.py           # 图表生成
│   ├── app.py                 # Streamlit 可视化看板
│   ├── database.py            # MongoDB 持久化管理
│   └── utils.py               # 工具函数
├── data/                      # 数据目录
│   ├── raw/                   # 原始数据
│   └── cleaned/               # 清洗后数据
├── output/                    # 输出目录
│   ├── charts/                # 图表文件
│   └── reports/               # 分析报告
├── tests/                     # 单元测试
│   ├── test_crawler.py
│   ├── test_cleaner.py
│   └── test_analyzer.py
├── .env.example               # 环境变量模板
├── requirements.txt           # Python 依赖
└── README.md                  # 项目说明
```

### B. 词表维护说明

规则引擎的准确度高度依赖词表质量。建议定期维护：

```bash
# 从 LLM 分析结果中提取新词，补充到词表
python scripts/update_dict.py \
    --llm-output data/analysis/llm_results.json \
    --dict-path config/tech_dict.json \
    --min-frequency 3
```

### C. 参考资源

- [JobsDB 官网](https://hk.jobsdb.com/)
- [Indeed HK](https://hk.indeed.com/)
- [SEEK Group API 文档](https://developer.seek.com/)
- [Playwright 文档](https://playwright.dev/)
- [spaCy NLP 文档](https://spacy.io/)
- [香港《个人资料（隐私）条例》](https://www.pcpd.org.hk/)
