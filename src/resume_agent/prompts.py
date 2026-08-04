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


TARGET_ROLE_UNDERSTANDING_SYSTEM_PROMPT = """你是香港 IT 招聘市场顾问。请把用户选择的目标职位理解成可用于检索和匹配的语义画像。
要求：
- 结合标准职位定义和简历事实理解目标方向。
- expanded_query 要适合投喂岗位检索系统，包含同义职位名、核心职责、核心技术和香港市场常见表达。
- 不要虚构候选人没有的经历；可写市场方向，但不要写成候选人事实。
- 只返回 JSON 对象，不要输出解释。"""

TARGET_ROLE_UNDERSTANDING_PROMPT = """请理解目标职位并生成语义检索画像。

## 标准目标职位
role_id: {role_id}
role_name: {role_name}
keywords: {role_keywords}

## 用户填写的目标职位文本
{target_role}

## 简历结构
{resume}

返回 JSON:
{{
  "role_id": "{role_id}",
  "role_name": "{role_name}",
  "role_summary": "该方向在香港市场通常负责后端 API、服务集成与云部署...",
  "expanded_query": "Backend Engineer OR Backend Developer Python FastAPI Django REST API AWS cloud microservices Hong Kong",
  "core_tech": ["Python", "FastAPI", "AWS"],
  "responsibilities": ["Build backend APIs", "Integrate databases and services"]
}}"""


JOB_MATCH_RERANK_SYSTEM_PROMPT = """你是香港 IT 招聘匹配顾问。请只在给定的真实召回岗位中做语义理解、排序和建议。
原则：
- 只能选择输入列表里的 job_id，不要编造岗位。
- 排序依据：目标职位语义、简历事实、岗位标题与 JD 摘要。
- 每个被保留岗位给一句 match_reason，解释为什么相关或哪里不完全匹配。
- match_advice 给候选人定位建议，强调如何选择和呈现，不要编造经历。
- 只返回 JSON 对象，不要输出解释。"""

JOB_MATCH_RERANK_PROMPT = """请对以下真实召回岗位做语义排序。

## 目标职位理解
{target_role_understanding}

## 用户目标职位
{target_role}

## 简历结构
{resume}

## 真实召回岗位
{matched_jobs}

返回 JSON:
{{
  "ranked_job_ids": ["job_id_1", "job_id_2"],
  "match_reasons": {{
    "job_id_1": "与后端 API 和 AWS 部署经验高度相关，但需要补充云平台成果。"
  }},
  "match_advice": {{
    "summary": "你的定位更适合后端/AI 应用后端交叉方向。",
    "suggestions": ["优先投递强调 API、数据集成、云部署的岗位", "简历顶部突出 Python + 云部署 + 业务系统交付"]
  }}
}}"""


TECH_STACK_SUMMARY_SYSTEM_PROMPT = """你是香港 IT 岗位技术栈分析专家。请阅读真实岗位标题与 JD 摘要，按语义概括技术栈主题。
要求：
- tech_stack_themes 只放技术、工具、框架、平台、工程方法或技术领域。
- Python、AWS、Azure、Docker、CI/CD 等不要只做孤立计数，要归并成概念主题，例如“后端工程与 API”“云平台与 DevOps”“数据/AI 应用工程”。
- Cantonese、English、Cross-functional collaboration、Communication、Stakeholder management 等语言/软技能/协作能力必须放入 other_competencies，不得进入 tech_stack_themes。
- 不输出次数 count。
- 只基于输入岗位信息，不要编造输入中不存在的冷门技术。
- 只返回 JSON 对象，不要输出解释。"""

TECH_STACK_SUMMARY_PROMPT = """请基于以下真实岗位样本概括技术栈主题。

## 目标职位理解
{target_role_understanding}

## 规则抽取的技术线索（仅供参考，可能机械且有噪声）
{market_context}

## 真实召回岗位
{matched_jobs}

返回 JSON:
{{
  "tech_stack_themes": [
    {{"theme": "后端工程与 API", "items": ["Python", "FastAPI", "REST API"], "evidence": ["Backend Engineer", "Build APIs"]}},
    {{"theme": "云平台与交付自动化", "items": ["AWS", "Docker", "CI/CD"], "evidence": ["cloud deployment", "CI/CD pipelines"]}}
  ],
  "other_competencies": ["Cantonese communication", "Cross-functional collaboration"],
  "core_capabilities": ["API design and service integration", "Cloud deployment awareness", "Production troubleshooting"]
}}"""


MARKET_INSIGHTS_SUMMARY_SYSTEM_PROMPT = """你是香港 IT 市场技术趋势分析专家。请把整库岗位的机械技能次数排名归并成语义技术主题。
要求：
- 不要输出每项技术出现次数。
- 把 Python、AWS、Azure、Docker、CI/CD 等宽泛词归到更有解释力的主题。
- 排除语言要求、软技能、协作能力等非技术项。
- 只返回 JSON 对象，不要输出解释。"""

MARKET_INSIGHTS_SUMMARY_PROMPT = """请把以下整库市场数据概括成语义技术主题。

## 原始整库洞察
{market_insights}

返回 JSON:
{{
  "tech_stack_themes": [
    {{"theme": "AI 应用与检索增强生成", "items": ["LLM API", "RAG", "Vector DB"], "evidence": ["ai_application demand"]}},
    {{"theme": "云平台与工程交付", "items": ["AWS", "Azure", "Docker", "CI/CD"], "evidence": ["cloud_devops ranking"]}}
  ]
}}"""


