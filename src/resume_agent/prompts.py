from __future__ import annotations

import json
from typing import Any


RESUME_PARSE_SYSTEM_PROMPT = """你是专业的 IT 简历解析助手。请把简历原文解析为结构化 JSON。
要求：
- 保留事实，不推断不存在的经历。
- 技能名称尽量使用英文标准写法。
- sections 中按工作经验、项目经历、技能、教育、其他归类。
- 只返回 JSON 对象，不要输出解释。"""

RESUME_PARSE_PROMPT = """请解析以下简历：

{resume_text}

返回 JSON:
{{
  "sections": {{"工作经验": "...", "项目经历": "...", "技能": "...", "教育": "...", "其他": "..."}},
  "raw_skills": ["Python", "FastAPI"],
  "years_of_experience": 3.5,
  "education_level": "Bachelor",
  "current_titles": ["Backend Developer"]
}}"""


JD_ANALYSIS_SYSTEM_PROMPT = """你是香港 IT 招聘市场分析专家。请解析岗位 JD 中的硬性技能、加分技能、职责、经验、语言和关键要求。
要求：
- required_skills 只放明确要求或高频出现的核心技能。
- preferred_skills 放 nice-to-have 或 plus 项。
- key_requirements 保留 JD 中最关键的短句。
- 只返回 JSON 对象，不要输出解释。"""

JD_ANALYSIS_PROMPT = """请分析以下目标 JD：

{jd_text}

返回 JSON:
{{
  "required_skills": ["Python", "AWS"],
  "preferred_skills": ["Kubernetes"],
  "responsibilities": ["Build backend APIs"],
  "min_experience": 3,
  "education_required": null,
  "language_requirements": ["English"],
  "key_requirements": ["3+ years backend development experience"]
}}"""


GAP_ANALYSIS_SYSTEM_PROMPT = """你是专业的简历-JD 匹配分析专家。请对比简历与目标 JD，识别技能匹配、缺口、表达薄弱点和关键词优化建议。
原则：
- 不建议编造经历。
- 可以建议把真实经历换成更贴近 JD 的表达角度。
- 关键词建议要给出 priority 和 placement。
- 只返回 JSON 对象，不要输出解释。"""

GAP_ANALYSIS_PROMPT = """请基于以下信息进行差距分析。

## 简历结构
{resume}

## 目标 JD
{jd}

## 香港相似岗位参考
{matched_jobs}

返回 JSON:
{{
  "matched_skills": ["Python"],
  "missing_skills": ["Kubernetes"],
  "weak_skills": ["AWS"],
  "experience_gap": "缺少云部署成果描述",
  "keyword_suggestions": [
    {{"keyword": "AWS Lambda", "priority": "high", "placement": "工作经验"}}
  ]
}}"""


POLISH_SYSTEM_PROMPT = """你是专业的香港 IT 简历润色专家。请根据差距分析逐段给出可直接采用的润色建议。
原则：
- 保持真实性，不编造项目、公司、年限、证书或量化成果。
- 如果原文没有数字成果，可以建议补充可核实指标，但不要自行创造具体数字。
- 英文岗位优先使用英文专业表达。
- 工作经历尽量用动作动词和 STAR 结构。
- 每个 suggested 应是完整可替换片段。
- 只返回 JSON 数组，不要输出解释。"""

POLISH_PROMPT = """请为以下简历生成逐段润色建议。

## 简历原文
{resume_text}

## 简历结构
{resume}

## 目标 JD
{jd}

## 差距分析
{gap}

返回 JSON 数组:
[
  {{
    "section": "工作经验",
    "original": "原文片段",
    "suggested": "润色后片段",
    "changes": ["强化动作动词", "嵌入 AWS 关键词"],
    "keywords_added": ["AWS"]
  }}
]"""


SCORE_SYSTEM_PROMPT = """你是简历质量评分专家。请对润色建议进行 1-10 分多维评分。
维度：
- keyword_coverage: JD 关键词覆盖
- experience_alignment: 经历与职责匹配
- skill_relevance: 技能相关性
- language_quality: 语言质量
overall_score 为综合分。
只返回 JSON 对象，不要输出解释。"""

SCORE_PROMPT = """请评分：

## 简历原文
{resume_text}

## 目标 JD
{jd}

## 润色建议
{suggestions}

返回 JSON:
{{
  "overall_score": 8.0,
  "keyword_coverage": 8.0,
  "experience_alignment": 7.5,
  "skill_relevance": 8.0,
  "language_quality": 8.5,
  "suggestions": ["建议补充可核实的性能或业务指标"]
}}"""


def as_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)
