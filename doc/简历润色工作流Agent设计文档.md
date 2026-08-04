# 简历润色工作流 Agent 设计文档

**版本**: v1.2  
**日期**: 2026-06-28  
**状态**: 第 13 章已落地（见 §13.10 落地说明）

---

## 修订记录

| 版本 | 日期 | 修订内容 | 修订人 |
|------|------|---------|--------|
| v1.0 | 2026-06-23 | 初始版本 | - |
| v1.1 | 2026-06-24 | 增补 JobResearch、输入体检、证据审计、面试深挖、质量闸门与求职全链路工作流设计 | - |
| v1.2 | 2026-06-28 | 新增第 13 章：复用统计分析重构产出的结构化标签资产（`tag_profile` 分层、`cross_industry_profile` 六维、`soft_skills` 六类、`job_context_profile` 组合画像、`skill_taxonomy` 词库与聚合榜单），改造 `analyze_jd`/`market_insights`/`gap_analysis`/`score`，修复"示例当硬要求""跨行业能力被压扁"两处与统计文档 §11.1 同源缺陷 | - |

---

## 目录

1. [项目背景与目标](#1-项目背景与目标)
2. [系统定位与集成方案](#2-系统定位与集成方案)
3. [总体架构](#3-总体架构)
4. [Agent 工作流设计（LangGraph）](#4-agent-工作流设计langgraph)
5. [模块详细设计](#5-模块详细设计)
6. [Prompt 设计](#6-prompt-设计)
7. [后端 API 设计](#7-后端-api-设计)
8. [前端设计](#8-前端设计)
9. [可复用基础设施清单](#9-可复用基础设施清单)
10. [文件清单](#10-文件清单)
11. [里程碑规划](#11-里程碑规划)
12. [v2.9 增强工作流设计](#12-v29-增强工作流设计)
13. [复用统计分析数据](#13-复用统计分析数据)

---

## 1. 项目背景与目标

### 1.1 背景

香港 IT 招聘市场竞争激烈，求职者投递简历时常面临以下痛点：

- **岗位匹配度低**：简历内容与目标岗位要求不吻合，海投效率低
- **本地化不足**：香港招聘市场以英文 JD 为主，但夹杂粤语/中文术语，内地求职者难以适配
- **关键词缺失**：ATS（Applicant Tracking System）自动筛选简历，缺乏目标 JD 中的关键词导致被过滤
- **技能展示不当**：技术栈描述过于笼统或过时，未能突出香港市场热门技能

本系统（HK-JobMarket-Analyzer）已积累大量香港 IT 岗位数据、技能词库和 LLM 分析能力，具备为简历润色提供**数据驱动决策支持**的基础。

### 1.2 目标

构建一个基于 LangGraph 的**简历润色工作流 Agent**，实现：

1. **JD 解析**：解析目标岗位 JD，提取核心技能要求、经验门槛、职责描述
2. **岗位匹配**：通过向量检索从知识库中召回相似岗位，辅助理解目标职位的市场定位
3. **差距分析**：对比用户简历与目标 JD，识别技能缺口和优化方向
4. **智能润色**：基于差距分析结果，逐段优化简历内容，确保关键词覆盖和本地化表达
5. **评分验证**：对润色后的简历进行多维评分，迭代优化直至达标

### 1.3 与现有系统的关系

简历润色 Agent 作为 **HK-JobMarket-Analyzer** 的内置功能模块运行，复用现有基础设施，不独立部署。

```
HK-JobMarket-Analyzer/
├── src/resume_agent/          ← 新模块：简历润色 Agent
├── api/routers/resume.py      ← 新模块：简历润色 API 端点
├── web/src/views/ResumePage.vue  ← 新模块：简历润色前端页面
├── src/analyzer/              ← 复用：LLM 引擎
├── src/embeddings/            ← 复用：向量检索
├── src/knowledge_base/        ← 复用：知识库查询
└── config/                    ← 复用：配置管理
```

---

## 2. 系统定位与集成方案

### 2.1 模块边界

| 维度 | 边界说明 |
|------|---------|
| 职责范围 | 简历解析 → 岗位匹配 → 差距分析 → 润色 → 评分，端到端工作流 |
| 数据依赖 | 读：知识库岗位数据、向量索引、技能词表；写：无（不修改知识库） |
| 技术栈 | LangGraph 编排工作流、LangChain OpenAI 调用 LLM、复现有 VectorStore |
| 输出产物 | 润色建议 JSON（逐段修改建议 + 关键词覆盖报告 + 评分） |
| 约束 | 不存储用户简历原文，润色结果可导出/下载 |

### 2.2 依赖隔离策略

LangGraph / LangChain 不加入核心 `requirements.txt`，采用可选依赖方式：

**方案**：`requirements-resume.txt`

```
# ===== 简历润色 Agent（可选）=====
langgraph==0.2.x
langchain-openai==0.2.x
langchain-core==0.3.x
```

安装方式：`pip install -r requirements-resume.txt`

这样做的好处：
- 不污染现有环境的依赖
- Docker 镜像中可选择性包含
- 不影响 CI 流水线中原有测试

---

## 3. 总体架构

### 3.1 架构分层

```
                    ┌─────────────────────────────────────────┐
                    │         用户交互层 (Vue 3 前端)            │
                    │  ResumePage.vue / 简历上传 / 结果展示      │
                    └──────────────────┬──────────────────────┘
                                       │ Axios JSON API
                    ┌──────────────────▼──────────────────────┐
                    │         API 网关层 (FastAPI)              │
                    │  POST /api/resume/polish                 │
                    │  POST /api/resume/analyze                │
                    │  POST /api/resume/match-jobs             │
                    └──────────────────┬──────────────────────┘
                                       │
                    ┌──────────────────▼──────────────────────┐
                    │       Agent 工作流层 (LangGraph)           │
                    │                                          │
                    │  ┌─────────┐  ┌──────────┐  ┌─────────┐ │
                    │  │ 简历解析  │→│ JD 分析   │→│ 岗位匹配  │ │
                    │  │ 节点     │  │ 节点      │  │ 节点     │ │
                    │  └─────────┘  └──────────┘  └─────────┘ │
                    │       │              │              │    │
                    │       ▼              ▼              ▼    │
                    │  ┌─────────┐  ┌──────────┐  ┌─────────┐ │
                    │  │ 差距分析  │→│ 润色生成  │→│ 评分验证  │ │
                    │  │ 节点     │  │ 节点      │  │ 节点     │ │
                    │  └─────────┘  └──────────┘  └─────────┘ │
                    └──────────────────┬──────────────────────┘
                                       │
          ┌────────────────────────────┼────────────────────────┐
          │                            │                        │
          ▼                            ▼                        ▼
   ┌──────────────┐          ┌──────────────────┐     ┌──────────────┐
   │  LLM 引擎     │          │ VectorStore       │     │ 知识库查询    │
   │ (langchain)  │          │ (ChromaDB 语义搜索) │     │ (MongoDB)    │
   └──────────────┘          └──────────────────┘     └──────────────┘
```

### 3.2 与现有系统的交互关系

```
┌──────────────────────────────────────────────────────────────────┐
│                        HK-JobMarket-Analyzer                      │
│                                                                   │
│  ┌─────────────────────┐    ┌──────────────────────────────────┐ │
│  │  已有模块（复用）      │    │  新模块：resume_agent             │ │
│  │                      │    │                                  │ │
│  │  · LLMConfigManager  │───→│  · graph.py (LangGraph 工作流)    │ │
│  │  · VectorStore       │───→│  · nodes.py (各节点实现)          │ │
│  │  · RuleBasedSkill... │───→│  · state.py (状态 Schema)        │ │
│  │  · RoleClassifier    │    │  · prompts.py (润色 Prompt)      │ │
│  │  · Translator        │    │  · models.py (数据模型)          │ │
│  │  · config/settings   │───→│                                  │ │
│  │  · knowledge_base    │───→│  API: /api/resume/*               │ │
│  │  · MongoDB           │    │  Vue: ResumePage.vue              │ │
│  └─────────────────────┘    └──────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

---

## 4. Agent 工作流设计（LangGraph）

### 4.1 工作流总览

采用 **6 节点串行 + 条件分支** 的 LangGraph 工作流，支持在评分不达标时自动回退重润色。

```
                    ┌──────────────────┐
                    │    resume_input   │  ← 用户输入：简历原文 + 目标 JD URL/文本
                    └────────┬─────────┘
                             ▼
                    ┌──────────────────┐
                    │  parse_resume     │  ← 解析简历：提取结构（经验/技能/教育/项目）
                    └────────┬─────────┘
                             ▼
                    ┌──────────────────┐
                    │  analyze_jd       │  ← 分析 JD：提取 requirements、职责、技能
                    └────────┬─────────┘
                             ▼
                    ┌──────────────────┐
                    │  match_jobs       │  ← 向量检索相似岗位（可选增强）
                    └────────┬─────────┘
                             ▼
                    ┌──────────────────┐
                    │  gap_analysis     │  ← 差距分析：对比简历 vs JD 技能缺口
                    └────────┬─────────┘
                             ▼
                    ┌──────────────────┐
                    │  generate_polish  │  ← 逐段生成润色建议
                    └────────┬─────────┘
                             ▼
                    ┌──────────────────┐
                    │  score_and_verify │  ← 评分验证
                    └────────┬─────────┘
                             │
                    ┌────────┴────────┐
                    │                 │
                  score≥7           score<7
                    │                 │
                    ▼                 ▼
              ┌──────────┐   ┌──────────────────┐
              │  output   │   │  regenerate_path  │  ← 回到 gap_analysis 重试
              └──────────┘   └──────────────────┘
                                    │
                                    ▼
                             (最多重试 2 次)
```

### 4.2 State 设计

```python
# src/resume_agent/state.py

from typing import Optional
from typing_extensions import TypedDict


class ResumeAnalysis(TypedDict, total=False):
    """简历解析结果"""
    sections: dict[str, str]          # {"工作经验": "...", "技能": "...", "教育": "...", "项目": "..."}
    raw_skills: list[str]             # 从简历提取的技能列表
    years_of_experience: Optional[float]
    education_level: Optional[str]
    current_titles: list[str]         # 当前/最近职位名称


class JDAnalysis(TypedDict, total=False):
    """JD 分析结果"""
    required_skills: list[str]        # 硬性技能要求
    preferred_skills: list[str]       # 加分技能
    responsibilities: list[str]       # 核心职责
    min_experience: Optional[float]   # 经验要求
    role_category: str                # 角色分类（复用 RoleClassifier）
    key_requirements: list[str]       # 关键要求原文


class GapAnalysis(TypedDict, total=False):
    """差距分析结果"""
    matched_skills: list[str]         # 已匹配的技能
    missing_skills: list[str]         # 缺失的技能
    weak_skills: list[str]            # 需加强的技能
    experience_gap: Optional[str]     # 经验差距描述
    keyword_suggestions: list[dict]   # 关键词建议 [{"keyword": "...", "priority": "high"}]


class PolishSuggestion(TypedDict, total=False):
    """单段润色建议"""
    section: str                      # 段落名称
    original: str                     # 原文片段
    suggested: str                    # 润色后文本
    changes: list[str]                # 修改说明列表
    keywords_added: list[str]         # 新增的关键词


class ScoreReport(TypedDict, total=False):
    """评分报告"""
    overall_score: float              # 总分 1-10
    keyword_coverage: float           # 关键词覆盖率
    experience_alignment: float       # 经验匹配度
    skill_relevance: float            # 技能相关性
    language_quality: float           # 语言质量
    suggestions: list[str]            # 改进建议


class AgentState(TypedDict):
    """Agent 工作流状态"""
    # 输入
    resume_text: str                  # 简历原文
    target_jd_text: str               # 目标 JD 原文
    target_jd_url: Optional[str]      # 目标 JD 链接（可选）
    target_role: Optional[str]        # 目标职位名称（可选）

    # 各节点输出
    resume: Optional[ResumeAnalysis]
    jd: Optional[JDAnalysis]
    matched_jobs: Optional[list[dict]]
    gap: Optional[GapAnalysis]
    polish_suggestions: Optional[list[PolishSuggestion]]
    score: Optional[ScoreReport]

    # 工作流控制
    retry_count: int                  # 重试次数
    max_retries: int                  # 最大重试次数
    error: Optional[str]              # 错误信息
```

### 4.3 节点定义

#### 4.3.1 简历解析节点 (parse_resume)

```python
# src/resume_agent/nodes.py

def parse_resume(state: AgentState, llm) -> dict:
    """
    解析简历文本，提取结构化信息。

    输入: state.resume_text
    输出: state.resume (ResumeAnalysis)

    策略:
    - 使用 LLM 提取工作经验、技能列表、教育背景、项目经历
    - 识别当前职位名称、工作年限、学历等级
    - 输出结构化 JSON
    """
    prompt = RESUME_PARSE_PROMPT.format(resume_text=state["resume_text"])
    response = llm.invoke(prompt)
    parsed = parse_llm_json(response.content)
    return {"resume": parsed}
```

#### 4.3.2 JD 分析节点 (analyze_jd)

```python
def analyze_jd(state: AgentState, llm) -> dict:
    """
    分析目标 JD，提取技能要求、职责、经验门槛。

    输入: state.target_jd_text
    输出: state.jd (JDAnalysis)

    策略:
    - 硬性技能 vs 加分技能分离
    - 调用 RoleClassifier.llm_extract() 获取角色分类
    - 提取经验年限、学历要求
    """
    prompt = JD_ANALYSIS_PROMPT.format(jd_text=state["target_jd_text"])
    response = llm.invoke(prompt)
    jd_data = parse_llm_json(response.content)

    # 复用现有 RoleClassifier 获取角色分类
    from src.analyzer.role_classifier import RoleClassifier
    classifier = RoleClassifier()
    role = classifier.classify(state["target_jd_text"])
    jd_data["role_category"] = role.get("role_id", "other")

    return {"jd": jd_data}
```

#### 4.3.3 岗位匹配节点 (match_jobs)

```python
def match_jobs(state: AgentState) -> dict:
    """
    从知识库中召回与目标 JD 相似的岗位，作为润色参考。

    输入: state.target_jd_text
    输出: state.matched_jobs (list[dict])

    策略:
    - 复用 VectorStore.search() 语义检索
    - 返回 top_k=5 相似岗位的 title、skills、salary_range
    - 这些岗位用于 gap_analysis 和 generate_polish 的市场参考
    """
    from src.embeddings.vector_store import VectorStore
    store = VectorStore()
    results = store.search(state["target_jd_text"], top_k=5)

    matched = []
    for r in results:
        matched.append({
            "title": r.get("title", ""),
            "company": r.get("company", ""),
            "score": r.get("score", 0),
            "snippet": r.get("snippet", ""),
        })

    return {"matched_jobs": matched}
```

#### 4.3.4 差距分析节点 (gap_analysis)

```python
def gap_analysis(state: AgentState, llm) -> dict:
    """
    对比简历 vs JD，识别技能缺口和优化方向。

    输入: state.resume, state.jd, state.matched_jobs
    输出: state.gap (GapAnalysis)

    策略:
    - LLM 对比分析：简历技能列表 vs JD 要求技能
    - 分类为 matched/missing/weak
    - 结合相似岗位的市场数据给出关键词建议
    - 识别经验描述差距（如"用过"vs"精通"）
    """
    prompt = GAP_ANALYSIS_PROMPT.format(
        resume=json.dumps(state["resume"], ensure_ascii=False),
        jd=json.dumps(state["jd"], ensure_ascii=False),
        matched_jobs=json.dumps(state["matched_jobs"], ensure_ascii=False),
    )
    response = llm.invoke(prompt)
    gap = parse_llm_json(response.content)
    return {"gap": gap}
```

#### 4.3.5 润色生成节点 (generate_polish)

```python
def generate_polish(state: AgentState, llm) -> dict:
    """
    逐段生成简历润色建议。

    输入: state.resume, state.jd, state.gap
    输出: state.polish_suggestions (list[PolishSuggestion])

    策略:
    - 每段独立优化（工作经验、技能列表、项目经历、个人简介）
    - 遵循 STAR 原则改写经历描述
    - 嵌入 JD 中的关键词
    - 保持真实性，不编造经历
    - 适配香港招聘市场的语言风格（英文为主）
    """
    prompt = POLISH_PROMPT.format(
        resume=json.dumps(state["resume"], ensure_ascii=False),
        jd=json.dumps(state["jd"], ensure_ascii=False),
        gap=json.dumps(state["gap"], ensure_ascii=False),
    )
    response = llm.invoke(prompt)
    suggestions = parse_llm_json(response.content)
    return {"polish_suggestions": suggestions}
```

#### 4.3.6 评分验证节点 (score_and_verify)

```python
def score_and_verify(state: AgentState, llm) -> dict:
    """
    对润色结果进行多维评分。

    输入: state.resume, state.jd, state.polish_suggestions
    输出: state.score (ScoreReport)

    评分维度:
    - keyword_coverage: 关键词覆盖率（JD 中的关键词在润色后简历中的出现比例）
    - experience_alignment: 经验匹配度（工作描述是否贴合 JD 要求）
    - skill_relevance: 技能相关性（展示的技能是否对目标岗位有价值）
    - language_quality: 语言质量（语法、表达、专业度）

    条件分支:
    - overall_score >= 7: 输出结果
    - overall_score < 7 且 retry_count < max_retries: 回退到 gap_analysis
    """
    prompt = SCORE_PROMPT.format(
        resume=json.dumps(state["resume"], ensure_ascii=False),
        jd=json.dumps(state["jd"], ensure_ascii=False),
        suggestions=json.dumps(state["polish_suggestions"], ensure_ascii=False),
    )
    response = llm.invoke(prompt)
    score = parse_llm_json(response.content)
    return {"score": score}
```

### 4.4 工作流编排

```python
# src/resume_agent/graph.py

import json
from typing import Literal
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI

from src.resume_agent.state import AgentState
from src.resume_agent.nodes import (
    parse_resume,
    analyze_jd,
    match_jobs,
    gap_analysis,
    generate_polish,
    score_and_verify,
)
from src.llm_config_manager import LLMConfigManager


def build_resume_agent() -> StateGraph:
    """构建简历润色 Agent 工作流图"""

    # 初始化 LLM（复用系统配置）
    config = LLMConfigManager().build_kwargs()
    llm = ChatOpenAI(
        api_key=config["api_key"],
        base_url=config["api_base"],
        model=config["model"],
        temperature=0.3,
    )

    # 构建图
    workflow = StateGraph(AgentState)

    # 添加节点
    workflow.add_node("parse_resume", lambda s: parse_resume(s, llm))
    workflow.add_node("analyze_jd", lambda s: analyze_jd(s, llm))
    workflow.add_node("match_jobs", match_jobs)
    workflow.add_node("gap_analysis", lambda s: gap_analysis(s, llm))
    workflow.add_node("generate_polish", lambda s: generate_polish(s, llm))
    workflow.add_node("score_and_verify", lambda s: score_and_verify(s, llm))

    # 设置入口
    workflow.set_entry_point("parse_resume")

    # 添加边
    workflow.add_edge("parse_resume", "analyze_jd")
    workflow.add_edge("analyze_jd", "match_jobs")
    workflow.add_edge("match_jobs", "gap_analysis")
    workflow.add_edge("gap_analysis", "generate_polish")
    workflow.add_edge("generate_polish", "score_and_verify")

    # 条件分支：评分达标则结束，否则重试
    def should_retry(state: AgentState) -> Literal["gap_analysis", "__end__"]:
        if state.get("score") and state["score"].get("overall_score", 0) >= 7:
            return END
        if state.get("retry_count", 0) < state.get("max_retries", 2):
            state["retry_count"] = state.get("retry_count", 0) + 1
            return "gap_analysis"
        return END

    workflow.add_conditional_edges("score_and_verify", should_retry)

    return workflow.compile()


def run_resume_agent(resume_text: str, jd_text: str, **kwargs) -> dict:
    """运行简历润色 Agent 的便捷入口"""
    agent = build_resume_agent()
    initial_state = AgentState(
        resume_text=resume_text,
        target_jd_text=jd_text,
        target_jd_url=kwargs.get("jd_url"),
        target_role=kwargs.get("target_role"),
        retry_count=0,
        max_retries=kwargs.get("max_retries", 2),
    )
    result = agent.invoke(initial_state)
    return result
```

---

## 5. 模块详细设计

### 5.1 模块结构

```
src/resume_agent/
├── __init__.py           # 模块入口，导出 run_resume_agent
├── graph.py              # LangGraph 工作流编排
├── nodes.py              # 6 个 Agent 节点实现
├── state.py              # AgentState TypedDict 定义
├── prompts.py            # 所有 Prompt 模板
├── models.py             # Pydantic 数据模型
└── utils.py              # 工具函数（JSON 解析、格式校验等）
```

### 5.2 模块职责

| 文件 | 职责 | 关键类/函数 |
|------|------|------------|
| `__init__.py` | 导出 `run_resume_agent()` 入口 | `run_resume_agent` |
| `graph.py` | LangGraph 工作流构建与编排 | `build_resume_agent()` |
| `nodes.py` | 各 Agent 节点业务逻辑 | `parse_resume`, `analyze_jd`, `match_jobs`, `gap_analysis`, `generate_polish`, `score_and_verify` |
| `state.py` | Agent 工作流状态定义 | `AgentState`, `ResumeAnalysis`, `JDAnalysis`, `GapAnalysis`, `PolishSuggestion`, `ScoreReport` |
| `prompts.py` | 所有系统/用户 Prompt | `RESUME_PARSE_PROMPT`, `JD_ANALYSIS_PROMPT`, `GAP_ANALYSIS_PROMPT`, `POLISH_PROMPT`, `SCORE_PROMPT` |
| `models.py` | 请求/响应 Pydantic 模型 | `ResumePolishRequest`, `ResumePolishResponse`, `ScoreReport` |
| `utils.py` | 通用工具 | `parse_llm_json()`, `validate_resume_text()` |

### 5.3 与现有模块的依赖关系

| 现有模块 | 依赖位置 | 用途 |
|---------|---------|------|
| `src.llm_config_manager.LLMConfigManager` | `graph.py` | 读取 LLM 配置（key/base_url/model） |
| `src.embeddings.vector_store.VectorStore` | `nodes.py` (match_jobs) | 语义搜索相似岗位 |
| `src.analyzer.role_classifier.RoleClassifier` | `nodes.py` (analyze_jd) | JD 角色分类 |
| `src.analyzer.llm_engine.LLMExtractor` | （不直接依赖） | LangChain 替代裸 requests 调用 |
| `config.settings.settings` | `graph.py` | 读取系统全局配置 |
| `src.logger.get_logger` | 各文件 | 日志记录 |

---

## 6. Prompt 设计

### 6.1 简历解析 Prompt

```python
# src/resume_agent/prompts.py

RESUME_PARSE_SYSTEM_PROMPT = """你是一个专业的简历解析专家。你的任务是从简历文本中提取结构化信息。

要求：
1. 提取所有工作经验（公司、职位、时间段、职责描述）
2. 提取技术技能（编程语言、框架、工具、平台）
3. 提取教育背景（学校、专业、学历、毕业时间）
4. 提取项目经历（项目名称、技术栈、职责）
5. 估算总工作年限
6. 识别当前/最近职位名称

输出格式为 JSON，包含以下字段：
- sections: dict，按段落名分组的内容
- raw_skills: list[str]，所有技能列表
- years_of_experience: float 或 null
- education_level: str 或 null
- current_titles: list[str]
"""

RESUME_PARSE_PROMPT = """请解析以下简历文本，返回结构化 JSON：

{resume_text}
"""
```

### 6.2 JD 分析 Prompt

```python
JD_ANALYSIS_SYSTEM_PROMPT = """你是一个香港 IT 招聘市场的 JD 分析专家。你的任务是从岗位描述中提取关键信息。

分析维度：
1. 硬性技能要求（must-have）：招聘方明确要求的技术栈
2. 加分技能（nice-to-have）：招聘方提到的加分项
3. 核心职责：该岗位的主要工作内容
4. 经验要求：最低工作年限
5. 学历要求：最低学历
6. 语言要求：是否需要粤语/英语/普通话

注意区分：
- "精通/熟练/strong in" → 硬性要求
- "熟悉/了解/experience with" → 加分项
- "优先/plus/加分" → 加分项

输出 JSON 格式：
{
    "required_skills": [...],
    "preferred_skills": [...],
    "responsibilities": [...],
    "min_experience": float | null,
    "education_required": str | null,
    "language_requirements": [...],
    "key_requirements": [...]
}
"""

JD_ANALYSIS_PROMPT = """请分析以下香港 IT 岗位 JD，提取结构化信息：

{jd_text}
"""

# 在 analyze_jd 节点中，system 和 user 消息组合如下
def build_jd_analysis_messages(jd_text: str) -> list[dict]:
    return [
        {"role": "system", "content": JD_ANALYSIS_SYSTEM_PROMPT},
        {"role": "user", "content": JD_ANALYSIS_PROMPT.format(jd_text=jd_text)},
    ]
```

### 6.3 差距分析 Prompt

```python
GAP_ANALYSIS_SYSTEM_PROMPT = """你是一个专业的简历-JD 匹配分析专家。你的任务是深入对比简历内容与目标岗位要求，识别差距与优化机会。

分析维度：
1. 技能匹配：逐一对比简历中的技能与 JD 要求的技能
   - matched: 简历中已具备且 JD 要求的技能
   - missing: JD 要求但简历中未出现的技能
   - weak: 简历中有提及但描述不够突出/深度的技能

2. 经验匹配：对比简历中的工作描述与 JD 职责要求
   - 是否有直接相关的经验
   - 是否可以用已有经验"重新表述"来匹配 JD
   - 经验年限是否达标

3. 关键词优化建议：
   - 给出应在简历中的"工作经验"部分嵌入的关键词
   - 按优先级排序（high/medium/low）

4. 表达层次提升：
   - "使用过" → 可以升级为"精通"还是保持"了解"
   - 建议使用更主动/量化的动词

重要原则：
- 保持真实性，不得建议编造经历
- 可以在真实经历的基础上优化表达角度
- 可以建议重新排序技能优先级
"""

GAP_ANALYSIS_PROMPT = """请对比以下简历与目标 JD，进行差距分析。

## 简历信息
{resume}

## 目标 JD 要求
{jd}

## 相似岗位市场参考（来自香港招聘数据库）
{matched_jobs}

请返回 JSON 格式的差距分析结果：
{{
    "matched_skills": [...],      // 已匹配的技能
    "missing_skills": [...],      // 缺失的关键技能
    "weak_skills": [...],         // 需加强的技能
    "experience_gap": "...",      // 经验差距描述
    "keyword_suggestions": [      // 关键词优化建议
        {{"keyword": "...", "priority": "high/medium/low", "placement": "工作经验/技能/项目"}}
    ]
}}
"""
```

### 6.4 润色生成 Prompt

```python
POLISH_SYSTEM_PROMPT = """你是一个专业的简历润色专家，专注于香港 IT 招聘市场。你的任务是根据差距分析结果，逐段优化简历内容。

润色原则：
1. 保持真实性：基于简历原文优化表达，不编造经历
2. 关键词覆盖：在合适的上下文嵌入目标 JD 中的关键词
3. STAR 原则：对工作经历采用 Situation-Task-Action-Result 结构改写
4. 量化成果：尽量增加可量化的结果描述（如"将性能提升了 40%"）
5. 本地化适配：使用香港招聘市场通用的表达方式（英文为主）
6. 技能优先级：将 JD 最看重的技能放在段落前面
7. 简洁有力：每段不超过 5 行，用动词开头

输出格式：
[
    {{
        "section": "工作经验",           // 段落名称
        "original": "原文内容...",        // 该段原文
        "suggested": "润色后内容...",     // 润色后文本
        "changes": [                      // 修改说明列表
            "将'用过 Python'改为'使用 Python 构建了...'",
            "嵌入关键词：AWS Lambda、Kubernetes"
        ],
        "keywords_added": ["AWS Lambda", "Kubernetes"]
    }},
    ...
]
"""

POLISH_PROMPT = """请根据以下信息对简历进行逐段润色优化。

## 简历原文
{resume}

## 目标 JD 要求
{jd}

## 差距分析结果
{gap}

请逐段给出润色建议，返回 JSON 数组。
"""
```

### 6.5 评分 Prompt

```python
SCORE_SYSTEM_PROMPT = """你是一个简历质量评分专家。对润色后的简历进行 1-10 分的多维评分。

评分维度：
1. keyword_coverage (1-10)：JD 中的关键要求项在简历中的覆盖比例
   - 10 = 所有关键要求都在简历中有对应体现
   - 1 = 几乎没有覆盖

2. experience_alignment (1-10)：工作经历与 JD 职责的匹配程度
   - 10 = 每段经历都直接相关且有 STAR 描述
   - 1 = 经历完全不相关

3. skill_relevance (1-10)：展示的技能与目标岗位的关联度
   - 10 = 只展示 JD 最看重的技能
   - 1 = 展示大量不相关技能

4. language_quality (1-10)：语言表达的专业度
   - 10 = 语法正确、动词精准、量化成果
   - 1 = 语法错误多、表达笼统

最终 overall_score = weighted average of above

输出 JSON:
{{
    "overall_score": 8.5,
    "keyword_coverage": 8.0,
    "experience_alignment": 7.5,
    "skill_relevance": 9.0,
    "language_quality": 8.5,
    "suggestions": ["建议在技能部分强调 AWS 相关经验"]
}}
"""

SCORE_PROMPT = """请对以下润色结果进行评分。

## 简历原文（润色前）
{resume}

## 目标 JD
{jd}

## 润色建议
{suggestions}

请返回 JSON 格式的评分报告。
"""
```

---

## 7. 后端 API 设计

### 7.1 API 端点

| 方法 | 端点 | 说明 | 请求体 | 响应 |
|------|------|------|--------|------|
| POST | `/api/resume/polish` | 全流程简历润色 | `ResumePolishRequest` | `ResumePolishResponse` |
| POST | `/api/resume/analyze` | 仅分析不润色 | `ResumeAnalyzeRequest` | `ResumeAnalyzeResponse` |
| POST | `/api/resume/match-jobs` | 仅岗位匹配 | `JobMatchRequest` | `JobMatchResponse` |

### 7.2 Pydantic 模型

```python
# src/resume_agent/models.py

from pydantic import BaseModel, Field
from typing import Optional


class ResumePolishRequest(BaseModel):
    """简历润色请求"""
    resume_text: str = Field(..., description="简历原文", min_length=50, max_length=50000)
    jd_text: str = Field(..., description="目标 JD 原文", min_length=50, max_length=20000)
    jd_url: Optional[str] = Field(None, description="JD 链接（可选）")
    target_role: Optional[str] = Field(None, description="目标职位名称")
    max_retries: int = Field(2, description="最大重试次数", ge=0, le=5)


class PolishSection(BaseModel):
    """单段润色建议"""
    section: str
    original: str
    suggested: str
    changes: list[str]
    keywords_added: list[str]


class ScoreReport(BaseModel):
    """评分报告"""
    overall_score: float
    keyword_coverage: float
    experience_alignment: float
    skill_relevance: float
    language_quality: float
    suggestions: list[str]


class ResumePolishResponse(BaseModel):
    """简历润色响应"""
    success: bool
    polish_suggestions: list[PolishSection]
    score: Optional[ScoreReport] = None
    gap_analysis: Optional[dict] = None
    matched_jobs: Optional[list[dict]] = None
    error: Optional[str] = None
```

### 7.3 API 路由

```python
# api/routers/resume.py

from fastapi import APIRouter, HTTPException
from src.resume_agent.models import ResumePolishRequest, ResumePolishResponse
from src.resume_agent import run_resume_agent

router = APIRouter(prefix="/api/resume", tags=["简历润色"])


@router.post("/polish", response_model=ResumePolishResponse)
async def polish_resume(request: ResumePolishRequest):
    """简历润色全流程：解析 → 分析 → 匹配 → 差距分析 → 润色 → 评分"""
    try:
        result = run_resume_agent(
            resume_text=request.resume_text,
            jd_text=request.jd_text,
            jd_url=request.jd_url,
            target_role=request.target_role,
            max_retries=request.max_retries,
        )
        return ResumePolishResponse(
            success=True,
            polish_suggestions=result.get("polish_suggestions", []),
            score=result.get("score"),
            gap_analysis=result.get("gap"),
            matched_jobs=result.get("matched_jobs"),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### 7.4 注册到主应用

```python
# api/main.py（追加）

from api.routers import resume  # 新增导入

app.include_router(resume.router)  # 新增注册
```

---

## 8. 前端设计

### 8.1 页面路由

| 路由 | 页面 | 说明 |
|------|------|------|
| `/resume` | `ResumePage.vue` | 简历润色入口 |

侧边栏新增导航项："简历润色"，图标 `DocumentEdit`。

### 8.2 页面布局

```
┌─────────────────────────────────────────────────────────────┐
│  简历润色                                                    │
│  ───────────────────────────────────────────────────────────  │
│                                                               │
│  ┌─ 左侧：输入区 ────────────┐  ┌─ 右侧：结果区 ────────────┐ │
│  │                            │  │                            │ │
│  │  简历原文 (文本域)          │  │  润色建议（分 Tab 展示）    │ │
│  │  ┌─────────────────────┐  │  │  ┌─ Tab1: 整体评分 ────┐  │ │
│  │  │ 粘贴简历内容...       │  │  │  │ 评分雷达图          │  │ │
│  │  └─────────────────────┘  │  │  │ 关键词覆盖率: ███ 8/10│  │ │
│  │                            │  │  │ 经验匹配度:   ████ 9/10│  │ │
│  │  目标 JD (文本域)          │  │  │ 技能相关性:  ████ 8/10│  │ │
│  │  ┌─────────────────────┐  │  │  │ 语言质量:    ████ 7/10│  │ │
│  │  │ 粘贴目标 JD 内容...   │  │  │  └────────────────────┘  │ │
│  │  └─────────────────────┘  │  │                            │ │
│  │                            │  │  ┌─ Tab2: 逐段对比 ────┐  │ │
│  │  [开始润色] [清空]        │  │  │  ┌─── 工作经验 ────┐  │  │ │
│  │                            │  │  │ 对比模式:           │  │ │
│  │  可选：                     │  │  │ 原文 | 润色后       │  │ │
│  │  ☐ JD 链接                 │  │  │ "用过 Python..."    │  │ │
│  │  ☐ 目标职位名称             │  │  │ "使用 Python 构..." │  │ │
│  │                            │  │  │ 修改: +2 关键词    │  │ │
│  └────────────────────────────┘  │  └────────────────────┘  │ │
│                                   │                            │ │
│                                   │  ┌─ Tab3: 差距分析 ────┐  │ │
│                                   │  │  ✅ 已匹配: Python... │  │ │
│                                   │  │  ❌ 缺失: K8s,Docker  │  │ │
│                                   │  │  🔺 需加强: AWS      │  │ │
│                                   │  └────────────────────┘  │ │
│                                   │                            │ │
│                                   │  [导出润色结果] [复制全文]  │ │
│                                   └────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 8.3 状态管理

```typescript
// web/src/stores/resume.ts

import { defineStore } from 'pinia'
import { api } from '@/api/client'

interface PolishSection {
  section: string
  original: string
  suggested: string
  changes: string[]
  keywords_added: string[]
}

interface ScoreReport {
  overall_score: number
  keyword_coverage: number
  experience_alignment: number
  skill_relevance: number
  language_quality: number
  suggestions: string[]
}

interface PolishResult {
  polish_suggestions: PolishSection[]
  score: ScoreReport | null
  gap_analysis: any
  matched_jobs: any[]
}

export const useResumeStore = defineStore('resume', {
  state: () => ({
    resumeText: '',
    jdText: '',
    jdUrl: '',
    targetRole: '',
    loading: false,
    result: null as PolishResult | null,
    error: '',
    activeTab: 'score',     // score | diff | gap
  }),

  actions: {
    async polish() {
      this.loading = true
      this.error = ''
      try {
        const response = await api.post('/api/resume/polish', {
          resume_text: this.resumeText,
          jd_text: this.jdText,
          jd_url: this.jdUrl || undefined,
          target_role: this.targetRole || undefined,
        })
        this.result = response.data
      } catch (e: any) {
        this.error = e.message || '润色失败，请检查 LLM 配置'
      } finally {
        this.loading = false
      }
    },

    clear() {
      this.resumeText = ''
      this.jdText = ''
      this.jdUrl = ''
      this.targetRole = ''
      this.result = null
      this.error = ''
    },
  },
})
```

### 8.4 组件树

```
ResumePage.vue
├── ResumeInput.vue          # 简历/JD 输入区
│   ├── TextAreaField.vue    # 文本域组件（简历原文）
│   └── TextAreaField.vue    # 文本域组件（目标 JD）
├── ResumeResult.vue         # 结果展示区
│   ├── ScoreTab.vue         # 评分 Tab（雷达图）
│   │   ├── RadarChart.vue   # 评分雷达图
│   │   └── ScoreCard.vue    # 评分卡片
│   ├── DiffTab.vue          # 逐段对比 Tab
│   │   └── SectionDiff.vue  # 段落对比组件（左右对照）
│   └── GapTab.vue           # 差距分析 Tab
│       ├── SkillMatchList.vue    # 技能匹配列表
│       └── KeywordSuggestion.vue # 关键词建议
└── ActionBar.vue            # 操作栏
    ├── ExportButton.vue     # 导出按钮
    └── CopyButton.vue       # 复制按钮
```

### 8.5 与现有前端的集成

路由注册（`web/src/router/index.ts`）：

```typescript
{
  path: '/resume',
  name: 'resume',
  component: () => import('@/views/ResumePage.vue'),
  meta: { title: '简历润色', icon: 'DocumentEdit', requiresAuth: false },
}
```

侧边栏导航（`web/src/components/AppSidebar.vue`）新增菜单项。

---

## 9. 可复用基础设施清单

| 现有模块 | 复用方式 | 备注 |
|---------|---------|------|
| [LLMConfigManager](file:///e:/文档/Project/HK-JobMarket-Analyzer/src/llm_config_manager.py) | 直接导入 | 读取 LLM key/base_url/model |
| [VectorStore.search()](file:///e:/文档/Project/HK-JobMarket-Analyzer/src/embeddings/vector_store.py#L131) | 直接调用 | 岗位语义匹配 |
| [RoleClassifier](file:///e:/文档/Project/HK-JobMarket-Analyzer/src/analyzer/role_classifier.py) | 复用 classify() | JD 角色分类 |
| [settings](file:///e:/文档/Project/HK-JobMarket-Analyzer/config/settings.py) | 直接导入 | 全局配置 |
| [Translator](file:///e:/文档/Project/HK-JobMarket-Analyzer/src/i18n/translator.py) | 前端显示用 | 地点/类别中文化 |
| [config/tech_dict.json](file:///e:/文档/Project/HK-JobMarket-Analyzer/config/tech_dict.json) | 差距分析参考 | 技能词表 |
| [config/i18n/locations_zh.json](file:///e:/文档/Project/HK-JobMarket-Analyzer/config/i18n/locations_zh.json) | 前端显示 | 地点中文映射 |
| [config/settings.py](file:///e:/文档/Project/HK-JobMarket-Analyzer/config/settings.py) | 直接导入 | .env 配置 |
| Docker / docker-compose.yml | 无需改动 | 新增路由后自动包含 |
| FastAPI CORS 配置 | 无需改动 | 自动支持新路由 |

---

## 10. 文件清单

### 10.1 新增文件

| 文件 | 用途 | 预估行数 |
|------|------|---------|
| `src/resume_agent/__init__.py` | 模块入口，导出 `run_resume_agent` | 10 |
| `src/resume_agent/graph.py` | LangGraph 工作流构建 | 80 |
| `src/resume_agent/nodes.py` | 6 个 Agent 节点实现 | 200 |
| `src/resume_agent/state.py` | AgentState TypedDict | 80 |
| `src/resume_agent/prompts.py` | Prompt 模板 | 250 |
| `src/resume_agent/models.py` | Pydantic 请求/响应模型 | 60 |
| `src/resume_agent/utils.py` | 工具函数 | 40 |
| `api/routers/resume.py` | 简历润色 API 路由 | 50 |
| `web/src/views/ResumePage.vue` | 简历润色页面 | 300 |
| `web/src/stores/resume.ts` | 简历润色状态管理 | 80 |
| `web/src/api/resume.ts` | 简历润色 API 封装 | 20 |
| `web/src/components/resume/ResumeInput.vue` | 简历/JD 输入组件 | 100 |
| `web/src/components/resume/ResumeResult.vue` | 结果展示容器 | 50 |
| `web/src/components/resume/ScoreTab.vue` | 评分展示 Tab | 80 |
| `web/src/components/resume/DiffTab.vue` | 逐段对比 Tab | 100 |
| `web/src/components/resume/GapTab.vue` | 差距分析 Tab | 80 |
| `requirements-resume.txt` | 可选 LangGraph/LangChain 依赖 | 5 |

**总计新增：约 1585 行**

### 10.2 修改文件

| 文件 | 修改内容 |
|------|---------|
| `api/main.py` | 追加 `app.include_router(resume.router)` |
| `web/src/router/index.ts` | 追加 `/resume` 路由 |
| `web/src/components/AppSidebar.vue` | 追加"简历润色"导航项 |
| `web/src/api/client.ts` | （可选）如有需要可追加拦截规则 |

---

## 11. 里程碑规划

| 里程碑 | 内容 | 预估工时 | 依赖 |
|-------|------|---------|------|
| **M1** 基础搭建 | `state.py` + `models.py` + `utils.py`，定义数据结构和工具函数 | 0.5 天 | — |
| **M2** Prompt 工程 | `prompts.py`，完成 5 套 Prompt 的设计与测试 | 1 天 | M1 |
| **M3** 节点实现 | `nodes.py`，实现 6 个 Agent 节点，单节点单元测试 | 1.5 天 | M1 + M2 |
| **M4** 工作流编排 | `graph.py`，LangGraph 图构建 + 条件分支 + 端到端测试 | 1 天 | M3 |
| **M5** 后端 API | `api/routers/resume.py`，注册路由 + 参数校验 + 错误处理 | 0.5 天 | M4 |
| **M6** 前端页面 | ResumePage.vue + Pinia store + 组件实现 | 1.5 天 | M5 |
| **M7** 联调与优化 | 前后端联调、Prompt 调优、边界情况处理 | 1 天 | M5 + M6 |
| **M8** 集成测试 | pytest 测试 + 前端 Vitest 测试 | 0.5 天 | M7 |

**总计预估工时：7.5 天**

---

## 12. v2.9 增强工作流设计

### 12.1 设计背景

v2.8 已将简历 Agent 从 MVP 推进到可用的智能润色工作流：

- PDF 简历读取与前端上传回填。
- 目标 JD 选填，缺省时基于知识库合成目标岗位画像。
- MongoDB 全文检索 + ChromaDB 向量检索 + Qwen3 rerank 的混合召回。
- 市场上下文、整库岗位需求洞察、评分讲解。
- SSE 流式输出，先完成阶段先展示。

但当前工作流仍主要集中于“简历润色 / 岗位匹配”，缺少完整求职链路中的几个关键环节：

- 开工前的输入体检与降级策略。
- 简历润色前的独立岗位调研阶段。
- 对每个简历 claim 的证据化审计。
- 从最终简历 bullet 到面试准备的闭环。
- 质量闸门与回归评测。
- 用户长期素材库，包括基础简历、个人档案、项目库。

v2.9 目标是把现有简历 Agent 从“润色工具”升级为“香港 IT 求职全链路工作流”：先理解岗位，再选择和翻译真实经历，最后生成可被面试追问的安全表达。

### 12.2 总体增强链路

```text
Stage 0 输入体检
→ Stage 1 JobResearch 岗位 / 市场调研
→ Stage 2 简历解析与项目素材抽取
→ Stage 3 JD / 市场画像分析
→ Stage 4 经历 - 岗位能力匹配矩阵
→ Stage 5 简历 bullet 改写
→ Stage 6 证据审计与风险降级
→ Stage 7 评分与质量闸门
→ Stage 8 面试准备：逐 bullet 深挖 + 风险地图 + 自我介绍
```

与现有 v2.8 的衔接：

- `HybridJobSearch` 继续作为 `JobResearch` 与 `match_jobs` 的召回底座。
- `market_context` / `market_insights` 从内部辅助上下文前置为可见的岗位调研产物。
- `run_resume_agent_stream` 扩展事件：`input_health` / `job_research` / `evidence_audit` / `interview_prep`。
- 前端结果区新增：`岗位调研`、`证据审计`、`面试深挖`。

### 12.3 Stage 0：输入体检

目标：在进入调研和改写前，先判断输入是否足够、哪些可自动补齐、哪些必须提示用户。

建议新增数据结构：

```python
class InputHealth(BaseModel):
    status: Literal["complete", "workable", "blocked"]
    target_company: str | None = None
    target_role: str | None = None
    target_market: str | None = None
    jd_status: Literal["provided", "missing", "partial"]
    resume_status: Literal["provided", "missing", "partial", "parse_failed"]
    application_status: Literal["not_applied", "applied", "unknown"]
    interview_stage: str | None = None
    assumptions: list[str] = []
    gaps: list[str] = []
    blocking_questions: list[str] = []
```

状态定义：

| 状态 | 说明 | 处理 |
|------|------|------|
| `complete` | 目标岗位、市场/JD、简历、投递状态足够明确 | 直接进入后续阶段 |
| `workable` | 有缺口但不阻塞 | 自动推断、知识库补齐、低置信标注后继续 |
| `blocked` | 缺少目标岗位或简历正文等硬输入 | 停止生成，只问最少必要问题 |

自动恢复策略：

- 缺 JD：有目标岗位时用知识库生成市场岗位画像；后续可选 WebSearch 找官方 / 同岗 JD。
- 缺市场：优先从岗位语言、地点、平台、公司实体推断；推不出时标记 `target_market=unknown`。
- 简历只有片段：只处理已提供内容，并输出素材缺口清单。
- 已投递：不再建议改动已投版本，转入面试准备与风险兜底。
- 轮次未知：不硬生成 HR 面 / 二面 / 三面，只输出通用面试深挖和待确认轮次。

### 12.4 Stage 1：JobResearch 知识库岗位调研

目标：将现有岗位知识库能力前置，形成独立的岗位调研报告，为简历改写和面试准备提供共同靶心。

推荐分层：

```text
JobResearch
├─ KB Research：基于本地 MongoDB / ChromaDB / HybridSearch 分析香港 IT 市场共性需求
└─ Web Research：后续可选，补公司官网、最新 JD、面经、新闻与产品动态
```

知识库可支撑的调研内容：

- 目标岗位画像：同类岗位常见 title、职责、年限、学历、语言要求。
- 核心能力关键词：从 `skills`、`jd_text`、`kb_document_text` 聚合高频技能。
- 技术栈趋势：Python、AWS、Azure、LangChain、RAG、MLOps 等出现频次。
- 角色方向判断：AI 应用开发、后端、DevOps、数据、Technical PM 等。
- 香港市场措辞：常见英文 JD 表达、responsibilities / requirements 句式。
- 相似岗位样本：召回 5-10 条代表性岗位作为依据。
- 简历改写靶心：收敛成 3-5 个核心能力关键词。
- 置信度与缺口：样本少时标注低置信，不把市场画像伪装成具体公司结论。

边界：

- 知识库能回答“香港市场类似岗位通常要什么”。
- 单靠知识库不能回答“某公司这个具体岗位最新要求是什么”。
- 用户提供 JD 时，JD 是最高优先级；未提供 JD 时，知识库生成“市场岗位画像”。

建议流程：

```text
输入：target_role / target_company / jd_text 可选

1. build_search_query
   优先级：JD 文本 > 目标岗位 + 公司 > 目标岗位 > 简历技能

2. HybridJobSearch
   使用 MongoDB 全文 + ChromaDB 向量 + rerank 召回相似岗位

3. aggregate_market_profile
   聚合 skills、title、role_category、experience、education、language、salary、JD snippets

4. extract_core_capabilities
   输出 3-5 个核心能力关键词

5. build_research_report
   生成岗位调研报告：
   - 样本数量
   - 相似岗位
   - 高频技能
   - 常见职责
   - 隐性门槛
   - 简历改写建议
   - 来源覆盖说明
```

建议数据结构：

```python
class SkillStat(BaseModel):
    name: str
    count: int
    ratio: float | None = None


class JobResearchReport(BaseModel):
    target_role: str | None
    target_company: str | None
    source: Literal["jd", "knowledge_base", "mixed"]
    confidence: Literal["high", "medium", "low"]
    sample_count: int
    core_capabilities: list[str]
    high_frequency_skills: list[SkillStat]
    common_titles: list[str]
    common_responsibilities: list[str]
    hidden_requirements: list[str]
    similar_jobs: list[dict]
    resume_positioning_advice: list[str]
    source_coverage_note: str
```

### 12.5 Stage 2：长期素材库与项目素材抽取

参考 `job-hunt-copilot-public.skill`，建议为 Agent 增加长期素材层：

```text
resources/
├─ self_profile.md      # 用户背景、求职偏好、技能标签
├─ resume_base.md       # 全量基础简历
└─ projects/            # 项目素材库
   └─ {project_name}.md
```

项目模板字段：

- 项目名称、组织、时间周期、角色与团队规模。
- 背景与问题。
- 从 0 到 1 的关键过程。
- 结果与数据。
- 原始素材区。
- 能力标签。

用途：

- 按 JD / JobResearch 从项目库中选择 2-4 个最相关项目。
- 将真实经历翻译成目标岗位语言。
- 为每条 bullet 提供证据来源。
- 支撑面试项目讲稿和 STAR 结构回答。

隐私策略：

- 默认不自动持久化用户上传的简历原文。
- 项目库 / 基础简历保存前应由用户确认。
- 生成版本可保存摘要、结构化字段和用户确认后的内容，不保存未经确认的敏感原文。

### 12.6 Stage 4：经历 - 岗位能力匹配矩阵

目标：把 JobResearch 产出的岗位能力要求，与用户真实经历和项目素材建立映射，决定哪些经历应放大、弱化或删除。

建议数据结构：

```python
class ExperienceCapabilityMatch(BaseModel):
    capability: str
    source_basis: str
    matched_experiences: list[str]
    evidence_strength: Literal["strong", "medium", "weak", "missing"]
    suggested_resume_angle: str
    risk_note: str | None = None
```

匹配原则：

- 每个核心能力必须尽量找到真实经历支撑。
- 没有真实锚点的能力不能写成用户已具备，只能放入“补强建议”。
- 最相关项目 / 经历优先前置。
- 跨背景表达要自然融入 bullet，不输出“迁移句:”等工作痕迹。

### 12.7 Stage 6：证据审计与风险降级

目标：对最终简历中的数字、强动词、职责边界和成果 claim 做结构化审计，避免过度包装和面试追问崩塌。

建议新增数据结构：

```python
class ClaimEvidence(BaseModel):
    claim: str
    claim_type: Literal["number", "role", "skill", "achievement", "education", "employment"]
    source: Literal["resume", "project_library", "user_confirmed", "inferred"]
    confidence: Literal["strong", "medium", "weak", "risky"]
    action: Literal["keep", "soften", "remove", "ask_user"]
    interview_strategy: str
```

处理原则：

- 每个数字、强动词、成果 claim 都要有来源或降级策略。
- 讲不清来源的数字模糊化或删除。
- 学历、在职时间、职位名称、公司名等背调硬信息不改。
- 市场 JD 中出现的技能不能直接写成用户经历，除非用户简历或项目素材中已有证据。
- `risky` claim 如果简历未投，应建议删除或改弱；如果已投，应生成诚实兜底话术。

### 12.8 Stage 8：面试准备与 bullet 深挖

目标：将最终简历每一条 bullet 转成可被面试追问的讲法，形成简历到面试的下游闭环。

建议新增数据结构：

```python
class ResumeBulletInventory(BaseModel):
    bullet_id: str
    final_text: str
    target_capability: str
    evidence_source: str
    evidence_confidence: Literal["strong", "medium", "weak", "risky"]
    talk_track_30s: str
    expanded_talk_track_90s: str | None = None
    follow_up_questions: list[str]
    deep_follow_up: str | None = None
    risk_notes: list[str]
    fallback_answer: str
    forbidden_claims: list[str] = []
```

每条 bullet 至少覆盖：

- 30 秒口语讲法。
- 2-4 个高概率追问。
- 1 个二三层追问或兜底。
- 证据口径：数字怎么算、样本哪来、基线是什么。
- 不能说什么：容易露馅或过度包装的表达。
- 处理策略：放大、正常讲、降级、转场。

前端展示建议：

- 新增 `面试深挖` Tab。
- 按 bullet ID 展示“原文 / 证明能力 / 讲法 / 追问 / 证据 / 风险”。
- 高风险 bullet 使用醒目但克制的风险标记。
- 支持导出 `面试准备/01-简历bullet逐条深挖.md`。

### 12.9 质量闸门与回归评测

目标：把“简历写得好”拆成可执行、可测试的质量标准。

质量闸门：

| 级别 | 检查重点 |
|------|----------|
| P0 红线 | 造假、背调硬信息改动、低质量来源冒充事实、过度包装、标签泄漏 |
| P1 核心质量 | JD 核心能力映射到真实经历；每条最终 bullet 有面试讲法和证据状态；低置信内容明确标注 |
| P2 体验质量 | 文件名、结构、扫读体验、语言自然度、前端可读性 |

建议回归场景：

- 完整 JD + 完整简历。
- 无 JD，仅目标岗位。
- 简历已投，不允许改写，只准备面试。
- 用户承认某个数字记不清。
- PDF 简历 + 知识库模式。
- 香港岗位 + 英文 JD。
- 轮次未知，不能硬生成 HR 面 / 二面 / 三面。

机器检查可先从结构层做起：

- 正式简历中不得出现 `迁移句:`、`旧版`、`半成品`、`保留作参考` 等工作痕迹。
- 面试准备必须覆盖最终简历的所有 bullet。
- `JobResearchReport` 必须包含来源覆盖说明与置信度。
- `ClaimEvidence` 中 `risky` 项必须有处理策略。

### 12.10 API 与流式事件扩展

建议新增 / 扩展端点：

| 方法 | 路径 | 用途 |
|------|------|------|
| `POST` | `/api/resume/input-health` | 输入体检 |
| `POST` | `/api/resume/job-research` | 独立岗位调研 |
| `POST` | `/api/resume/evidence-audit` | 对润色结果做证据审计 |
| `POST` | `/api/resume/interview-prep` | 生成 bullet 面试深挖 |
| `POST` | `/api/resume/polish-stream` | 扩展现有 SSE 全链路输出 |

SSE 事件建议：

```text
input_health
job_research
resume_analysis
matched_jobs
market_context
market_insights
target_profile
gap
polish
evidence_audit
score
interview_prep
done
error
```

### 12.11 前端增强

现有结果展示建议扩展为：

- `岗位调研`：展示样本数量、核心能力、高频技能、相似岗位、来源覆盖说明。
- `评分`：保留综合评分和逐维原因。
- `逐段对比`：保留原文 / 润色建议 / 修改理由。
- `差距分析`：保留技能差距、市场需求分析、补强建议。
- `证据审计`：展示 claim、来源、置信度、处理建议。
- `面试深挖`：逐 bullet 展示讲法、追问、证据口径、风险和兜底。

输入区建议增加：

- 投递状态：未投 / 已投 / 未确认。
- 目标市场：香港 / 中国大陆 / 美国 / 其他 / 自动判断。
- 工作流模式：只润色 / 岗位调研 + 润色 / 面试准备 / 全链路。
- 是否允许保存到长期素材库。

### 12.12 v2.9 优先级拆解

P0：

- 新增 `InputHealth`、`JobResearchReport`、`ClaimEvidence`、`ResumeBulletInventory` 数据结构。
- 将现有 `market_context` / `market_insights` 提炼为独立 `JobResearch` 阶段。
- 在无 JD 时明确输出“知识库市场画像”，不伪装成具体公司 JD。

P1：

- 简历润色后生成 bullet inventory。
- 每条最终 bullet 生成 30 秒讲法、追问、证据口径、风险等级和兜底话术。
- 前端新增 `岗位调研` 与 `面试深挖` Tab。

P2：

- 增加证据审计与风险地图。
- 对讲不清来源的数字 / 强 claim 进行自动降级建议。
- 增加求职质量闸门测试。

P3：

- 引入用户长期素材库：基础简历、个人档案、项目库。
- 支持按 JD 选择项目、解释选用 / 排除原因。
- 支持生成面试项目讲稿和自我介绍关键字卡。

P4：

- 可选接入 WebSearch：补具体公司官网、最新招聘页、面经、产品动态。
- 支持 Markdown / docx 交付包：
  - `岗位调研.md`
  - `改后简历.docx`
  - `面试准备/00-总览.md`
  - `面试准备/01-简历bullet逐条深挖.md`
  - `面试准备/02-表达状态与自我介绍.md`
  - `面试准备/99-面后复盘题库.md`

---

## 13. 复用统计分析数据

### 13.1 设计背景

统计分析架构重构（见 `doc/统计分析架构重构方案.md`）已经把角色分类链路从"扁平字符串技能列表"升级为**证据驱动、分层、跨行业六维的结构化标签资产**，逐岗位持久化在 `role_cache.json`，并产出一系列治理后的聚合榜单。

但当前简历润色 Agent 几乎没有复用这批资产：

- `analyze_jd` 节点用一套独立、较弱的 Prompt **重新解析目标 JD**，只粗暴二分成 `required_skills` / `preferred_skills`，没有证据、置信度和层级。
- `src/resume_agent/market_insights.py` 只消费两样最粗的数据：
  - 从 `jobs.csv` 的 `skills` 字段数出来的**裸技术词频**（未按 `requirement_level` 过滤，PowerPoint/Excel 等会混入）。
  - `role_cache.json` 里的 `role_id`。在 `_build()` 中重建 `RoleResult` 时**显式丢弃了** `soft_skills` / `tag_profile` / `cross_industry_profile`。

由此带来两处与统计文档 §11.1 同源的质量缺陷，在简历侧被重新复现：

| 缺陷 | 现象 | 与统计文档对应 |
|------|------|---------------|
| 示例当硬要求 | JD 中 "e.g. JavaScript/Go/Java 任一" 的备选语言池，被简历 Agent 当成缺失的硬技能，差距分析和评分都被噪声拉偏 | §11.1「示例技能被当成强要求」 |
| 跨行业能力被压扁 | 只比技术栈，无法区分"会 Python"和"会在金融支付/政府水务场景落地 Python"，简历改写丢失行业迁移价值 | §11.1/§11.10「跨行业复合背景被压扁」 |

本章定义简历工作流**复用统计分析数据**的接入方案：把"自己用弱 Prompt 重新解析 JD + 数裸技能词频"替换为"直接消费已治理好的结构化标签 + 聚合榜单"。

### 13.2 可复用的统计分析数据资产

| 数据资产 | 位置 | 结构要点 | 简历侧消费方 |
|---------|------|---------|-------------|
| `tag_profile` | `role_cache.json` 每条记录 | `technical` / `non_technical` / `experience`，每标签含 `name`/`category`/`requirement_level`(required/preferred/example/inferred)/`confidence`/`evidence` | `analyze_jd`、`gap_analysis`、`score` |
| `cross_industry_profile` | `role_cache.json` | 六维：`industry_context`/`business_scenario`/`solution_domain`/`delivery_motion`/`compliance_standard`/`system_or_asset` | `JobResearch`、经历-能力匹配矩阵 |
| `job_context_profile.summary_tags` | `role_cache.json` | 由 ≥2 维证据触发的组合画像（如"政府公用事业 AI/Digital Twin 售前解决方案"） | `JobResearch` 改写靶心、自我介绍 |
| `soft_skills`（六类） | `role_cache.json` | `education`/`language`/`soft_skill`/`domain_knowledge`/`certification`/`business_skill`，已同义归并为规范中文 | `analyze_jd` 非技术维度、`score.experience_alignment` |
| `taxonomy_candidates` | `role_cache.json` + `data/taxonomy/taxonomy_candidates.json` | 高置信新兴场景候选标签 | `gap_analysis` 前瞻补强建议 |
| `skill_taxonomy.json` + `taxonomy_aliases.json` | `data/taxonomy/` | 正式词库规范写法 + 别名映射（如 `Proof-Of-Concept`→`POC 測試`） | 关键词归一、ATS 适配 |
| `taxonomy_rejections.json` | `data/taxonomy/` | 误判词与负例语境（福利里的 insurance、Tai Po 等） | 证据审计、防止误判词写进简历 |
| `tech_stack_ranking`（已过滤） | `compute_market_insights()` / `stats.py` | 仅统计 required/preferred，排除办公工具 | `JobResearch` 市场上下文 |
| `场景化能力统计` | `stats.py`（§11.10.5） | 跨行业能力趋势（金融支付/零售 ERP/政府投标 POC/物流 TMS/设备监测…） | `JobResearch` 趋势表达 |
| `role_salary` / `salary_by_role` | `stats.py` 薪资分析 | 按角色薪资分布 | `JobResearch` 薪资定位 |

> 隐私边界不变：简历工作流只**读**上述数据，不写回 `role_cache.json` / 词库；用户简历原文仍不持久化。

### 13.3 复用策略总览

```text
role_cache.json / data/taxonomy/*.json / 聚合榜单（统计侧已产出）
        │  只读复用
        ▼
┌────────────────────────────────────────────────────────────┐
│ 新增桥接层：src/resume_agent/market_data.py                  │
│  · load_job_tag_profile(job_id|jd_text)  → tag_profile       │
│  · load_cross_industry_profile(...)      → 六维 + summary    │
│  · load_taxonomy()                       → 词库/别名/拒绝表  │
│  · market_capability_stats()             → 场景化能力统计    │
└────────────────────────────────────────────────────────────┘
        │
        ├─→ analyze_jd        复用 tag_profile + soft_skills（命中库内岗位则免重解析）
        ├─→ JobResearch       复用 cross_industry_profile / summary_tags / 聚合榜单 / 薪资
        ├─→ gap_analysis      按 requirement_level 加权；example 不算缺口；接 taxonomy_candidates 补强
        ├─→ generate_polish   用 skill_taxonomy 规范写法 + 别名归一，保证 ATS 关键词一致
        ├─→ score             keyword_coverage 仅对 required/preferred 计算
        └─→ evidence_audit    用 tag_profile.evidence + rejections 校验关键词是否为真实硬要求
```

### 13.4 新增桥接模块：`market_data.py`

为避免在多个节点里散落读取 `role_cache.json` 和词库文件，新增统一只读桥接层。

```python
# src/resume_agent/market_data.py（新增）

from __future__ import annotations
from typing import Any, Optional

from src.analyzer.role_classifier import RoleClassifier


def load_job_tag_profile(jd_text: str) -> Optional[dict[str, Any]]:
    """命中库内已分类岗位时返回治理后的 tag_profile，否则 None。

    优先用 RoleClassifier 的缓存键匹配；未命中时调用方应回退到
    LLM 解析（analyze_jd 原有逻辑）。
    """
    classifier = RoleClassifier()
    cache_key = classifier._make_cache_key(jd_text)
    cached = classifier._cache.get(cache_key)
    if not cached:
        return None
    return {
        "tag_profile": cached.get("tag_profile") or {},
        "soft_skills": cached.get("soft_skills") or {},
        "cross_industry_profile": cached.get("cross_industry_profile") or {},
        "job_context_profile": cached.get("job_context_profile") or {},
    }


def split_jd_by_requirement(tag_profile: dict) -> dict[str, list[dict]]:
    """把 tag_profile 拆成 required / preferred / example / inferred 四桶。

    example/inferred 不进入硬性技能差距统计（修复§13.1「示例当硬要求」）。
    """
    buckets = {"required": [], "preferred": [], "example": [], "inferred": []}
    for group in ("technical", "non_technical", "experience"):
        for tag in tag_profile.get(group, []) or []:
            level = tag.get("requirement_level", "required")
            buckets.setdefault(level, []).append(tag)
    return buckets


def load_taxonomy() -> dict[str, Any]:
    """加载正式词库 / 别名 / 拒绝列表，供关键词归一与误判抑制。"""
    import json
    from config.settings import settings
    base = settings.data_dir / "taxonomy"
    out: dict[str, Any] = {}
    for name in ("skill_taxonomy", "taxonomy_aliases", "taxonomy_rejections",
                 "taxonomy_candidates"):
        path = base / f"{name}.json"
        try:
            out[name] = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            out[name] = {}
    return out
```

### 13.5 节点改造点

#### 13.5.1 `analyze_jd`：优先复用 `tag_profile`，免重解析

```python
def analyze_jd(state: AgentState, llm) -> dict:
    from src.resume_agent.market_data import load_job_tag_profile, split_jd_by_requirement

    reused = load_job_tag_profile(state["target_jd_text"])
    if reused and reused["tag_profile"]:
        # 命中库内岗位：直接采用治理后的分层标签，省一次 LLM 调用、口径与统计侧统一
        buckets = split_jd_by_requirement(reused["tag_profile"])
        jd_data = {
            "required_skills": [t["name"] for t in buckets["required"]],
            "preferred_skills": [t["name"] for t in buckets["preferred"]],
            "example_skills":   [t["name"] for t in buckets["example"]],   # 备选池，不计缺口
            "inferred_skills":  [t["name"] for t in buckets["inferred"]],
            "soft_skills": reused["soft_skills"],
            "cross_industry_profile": reused["cross_industry_profile"],
            "tag_evidence": {t["name"]: t.get("evidence", "")
                             for g in reused["tag_profile"].values() for t in g},
            "reused_from_cache": True,
        }
    else:
        # 未命中：回退到原 LLM 解析逻辑
        jd_data = _llm_analyze_jd(state["target_jd_text"], llm)
        jd_data["reused_from_cache"] = False
    # 角色分类仍复用 RoleClassifier
    ...
    return {"jd": jd_data}
```

`JDAnalysis`（`state.py`）相应扩展字段：

```python
class JDAnalysis(TypedDict, total=False):
    required_skills: list[str]
    preferred_skills: list[str]
    example_skills: list[str]          # 新增：备选/示例技能池，不计入硬性缺口
    inferred_skills: list[str]         # 新增：合理推断技能
    soft_skills: dict[str, list[str]]  # 新增：六类软技能（学历/语言/能力/行业/认证/业务）
    cross_industry_profile: dict       # 新增：跨行业六维
    tag_evidence: dict[str, str]       # 新增：标签→JD 原文证据
    responsibilities: list[str]
    min_experience: Optional[float]
    role_category: str
    key_requirements: list[str]
    reused_from_cache: bool            # 新增：是否复用了统计侧缓存
```

#### 13.5.2 `gap_analysis`：按层级加权 + 跨行业维度对齐

- `missing_skills` 只对 `required` 计入硬缺口；`preferred` 单列为"加分项缺口"；`example_skills` **不计缺口**（备选语言池满足其一即可）。
- 在 Prompt 中传入 `cross_industry_profile`，要求把用户经历映射到"业务场景 / 交付动作 / 行业知识"维度，而不仅技术栈——区分"会 Python"与"会在该行业场景落地 Python"。
- `keyword_suggestions` 的 `priority` 直接由 `requirement_level` + `confidence` 推导，替代拍脑袋打分。
- 接入 `taxonomy_candidates` 中的高置信新兴场景标签，作为"市场正在出现、你简历尚缺"的前瞻补强建议（喂给 Stage 4 补强建议）。

#### 13.5.3 `generate_polish`：词库归一保证 ATS 一致

- 写进简历的关键词，统一用 `skill_taxonomy.json` 的规范写法，并经 `taxonomy_aliases.json` 归并同义异形（如 `Proof-Of-Concept`→`POC 測試`），避免 ATS 因写法差异漏匹配。
- 命中 `taxonomy_rejections.json` 负例语境的词（福利里的 insurance、地点 Tai Po 误命中 ai 等）禁止作为"市场要求"写入简历。

#### 13.5.4 `score`：覆盖率只算硬要求

- `keyword_coverage` 仅对 `required` + `preferred` 计算覆盖比例，`example` / `inferred` 不参与，避免分数被备选/推断噪声拉偏。
- `experience_alignment` 引入 `soft_skills.business_skill` 与 `cross_industry_profile.business_scenario` 作为对齐依据。

#### 13.5.5 `evidence_audit`（v2.9 Stage 6）：双向证据锚点

- 用户简历 claim 侧已有 `ClaimEvidence`（§12.7）；本章补充**市场要求侧**证据锚点：`tag_profile.evidence` 提供"该关键词在真实 JD 里到底是 required 还是来自福利/地点误命中"，避免把误判关键词当成硬要求塞进简历后在面试被追问崩塌。

### 13.6 `market_insights.py` 改造

将 [`_build()`](file:///e:/文档/Project/HK-JobMarket-Analyzer/src/resume_agent/market_insights.py) 中的统计逻辑升级：

1. **技术栈榜单**：从直接数 `jobs.csv` 的裸 `skills`，改为优先读 `role_cache.json` 的 `tag_profile`，只统计 `required` / `preferred`，排除办公工具；缓存缺失时再回退到 `skills` 词频。
2. **保留 `tag_profile` / `cross_industry_profile`**：`_build()` 重建 `RoleResult` 时不再丢弃这些字段，向 `JobResearch` 透出。
3. **新增场景化能力统计**：复用统计侧 `场景化能力统计`（§11.10.5），让 `JobResearchReport` 能表达"哪些行业场景在吸收 AI/自动化能力"，而非只说"AI 和云需求高"。
4. **新增薪资定位**：透出 `role_salary` / `salary_by_role`，补全 `JobResearchReport` 目前缺失的薪资参考。

### 13.7 与统计侧的耦合与降级

| 场景 | 策略 |
|------|------|
| `role_cache.json` 未分类该 JD | `analyze_jd` 自动回退 LLM 解析（`reused_from_cache=False`），功能不阻塞 |
| 词库文件缺失 | `load_taxonomy()` 返回空结构，关键词归一退化为原样写入 |
| 统计侧字段缺失（旧缓存） | 读取默认空结构，按"无该维度"处理，与统计文档 §11.11.3 兼容策略一致 |
| 仅只读耦合 | 简历工作流不写 `role_cache.json` / 词库，不触发统计侧缓存失效，两系统单向依赖 |

### 13.8 文件清单补充

| 文件 | 改动 |
|------|------|
| `src/resume_agent/market_data.py`（新增） | 统一只读桥接层：`load_job_tag_profile` / `split_jd_by_requirement` / `load_taxonomy` / `market_capability_stats` |
| `src/resume_agent/market_insights.py` | 技术栈榜单按 `requirement_level` 过滤；保留 `tag_profile`/`cross_industry_profile`；新增场景化能力与薪资定位 |
| `src/resume_agent/nodes.py` | `analyze_jd` 优先复用 `tag_profile`；`gap_analysis`/`generate_polish`/`score` 按本章改造 |
| `src/resume_agent/state.py` | `JDAnalysis` 扩展 `example_skills`/`inferred_skills`/`soft_skills`/`cross_industry_profile`/`tag_evidence`/`reused_from_cache` |
| `src/resume_agent/prompts.py` | `GAP_ANALYSIS_PROMPT` 传入跨行业六维；`POLISH_PROMPT` 加入词库规范写法约束 |

### 13.9 落地优先级

| 优先级 | 内容 | 修复缺陷 |
|--------|------|---------|
| P0 | 新增 `market_data.py`；`analyze_jd` 复用 `tag_profile` 并按层级拆桶；`gap_analysis` 中 `example` 不计缺口 | §13.1「示例当硬要求」 |
| P1 | `gap_analysis`/`JobResearch` 接入 `cross_industry_profile` 六维与 `summary_tags` | §13.1「跨行业能力被压扁」 |
| P2 | `generate_polish` 接入 `skill_taxonomy`/别名归一；`score.keyword_coverage` 只算硬要求 | ATS 关键词一致性、评分准确性 |
| P3 | `market_insights.py` 接入场景化能力统计与薪资定位；`evidence_audit` 接入市场侧证据锚点 | JobResearch 表达力、证据审计 |

### 13.10 落地说明（实现与设计稿的差异）

实现时对照真实代码与 `role_cache.json` 数据结构，对设计稿做了如下务实校正：

1. **`tag_profile` 仅有 `technical` / `non_technical` 两个桶**（无独立 `experience` 组，经验类标签以 `category="experience"` 归在 `non_technical` 下）。因此 `split_jd_by_requirement` 遍历真实存在的两个分组，按 `requirement_level` 拆 `required/preferred/example/inferred` 四桶。实测全库分布：required 2781 / preferred 434 / example 372 / inferred 8，example 量级可观，修复"示例当硬要求"确有价值。
2. **`analyze_jd` 命中缓存即免重解析**：`load_job_tag_profile` 直接命中 `RoleClassifier._cache`，命中则由 `_jd_from_tag_profile` 确定性派生 JDAnalysis（职责取自跨行业 `delivery_motion`+`business_scenario`，`min_experience` 用正则从经验标签解析，语言/学历取自 `soft_skills`），不再调一次 JD 解析 LLM；未命中回退原 LLM 逻辑，`reused_from_cache` 标记来源。
3. **`gap_analysis` 双保险**：除在 Prompt 中声明备选池不算缺口外，节点层再做确定性守卫，强制把 `example_skills`/`inferred_skills` 从 `missing_skills` 剔除；并接入 `taxonomy_candidates` 高置信新兴标签为 `emerging_suggestions`。
4. **词库文件可选**：`data/taxonomy/` 当前仅有 `taxonomy_candidates.json`，`skill_taxonomy/aliases/rejections` 暂缺。`load_taxonomy` 缺失即返回空结构，`normalize_keywords` 退化为去重去空（仍保证 ATS 一致性），与 §13.7 降级策略一致；词库补齐后自动生效。
5. **`market_insights` 技术栈榜单**改为优先从 `role_cache.json` 的 `technical` 桶统计（仅 `required/preferred`、排除 `office_tools`），缓存缺失回退裸 `skills` 词频；缓存签名追加 `role_cache.json` 的 mtime 以正确失效。
6. **新增回归测试** `tests/test_resume_market_data.py` 覆盖分桶、词库归一、缓存复用、example 守卫等核心逻辑（全部通过）。

> 已落地优先级：P0/P1/P2 + P3 的 `market_insights` 技术栈口径统一。P3 余项（场景化能力统计、薪资定位、`evidence_audit` 市场侧证据锚点）待后续接入统计侧 `stats.py` 产物。

---

## 附录 A：LangGraph 关键概念映射

| LangGraph 概念 | 本系统中的使用 |
|---------------|--------------|
| `StateGraph` | `build_resume_agent()` 中构建工作流图 |
| `Node` | `parse_resume`, `analyze_jd`, `match_jobs`, `gap_analysis`, `generate_polish`, `score_and_verify` |
| `Edge` | `add_edge()` 连接各节点 |
| `ConditionalEdge` | `should_retry()` 根据评分决定回退或结束 |
| `State` | `AgentState` 传递各节点输出 |
| `CompiledGraph` | `workflow.compile()` 生成可运行实例 |

## 附录 B：安全与隐私考虑

| 关注点 | 措施 |
|-------|------|
| 简历数据存储 | 不持久化存储用户简历原文，仅在工作流运行时驻留内存 |
| LLM API 调用 | 复用系统现有 LLM 配置，不额外暴露 key |
| 输入校验 | Pydantic 校验简历/JD 文本长度（50-50000 字符） |
| 输出限制 | 润色结果仅包含修改建议，不包含完整简历副本（需前端拼接） |
| 日志脱敏 | 日志中截断长文本，不记录完整简历内容 |
