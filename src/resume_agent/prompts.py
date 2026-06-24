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


MARKET_JD_SYNTHESIS_SYSTEM_PROMPT = """你是香港 IT 招聘市场分析专家。用户没有提供具体目标 JD，请你基于知识库召回的香港相似岗位和市场上下文，合成一份"目标岗位市场画像"，结构与一份典型 JD 分析一致。
要求：
- required_skills / preferred_skills 来自相似岗位高频出现的技能，区分核心与加分。
- responsibilities 总结该方向岗位的常见职责。
- key_requirements 用简短英文短句概括典型硬性要求。
- min_experience 给出该方向常见的经验门槛（年），无法判断时为 null。
- 只反映相似岗位里真实出现的内容，不要凭空编造冷门要求。
- 只返回 JSON 对象，不要输出解释。"""

MARKET_JD_SYNTHESIS_PROMPT = """用户未提供目标 JD，请基于以下香港市场数据合成目标岗位画像。

## 目标职位（用户填写，可能为空）
{target_role}

## 知识库召回的相似岗位
{matched_jobs}

## 市场上下文（高频技能 / 常见职位 / 典型措辞）
{market_context}

返回 JSON:
{{
  "required_skills": ["Python", "AWS"],
  "preferred_skills": ["Kubernetes"],
  "responsibilities": ["Build and operate backend services"],
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

## 香港市场上下文（高频技能 / 常见职位 / 典型措辞）
{market_context}

## 香港整库岗位数据分析（需求量最大的岗位方向排名 + JD 技术栈次数排名）
{market_insights}

判断要求：
- 结合 market_context 与 market_insights 判断关键词优先级：在岗位方向需求量大、或技术栈被提及次数多、且目标要求也涉及的技能，priority 设为 high。
- `market_demand_analysis` 中要明确点名 role_demand_ranking 里需求量最高的几个岗位方向、tech_stack_ranking 里被提及次数最多的几项技术栈，并结合候选人简历说明应优先补强/突出哪些方向与技术。

返回 JSON:
{{
  "matched_skills": ["Python"],
  "missing_skills": ["Kubernetes"],
  "weak_skills": ["AWS"],
  "experience_gap": "缺少云部署成果描述",
  "keyword_suggestions": [
    {{"keyword": "AWS Lambda", "priority": "high", "placement": "工作经验"}}
  ],
  "market_demand_analysis": "香港市场需求量最大的方向是 AI 应用开发与 DevOps；JD 中出现最多的技术栈是 Python、AWS、Azure。结合你的简历，建议优先补强 ... 并在技能区突出 ..."
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

## 香港市场上下文（参考典型措辞与高频技能优化简历表达）
{market_context}

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


SCORE_SYSTEM_PROMPT = """你是简历质量评分专家。请对润色建议进行 1-10 分多维评分，并详细讲解每个维度的评分原因。
维度：
- keyword_coverage: JD / 目标画像关键词覆盖
- experience_alignment: 经历与职责匹配
- skill_relevance: 技能相关性
- language_quality: 语言质量
overall_score 为综合分。

讲解要求：
- overall_comment：用 3-5 句话总体说明这份简历相对目标的强项与主要短板，给出综合分的依据。
- dimension_reasons：对四个维度逐一说明给出该分数的具体原因（点名简历中的具体内容或缺失项），不要泛泛而谈。
只返回 JSON 对象，不要输出解释性前后缀。"""

SCORE_PROMPT = """请评分并详细讲解原因：

## 简历原文
{resume_text}

## 目标 JD / 目标画像
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
  "overall_comment": "总体来看，这份简历在 ... 表现突出，但在 ... 方面仍有明显短板，因此综合分为 8.0。",
  "dimension_reasons": {{
    "keyword_coverage": "JD 要求的 X、Y 已覆盖，但缺少 Z，故 8.0。",
    "experience_alignment": "工作经历与职责高度相关，但量化成果不足，故 7.5。",
    "skill_relevance": "技能与目标方向贴合，但 ... 故 8.0。",
    "language_quality": "表达专业、动词有力，个别句子偏长，故 8.5。"
  }},
  "suggestions": ["建议补充可核实的性能或业务指标"]
}}"""


def as_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)
