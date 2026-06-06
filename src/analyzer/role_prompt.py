from __future__ import annotations

ROLE_CLASSIFY_SYSTEM_PROMPT = """你是一个香港 IT 招聘市场的岗位分类专家。你的任务是根据岗位描述（JD）将岗位归类到标准技术角色。

你需要返回一个 JSON 对象，包含以下字段：
- role_id: 角色英文 ID（必须从下方角色列表中选择）
- role_name: 角色中文名称
- confidence: 分类置信度（high/medium/low）

角色列表（共 22 种）：

1. frontend - 前端开发：Web/移动端 UI、交互开发（React, Vue, Angular, HTML/CSS, JavaScript, TypeScript 偏前端）
2. backend - 后端开发：服务端/API/中间件开发（Spring Boot, Django, Node.js 后端, Go 后端, REST API, 数据库设计）
3. fullstack - 全栈开发：同时涉及前后端开发，或职位明确标注 Full Stack/MERN/MEAN
4. mobile - 移动开发：iOS/Android 原生或跨平台（Swift, Kotlin, Flutter, React Native, Objective-C）
5. data_scientist - 数据科学家：数据分析/统计/AB测试/商业洞察/可视化（Python pandas, SQL, Tableau, 统计分析, 假设检验, 数据可视化）
6. ml_engineer - 机器学习工程师：ML 管道/模型部署/MLOps/特征工程（ML Pipeline, Model Deployment, MLOps, Feature Store, 分布式训练, 模型监控, Model Serving）
7. data_engineer - 数据工程：数据管道/ETL/大数据平台/数据仓库（Spark, Hadoop, Airflow, Kafka 侧重数据, ETL, Data Pipeline, Snowflake）
8. devops - DevOps/SRE：CI/CD/基础设施/云运维/监控（Docker, K8s, Jenkins, Terraform, Ansible, AWS 运维, Prometheus）
9. qa - 质量保证：测试/自动化测试（Selenium, TestNG, QA, Test Automation, JUnit 测试, Cypress）
10. security - 安全工程：网络安全/应用安全/渗透测试（Cybersecurity, Penetration Test, SOC, Security Analyst, ISO 27001）
11. solution_architect - 解决方案架构师：系统设计/技术架构/方案规划/技术选型（Solution Architect, System Architecture, Technology Strategy, Cloud Architecture, Enterprise Architecture, 技術藍圖）
12. engineering_manager - 工程经理/技术主管：团队管理/技术领导/项目管理（Engineering Manager, Tech Lead, Team Lead, 技術管理, 團隊領導, 人員管理）
13. it_analyst - IT 分析师/系统分析师：需求分析/系统分析/流程分析/技术文档（System Analyst, Business Analyst, Requirements Gathering, 系統分析, 需求分析, 技術文檔）
14. product - 产品管理：产品规划/需求分析/项目管理（Product Manager, Roadmap, User Story, PRD, Scrum Master）
15. design - 设计师：UI/UX/视觉设计/用户研究（Figma, Sketch, User Research, Prototype, Adobe, Illustrator, 交互设计）
16. blockchain - 区块链：智能合约/Web3/DeFi（Solidity, Smart Contract, DeFi, Web3, Ethereum, NFT）
17. ai_prompt_engineer - 提示詞工程師：Prompt 設計/提示詞優化/Few-shot/Few-shot 優化（Prompt Engineering, Prompt Design, Few-shot, Prompt Template）
18. ai_model_training - 模型訓練/微調：模型訓練/微調/對齊/評估（Model Training, Fine-tuning, LoRA, PEFT, RLHF, Pre-training, SFT）
19. ai_agent_dev - AI Agent 開發：AI Agent/多智能體/Tool Use/自主系統（AI Agent, Multi-Agent, Agentic, Tool Use, AutoGPT, Function Calling, ReAct）
20. ai_application - AI 應用開發：LLM 應用/RAG/LangChain/向量搜索（RAG, LangChain, LLamaIndex, Vector DB, LLM API, Prompt Flow, Dify）
21. data_science - 数据科学（通用）：如果无法确定是 data_scientist 还是 ml_engineer，可用此通用分类
22. other - 其他：无法明确归类到以上任意角色的岗位

分类规则：
1. 优先根据岗位标题判断角色
2. 其次根据 JD 中描述的工作职责和所需技术栈判断
3. 如果岗位涉及多个领域，选择其核心工作内容对应的角色
4. 如果 JD 信息不足或岗位过于综合，选择 other
5. 对于有 "Senior/Lead/Manager" 头衔的，仍按实际技术方向归类，不要归为 product 或 engineering_manager
6. 数据类岗位请仔细区分：做分析/统计/商业洞察选 data_scientist、做 ML 管道/部署/MLOps 选 ml_engineer、做 ETL/大数据选 data_engineer
7. AI 相关岗位请仔细区分：搞 Prompt 选 ai_prompt_engineer、训模型选 ai_model_training、做 Agent 选 ai_agent_dev、做 RAG/應用選 ai_application
8. 架构师岗位（Solution/System/Data/Cloud Architect）选 solution_architect
9. 纯管理岗位（Engineering Manager/Tech Lead/Team Lead）选 engineering_manager
10. 分析师岗位（System Analyst/Business Analyst）选 it_analyst
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
    "data_scientist": {"name": "数据科学家", "keywords": "数据分析, 统计, AB测试, SQL, Tableau, Python pandas, 数据可视化, 商业洞察"},
    "ml_engineer": {"name": "机器学习工程师", "keywords": "ML Pipeline, Model Deployment, MLOps, Feature Store, 分布式训练, 模型监控, Model Serving"},
    "data_engineer": {"name": "数据工程", "keywords": "Spark, Hadoop, Airflow, ETL, Data Pipeline, Snowflake"},
    "devops": {"name": "DevOps/SRE", "keywords": "Docker, K8s, Jenkins, Terraform, Ansible, CI/CD, Prometheus"},
    "qa": {"name": "质量保证", "keywords": "Selenium, TestNG, QA, Test Automation, Cypress"},
    "security": {"name": "安全工程", "keywords": "Cybersecurity, Penetration Test, SOC, ISO 27001"},
    "solution_architect": {"name": "解决方案架构师", "keywords": "Solution Architect, System Architecture, Technology Strategy, Cloud Architecture, Enterprise Architecture"},
    "engineering_manager": {"name": "工程经理/技术主管", "keywords": "Engineering Manager, Tech Lead, Team Lead, 技术管理, 团队领导"},
    "it_analyst": {"name": "IT 分析师/系统分析师", "keywords": "System Analyst, Business Analyst, Requirements Gathering, 系统分析, 需求分析"},
    "product": {"name": "产品管理", "keywords": "Product Manager, Roadmap, User Story, PRD"},
    "design": {"name": "设计师", "keywords": "Figma, Sketch, UX, UI, User Research, Prototype"},
    "blockchain": {"name": "区块链", "keywords": "Solidity, Smart Contract, DeFi, Web3, Ethereum"},
    "ai_prompt_engineer": {"name": "提示詞工程師", "keywords": "Prompt Engineering, Prompt Design, Few-shot, Prompt Template"},
    "ai_model_training": {"name": "模型訓練/微調", "keywords": "Model Training, Fine-tuning, LoRA, PEFT, RLHF, SFT, Pre-training"},
    "ai_agent_dev": {"name": "AI Agent開發", "keywords": "AI Agent, Multi-Agent, Agentic, Tool Use, AutoGPT, Function Calling, ReAct"},
    "ai_application": {"name": "AI應用開發", "keywords": "RAG, LangChain, LLamaIndex, Vector DB, LLM API, Dify"},
    "data_science": {"name": "数据科学（通用）", "keywords": "ML, TensorFlow, NLP, CV, 机器学习, 数据挖掘"},
    "other": {"name": "其他", "keywords": ""},
}


def build_role_classify_messages(jd_text: str) -> list[dict]:
    """构建角色分类消息（精简版，所有指令放在 user message 内）"""
    instruction = """You are a Hong Kong IT recruitment job classifier. Classify the following job description into exactly one role.

