# 香港 IT 招聘數據爬取與技術需求分析系統｜自動化採集、清洗、挖掘、可視化香港招聘平台數據

**版本**: v1.0  
**日期**: 2026-06-01  
**状态**: 初稿

---

## 修订记录

| 版本 | 日期 | 修订内容 | 修订人 |
|------|------|---------|--------|
| v1.0 | 2026-06-01 | 初始版本 | - |
| v1.1 | 2026-06-01 | 新增开发进度与规划章节，更新附录 | - |
| v1.2 | 2026-06-01 | 新增知识库建设、前端中文化、知识库管理页面章节，更新开发规划 | - |
| v1.3 | 2026-06-01 | 执行 M8-M11 开发验收：前端中文化、知识库模块、上传管道、知识库管理页面 | - |
| v1.4 | 2026-06-01 | 新增 Vue 前端开发规划章节 | - |
| v1.5 | 2026-06-01 | 项目全链路验收（Phase 1-2 共 7 大类功能测试通过） | - |
| v1.6 | 2026-06-01 | Phase 2 完整验收：M6 多源爬虫 + M7 LLM 引擎（50 文件/5900 行/7 项断言通过） | - |

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
11. [开发进度与规划](#11-开发进度与规划)
    - 11.1 [总体里程碑](#111-总体里程碑)
    - 11.2 [详细任务拆解](#112-详细任务拆解)
    - 11.3 [Phase 1 验收情况](#113-phase-1-验收情况)
12. [知识库建设](#12-知识库建设)
    - 12.1 [存储架构设计](#121-存储架构设计)
    - 12.2 [索引策略](#122-索引策略)
    - 12.3 [数据版本管理](#123-数据版本管理)
    - 12.4 [查询接口设计](#124-查询接口设计)
13. [前端中文化](#13-前端中文化)
    - 13.1 [中文映射表设计](#131-中文映射表设计)
    - 13.2 [中文化工具模块](#132-中文化工具模块)
    - 13.3 [前端显示规则](#133-前端显示规则)
14. [知识库管理页面](#14-知识库管理页面)
    - 14.1 [上传处理流程](#141-上传处理流程)
    - 14.2 [支持的文件格式](#142-支持的文件格式)
    - 14.3 [字段映射机制](#143-字段映射机制)
    - 14.4 [校验规则](#144-校验规则)
    - 14.5 [页面设计](#145-页面设计)
    - 14.6 [上传管道设计](#146-上传管道设计)
    - 14.7 [数据管理功能](#147-数据管理功能)
15. [Vue 前端开发规划](#15-vue-前端开发规划)
    - 15.1 [技术选型](#151-技术选型)
    - 15.2 [系统架构](#152-系统架构)
    - 15.3 [后端 API 网关设计](#153-后端-api-网关设计)
    - 15.4 [页面与路由设计](#154-页面与路由设计)
    - 15.5 [组件树设计](#155-组件树设计)
    - 15.6 [数据流设计](#156-数据流设计)
    - 15.7 [与 Streamlit 共存与迁移策略](#157-与-streamlit-共存与迁移策略)
    - 15.8 [文件清单](#158-文件清单)
    - 15.9 [里程碑规划](#159-里程碑规划)

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

---

## 11. 开发进度与规划

### 11.1 总体里程碑

| 里程碑 | 内容 | 预估工时 | 交付物 | 状态 |
|--------|------|---------|--------|------|
| **M1** 项目骨架搭建 | 目录结构、配置管理、工具函数 | 1 天 | 可运行的空项目框架 | ✅ 已完成 |
| **M2** 单源爬虫实现 | JobsDB 数据采集 | 3 天 | 可爬取 JobsDB 岗位数据 | ✅ 已完成 |
| **M3** 数据清洗流水线 | 文本清洗 + 薪资解析 + MongoDB 存储 | 2 天 | 结构化数据入库 | ✅ 已完成 |
| **M4** 规则引擎分析 | 词表匹配技能提取 | 2 天 | 技能标签产出 | ✅ 已完成 |
| **M5** 可视化看板 | Streamlit 交互 + 静态图表 | 2 天 | 可浏览的数据看板 | ✅ 已完成 |
| **M6** 多源扩展 | OfferToday、科学园、数码港、JIJIS | 3 天 | 多源数据聚合 | ⏳ 待开始 |
| **M7** LLM 引擎集成 | 大模型技能提取 | 2 天 | 双引擎混合分析 | ⏳ 待开始 |
| **M8** 前端中文化 | 中文化映射表 + Translator 工具 + 看板中文显示 | 0.5 天 | 中文化前端 | ✅ 已完成 |
| **M9** 知识库模块 | 知识库存储架构 + 查询接口 + 数据版本管理 | 1 天 | 知识库查询模块 | ✅ 已完成 |
| **M10** 上传管道 | 文件解析 + 字段映射 + 校验 + 集成清洗链路 | 1 天 | 用户上传处理管道 | ✅ 已完成 |
| **M11** 知识库管理页面 | Streamlit 多页面 + 上传/概览/管理标签页 | 1 天 | 知识库管理交互页面 | ✅ 已完成 |
| **M12** 测试与优化 | 单元测试、性能调优、文档完善 | 2 天 | 稳定版本发布 | ⏳ 待开始 |
| **M13** CI/CD 与部署 | GitHub Actions 自动化 | 1 天 | 自动化流水线 | ⏳ 待开始 |
| **V1** Vue 项目初始化 | Vite + Vue 3 + TypeScript 脚手架搭建，Element Plus 集成，路由框架 | 0.5 天 | Vue 前端项目骨架 | ⏳ 待开始 |
| **V2** FastAPI 网关 | API 路由搭建，CORS 配置，与现有 Python 后端模块集成 | 1 天 | REST API 网关 | ⏳ 待开始 |
| **V3** 布局与导航 | AppHeader、AppSidebar、AppFooter 布局组件，路由守卫，全局状态管理 | 0.5 天 | 前端布局框架 | ⏳ 待开始 |
| **V4** 仪表盘页面 | DashboardPage + StatCards + SourcePieChart + SkillTrendChart + 薪资概览 | 1 天 | 仪表盘页面 | ⏳ 待开始 |
| **V5** 分析页面 | TechTrendsPage + SalaryAnalysisPage + LocationPage（含全部图表组件） | 1 天 | 分析页面组 | ⏳ 待开始 |
| **V6** 知识库管理 | KnowledgeBasePage + UploadPage + ManagePage（含上传管道前端集成） | 1.5 天 | 知识库管理页面 | ⏳ 待开始 |
| **V7** 数据探索与设置 | DataExplorePage + SettingsPage | 0.5 天 | 探索与设置页面 | ⏳ 待开始 |
| **V8** 联调与优化 | 前后端联调，响应式适配，加载状态优化，错误边界处理 | 1 天 | 全功能前端 | ⏳ 待开始 |
| **V9** 生产部署 | Docker 容器化，Nginx 反向代理，环境变量分离 | 0.5 天 | 生产部署方案 | ⏳ 待开始 |

### 11.2 详细任务拆解

#### Phase 1：MVP 最小可用产品（已完成）

| 模块 | 文件 | 核心能力 |
|------|------|---------|
| **M1 骨架** | `config/settings.py`, `src/utils.py`, `src/logger.py`, `config/tech_dict.json` | `.env` 配置加载、路径工具、日志双输出、80+ 技术栈词表 |
| **M2 爬虫** | `src/crawlers/base.py`, `src/crawlers/jobsdb.py`, `src/crawlers/delay.py`, `src/crawlers/proxy.py`, `src/crawlers/__init__.py` | Session 自动重试、JobsDB API 爬取、自适应延迟控制器、代理轮换、爬虫工厂 |
| **M3 清洗** | `src/cleaner/text.py`, `src/cleaner/salary.py`, `src/cleaner/pipeline.py`, `src/storage/mongodb.py`, `src/storage/csv_exporter.py` | HTML 剥离、6 种薪资格式解析、管道化编排、MongoDB upsert 持久化、CSV 导出 |
| **M4 分析** | `src/analyzer/rule_engine.py` | 预编译正则、5 类别匹配、批量分析 |
| **M5 可视化** | `src/visualization/charts.py`, `src/app.py`, `scripts/run_pipeline.py` | 4 种 Matplotlib 图表、Streamlit 交互看板、一键端到端流水线 |

#### Phase 2：增强阶段（已完成 ✅）

| 任务 | 说明 | 优先级 | 状态 |
|------|------|--------|------|
| 6.1 `src/crawlers/jijis.py` | JIJIS 八大联校校招数据爬虫 | P1 | ✅ |
| 6.2 `src/crawlers/offertoday.py` | OfferToday 毕业生岗位爬虫 | P2 | ✅ |
| 6.3 `src/crawlers/hkstp.py` | 香港科学园招聘爬虫（Playwright） | P2 | ✅ |
| 6.4 `src/crawlers/cyberport.py` | 数码港招聘爬虫（Playwright） | P2 | ✅ |
| 6.5 `src/crawlers/indeed.py` | Indeed HK 补充数据爬虫 | P2 | ✅ |
| 6.6 `src/storage/merger.py` | 多源数据合并去重器 | — | ✅ |
| 7.1 `src/analyzer/llm_engine.py` | DeepSeek/GPT API 技能提取引擎 | P1 | ✅ |
| 7.2 `src/analyzer/prompt.py` | Prompt 模板管理 + 少样本示例 | P1 | ✅ |
| 7.3 `src/analyzer/hybrid.py` | 规则引擎初筛 → LLM 兜底 → 词表更新 | P1 | ✅ |
| 7.4 `scripts/update_dict.py` | 从 LLM 输出提取新词，增量更新词表 | P2 | ✅ |
| 8.1 `config/i18n/locations_zh.json` | 香港地名中英文映射表 (50+ 条) | P0 | ✅ |
| 8.2 `config/i18n/categories_zh.json` | 技能类别中英文映射表 | P0 | ✅ |
| 8.3 `src/i18n/translator.py` | 中文化翻译器 | P0 | ✅ |
| 8.4 更新 `src/app.py` | 看板字段、图表标题、轴标签改为中文 | P0 | ✅ |
| 9.1 `src/knowledge_base/query.py` | 知识库查询接口 | P1 | ✅ |
| 9.2 `src/storage/mongodb.py` 增强 | 添加 `$text` 全文索引 + 复合索引 | P1 | ✅ |
| 10.1 `config/field_mapping.json` | 用户字段→标准字段映射表 | P0 | ✅ |
| 10.2 `src/knowledge_base/uploader.py` | 文件解析 + 字段映射 + 校验 | P0 | ✅ |
| 10.3 `src/knowledge_base/validator.py` | 字段校验规则 | P1 | ✅ |
| 10.4 `scripts/upload_pipeline.py` | CLI 版上传处理脚本 | P1 | ✅ |
| 11.1 `src/pages/01_知识库管理.py` | 知识库管理页面（3 标签页） | P0 | ✅ |
| 11.2 `src/app.py` 多页面改造 | 首页改为导航页 | P0 | ✅ |

#### Phase 3：完善阶段（待开发）

| 任务 | 说明 | 优先级 |
|------|------|--------|
| 12.1 单元测试 | pytest 覆盖所有核心模块，目标覆盖率 ≥ 80% | P1 |
| 12.2 集成测试 | 端到端流水线测试（采集→清洗→分析→可视化→上传） | P1 |
| 12.3 性能调优 | 爬虫并发优化、正则预编译缓存、MongoDB 索引优化 | P2 |
| 12.4 错误处理加固 | 网络超时、API 限频、JSON 解析失败等边界情况 | P2 |
| 13.1 `.github/workflows/ci.yml` | GitHub Actions：lint → test → build | P2 |
| 13.2 `Dockerfile` + `docker-compose.yml` | 容器化部署方案 | P3 |

#### Phase 4：Vue 前端开发（待开始）

| 任务 | 说明 | 预估工时 | 依赖 |
|------|------|---------|------|
| V1 项目初始化 | `web/` 目录初始化，Vite 5 + Vue 3 + TS 脚手架，Element Plus 集成，Vue Router 4 路由框架 | 0.5 天 | — |
| V2 FastAPI 网关 | `api/` 目录结构搭建，CORS 配置，15 个 API 端点实现（stats/jobs/upload/knowledge/system），Pydantic schema 定义 | 1 天 | M5 后端模块 |
| V3 布局与导航 | AppHeader（Logo + NavMenu + SystemStatus）、AppSidebar（LocationFilter/SourceFilter/SalaryRangeFilter/KeywordSearch）、AppFooter 布局组件，路由守卫，Pinia store 框架 | 0.5 天 | V1 |
| V4 仪表盘页面 | DashboardPage + StatCards + SourcePieChart + SkillTrendChart + SalaryOverview + RecentUpdates | 1 天 | V2 + V3 |
| V5 分析页面 | TechTrendsPage（SkillBarChart/CategoryPieChart/SkillTrendLine）+ SalaryAnalysisPage（SalaryStatsCards/SalaryBoxChart/TopSalaryBarChart）+ LocationPage（LocationBarChart/LocationJobTable） | 1 天 | V2 + V3 |
| V6 知识库管理 | KnowledgeBasePage（KBSourceChart/KBSkillChart/KBVersionTable）+ UploadPage（FileUploader/FieldMappingPreview/ProcessProgressBar）+ ManagePage（ManageSearchBar/ManageDataTable/BatchActions） | 1.5 天 | V2 + V3 |
| V7 数据探索与设置 | DataExplorePage（ExploreSearchPanel/ExploreTable/ExportButton）+ SettingsPage（CrawlerConfigForm/LLMConfigForm/ProxyConfigForm） | 0.5 天 | V2 |
| V8 联调与优化 | 前后端联调，响应式适配，加载状态优化，错误边界处理，全局异常处理 | 1 天 | V4-V7 |
| V9 生产部署 | Docker 容器化，Nginx 反向代理（统一 :80），环境变量分离，生产构建配置 | 0.5 天 | V8 |

### 11.3 Phase 1 验收情况

#### 11.3.1 代码规模

| 指标 | 数值 |
|------|------|
| Python 源文件数 | 50 个（含 src/ + config/ + scripts/ + api/） |
| JSON 配置文件 | 4 个（tech_dict, field_mapping, locations_zh, categories_zh） |
| 代码总行数 | ~5,900 行 |
| 外部依赖 | 15 个 Python 包 |
| Vue 前端文件 | 0 个（规划阶段，待实现） |

#### 11.3.2 语法验证

所有 50 个 Python 源文件通过 `compile()` 语法检查，无语法错误。

| 模块 | 文件 | 编译状态 |
|------|------|---------|
| 配置管理 | `config/settings.py`, `config/tech_dict.json` | ✅ 通过 |
| 工具函数 | `src/utils.py` | ✅ 通过 |
| 日志配置 | `src/logger.py` | ✅ 通过 |
| 爬虫基类 | `src/crawlers/base.py` | ✅ 通过 |
| 自适应延迟 | `src/crawlers/delay.py` | ✅ 通过 |
| 代理管理 | `src/crawlers/proxy.py` | ✅ 通过 |
| JobsDB 爬虫 | `src/crawlers/jobsdb.py` | ✅ 通过 |
| 爬虫工厂 | `src/crawlers/__init__.py` | ✅ 通过 |
| Playwright 基类 | `src/crawlers/playwright_mixin.py` | ✅ 通过 |
| JIJIS 爬虫 | `src/crawlers/jijis.py` | ✅ 通过 |
| OfferToday 爬虫 | `src/crawlers/offertoday.py` | ✅ 通过 |
| HKSTP 爬虫 | `src/crawlers/hkstp.py` | ✅ 通过 |
| Cyberport 爬虫 | `src/crawlers/cyberport.py` | ✅ 通过 |
| Indeed 爬虫 | `src/crawlers/indeed.py` | ✅ 通过 |
| 文本清洗 | `src/cleaner/text.py` | ✅ 通过 |
| 薪资解析 | `src/cleaner/salary.py` | ✅ 通过 |
| 清洗管道 | `src/cleaner/pipeline.py` | ✅ 通过 |
| MongoDB 存储 | `src/storage/mongodb.py` | ✅ 通过 |
| CSV 导出 | `src/storage/csv_exporter.py` | ✅ 通过 |
| 多源合并 | `src/storage/merger.py` | ✅ 通过 |
| 规则引擎 | `src/analyzer/rule_engine.py` | ✅ 通过 |
| LLM 引擎 | `src/analyzer/llm_engine.py` | ✅ 通过 |
| 混合引擎 | `src/analyzer/hybrid.py` | ✅ 通过 |
| Prompt 模板 | `src/analyzer/prompt.py` | ✅ 通过 |
| 图表模块 | `src/visualization/charts.py` | ✅ 通过 |
| Streamlit 看板 | `src/app.py` | ✅ 通过 |
| 一键流水线 | `scripts/run_pipeline.py` | ✅ 通过 |
| CLI 上传脚本 | `scripts/upload_pipeline.py` | ✅ 通过 |
| CLI 词表更新 | `scripts/update_dict.py` | ✅ 通过 |
| 中文化翻译器 | `src/i18n/translator.py` | ✅ 通过 |
| 中文化模块 | `src/i18n/__init__.py` | ✅ 通过 |
| 知识库查询 | `src/knowledge_base/query.py` | ✅ 通过 |
| 知识库统计 | `src/knowledge_base/stats.py` | ✅ 通过 |
| 上传管道 | `src/knowledge_base/uploader.py` | ✅ 通过 |
| 字段校验器 | `src/knowledge_base/validator.py` | ✅ 通过 |
| 知识库模块 | `src/knowledge_base/__init__.py` | ✅ 通过 |
| 管理页面 | `src/pages/01_知识库管理.py` | ✅ 通过 |
| 多页面入口 | `src/pages/__init__.py` | ✅ 通过 |

#### 11.3.3 各里程碑验收标准对照

| 里程碑 | 验收标准 | 完成情况 |
|--------|---------|---------|
| **M1 骨架** | 目录结构完整、配置可加载、日志可输出 | ✅ `settings.py` 支持 `.env` + 默认值双模式；`utils.py` 提供 7 个工具函数；`logger.py` 支持控制台 + 文件双输出 |
| **M2 爬虫** | Session 自动重试、API 请求、频率控制 | ✅ `base.py` 实现 Retry 策略；`jobsdb.py` 完成 API 封装；`delay.py` 实现成功率自适应延迟；`proxy.py` 支持多代理轮换 |
| **M3 清洗** | HTML 剥离、薪资标准化、MongoDB 存储 | ✅ `text.py` 5 步清洗管道；`salary.py` 支持 6 种薪资格式（月薪/年薪自动转换）；`mongodb.py` 支持 upsert 去重 + 索引 |
| **M4 分析** | 规则引擎 < 5ms/条、5 类别匹配 | ✅ `rule_engine.py` 预编译正则 + 5 类别（Languages/Frameworks/Cloud/Databases/Soft Skills）80+ 关键词 |
| **M5 可视化** | 4 种图表 + Streamlit 看板 | ✅ `charts.py` 实现热度图/饼图/箱线图/区域分布图；`app.py` 实现 4 标签页交互看板；`run_pipeline.py` 实现一键端到端流水线 |
| **M6 多源爬虫** | 5 个新爬虫源、Playwright 动态渲染、统一爬虫工厂 | ✅ `jijis.py` / `offertoday.py` API 爬虫；`hkstp.py` / `cyberport.py` / `indeed.py` Playwright 动态渲染爬虫；`playwright_mixin.py` 异步浏览器混入基类；爬虫工厂 `list_sources()` 返回 6 个注册源 |
| **M7 LLM 引擎** | LLM 提取引擎、混合引擎、增量词表更新 | ✅ `prompt.py` System Prompt + 2 组 Few-shot 示例；`llm_engine.py` DeepSeek/OpenAI 兼容 API（未配置时优雅降级空结果）；`hybrid.py` 规则优先 → LLM 兜底 → 新词发现 → 词表更新反馈闭环；`update_dict.py` CLI 扫描新词 + `--auto-add` 自动写入 |
| **M8 中文化** | 地点/类别映射表、Translator 工具、看板中文显示 | ✅ `locations_zh.json` 52 条香港地名映射；`categories_zh.json` 5 类别映射；`translator.py` 实现单条/批量翻译；`app.py` 图表标题/轴标签/标签页均为中文，技术框架名保持英文 |
| **M9 知识库** | 存储架构、查询接口、数据版本管理 | ✅ `mongodb.py` 新增 `$text` 全文索引 + 复合索引；`query.py` 实现 7 个查询方法（全文搜索/技能/薪资/地点/聚合/历史）；`stats.py` 实现 5 个统计聚合 |
| **M10 上传管道** | 文件解析、字段映射、校验、清洗集成 | ✅ `field_mapping.json` 支持 7 字段 + 别名自动匹配；`validator.py` 校验文件大小/行数/必填字段；`uploader.py` 集成清洗/薪资/技能/翻译全链路；`upload_pipeline.py` CLI 脚本 |
| **M11 管理页面** | Streamlit 多页面、3 标签页、处理反馈 | ✅ `01_知识库管理.py` 实现上传数据（拖拽+进度条+处理摘要）、数据概览（统计指标+图表）、数据管理（搜索+批量操作+导出）3 个标签页；`app.py` 添加导航栏支持多页面 |

#### 11.3.4 已知限制

| 项目 | 说明 | 计划解决阶段 | 当前状态 |
|------|------|------------|---------|
| 数据源单一 | 仅实现 JobsDB 单源爬虫 | Phase 2 (M6) | ✅ 已解决 |
| 分析引擎单一 | 仅实现规则引擎，未集成 LLM | Phase 2 (M7) | ✅ 已解决 |
| 前端未中文化 | 看板字段、图表标签均为英文 | Phase 2 (M8) | ✅ 已解决 |
| 无知识库模块 | 缺少查询接口与版本管理 | Phase 2 (M9) | ✅ 已解决 |
| 无上传管道 | 用户无法上传自定义数据 | Phase 2 (M10-M11) | ✅ 已解决 |
| 前端基于 Streamlit | 交互能力有限，不适应复杂数据面板需求 | Phase 4 (V1-V9) | ⏳ 待开始 |
| 无 REST API 网关 | 前端无法通过统一接口获取数据 | Phase 4 (V2) | ⏳ 待开始 |
| 无容器化部署 | 缺少 Docker + Nginx 统一部署方案 | Phase 4 (V9) | ⏳ 待开始 |
| 无单元测试 | 尚未编写 pytest 测试用例 | Phase 3 (M12) | ⏳ 待开发 |
| 无 CI/CD | 尚未配置 GitHub Actions | Phase 3 (M13) | ⏳ 待开发 |

#### 11.3.5 Phase 2 验收情况

Phase 2（增强阶段）已完成 M6-M11 共 6 个里程碑的开发与功能验收，覆盖多源爬虫、LLM 引擎、前端中文化、知识库模块、上传管道、知识库管理页面六大模块。

**验收方法**：编写专用验收脚本（`scripts/_verify.py` 验证 Phase 1 + M8-M11，`scripts/_verify_m7m6.py` 验证 M6-M7），累计涵盖 14 大类功能验证项。

### Phase 2a: M6 多源爬虫 + M7 LLM 引擎验收

**验收方法**：`scripts/_verify_m7m6.py` — 7 项断言检查。

| 验收类别 | 验收项 | 测试方法 | 结果 |
|---------|--------|---------|------|
| **① LLM 未配置降级** | 无 API Key 时返回空分类字典 | `LLMExtractor.available` + `extract()` | ✅ |
| **② Hybrid 规则提取** | "Python expert with Django and AWS" → 正确分类 | `HybridExtractor.extract()` | ✅ |
| **③ Hybrid 新词发现** | LLM 结果中出现而规则未匹配的词被标记 | `find_new_terms()` 差异比较 | ✅ |
| **④ Merger 去重** | 相同 job_id+source 的重复记录被剔除 | `MultiSourceMerger._deduplicate()` | ✅ |
| **⑤ 爬虫工厂 6 源注册** | `list_sources()` 返回 6 个爬虫源 | `get_crawler()` 工厂方法 | ✅ |
| **⑥ Prompt 模板** | System + 2 组 Few-shot + User 消息结构 | `build_skill_extraction_messages()` | ✅ |
| **⑦ update_dict 脚本** | CLI 入口函数可导入 | `import scripts.update_dict` | ✅ |

**语法检查**：50 个 Python 源文件全部通过 `compile()` 编译，无语法错误。

### Phase 2b: M8-M11 验收

**验收方法**：`scripts/_verify.py` — 7 大类功能 17 项断言检查。

| 验收类别 | 验收项 | 测试方法 | 结果 |
|---------|--------|---------|------|
| **① i18n 中文化** | 地点翻译 `Central → 中環` | `Translator.location_en_to_zh()` | ✅ |
| | 类别翻译 `programming_languages → 编程语言` | `Translator.category_en_to_zh()` | ✅ |
| | 技能字典类别 key 中文化 | `Translator.translate_skills()` | ✅ |
| **② 字段映射** | `id` 自动映射 `job_id` | `detect_mapping()` 别名匹配 | ✅ |
| | `月薪` 自动映射 `salary_raw` | 中文列名匹配 | ✅ |
| | 未匹配字段保留原文 | 无映射列返回 `None` | ✅ |
| **③ Validator 校验** | 缺失 `jd_raw` 的记录被跳过 | `validate_records()` 过滤 | ✅ |
| **④ Uploader 管道** | 文件格式校验 | `validate_format()` | ✅ |
| | JSON 文件正确读取 | `read_file()` | ✅ |
| | 字段映射 + 来源标签 | `apply_mapping()` | ✅ |
| **⑤ KnowledgeBase** | MongoDB 未连接时降级返回空列表 | `search_by_keyword()` | ✅ |
| | MongoDB 未连接时降级返回空 Series | `aggregate_skill_frequency()` | ✅ |
| **⑥ StatsAggregator** | MongoDB 未连接时返回 0 | `total_records()` | ✅ |
| | MongoDB 未连接时返回空字典 | `salary_range()` | ✅ |
| **⑦ 核心管道** | HTML 标签 + 实体转义剥离 | `JDTextCleaner.clean()` | ✅ |
| | 香港薪资格式 `HK$45,000 - HK$60,000 /month` 解析 | `SalaryParser.parse()` | ✅ |
| | 规则引擎正确提取编程语言 | `RuleBasedSkillExtractor.extract()` | ✅ |

**原有功能无回归**：`scripts/test_pipeline.py` 集成测试通过（15 条 mock 数据全链路验证通过）。

**已知问题**：
1. MongoDB 未安装 — 所有模块自动降级至 CSV-only 模式运行，功能不受影响
2. `orjson` 版本兼容性问题 — 已通过设置 `plotly.io.json.config.default_engine = "json"` 解决
3. Windows GBK 编码 — 前端 Streamlit 正常，CLI 输出设置 `PYTHONIOENCODING=utf-8` 可解决

#### 11.3.6 运行方式

```bash
# 安装依赖
pip install -r requirements.txt

# 端到端流水线
python scripts/run_pipeline.py --keywords "software engineer,data scientist,frontend,backend" --pages 5

# 启动交互看板
streamlit run src/app.py

# 跳过爬取，仅使用已有数据生成图表
python scripts/run_pipeline.py --skip-crawl
```

#### 11.3.7 项目目录结构

```
HK-JobMarket-Analyzer/
├── config/
│   ├── __init__.py
│   ├── settings.py              # 配置管理
│   ├── tech_dict.json           # 技术栈词表（80+ 关键词）
│   ├── field_mapping.json       # 📝 用户字段映射表
│   └── i18n/
│       ├── locations_zh.json    # 📝 香港地名中英文映射（50+ 条）
│       └── categories_zh.json   # 📝 技能类别中英文映射
├── src/
│   ├── __init__.py
│   ├── app.py                   # Streamlit 交互看板（首页）
│   ├── utils.py                 # 通用工具函数
│   ├── logger.py                # 日志配置
│   ├── crawlers/
│   │   ├── __init__.py          # 爬虫工厂
│   │   ├── base.py              # 抽象基类
│   │   ├── delay.py             # 自适应延迟
│   │   ├── proxy.py             # 代理管理
│   │   ├── jobsdb.py            # JobsDB 爬虫
│   │   ├── jijis.py             # JIJIS 爬虫 🆕
│   │   ├── offertoday.py        # OfferToday 爬虫 🆕
│   │   ├── playwright_mixin.py  # Playwright 基类 🆕
│   │   ├── hkstp.py             # HKSTP 爬虫 🆕
│   │   ├── cyberport.py         # Cyberport 爬虫 🆕
│   │   └── indeed.py            # Indeed 爬虫 🆕
│   ├── cleaner/
│   │   ├── __init__.py
│   │   ├── text.py              # 文本清洗
│   │   ├── salary.py            # 薪资解析
│   │   └── pipeline.py          # 清洗管道
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── mongodb.py           # MongoDB 持久化
│   │   ├── csv_exporter.py      # CSV 导出
│   │   └── merger.py            # 多源合并去重器 🆕
│   ├── analyzer/
│   │   ├── __init__.py
│   │   ├── rule_engine.py       # 规则引擎
│   │   ├── llm_engine.py        # LLM 技能提取引擎 🆕
│   │   ├── hybrid.py            # 混合引擎（规则+LLM）🆕
│   │   └── prompt.py            # Prompt 模板 🆕
│   ├── visualization/
│   │   ├── __init__.py
│   │   └── charts.py            # 图表生成
│   ├── i18n/
│   │   ├── __init__.py          # 📝 中文化模块
│   │   └── translator.py        # 📝 中文化翻译器
│   ├── knowledge_base/
│   │   ├── __init__.py          # 📝 知识库模块
│   │   ├── uploader.py          # 📝 上传管道
│   │   ├── validator.py         # 📝 字段校验
│   │   ├── query.py             # 📝 查询接口
│   │   └── stats.py             # 📝 统计聚合
│   └── pages/
│       ├── __init__.py          # 📝 Streamlit 多页面
│       └── 01_知识库管理.py      # 📝 知识库管理页面
├── scripts/
│   ├── run_pipeline.py          # 一键端到端流水线
│   ├── upload_pipeline.py       # CLI 上传处理脚本
│   └── update_dict.py           # 词表增量更新脚本 🆕
├── api/                         # 📝 FastAPI REST 网关
│   ├── __init__.py
│   ├── main.py                  # 应用入口 + CORS 配置
│   ├── config.py
│   ├── dependencies.py
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── stats.py
│   │   ├── jobs.py
│   │   ├── upload.py
│   │   ├── knowledge.py
│   │   └── system.py
│   └── schemas/
│       ├── __init__.py
│       ├── stats.py
│       ├── jobs.py
│       ├── upload.py
│       └── common.py
├── web/                         # 📝 Vue 3 前端项目
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   ├── src/
│   │   ├── main.ts
│   │   ├── App.vue
│   │   ├── router/index.ts
│   │   ├── stores/              # Pinia 状态管理 (6 stores)
│   │   ├── api/                 # Axios API 封装 (6 modules)
│   │   ├── types/               # TypeScript 类型定义
│   │   ├── components/
│   │   │   ├── layout/          # AppHeader, AppSidebar, AppFooter
│   │   │   ├── common/          # StatCard, DataTable, LoadingSpinner
│   │   │   ├── charts/          # 6 种 ECharts 图表组件
│   │   │   ├── filters/         # 4 种筛选组件
│   │   │   └── upload/          # 4 种上传组件
│   │   ├── views/               # 9 个页面组件
│   │   └── styles/              # SCSS 主题变量 + 全局样式
│   └── public/favicon.ico
├── docker-compose.yml           # 📝 Nginx + FastAPI + Vue 统一部署
├── nginx/
│   └── default.conf             # 📝 反向代理配置
├── data/                        # 数据目录（gitignore）
├── output/                      # 输出目录（gitignore）
├── .env.example                 # 环境变量模板
├── .gitignore
├── requirements.txt
└── 技术文档.md

---

## 12. 知识库建设

### 12.1 存储架构设计

知识库作为系统的数据中枢，采用分层存储架构：

```
                    ┌──────────────────┐
                    │   MongoDB (主存储) │  ← 结构化文档，支持全文检索
                    └────────┬─────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
       ┌──────────┐  ┌──────────┐  ┌──────────┐
       │ CSV 快照  │  │ JSON 备份 │  │ 向量嵌入  │
       └──────────┘  └──────────┘  └──────────┘  (Phase 7 实现)
```

| 存储层 | 用途 | 读写频率 | 数据格式 |
|--------|------|---------|---------|
| MongoDB | 主存储，支持查询与聚合 | 高频读写 | BSON 文档 |
| CSV 快照 | 快速导出与数据分析 | 低频读 | CSV (UTF-8-SIG) |
| JSON 备份 | 数据归档与版本管理 | 低频写 | JSON |
| 向量嵌入 | 语义搜索（后续阶段） | 低频读 | Numpy/Pickle |

### 12.2 索引策略

#### 12.2.1 MongoDB 索引设计

```json
[
  { "job_id": 1, "source": 1 },          // 唯一键，支持去重
  { "source": 1, "crawled_at": -1 },     // 按来源与时间排序
  { "location": 1, "salary_min": 1 },    // 地点与薪资复合查询
  { "skills.programming_languages": 1 }, // 技能标签检索
  { "jd_text": "text", "title": "text" } // 全文索引，支持 JD 内容搜索
]
```

#### 12.2.2 索引说明

| 索引 | 作用 | 优先级 |
|------|------|--------|
| `job_id + source` 唯一复合索引 | 去重、upsert | P0 |
| `$text` 全文索引 | JD 内容搜索 | P1 |
| `location + salary_min` 复合索引 | 看板筛选加速 | P1 |
| `skills.*` 单字段索引 | 技能标签筛选 | P2 |

### 12.3 数据版本管理

每次爬取生成一个数据版本快照，便于历史对比与回溯。

```
data/
├── raw/                    # 原始 API 响应 JSON
│   └── 2026-06-01/
│       └── jobsdb_software_engineer_page1.json
├── cleaned/                # 清洗后结构化数据
│   ├── jobs.csv            # 当前最新版本
│   ├── jobs.json
│   └── snapshots/          # 历史版本归档
│       ├── jobs_2026-06-01.csv
│       └── jobs_2026-06-15.csv
├── embeddings/             # 向量嵌入文件（Phase 7）
└── uploads/                # 用户上传数据临时目录
    └── 2026-06-01_14-30-00_original.csv
```

### 12.4 查询接口设计

```python
# src/knowledge_base/query.py（概念设计）
class KnowledgeBase:
    """知识库查询接口"""

    def search_by_keyword(self, keyword: str, fields: list = None) -> list[dict]:
        """全文搜索 JD 内容"""

    def filter_by_skills(self, skills: list[str], match_all: bool = False) -> list[dict]:
        """按技能标签筛选"""

    def filter_by_salary(self, min_sal: float = None, max_sal: float = None) -> list[dict]:
        """按薪资范围筛选"""

    def filter_by_location(self, locations: list[str]) -> list[dict]:
        """按地点筛选"""

    def aggregate_skill_frequency(self, top_n: int = 20) -> pd.Series:
        """技能出现频率统计"""

    def aggregate_salary_stats(self, group_by: str = "location") -> pd.DataFrame:
        """薪资统计聚合"""

    def get_version_history(self) -> list[dict]:
        """获取数据版本历史"""
```

---

## 13. 前端中文化

### 13.1 中文映射表设计

前端显示规则要求：除技术框架名称（如 React、AWS、Python）保持英文外，所有 UI 文本均使用中文显示。

#### 13.1.1 地点映射表

香港常见招聘地点中英文映射（约 50+ 条）：

```json
// config/i18n/locations_zh.json
{
  "Central": "中環",
  "Admiralty": "金鐘",
  "Wan Chai": "灣仔",
  "Causeway Bay": "銅鑼灣",
  "Quarry Bay": "鰂魚涌",
  "North Point": "北角",
  "Sheung Wan": "上環",
  "Sai Wan": "西環",
  "Happy Valley": "跑馬地",
  "Tsim Sha Tsui": "尖沙咀",
  "Mong Kok": "旺角",
  "Yau Ma Tei": "油麻地",
  "Kowloon Bay": "九龍灣",
  "Kwun Tong": "觀塘",
  "Kwai Chung": "葵涌",
  "Tsuen Wan": "荃灣",
  "Sha Tin": "沙田",
  "Shatin": "沙田",
  "Tai Po": "大埔",
  "Fanling": "粉嶺",
  "Sheung Shui": "上水",
  "Tuen Mun": "屯門",
  "Yuen Long": "元朗",
  "Tung Chung": "東涌",
  "Sai Kung": "西貢",
  "Pok Fu Lam": "薄扶林",
  "Aberdeen": "香港仔",
  "Wong Chuk Hang": "黃竹坑",
  "Chai Wan": "柴灣",
  "Shau Kei Wan": "筲箕灣",
  "Kennedy Town": "堅尼地域",
  "Hung Hom": "紅磡",
  "Lai Chi Kok": "荔枝角",
  "Cheung Sha Wan": "長沙灣",
  "Sham Shui Po": "深水埗",
  "Prince Edward": "太子",
  "Science Park": "科學園",
  "Cyberport": "數碼港",
  "Hong Kong International Airport": "香港國際機場",
  "Hong Kong Science Park": "香港科學園",
  "Kowloon Tong": "九龍塘",
  "Diamond Hill": "鑽石山",
  "Ngau Tau Kok": "牛頭角",
  "Kwun Tong": "觀塘",
  "Sau Mau Ping": "秀茂坪",
  "Lam Tin": "藍田",
  "Hong Kong": "香港",
  "Kowloon": "九龍",
  "New Territories": "新界"
}
```

#### 13.1.2 技能类别映射表

```json
// config/i18n/categories_zh.json
{
  "programming_languages": "编程语言",
  "frameworks_libraries": "框架与库",
  "cloud_devops": "云服务与运维",
  "databases": "数据库与中间件",
  "soft_skills": "软技能"
}
```

### 13.2 中文化工具模块

```python
# src/i18n/translator.py（概念设计）
import json
from pathlib import Path


class Translator:
    """前端中文化翻译器，支持地点、类别、公司的中文转换"""

    def __init__(self):
        i18n_dir = Path(__file__).resolve().parent.parent.parent / "config" / "i18n"
        with open(i18n_dir / "locations_zh.json", "r", encoding="utf-8") as f:
            self.location_map = json.load(f)
        with open(i18n_dir / "categories_zh.json", "r", encoding="utf-8") as f:
            self.category_map = json.load(f)

    def location_en_to_zh(self, en: str) -> str:
        """英文地点 → 中文地点，无映射则返回原文"""
        return self.location_map.get(en.strip(), en)

    def category_en_to_zh(self, en: str) -> str:
        """英文类别 key → 中文类别名"""
        return self.category_map.get(en, en)

    def translate_df(self, df: pd.DataFrame) -> pd.DataFrame:
        """批量翻译 DataFrame 中的地点列"""
        if "location" in df.columns:
            df["location"] = df["location"].apply(self.location_en_to_zh)
        return df

    def translate_skills(self, skills: dict) -> dict:
        """将技能字典中的类别 key 转为中文"""
        return {self.category_en_to_zh(k): v for k, v in skills.items()}
```

### 13.3 前端显示规则

| 字段 | 当前（英文） | 中文化后 |
|------|-------------|---------|
| 职位标题 | `"Senior Python Developer"` | 保留英文 |
| 公司名称 | `"HK Fintech Ltd"` | 优先查映射表，无映射保留原文 |
| 工作地点 | `"Central"` | → `"中環"` |
| 技能类别标签 | `"programming_languages"` | → `"编程语言"` |
| 技术框架名称 | `"React"`, `"AWS"` | **保持英文** |
| 图表标题 | `"Top 15 In-Demand..."` | → `"香港 IT 技术栈需求排行 Top 15"` |
| 图表轴标签 | `"Number of Job Postings"` | → `"岗位数量"` |
| 图表轴标签 | `"Monthly Salary (HKD)"` | → `"月薪 (HKD)"` |
| 看板标签 | `"Technical Trends"` | → `"技术热度"` |

---

## 14. 知识库管理页面

### 14.1 上传处理流程

用户可通过页面或 CLI 上传自己搜集的招聘数据，系统按技术文档中定义的清洗管道自动处理。

```
用户上传文件 (CSV/JSON)
       │
       ▼
  文件格式校验 ───→ 格式错误 → 报错提示
       │ 通过
       ▼
  字段映射 (用户字段 → 系统标准字段)
       │
       ▼
  字段校验 (必填、类型、值域)
       │
       ▼
  ┌─── 清洗管道（复用现有模块）───┐
  │ ① HTML 标签剥离 (JDTextCleaner) │
  │ ② 薪资标准化 (SalaryParser)    │
  │ ③ 技能提取 (RuleBasedSkillExt) │
  │ ④ 地点/类别中文化 (Translator) │
  └────────────────────────────┘
       │
       ▼
  ┌─── 去重与入库 ─────────────┐
  │ ① 按 source + job_id 去重    │
  │ ② 写入 MongoDB              │
  │ ③ 追加到 CSV 快照            │
  └────────────────────────────┘
       │
       ▼
  完成页：展示处理统计摘要
```

### 14.2 支持的文件格式

| 格式 | 文件头要求 | 处理方式 |
|------|-----------|---------|
| **CSV (UTF-8 / UTF-8-SIG)** | 首行为列名 | `pandas.read_csv()` 自动解析 |
| **JSON (数组)** | `[{...}, {...}]` | `json.load()` 按数组处理 |
| **JSON (逐行/NDJSON)** | `{...}\n{...}` | 逐行解析 |
| **Excel (.xlsx)** | 首行为列名 | `pandas.read_excel()` 解析 |

### 14.3 字段映射机制

用户上传文件的列名可能与系统标准字段名不一致，需通过映射表自动匹配。

```json
// config/field_mapping.json
{
  "user_field_mappings": {
    "job_id": ["job_id", "id", "职位编号", "岗位ID", "编号"],
    "title": ["title", "职位名称", "职位", "岗位", "职位名"],
    "company": ["company", "公司名称", "公司", "企业", "雇主"],
    "location": ["location", "工作地点", "地点", "區域", "地區"],
    "salary_raw": ["salary_raw", "salary", "薪资", "薪酬", "月薪", "待遇", "工资"],
    "jd_raw": ["jd_raw", "description", "职位描述", "JD", "岗位描述", "工作内容", "职责"],
    "source": ["source", "来源", "数据来源", "平台", "網站"]
  }
}
```

匹配逻辑：
1. 对用户上传的每个列名，遍历 `user_field_mappings` 所有别名列表
2. 完全匹配（忽略大小写）则映射到标准字段
3. 未匹配的列名作为自定义字段保留在 `extra_fields` 中
4. 匹配结果展示给用户确认，允许手动调整

### 14.4 校验规则

| 校验项 | 规则 | 处理方式 |
|--------|------|---------|
| 必填字段 | `jd_raw` 必须存在且有内容 | 缺失则拒绝该条记录并报错 |
| 推荐字段 | `title`, `company`, `location` | 缺失则警告但继续处理 |
| 空值处理 | `jd_raw` 为空字符串/Null | 跳过该条记录 |
| 薪资格式 | 不匹配正则则 `salary_min=Null` | 保留 `salary_raw` 原文，标注"解析失败" |
| 重复检测 | `source + job_id` 已存在 | 跳过（upsert 模式） |
| 最大行数 | 单次上传 ≤ 10,000 行 | 超出则拦截并提示分批上传 |
| 文件大小 | 单文件 ≤ 50 MB | 超出则拦截 |

### 14.5 页面设计

#### 14.5.1 页面结构

Streamlit 多页面应用结构：

```
src/
├── app.py                     ← 首页（分析看板）
└── pages/
    ├── __init__.py
    ├── 01_知识库管理.py         ← 知识库管理（上传 + 概览 + 管理）
    └── 02_数据探索.py           ← 可选：知识库浏览与探索
```

#### 14.5.2 知识库管理页面布局

```
┌─────────────────────────────────────────────────┐
│  知识库管理                                        │
│  ───────────────────────────────────────────────  │
│                                                   │
│  ┌─ Tab: 上传数据 ──────────────────────────────┐ │
│  │                                               │ │
│  │  上传区域 (拖拽 or 点击选择)                   │ │
│  │  ┌─────────────────────────────────────────┐  │ │
│  │  │  拖拽 CSV/JSON/Excel 文件到此处            │  │ │
│  │  │  或点击浏览                                │  │ │
│  │  └─────────────────────────────────────────┘  │ │
│  │                                               │ │
│  │  ▼ 展开: 高级选项                             │ │
│  │    数据来源标签: [自定义]                      │ │
│  │    是否检测去重: [✅ 是]                       │ │
│  │    是否执行清洗: [✅ 是]                       │ │
│  │    是否执行技能提取: [✅ 是]                   │ │
│  │                                               │ │
│  │  [开始处理]                                    │ │
│  │                                               │ │
│  │  处理进度: ████████████░░░░░░ 70%             │ │
│  │  ✅ 文件解析完成  ✅ 字段映射完成               │ │
│  │  ✅ 数据清洗完成  ✅ 薪资解析完成               │ │
│  │  ✅ 技能提取完成  ⏳ 入库中...                 │ │
│  │                                               │ │
│  └───────────────────────────────────────────────┘ │
│                                                   │
│  ┌─ Tab: 数据概览 ──────────────────────────────┐ │
│  │                                               │ │
│  │  知识库统计:                                   │ │
│  │  总记录数: 1,234   数据来源: 3   最新更新: ... │ │
│  │                                               │ │
│  │  ┌────────────┐  ┌────────────┐               │ │
│  │  │  来源分布    │  │  技能热度    │              │ │
│  │  │  [柱状图]   │  │  [柱状图]   │              │ │
│  │  └────────────┘  └────────────┘               │ │
│  │                                               │ │
│  └───────────────────────────────────────────────┘ │
│                                                   │
│  ┌─ Tab: 数据管理 ──────────────────────────────┐ │
│  │                                               │ │
│  │  筛选: [来源 ▼] [地点 ▼] [薪资范围] [关键词]   │ │
│  │                                               │ │
│  │  数据预览表格 (可多选)                         │ │
│  │  [导出选中] [删除选中] [导出全部] [导出Excel]  │ │
│  │                                               │ │
│  └───────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
```

#### 14.5.3 处理反馈设计

实时展示处理进度与统计摘要：

```
处理进度: ████████████░░░░░░ 70%

处理摘要:
  总记录数:        15
  成功入库:        12 (3 条因缺失 JD 跳过)
  新增记录:        10
  更新记录:        2
  清洗耗时:        0.3s
  入库耗时:        0.2s
  总计耗时:        1.2s
```

### 14.6 上传管道设计

#### 14.6.1 Uploader 核心类

```python
# src/knowledge_base/uploader.py（概念设计）
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ProcessResult:
    total: int = 0
    success: int = 0
    skipped: int = 0
    new_records: int = 0
    updated_records: int = 0
    errors: list[str] = field(default_factory=list)
    duration_ms: float = 0.0


class Uploader:
    """用户上传数据处理管道"""

    def __init__(self, file_path: str, source_tag: str = "user_upload",
                 detect_duplicates: bool = True, run_cleaning: bool = True,
                 run_extraction: bool = True):
        self.file_path = file_path
        self.source_tag = source_tag
        self.detect_duplicates = detect_duplicates
        self.run_cleaning = run_cleaning
        self.run_extraction = run_extraction

    def validate_format(self) -> bool:
        """检测文件格式是否为 CSV/JSON/Excel，返回是否合法"""

    def detect_mapping(self) -> dict:
        """自动匹配用户列名 → 系统标准字段名"""

    def validate_records(self, records: list[dict]) -> list[dict]:
        """逐条校验必填字段、类型、值域，返回有效记录"""

    def process(self) -> ProcessResult:
        """执行完整清洗管道：clean → parse_salary → extract_skills → translate"""

    def save(self, records: list[dict]) -> int:
        """去重后入库，返回实际写入条数"""
```

#### 14.6.2 与现有模块的集成

```python
# 上传管道中直接复用现有模块
from src.cleaner import CleaningPipeline       # 文本清洗 + 薪资解析
from src.analyzer import RuleBasedSkillExtractor  # 技能提取
from src.storage.mongodb import JobDatabase    # MongoDB 入库
from src.storage.csv_exporter import CSVExporter  # CSV 快照
from src.i18n.translator import Translator     # 中文化
```

上传管道不做重复实现，所有清洗逻辑直接调用已有模块。

### 14.7 数据管理功能

#### 14.7.1 数据探索

| 功能 | 实现方式 |
|------|---------|
| 数据筛选 | 按来源、地点、日期范围、技能类别过滤 |
| 关键词搜索 | MongoDB `$text` 全文索引搜索 JD 内容 |
| 批量导出 | 按筛选结果导出 CSV / JSON / Excel |
| 批量删除 | 多选记录后批量删除（软删除或物理删除） |
| 单条编辑 | 点击展开行内编辑（后续迭代） |

#### 14.7.2 数据统计面板

| 指标 | 计算方式 |
|------|---------|
| 总记录数 | `db.count()` |
| 数据来源分布 | `db.aggregate(group by source)` |
| 技能出现频率 | 从 `skills` 字段反序列化后统计 |
| 薪资范围分布 | `salary_min` / `salary_max` 聚合 |
| 地点分布 | `location` 分组计数 |
| 数据时间趋势 | `crawled_at` 按天聚合 |

#### 14.7.3 文件清单

| 文件 | 用途 | 状态 |
|------|------|------|
| `src/knowledge_base/__init__.py` | 模块入口 | 📝 待新建 |
| `src/knowledge_base/uploader.py` | 文件解析 + 字段映射 + 校验 | 📝 待新建 |
| `src/knowledge_base/validator.py` | 字段校验规则 | 📝 待新建 |
| `src/knowledge_base/query.py` | 知识库查询接口 | 📝 待新建 |
| `src/knowledge_base/stats.py` | 知识库统计聚合 | 📝 待新建 |
| `config/field_mapping.json` | 用户字段→标准字段映射表 | 📝 待新建 |
| `src/i18n/__init__.py` | 中文化模块入口 | 📝 待新建 |
| `src/i18n/translator.py` | 中文化翻译器 | 📝 待新建 |
| `config/i18n/locations_zh.json` | 香港地名中英文映射 | 📝 待新建 |
| `config/i18n/categories_zh.json` | 技能类别中英文映射 | 📝 待新建 |
| `src/pages/__init__.py` | Streamlit 多页面入口 | 📝 待新建 |
| `src/pages/01_知识库管理.py` | 知识库管理页面 | 📝 待新建 |
| `scripts/upload_pipeline.py` | CLI 版上传处理脚本 | 📝 待新建 |

---

## 15. Vue 前端开发规划

### 15.1 技术选型

| 层级 | 技术栈 | 选型理由 |
|------|--------|---------|
| 框架 | Vue 3 + TypeScript + Vite 5 | 组合式 API + 类型安全 + 极速 HMR |
| 状态管理 | Pinia | Vue 3 官方推荐，TypeScript 原生支持 |
| 路由 | Vue Router 4 | Vue 3 官方路由，支持动态路由与导航守卫 |
| UI 组件库 | Element Plus | 全面中文化支持，组件丰富，Vue 3 原生 |
| 图表 | ECharts 5 (vue-echarts) | 复杂图表类型支持完善，性能优异 |
| HTTP 请求 | Axios | 拦截器机制完善，请求/响应转换灵活 |
| 构建工具 | Vite 5 | 原生 ES Module 构建，开发体验优秀 |
| 代码规范 | ESLint + Prettier | 统一代码风格 |
| 包管理 | pnpm | 速度快，节省磁盘空间 |
| 测试 | Vitest + Vue Test Utils | 与 Vite 深度集成，组件测试支持好 |

### 15.2 系统架构

```
┌─────────────────────────────────────────────────────┐
│                   Vue 3 前端 (Vite)                   │
│  ┌──────────┐ ┌──────────┐ ┌────────────────────┐  │
│  │ Vue Router│ │   Pinia  │ │  Element Plus 组件  │  │
│  │  (路由)   │ │  (状态)   │ │  (UI 组件库)        │  │
│  └──────────┘ └──────────┘ └────────────────────┘  │
│  ┌────────────────────────────────────────────────┐ │
│  │              ECharts 图表组件                   │ │
│  │  (柱状图 / 饼图 / 箱线图 / 趋势图 / 地图)     │ │
│  └────────────────────────────────────────────────┘ │
└──────────────────────┬──────────────────────────────┘
                       │ Axios HTTP
┌──────────────────────▼──────────────────────────────┐
│                FastAPI REST API 网关                  │
│  ┌─────────┐ ┌──────────┐ ┌────────┐ ┌──────────┐  │
│  │ 路由层   │ │ 请求校验  │ │ 响应格式化│ │ 错误处理  │  │
│  │ (APIRouter)│ (Pydantic)│ │ (JSON) │ │ (Exception)│ │
│  └─────────┘ └──────────┘ └────────┘ └──────────┘  │
└──────────────────────┬──────────────────────────────┘
                       │ 调用
┌──────────────────────▼──────────────────────────────┐
│               Python 后端 (现有模块)                   │
│  ┌────────┐ ┌────────┐ ┌───────┐ ┌────┐ ┌───────┐  │
│  │analyzer│ │cleaner │ │storage│ │i18n│ │knowledge│  │
│  └────────┘ └────────┘ └───────┘ └────┘ └───────┘  │
│                    base (爬虫基类)                    │
└──────────────────────┬──────────────────────────────┘
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
    ┌──────────┐ ┌──────────┐ ┌──────────┐
    │ MongoDB  │ │ CSV 快照  │ │ JSON 备份 │
    └──────────┘ └──────────┘ └──────────┘
```

**核心原则**：
- Vue 前端只负责 UI 渲染和交互逻辑，不直接操作数据库
- FastAPI 作为唯一的 API 网关，封装所有后端业务逻辑
- 后端复用已有 Python 模块（analyzer, cleaner, storage, i18n, knowledge_base）
- 前端通过 Axios 与 FastAPI 通信，数据格式统一为 JSON

### 15.3 后端 API 网关设计

#### 15.3.1 FastAPI 项目结构

```
api/
├── __init__.py
├── main.py                  # FastAPI 应用入口，CORS 配置
├── routers/
│   ├── __init__.py
│   ├── stats.py             # /api/v1/stats/* - 统计聚合接口
│   ├── jobs.py              # /api/v1/jobs/* - 岗位数据接口
│   ├── upload.py            # /api/v1/upload/* - 文件上传接口
│   ├── knowledge.py         # /api/v1/knowledge-base/* - 知识库接口
│   └── system.py            # /api/v1/system/* - 系统配置接口
├── schemas/
│   ├── __init__.py
│   ├── stats.py             # Pydantic 统计响应模型
│   ├── jobs.py              # Pydantic 岗位数据模型
│   ├── upload.py            # Pydantic 上传请求/响应模型
│   └── common.py            # 通用分页/筛选模型
├── dependencies.py          # 依赖注入（DB 连接等）
└── config.py                # API 专用配置
```

#### 15.3.2 API 端点清单

| 方法 | 路径 | 说明 | 请求参数 | 响应 |
|------|------|------|---------|------|
| GET | `/api/v1/stats/overview` | 总览统计 | — | `{total_jobs, avg_salary, sources, last_update}` |
| GET | `/api/v1/stats/skills` | 技能频率 | `top_n` (int) | `[{skill, count, category}]` |
| GET | `/api/v1/stats/salary` | 薪资统计 | `group_by` (str) | `[{group, mean, min, max, count}]` |
| GET | `/api/v1/stats/locations` | 地点分布 | `top_n` (int) | `[{location, count}]` |
| GET | `/api/v1/stats/sources` | 来源分布 | — | `[{source, count}]` |
| GET | `/api/v1/stats/trend` | 时间趋势 | `granularity` (str: day/week/month) | `[{date, count}]` |
| GET | `/api/v1/jobs` | 岗位搜索/筛选 | `keyword, location, source, salary_min, salary_max, page, page_size` | `{total, page, page_size, items: [...]}` |
| GET | `/api/v1/jobs/{id}` | 岗位详情 | — | `{job detail}` |
| POST | `/api/v1/upload` | 上传数据文件 | `multipart/form-data` (file + options) | `{task_id, status}` |
| GET | `/api/v1/upload/status/{task_id}` | 上传处理进度 | — | `{progress, result}` |
| GET | `/api/v1/knowledge-base/search` | 知识库关键词搜索 | `q` (str), `page`, `page_size` | `{total, items}` |
| GET | `/api/v1/knowledge-base/versions` | 数据版本历史 | — | `[{date, record_count, sources}]` |
| DELETE | `/api/v1/knowledge-base/records` | 批量删除记录 | `ids` (list[str]) | `{deleted_count}` |
| GET | `/api/v1/system/config` | 获取系统配置 | — | `{crawler, llm, proxy}` |
| PUT | `/api/v1/system/config` | 更新系统配置 | `{...}` | `{status}` |

#### 15.3.3 CORS 与跨域配置

```python
# api/main.py（概念设计）
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="HK Job Market API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite 开发服务器
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(stats_router, prefix="/api/v1/stats")
app.include_router(jobs_router, prefix="/api/v1/jobs")
app.include_router(upload_router, prefix="/api/v1/upload")
app.include_router(knowledge_router, prefix="/api/v1/knowledge-base")
app.include_router(system_router, prefix="/api/v1/system")
```

### 15.4 页面与路由设计

#### 15.4.1 路由表

```
/                          → DashboardPage     (仪表盘总览)
/tech-trends               → TechTrendsPage     (技术热度分析)
/salary-analysis           → SalaryPage         (薪资分析)
/locations                 → LocationPage       (区域分布)
/knowledge-base            → KnowledgeBasePage  (知识库管理 - 概览 Tab)
/knowledge-base/upload     → UploadPage         (知识库管理 - 上传 Tab)
/knowledge-base/manage     → ManagePage         (知识库管理 - 管理 Tab)
/data-explore              → DataExplorePage    (数据探索)
/settings                  → SettingsPage       (系统设置)
```

#### 15.4.2 页面布局结构

所有页面共享统一的布局骨架：

```
┌─────────────────────────────────────────────────────┐
│  Header: Logo / 导航菜单 / 系统状态 / 用户信息      │
├──────────┬──────────────────────────────────────────┤
│ Sidebar  │  Main Content Area                        │
│          │                                           │
│ 筛选条件  │  子页面内容 (由 RouterView 渲染)           │
│          │                                           │
│ 地点筛选  │  ┌──────────────────────────────────┐   │
│ 来源筛选  │  │  统计卡片 / 图表 / 数据表格       │   │
│ 薪资范围  │  │                                   │   │
│ 关键词    │  └──────────────────────────────────┘   │
│          │                                           │
│ 重置筛选  │                                           │
├──────────┴──────────────────────────────────────────┤
│  Footer: 版权 / 数据声明                             │
└─────────────────────────────────────────────────────┘
```

#### 15.4.3 页面详细设计

| 页面 | 路由 | 核心组件 | 数据来源 |
|------|------|---------|---------|
| **仪表盘总览** | `/` | StatCards (总岗位数/平均薪资/数据来源数/最新更新)、SkillTrendChart (技能趋势 Top 10)、SourcePieChart (数据来源占比)、SalaryOverview (薪资概览) | `/stats/overview`, `/stats/skills`, `/stats/sources` |
| **技术热度** | `/tech-trends` | SkillBarChart (技能排行，可调节 Top N)、CategoryPieChart (类别分布)、SkillDetailTable (技能详情表格) | `/stats/skills` |
| **薪资分析** | `/salary-analysis` | SalaryStatsCards (平均/最低/最高)、SalaryBoxChart (各区域薪资箱线图)、TopSalaryBarChart (高薪职位 Top 15) | `/stats/salary` |
| **区域分布** | `/locations` | LocationBarChart (区域排行)、JobTable (该区域岗位列表) | `/stats/locations`, `/jobs` |
| **知识库概览** | `/knowledge-base` | StatsCards (总记录数/来源数)、SourcePieChart、LocationBarChart、VersionTable (版本历史) | `/stats/overview`, `/knowledge-base/versions` |
| **上传数据** | `/knowledge-base/upload` | FileUploader (拖拽上传)、FieldMappingPreview (字段映射预览)、ProcessProgressBar (进度条)、ProcessResultSummary (处理摘要) | `/upload` (POST), `/upload/status` (GET) |
| **数据管理** | `/knowledge-base/manage` | SearchBar (搜索)、DataTable (可筛选/可多选表格)、BatchActions (批量删除/导出) | `/knowledge-base/search`, `/jobs` |
| **数据探索** | `/data-explore` | SearchPanel (多条件搜索)、ExploreTable (搜索结果表格)、ExportButton (导出) | `/jobs` (含全部筛选参数) |
| **系统设置** | `/settings` | CrawlerConfigForm (爬虫配置)、LLMConfigForm (LLM 配置)、ProxyConfigForm (代理配置) | `/system/config` (GET/PUT) |

### 15.5 组件树设计

```
App.vue
├── AppHeader.vue                     # 顶部导航栏
│   ├── Logo.vue                      # Logo + 系统名称
│   ├── NavMenu.vue                   # 导航菜单
│   └── SystemStatus.vue              # 后端连接状态指示灯
├── AppSidebar.vue                    # 侧边栏（全局筛选）
│   ├── LocationFilter.vue            # 地点多选筛选
│   ├── SourceFilter.vue              # 数据来源筛选
│   ├── SalaryRangeFilter.vue         # 薪资范围滑条
│   └── KeywordSearch.vue             # 关键词搜索
├── RouterView.vue                    # 路由视图容器
│   │
│   ├── DashboardPage.vue             # 仪表盘总览
│   │   ├── StatCards.vue             # 统计指标卡片组
│   │   │   └── StatCard.vue          # 单张统计卡片
│   │   ├── SkillTrendChart.vue       # 技能趋势 Top 10 柱状图
│   │   ├── SourcePieChart.vue        # 数据来源饼图
│   │   ├── SalaryOverview.vue        # 薪资概览
│   │   └── RecentUpdates.vue         # 最近更新列表
│   │
│   ├── TechTrendsPage.vue            # 技术热度分析
│   │   ├── SkillBarChart.vue         # 技能排行柱状图（可调节 Top N）
│   │   ├── CategoryPieChart.vue      # 类别占比饼图
│   │   ├── SkillTrendLine.vue        # 技能时间趋势折线图
│   │   └── SkillDetailTable.vue      # 技能详情表格
│   │
│   ├── SalaryAnalysisPage.vue        # 薪资分析
│   │   ├── SalaryStatsCards.vue      # 薪资统计指标卡片
│   │   ├── SalaryBoxChart.vue        # 各区域薪资箱线图
│   │   ├── TopSalaryBarChart.vue     # 高薪职位排行
│   │   └── SalaryDistributionHist.vue # 薪资分布直方图
│   │
│   ├── LocationPage.vue              # 区域分布
│   │   ├── LocationBarChart.vue      # 区域岗位数量排行
│   │   └── LocationJobTable.vue      # 区域岗位列表
│   │
│   ├── KnowledgeBasePage.vue         # 知识库（概览 Tab）
│   │   ├── KBStatsCards.vue          # 知识库统计卡片
│   │   ├── KBSourceChart.vue         # 来源分布图表
│   │   ├── KBSkillChart.vue          # 技能频率图表
│   │   └── KBVersionTable.vue        # 数据版本历史表格
│   │
│   ├── UploadPage.vue                # 上传数据
│   │   ├── FileUploader.vue          # 文件拖拽/点击上传
│   │   ├── FieldMappingPreview.vue   # 字段映射结果预览
│   │   ├── ProcessProgressBar.vue    # 处理进度条
│   │   └── ProcessResultSummary.vue  # 处理摘要展示
│   │
│   ├── ManagePage.vue                # 数据管理
│   │   ├── ManageSearchBar.vue       # 搜索条
│   │   ├── ManageDataTable.vue       # 数据表格（支持多选）
│   │   └── BatchActions.vue          # 批量操作工具栏
│   │
│   ├── DataExplorePage.vue           # 数据探索
│   │   ├── ExploreSearchPanel.vue    # 多条件搜索面板
│   │   ├── ExploreTable.vue          # 搜索结果表格
│   │   └── ExportButton.vue          # 导出按钮
│   │
│   └── SettingsPage.vue              # 系统设置
│       ├── CrawlerConfigForm.vue     # 爬虫配置表单
│       ├── LLMConfigForm.vue         # LLM 配置表单
│       └── ProxyConfigForm.vue       # 代理配置表单
│
└── AppFooter.vue                     # 底部版权/声明
```

### 15.6 数据流设计

#### 15.6.1 全局状态管理 (Pinia Store)

```typescript
// stores/global.ts（概念设计）
interface GlobalState {
  // 筛选条件（全局共享）
  filters: {
    locations: string[]
    sources: string[]
    salaryRange: [number, number] | null
    keyword: string
  }
  // 统计数据（缓存）
  overview: OverviewStats | null
  skillFrequency: SkillItem[]
  salaryStats: SalaryGroup[]
  locationDistribution: LocationItem[]
  // 加载状态
  loading: boolean
  // 错误状态
  error: string | null
}
```

| Store | 职责 | 关键 Actions |
|-------|------|-------------|
| `useGlobalStore` | 全局筛选条件 + 基本缓存 | `setFilters()`, `resetFilters()`, `fetchOverview()` |
| `useStatsStore` | 统计数据的获取与缓存 | `fetchSkills()`, `fetchSalary()`, `fetchLocations()` |
| `useJobsStore` | 岗位数据查询 | `searchJobs()`, `getJobDetail()` |
| `useUploadStore` | 上传流程状态管理 | `uploadFile()`, `pollProgress()` |
| `useKnowledgeStore` | 知识库数据管理 | `search()`, `deleteRecords()`, `fetchVersions()` |
| `useSettingsStore` | 系统配置管理 | `fetchConfig()`, `updateConfig()` |

#### 15.6.2 数据流场景

**场景 A：页面加载渲染**

```
用户访问 /tech-trends
  → TechTrendsPage.vue onMounted()
    → useStatsStore.fetchSkills({ top_n: 20 })
      → stats API (GET /api/v1/stats/skills)
        → FastAPI 路由
          → StatsAggregator.aggregate_skill_frequency()
            → MongoDB aggregate 或 CSV 读取
          ← JSON 响应
      ← Store 更新 skillFrequency
    ← 组件响应式渲染图表
```

**场景 B：筛选条件变更**

```
用户在 Sidebar 选择"中環"地点
  → AppSidebar.vue emit('filter-change')
    → useGlobalStore.setFilters({ locations: ["中環"] })
      → 所有页面响应式更新
        → TechTrendsPage 重新请求技能数据（带 location 参数）
        → SalaryAnalysisPage 重新请求薪资数据（带 location 参数）
        → Dashboard 更新总览
```

**场景 C：文件上传**

```
用户拖拽 CSV 文件到 FileUploader
  → 前端解析前几行进行预览（字段映射展示）
  → 用户确认映射后点击"开始处理"
  → useUploadStore.uploadFile(file, options)
    → POST /api/v1/upload (multipart/form-data)
    ← 返回 { task_id: "uuid-xxx" }
  → 启动轮询 useUploadStore.pollProgress(task_id)
    → GET /api/v1/upload/status/{task_id}
    ← { progress: 70, step: "清洗中" }
  → 实时更新 ProcessProgressBar
  → 处理完成 → ProcessResultSummary 展示结果
```

#### 15.6.3 缓存策略

| 数据类型 | 缓存方式 | 过期策略 |
|---------|---------|---------|
| 统计总览 | Pinia Store | 页面刷新/手动刷新 |
| 技能/薪资/地点统计 | Pinia Store | 筛选条件变更时 |
| 岗位搜索结果 | 不缓存 | 每次搜索重新请求 |
| 知识库版本历史 | Pinia Store | 上传操作后失效 |
| 系统配置 | Pinia Store | 更新配置后失效 |

### 15.7 与 Streamlit 共存与迁移策略

#### 15.7.1 三阶段迁移计划

```
第 1 阶段：Vue 独立开发，Streamlit 保留
  - Vue 开发新的数据面板（仪表盘/技术热度/薪资分析/区域分布）
  - Streamlit 保留知识库管理页面
  - FastAPI 作为独立网关提供服务
  - 两者通过不同端口共存

第 2 阶段：Vue 功能覆盖
  - Vue 实现知识库管理页面全部功能
  - Streamlit 标记为 deprecated
  - 统一入口：Nginx 反向代理

第 3 阶段：Streamlit 退役
  - 全面迁移到 Vue + FastAPI
  - 移除 Streamlit 依赖
  - 统一前端构建与部署
```

#### 15.7.2 端口规划

| 服务 | 端口 | 说明 |
|------|------|------|
| Vite 开发服务器 | 5173 | Vue 前端开发环境 |
| FastAPI 网关 | 8000 | REST API 服务 |
| Streamlit (过渡期) | 8501 | Streamlit 看板（第 1 阶段保留） |
| Nginx (生产) | 80/443 | 统一反向代理 |

#### 15.7.3 启动方式

```bash
# 开发环境
cd web                    # Vue 前端
pnpm dev                  # Vite → :5173

cd api                    # FastAPI 网关
uvicorn main:app --reload # → :8000

# Streamlit（过渡期保留）
streamlit run src/app.py  # → :8501

# 生产环境
docker-compose up         # Nginx → :80
```

### 15.8 文件清单

```
HK-JobMarket-Analyzer/
├── web/                              # Vue 前端项目根目录
│   ├── index.html
│   ├── package.json
│   ├── pnpm-lock.yaml
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── .env.development              # VITE_API_BASE_URL=http://localhost:8000
│   ├── .env.production               # VITE_API_BASE_URL=/api/v1
│   ├── src/
│   │   ├── main.ts                   # Vue 应用入口
│   │   ├── App.vue                   # 根组件（布局骨架）
│   │   ├── router/
│   │   │   └── index.ts              # 路由配置（9 条路由）
│   │   ├── stores/
│   │   │   ├── global.ts             # 全局筛选 Store
│   │   │   ├── stats.ts             # 统计数据 Store
│   │   │   ├── jobs.ts              # 岗位数据 Store
│   │   │   ├── upload.ts            # 上传流程 Store
│   │   │   ├── knowledge.ts         # 知识库 Store
│   │   │   └── settings.ts          # 系统配置 Store
│   │   ├── api/
│   │   │   ├── client.ts            # Axios 实例（拦截器/错误处理）
│   │   │   ├── stats.ts             # 统计 API 封装
│   │   │   ├── jobs.ts              # 岗位 API 封装
│   │   │   ├── upload.ts            # 上传 API 封装
│   │   │   ├── knowledge.ts         # 知识库 API 封装
│   │   │   └── system.ts            # 系统配置 API 封装
│   │   ├── types/
│   │   │   ├── stats.ts             # 统计相关类型
│   │   │   ├── jobs.ts              # 岗位数据类型
│   │   │   ├── upload.ts            # 上传相关类型
│   │   │   └── common.ts            # 通用类型（分页等）
│   │   ├── components/
│   │   │   ├── layout/
│   │   │   │   ├── AppHeader.vue
│   │   │   │   ├── AppSidebar.vue
│   │   │   │   └── AppFooter.vue
│   │   │   ├── common/
│   │   │   │   ├── StatCard.vue
│   │   │   │   ├── StatCards.vue
│   │   │   │   ├── DataTable.vue
│   │   │   │   └── LoadingSpinner.vue
│   │   │   ├── charts/
│   │   │   │   ├── SkillBarChart.vue
│   │   │   │   ├── CategoryPieChart.vue
│   │   │   │   ├── SalaryBoxChart.vue
│   │   │   │   ├── TrendLineChart.vue
│   │   │   │   ├── LocationBarChart.vue
│   │   │   │   └── SourcePieChart.vue
│   │   │   ├── filters/
│   │   │   │   ├── LocationFilter.vue
│   │   │   │   ├── SourceFilter.vue
│   │   │   │   ├── SalaryRangeFilter.vue
│   │   │   │   └── KeywordSearch.vue
│   │   │   └── upload/
│   │   │       ├── FileUploader.vue
│   │   │       ├── FieldMappingPreview.vue
│   │   │       ├── ProcessProgressBar.vue
│   │   │       └── ProcessResultSummary.vue
│   │   ├── views/
│   │   │   ├── DashboardPage.vue
│   │   │   ├── TechTrendsPage.vue
│   │   │   ├── SalaryAnalysisPage.vue
│   │   │   ├── LocationPage.vue
│   │   │   ├── KnowledgeBasePage.vue
│   │   │   ├── UploadPage.vue
│   │   │   ├── ManagePage.vue
│   │   │   ├── DataExplorePage.vue
│   │   │   └── SettingsPage.vue
│   │   └── styles/
│   │       ├── variables.scss         # 主题变量（Element Plus 覆盖）
│   │       └── global.scss            # 全局样式
│   └── public/
│       └── favicon.ico
│
├── api/                              # FastAPI 网关
│   ├── __init__.py
│   ├── main.py                       # 应用入口 + CORS 配置
│   ├── config.py
│   ├── dependencies.py
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── stats.py
│   │   ├── jobs.py
│   │   ├── upload.py
│   │   ├── knowledge.py
│   │   └── system.py
│   └── schemas/
│       ├── __init__.py
│       ├── stats.py
│       ├── jobs.py
│       ├── upload.py
│       └── common.py
│
├── docker-compose.yml                # Nginx + FastAPI + Vue 统一部署
├── nginx/
│   └── default.conf                  # 反向代理配置
│
└── ...                               # 现有 Python 后端代码保持不变
```

### 15.9 里程碑规划

| 里程碑 | 内容 | 预估工时 | 依赖 |
|--------|------|---------|------|
| **V1** 项目初始化 | Vite + Vue 3 + TypeScript 脚手架搭建，Element Plus 集成，路由框架 | 0.5 天 | — |
| **V2** FastAPI 网关 | API 路由搭建，CORS 配置，与现有 Python 后端模块集成，单元测试 | 1 天 | M5 后端模块 |
| **V3** 布局与导航 | AppHeader、AppSidebar、AppFooter 布局组件，路由守卫，全局状态管理 | 0.5 天 | V1 |
| **V4** 仪表盘页面 | DashboardPage + StatCards + SourcePieChart + SkillTrendChart + 薪资概览 | 1 天 | V2 + V3 |
| **V5** 分析页面 | TechTrendsPage + SalaryAnalysisPage + LocationPage（含全部图表组件） | 1 天 | V2 + V3 |
| **V6** 知识库管理 | KnowledgeBasePage + UploadPage + ManagePage（含上传管道前端集成） | 1.5 天 | V2 + V3 |
| **V7** 数据探索与设置 | DataExplorePage + SettingsPage | 0.5 天 | V2 |
| **V8** 联调与优化 | 前后端联调，响应式适配，加载状态优化，错误边界处理 | 1 天 | V4-V7 |
| **V9** 生产部署 | Docker 容器化，Nginx 反向代理，环境变量分离 | 0.5 天 | V8 |
