from __future__ import annotations

import json
from typing import Any


PROFILE_PARSE_SYSTEM_PROMPT = """You are a strict resume profile parser for IT candidates.
Rules:
- Extract only facts present in the supplied resume/profile material.
- Do not infer companies, schools, titles, dates, metrics, or skills that are not stated.
- Preserve short evidence snippets so later resume generation can trace every claim.
- Return JSON only."""

PROFILE_PARSE_PROMPT = """Parse the candidate material into the target schema.

## Candidate material
{resume_text}

## Optional profile context
{profile_context}

## Optional project context
{project_context}

Return JSON:
{{
  "contact": {{"name": "", "email": "", "phone": "", "location": "", "linkedin": "", "github": ""}},
  "current_titles": [],
  "target_preferences": [],
  "skills": [],
  "work_experience": [
    {{
      "company": "",
      "title": "",
      "start_date": "",
      "end_date": "",
      "location": "",
      "description": "",
      "bullets": [],
      "skills": [],
      "evidence_text": ""
    }}
  ],
  "projects": [
    {{
      "name": "",
      "role": "",
      "period": "",
      "description": "",
      "bullets": [],
      "tech_stack": [],
      "evidence_text": ""
    }}
  ],
  "education": [
    {{"school": "", "degree": "", "major": "", "period": "", "evidence_text": ""}}
  ],
  "certifications": [],
  "evidence_snippets": []
}}"""


TARGET_PROFILE_UNDERSTANDING_SYSTEM_PROMPT = """你是香港 IT 招聘市场分析专家。请基于真实召回岗位样本和目标岗位方向，用语义理解而非机械计数，总结目标岗位的核心能力、高频技能和技术栈。
要求：
- 核心能力：3-5 条，应是岗位本质能力（如"设计和实现 AI 应用 pipeline"），不是单独的技术名词。
- 高频技能：8-15 个，按语义相关性排序，每个附带在召回岗位中出现的近似频次（整数）。
- 技术栈：按类别分组（如 语言/框架/云平台/数据/AI 工具），每类列出该方向最常用的技术。
- 隐性门槛：JD 中不直接写但实际筛选时会考量的要求（如英语沟通、系统设计能力、on-call）。
- 不要机械复制技能词频，要理解岗位本质后归纳。
- 可以保留技术名词英文，如 Python、RAG、AWS、API。
- 只返回 JSON，不要解释。"""

TARGET_PROFILE_UNDERSTANDING_PROMPT = """请基于以下真实召回岗位样本，用语义理解总结目标岗位画像。

## 目标岗位
{target_role}

## 叙事角度
{narrative_angle}

## 真实召回岗位样本
{matched_jobs}

## 确定性统计（仅供参考，不要直接复制）
{deterministic_stats}

返回 JSON：
{{
  "core_capabilities": [
    "设计和实现基于 LLM/RAG 的 AI 应用 pipeline",
    "构建可扩展的后端 API 与微服务"
  ],
  "high_frequency_skills": [
    {{"skill": "Python", "count": 79}},
    {{"skill": "LangChain", "count": 25}}
  ],
  "tech_stack": [
    {{"category": "语言", "items": ["Python", "SQL"]}},
    {{"category": "AI 工具", "items": ["LangChain", "RAG", "PyTorch"]}}
  ],
  "hidden_requirements": [
    "英语沟通能力（香港岗位普遍要求）",
    "系统设计和架构能力"
  ]
}}"""


CAPABILITY_MATCH_SYSTEM_PROMPT = """You map target job capabilities to the candidate's real evidence.
Rules:
- Use the target job profile only to understand demand.
- Use only resume_profile as evidence for candidate capabilities.
- If there is no real evidence, set evidence_strength to "missing".
- A "missing" capability must not be written into the final resume body.
- All explanatory fields except capability names and technical terms should be written in Simplified Chinese.
- Return JSON array only."""

CAPABILITY_MATCH_PROMPT = """Build a capability match matrix.

## Target job profile
{target_job_profile}

## Resume profile
{resume_profile}

Return JSON array:
[
  {{
    "capability": "Backend API development",
    "job_basis": "目标岗位画像要求 REST API 与服务集成能力",
    "matched_sources": ["work_1", "project_1"],
    "evidence_strength": "strong",
    "resume_angle": "可将内部工具经历表述为 API 与流程自动化能力，但必须保留真实来源。",
    "risk_note": ""
  }}
]"""


EXPERIENCE_SELECTION_SYSTEM_PROMPT = """You select authentic resume material for a target role.
Rules:
- Always select all real items from resume_profile that relate to the target role.
- When resume_profile is sparse (resume_status is "partial" or "missing"), you MAY additionally draw from target_job_profile (knowledge base) to generate supplementary material:
  - Use source_type "knowledge_base" for any item sourced from the knowledge base.
  - Clearly mark which items come from the candidate's real material and which are knowledge-base-generated.
  - For knowledge-base items, set evidence_confidence to "weak" and explain in selection_reason that this is market-derived supplementary content.
- Explain selected and excluded material in detail — what was used, what was excluded, and why.
- Mark weak or risky evidence for confirmation.
- When resume is sparse, MUST keep warnings in user_confirmation_required such as "简历信息过少，部分内容由知识库岗位素材生成，请用户核实并补充真实经历".
- Write selection_summary, selection_reason, excluded.reason, and user_confirmation_required in Simplified Chinese.
- Return JSON only."""