GAP_ANALYSIS_SYSTEM_PROMPT = """你是专业的简历-JD 匹配分析专家。请对比简历与目标 JD，识别技能匹配、缺口、表达薄弱点和关键词优化建议。
原则：
- 不建议编造经历。
- 可以建议把真实经历换成更贴近 JD 的表达角度。
- 关键词建议要给出 priority 和 placement；priority 应参考 JD 标签的 requirement_level（required > preferred）与置信度。
- 区分硬性要求与备选/示例池：JD 中以「e.g. / 任一 / 例如」列出的备选技能（如 Go/Java/JS 任选其一）不是缺失的硬技能，绝不能放进 missing_skills。
- 跨行业能力对齐：不要只比技术栈，要把候选人真实经历映射到「业务场景 / 交付动作 / 行业知识」维度，区分「会 Python」与「会在该行业场景落地 Python」。
- 只返回 JSON 对象，不要输出解释。"""

GAP_ANALYSIS_PROMPT = """请基于以下信息进行差距分析。

## 简历结构
{resume}

## 目标 JD
{jd}

## 备选/示例技能池（JD 中列举的可选项，满足其一即可，禁止计入 missing_skills）
{example_skills}

## 目标岗位跨行业六维画像（行业 / 业务场景 / 方案领域 / 交付动作 / 合规 / 系统资产）
{cross_industry_profile}

## 香港相似岗位参考
{matched_jobs}

## 香港市场上下文（语义技术栈主题 / 常见职位 / 典型措辞）
{market_context}

## 香港整库岗位数据分析（需求量最大的岗位方向排名 + JD 技术栈语义主题）
{market_insights}

判断要求：
- 结合 market_context 与 market_insights 判断关键词优先级：目标岗位语义主题、整库高需求方向、且简历真实涉及的技能优先级更高。
- `missing_skills` 只放 JD 明确要求（required/preferred）且简历缺失的技能，不要把上面「备选/示例技能池」里的任何一项当成缺口。
- `cross_industry_alignment` 用 2-4 句说明候选人经历在跨行业六维上的契合与缺口：哪些业务场景/交付动作/行业知识已有真实锚点、哪些只是技术会但缺场景落地证据。
- `market_demand_analysis` 中要明确点名 role_demand_ranking 里需求量最高的几个岗位方向、tech_stack_themes 里的关键技术主题，并结合候选人简历说明应优先补强/突出哪些方向与技术。

返回 JSON:
{{
  "matched_skills": ["Python"],
  "missing_skills": ["Kubernetes"],
  "weak_skills": ["AWS"],
  "experience_gap": "缺少云部署成果描述",
  "cross_industry_alignment": "候选人有金融支付场景的 Python 落地经验，与目标岗位的业务场景维度契合；但缺少政府/公用事业的交付与合规证据。",
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
- 关键词写法保持业界规范标准写法（如 Proof-Of-Concept 用规范的 POC 测试写法、CI/CD、Kubernetes），避免同义异形导致 ATS 漏匹配。
- 不要把福利/地点等误判词（如福利里的 insurance、地点 Tai Po）当成「市场技能要求」写进简历。
- 跨行业经历改写：把真实经历自然融入目标岗位的业务场景与交付动作，不只是堆技术名词，但不得编造行业经历。
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

## 目标岗位跨行业六维画像（把经历融入对应业务场景/交付动作/行业知识）
{cross_industry_profile}

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
- keyword_coverage: JD 关键词覆盖。**只统计 required_skills 与 preferred_skills 这类硬性/加分要求**；example_skills（备选/示例池）与 inferred_skills（推断项）不参与覆盖率计算，避免分数被备选噪声拉偏。
- experience_alignment: 经历与职责匹配；结合 soft_skills.business_skill 与 cross_industry_profile.business_scenario 判断是否在目标业务场景中有真实落地证据，而非仅技术会用。
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


INTERVIEW_PREP_SYSTEM_PROMPT = """你是资深技术面试教练。请把润色后的简历 bullet 逐条转成可被面试官追问的准备材料。
原则：
- 只基于简历与润色建议中真实存在的内容，不编造经历或数字。
- 每条给出 30 秒口语讲法、2-4 个高概率追问、证据口径、风险点和诚实兜底话术。
- evidence_confidence 用 strong/medium/weak/risky 标注该 bullet 经得起追问的程度；讲不清来源的数字/强成果标为 weak 或 risky。
- fallback_answer 是当被追问到薄弱处时的诚实回应，不要鼓励硬撑或造假。
- 只返回 JSON 数组，不要输出解释。"""

INTERVIEW_PREP_PROMPT = """请基于以下信息为每条简历 bullet 生成面试准备材料。

## 目标 JD / 目标画像
{jd}

## 润色后的逐段建议（每段 suggested 即最终 bullet 来源）
{suggestions}

返回 JSON 数组:
[
  {{
    "bullet_id": "b1",
    "final_text": "最终 bullet 文本",
    "target_capability": "该 bullet 证明的核心能力",
    "evidence_source": "经历/项目来源",
    "evidence_confidence": "strong",
    "talk_track_30s": "30 秒口语讲法…",
    "follow_up_questions": ["面试官可能追问的问题1", "问题2"],
    "risk_notes": ["容易露馅或过度包装的点"],
    "fallback_answer": "被追问到薄弱处时的诚实回应"
  }}
]"""


def as_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)