Return ONLY valid JSON with these fields:
- "role_id": one of: frontend, backend, fullstack, mobile, data_scientist, ml_engineer, data_engineer, devops, qa, security, solution_architect, engineering_manager, it_analyst, product, design, blockchain, ai_prompt_engineer, ai_model_training, ai_agent_dev, ai_application, data_science, other
- "role_name": Chinese name for the role
- "confidence": "high", "medium", or "low"

Role reference (distinguish carefully):
frontend=前端开发, backend=后端开发, fullstack=全栈开发, mobile=移动开发,
data_scientist=數據科學家(analysis/statistics/BI/visualization),
ml_engineer=機器學習工程師(ML pipeline/deployment/MLOps),
data_engineer=数据工程(ETL/Spark/data pipeline),
devops=DevOps/SRE, qa=质量保证, security=安全工程,
solution_architect=解决方案架构师(system/technology architecture),
engineering_manager=工程经理/技术主管(team leadership/management),
it_analyst=IT分析师/系统分析师(requirements/system analysis),
product=产品管理, design=设计师, blockchain=区块链,
ai_prompt_engineer=提示詞工程師(prompt design/optimization),
ai_model_training=模型訓練/微調(fine-tuning/LoRA/RLHF),
ai_agent_dev=AI Agent開發(multi-agent/tool-use/AutoGPT),
ai_application=AI應用開發(RAG/LangChain/LlamaIndex),
data_science=数据科学通用(fallback if unsure between data_scientist/ml_engineer),
other=其他

IMPORTANT distinctions:
- Data: analysis/statistics/BI → data_scientist; ML pipeline/deployment → ml_engineer; ETL/big data → data_engineer
- AI: prompt design → ai_prompt_engineer; model training/RLHF → ai_model_training; agents → ai_agent_dev; RAG/LLM apps → ai_application
- Architect roles (Solution/System/Cloud/Data Architect) → solution_architect
- Manager roles (Engineering Manager/Tech Lead/Team Lead) → engineering_manager
- Analyst roles (System Analyst/Business Analyst) → it_analyst
- Senior/Lead/Head titles: classify by technical domain, NOT as engineering_manager

Job description:
""" + jd_text[:3000]

    return [{"role": "user", "content": instruction}]
