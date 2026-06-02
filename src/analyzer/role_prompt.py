from __future__ import annotations

ROLE_CLASSIFY_SYSTEM_PROMPT = """你是一个香港 IT 招聘市场的岗位分类专家。你的任务是根据岗位描述（JD）将岗位归类到标准技术角色。

你需要返回一个 JSON 对象，包含以下字段：
- role_id: 角色英文 ID（必须从下方角色列表中选择）
- role_name: 角色中文名称
- confidence: 分类置信度（high/medium/low）

角色列表（共 14 种）：

1. frontend - 前端开发：Web/移动端 UI、交互开发（React, Vue, Angular, HTML/CSS, JavaScript, TypeScript 偏前端）
2. backend - 后端开发：服务端/API/中间件开发（Spring Boot, Django, Node.js 后端, Go 后端, REST API, 数据库设计）
3. fullstack - 全栈开发：同时涉及前后端开发，或职位明确标注 Full Stack/MERN/MEAN
4. mobile - 移动开发：iOS/Android 原生或跨平台（Swift, Kotlin, Flutter, React Native, Objective-C）
5. data_science - 数据科学：数据分析/机器学习/深度学习/统计学/模型训练（Python ML, TensorFlow, NLP, Computer Vision, 数据挖掘）
6. data_engineer - 数据工程：数据管道/ETL/大数据平台/数据仓库（Spark, Hadoop, Airflow, Kafka 侧重数据, ETL, Data Pipeline, Snowflake）
7. devops - DevOps/SRE：CI/CD/基础设施/云运维/监控（Docker, K8s, Jenkins, Terraform, Ansible, AWS 运维, Prometheus）
8. qa - 质量保证：测试/自动化测试（Selenium, TestNG, QA, Test Automation, JUnit 测试, Cypress）
9. security - 安全工程：网络安全/应用安全/渗透测试（Cybersecurity, Penetration Test, SOC, Security Analyst, ISO 27001）
10. product - 产品管理：产品规划/需求分析/项目管理（Product Manager, Roadmap, User Story, PRD, Scrum Master）
11. design - 设计师：UI/UX/视觉设计/用户研究（Figma, Sketch, User Research, Prototype, Adobe, Illustrator, 交互设计）
12. blockchain - 区块链：智能合约/Web3/DeFi（Solidity, Smart Contract, DeFi, Web3, Ethereum, NFT）
13. ai_engineer - AI 工程师：LLM/AI 应用/RAG/LangChain/Prompt Engineering
14. other - 其他：无法明确归类到以上任意角色的岗位

分类规则：
1. 优先根据岗位标题判断角色
2. 其次根据 JD 中描述的工作职责和所需技术栈判断
3. 如果岗位涉及多个领域，选择其核心工作内容对应的角色
4. 如果 JD 信息不足或岗位过于综合，选择 other
5. 对于有 "Senior/Lead/Manager" 头衔的，仍按实际技术方向归类，不要归为 product
"""

FEW_SHOT_EXAMPLES = [
    {
        "role": "user",
        "content": (
            "Senior Frontend Engineer - We are looking for an experienced "
            "React developer to build responsive web applications. "
            "Required: TypeScript, React, Redux, Tailwind CSS, experience with "
            "RESTful APIs and GraphQL."
        ),
    },
    {
        "role": "assistant",
        "content": '{"role_id": "frontend", "role_name": "前端开发", "confidence": "high"}',
    },
    {
        "role": "user",
        "content": (
            "Data Scientist - Build and deploy machine learning models for "
            "financial risk prediction. Required: Python, TensorFlow, SQL, "
            "experience with NLP and time series analysis."
        ),
    },
    {
        "role": "assistant",
        "content": '{"role_id": "data_science", "role_name": "数据科学", "confidence": "high"}',
    },
    {
        "role": "user",
        "content": (
            "DevOps Engineer - Manage CI/CD pipelines, cloud infrastructure on AWS. "
            "Required: Docker, Kubernetes, Terraform, Jenkins, experience with "
            "monitoring tools like Prometheus and Grafana."
        ),
    },
    {
        "role": "assistant",
        "content": '{"role_id": "devops", "role_name": "DevOps/SRE", "confidence": "high"}',
    },
    {
        "role": "user",
        "content": (
            "Software Developer - Write code and fix bugs. "
            "Required: Bachelor degree in IT, good communication skills."
        ),
    },
    {
        "role": "assistant",
        "content": '{"role_id": "other", "role_name": "其他", "confidence": "medium"}',
    },
]

ROLE_DEFINITIONS: dict[str, dict[str, str]] = {
    "frontend": {"name": "前端开发", "keywords": "React, Vue, Angular, HTML, CSS, JavaScript 前端, UI 开发"},
    "backend": {"name": "后端开发", "keywords": "Spring Boot, Django, Node.js 后端, Go 后端, REST API, 数据库设计"},
    "fullstack": {"name": "全栈开发", "keywords": "Full Stack, MERN, MEAN, 前后端兼顾"},
    "mobile": {"name": "移动开发", "keywords": "Swift, Kotlin, Flutter, React Native, iOS, Android"},
    "data_science": {"name": "数据科学", "keywords": "ML, TensorFlow, NLP, CV, 机器学习, 数据挖掘"},
    "data_engineer": {"name": "数据工程", "keywords": "Spark, Hadoop, Airflow, ETL, Data Pipeline, Snowflake"},
    "devops": {"name": "DevOps/SRE", "keywords": "Docker, K8s, Jenkins, Terraform, Ansible, CI/CD, Prometheus"},
    "qa": {"name": "质量保证", "keywords": "Selenium, TestNG, QA, Test Automation, Cypress"},
    "security": {"name": "安全工程", "keywords": "Cybersecurity, Penetration Test, SOC, ISO 27001"},
    "product": {"name": "产品管理", "keywords": "Product Manager, Roadmap, User Story, PRD"},
    "design": {"name": "设计师", "keywords": "Figma, Sketch, UX, UI, User Research, Prototype"},
    "blockchain": {"name": "区块链", "keywords": "Solidity, Smart Contract, DeFi, Web3, Ethereum"},
    "ai_engineer": {"name": "AI 工程师", "keywords": "LLM, LangChain, RAG, Prompt Engineering, AI Agent"},
    "other": {"name": "其他", "keywords": ""},
}


def build_role_classify_messages(jd_text: str) -> list[dict]:
    messages = [{"role": "system", "content": ROLE_CLASSIFY_SYSTEM_PROMPT}]
    for example in FEW_SHOT_EXAMPLES:
        messages.append(example)
    messages.append({"role": "user", "content": jd_text[:3000]})
    return messages