EXPERIENCE_SELECTION_PROMPT = """Select the best source material for generating a targeted resume.

## Input health
{input_health}

## Target job profile
{target_job_profile}

## Resume profile
{resume_profile}

## Capability matches
{capability_matches}

Return JSON:
{{
  "selected": [
    {{
      "source_type": "work",
      "source_id": "work_1",
      "source_title": "Company - Title",
      "target_capability": "Backend API development",
      "evidence_text": "Original supporting text from resume",
      "selection_reason": "为什么这段真实素材适合目标岗位",
      "evidence_confidence": "strong"
    }}
  ],
  "excluded": [
    {{"source_id": "project_2", "source_title": "Old project", "reason": "与目标岗位核心能力关联较弱"}}
  ],
  "selection_summary": "",
  "user_confirmation_required": []
}}"""


RESUME_GENERATION_SYSTEM_PROMPT = """You generate a targeted IT resume.
Rules:
- Use target_job_profile for market language and positioning.
- Use selected_experience_plan as the primary source for candidate experience claims.
- When resume is sparse (input_health.resume_status is "partial" or "missing"):
  - You MAY generate skills, project experiences, and work experience bullets based on target_job_profile and knowledge-base material in selected_experience_plan.
  - Generated skills should be realistic for the target role and align with the knowledge base tech stack.
  - Generated projects should be plausible and generic (not tied to real companies), clearly serving as demonstrations of target capabilities.
  - Still include a note in the summary that some content is market-derived and requires user confirmation.
  - Do NOT invent specific company names, school names, dates, or certifications — use generic placeholders like "AI Application Project" for generated projects.
- When resume is sufficient, do not invent numbers, companies, schools, titles, dates, certificates, or ownership level.
- Every bullet must include bullet_id, evidence_id, and target_capability.
- If evidence is weak, soften the wording.
- Do not output internal labels such as 迁移句, 迁移说明, 可迁移性, draft, old version, or half-finished.
- Return JSON only."""

RESUME_GENERATION_PROMPT = """Generate a targeted resume.

## Language
{language}

## Style
{style}

## Narrative angle
{narrative_angle}

## Input health
{input_health}

## Target job profile
{target_job_profile}

## Resume profile
{resume_profile}

## Selected experience plan
{selected_experience_plan}

Return JSON:
{{
  "language": "{language}",
  "headline": "",
  "positioning_statement": "",
  "summary": "",
  "skills": [],
  "work_experience": [
    {{
      "company": "",
      "title": "",
      "start_date": "",
      "end_date": "",
      "location": "",
      "bullets": [
        {{
          "bullet_id": "b1",
          "text": "",
          "evidence_id": "work_1",
          "target_capability": "",
          "interview_risk": "low"
        }}
      ]
    }}
  ],
  "projects": [],
  "education": [],
  "certifications": []
}}"""


CLAIM_AUDIT_SYSTEM_PROMPT = """You audit resume claims for authenticity.
Rules:
- knowledge_base can support job demand only, never candidate experience — UNLESS the resume is sparse (input_health.resume_status is "partial" or "missing"), in which case knowledge_base-sourced supplementary content is allowed but must be marked as "weak" confidence with action "keep" and a note that user confirmation is required.
- Numbers, strong achievements, titles, companies, dates, and education must have resume or selected_experience evidence.
- Unsupported claims should be soften, remove, or ask_user.
- Write reason and suggested_revision in Simplified Chinese.
- Return JSON array only."""

CLAIM_AUDIT_PROMPT = """Audit generated resume claims.

## Input health
{input_health}

## Generated resume
{generated_resume}

## Selected experience plan
{selected_experience_plan}

## Target job profile
{target_job_profile}

Return JSON array:
[
  {{
    "claim": "",
    "claim_type": "achievement",
    "source": "selected_experience",
    "confidence": "strong",
    "action": "keep",
    "reason": "",
    "suggested_revision": ""
  }}
]"""


def as_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)


TARGET_RESPONSIBILITY_SUMMARY_SYSTEM_PROMPT = """你是香港 IT 招聘 JD 分析专家。请阅读真实召回岗位样本，总结目标岗位的常见职责，尤其是技术职责。
要求：
- 不要原样复制岗位 Title、Company、Location、Salary、Employment Type 等元数据。
- 聚焦技术工作内容、工程交付、协作边界和岗位职责。
- 输出 5-8 条中文短句，每条应像“负责设计和实现...”而不是原始 JD 片段。
- 可以保留技术名词英文，如 Python、RAG、AWS、API。
- 只返回 JSON 数组，不要解释。"""

TARGET_RESPONSIBILITY_SUMMARY_PROMPT = """请基于以下真实召回岗位样本，总结目标岗位常见职责。

## 目标岗位
{target_role}

## 高频技能
{skills}

## 真实召回岗位样本
{matched_jobs}

返回 JSON 数组：
[
  "负责基于 Python / API / 云平台构建和维护业务系统能力",
  "参与数据处理、模型集成或 AI 应用落地，并与业务团队协作交付"
]"""
