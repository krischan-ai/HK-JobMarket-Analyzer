# 简历润色工作流 Agent 设计文档

**版本**: v1.0  
**日期**: 2026-06-23  
**状态**: 初稿

---

## 修订记录

| 版本 | 日期 | 修订内容 | 修订人 |
|------|------|---------|--------|
| v1.0 | 2026-06-23 | 初始版本 | - |

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
