from __future__ import annotations

SYSTEM_PROMPT = """你是一个香港 IT 招聘市场的技术需求分析师。你的任务是从岗位描述（JD）中提取技术要求。

请严格按照以下分类提取技能关键词，只返回 JSON 格式，不要包含任何其他文字：

分类说明：
1. programming_languages: 编程语言（Python, Java, TypeScript, Go, Rust 等）
2. frameworks_libraries: 框架与库（React, Django, Spring Boot, PyTorch 等）
3. cloud_devops: 云服务与运维（AWS, Azure, Docker, Kubernetes, CI/CD 等）
4. databases: 数据库与中间件（PostgreSQL, MongoDB, Redis, Kafka 等）
5. soft_skills: 软技能（Communication, Leadership, Teamwork 等）

规则：
- 只提取明确提到的技术关键词
- 保持英文原文，不要翻译
- 每个类别最多返回 15 个关键词
- 如果没有找到任何技能，返回空列表
- 对于缩写词（如 K8s, FE, BE, SRE）保留原样
"""


FEW_SHOT_EXAMPLES = [
    {
        "role": "user",
        "content": (
            "We are looking for a senior Python developer with experience in "
            "Django and AWS. Knowledge of PostgreSQL and Docker is required. "
            "Strong problem-solving and communication skills."
        ),
    },
    {
        "role": "assistant",
        "content": (
            '{\n'
            '  "programming_languages": ["Python"],\n'
            '  "frameworks_libraries": ["Django"],\n'
            '  "cloud_devops": ["AWS", "Docker"],\n'
            '  "databases": ["PostgreSQL"],\n'
            '  "soft_skills": ["Problem Solving", "Communication"]\n'
            '}'
        ),
    },
    {
        "role": "user",
        "content": (
            "Frontend Engineer (React) needed. Expert in TypeScript, Next.js, "
            "Tailwind CSS. Familiar with GraphQL and RESTful APIs. "
            "Agile team player."
        ),
    },
    {
        "role": "assistant",
        "content": (
            '{\n'
            '  "programming_languages": ["TypeScript", "JavaScript"],\n'
            '  "frameworks_libraries": ["React", "Next.js", "Tailwind CSS", "GraphQL"],\n'
            '  "cloud_devops": [],\n'
            '  "databases": [],\n'
            '  "soft_skills": ["Agile", "Teamwork"]\n'
            '}'
        ),
    },
]


def build_skill_extraction_messages(jd_text: str) -> list[dict]:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for example in FEW_SHOT_EXAMPLES:
        messages.append(example)
    messages.append({"role": "user", "content": jd_text[:3000]})
    return messages
