from __future__ import annotations

from src.analyzer.skill_taxonomy import compact_known_labels

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
- "soft_skills": object with six arrays:
  - "education": education requirements in normalized Chinese labels
  - "language": language requirements in normalized Chinese labels
  - "soft_skill": personal capability requirements in normalized Chinese labels
  - "domain_knowledge": non-computer domain or industry knowledge requirements
  - "certification": professional qualifications or certificates
  - "business_skill": business, compliance, stakeholder, documentation, or project delivery skills
- "tag_profile": object with two arrays of evidence-backed structured tags:
  - "technical": technical skills/tools (programming_languages, frameworks_libraries, databases, cloud_devops, automation_toolkit, ai_api, ai_framework, ai_concepts, infrastructure, security_compliance, office_tools)
  - "non_technical": business_skill, domain_knowledge, soft_skill, education, language, certification, experience
  Each tag is an object: {"name","category","requirement_level","confidence","evidence"}
- "cross_industry_profile": object with six arrays of evidence-backed dimension tags (Hong Kong jobs are often "tech + industry client + business process + system object + compliance + delivery motion"):
  - "industry_context": served industry / client type (e.g. 政府/公共部門, 金融/銀行, 保險, 零售/電商, 物流, 醫療, 教育, 地產/物業, 公用事業/環保)
  - "business_scenario": concrete business process / scenario (e.g. 支付, 訂單, 履約, 風控, 設備監測, 水處理設施監測, 投標)
  - "solution_domain": solution / system direction (e.g. AI 方案, Digital Twin, ERP, CRM, D365, TMS, IT 基礎設施, 數據平台)
  - "delivery_motion": delivery action (e.g. 需求分析, 方案設計, 售前演示, 技術提案, POC 測試, 投標, 系統集成, 實施交付)
  - "compliance_standard": compliance/standard/security (e.g. ISO 27001, PDPO, AML/KYC, 政府合規, 信息安全合規)
  - "system_or_asset": built/integrated/monitored system or device (e.g. 傳感器, 機械設備, POS, 支付網關, 倉儲系統, 樓宇系統, ERP, 網絡設備)
  Each dimension tag is an object: {"name","confidence","evidence"}. Use 繁体中文 for names. Do NOT output combination/summary tags — the backend composes those.
- "candidate_taxonomy_updates": array of NEW reusable labels you discovered that are NOT already in the known taxonomy below. Each item: {"name","category","aliases":[...],"evidence","reason","confidence","requirement_level","status":"candidate"}.
- "candidate_alias_updates": array of term aliases mapping a JD term to a canonical label. Each item: {"alias","canonical","category","evidence","confidence"}.

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

Soft skill extraction rules:
- Only extract requirements explicitly present in the JD. Do not invent labels.
- Normalize education labels in Chinese, e.g. Bachelor's degree / bachelor / degree → "學士學位"; master preferred → "碩士優先"; computer science related degree → "計算機相關學歷".
- Normalize language labels in Chinese, e.g. English → "英語"; Cantonese → "粵語"; Mandarin / Putonghua → "普通話"; Chinese → "中文".
- Normalize personal capabilities in Chinese, e.g. communication → "溝通能力"; teamwork/collaboration/cross-functional collaboration → "團隊協作"; organizational skills → "組織能力"; problem-solving → "問題解決"; leadership → "領導力"; work under pressure → "抗壓能力".
- Extract domain_knowledge for non-computer professional knowledge, e.g. finance/fintech/banking → "金融/金融科技知識"; insurance/wealth management → "保險/財富管理知識"; risk/compliance/regulatory → "風險合規知識"; ecommerce/retail → "電商/零售業務知識".
- Extract certification for professional credentials, e.g. PMP, Scrum Master, CFA, FRM, CPA, SFC/HKMA, CISSP, CISA.
- Extract business_skill for stakeholder management, requirement gathering, documentation, presentation, project management, vendor management, customer-facing communication, compliance reporting.
- If a category is not mentioned, return an empty array for that category.

tag_profile extraction rules (evidence-driven, doc §11.5):
1. Every tag MUST cite a short JD quote in "evidence" (<=160 chars). No evidence => do not mark it as "required".
2. requirement_level is one of: "required" (essential/required/proficiency in/experience with), "preferred" (preferred/nice to have/familiarity with), "example" (skills after e.g./such as/like/one of, unless the same clause also says must/essential/required), "inferred" (reasonable but not stated in JD; confidence must be <=0.7).
3. Put OpenAI/Anthropic/Claude into category "ai_api"; LangChain/LlamaIndex into "ai_framework"; LLM/RAG/vector database into "ai_concepts". Do not output a standalone "llama" tag for LlamaIndex.
4. Do NOT extract domain/industry knowledge from benefits, location, or company-intro text; prefer responsibilities/requirements/qualifications.
5. Do NOT output "英語"/English as a language requirement merely because the JD is written in English; only when it explicitly requires English.
6. PowerPoint/Excel/MS Office go to category "office_tools", never into core technical stack.
7. "confidence" is a 0-1 float.

cross_industry_profile extraction rules (doc §11.10.2/§11.12):
1. Only extract from responsibilities/requirements/qualifications, with a JD quote in "evidence". Skip benefits/location/company-intro.
2. AI/Digital Twin alone must NOT decide the industry; when the client is government/utility/water, also output 政府/公共部門 (industry_context) and 水處理設施監測 (business_scenario), not just an AI tag.
3. Disambiguate by context: payment+banking/KYC → 金融/金融科技業務; payment+order/promotion/POS → 電商/零售業務; insurance+policy/claims → 保險/財富管理業務; insurance in benefits/coverage → do not output.
4. tender/POC/demo/proposal/pre-sales → delivery_motion (售前支持/技術提案/POC 測試/投標), not merely 溝通能力.
5. ISO 27001/PDPO/AML/KYC/government standards → compliance_standard, keeping the specific standard name.
6. sensors/machinery monitoring/water treatment facilities → system_or_asset (傳感器) and/or business_scenario (設備狀態監測); keep the industry scenario, not just a bare "Sensors".
7. business development manager is not a role tag, but when co-occurring with "develop business opportunities" output 業務拓展支持 (delivery_motion).

candidate_taxonomy_updates / candidate_alias_updates rules (doc §11.11.8):
1. Only propose REUSABLE labels (short phrases), never full sentences or one-off project descriptions.
2. Every candidate must have a JD-quote "evidence". No evidence => do not propose.
3. Do NOT propose a label already present in the known taxonomy list below (or an obvious synonym of it).
4. Mark each as "status":"candidate"; do not promote it to a formal label. Do not propose "inferred" candidates.
5. Use candidate_alias_updates when a JD term is clearly an alias of an existing canonical label (e.g. "Proof-Of-Concept" -> "POC 測試").
6. If you discover nothing genuinely new, return empty arrays.

Known taxonomy (do NOT re-propose these): """ + "、".join(compact_known_labels()) + """

Example output (a government/utility pre-sales solution JD):
{"role_id":"solution_architect","role_name":"解决方案架构师","confidence":"high","soft_skills":{"education":["學士學位"],"language":["英語","中文"],"soft_skill":["溝通能力"],"domain_knowledge":["政府/公共部門業務知識"],"certification":[],"business_skill":["需求分析","業務拓展支持"]},"tag_profile":{"technical":[{"name":"Digital Twin","category":"ai_concepts","requirement_level":"required","confidence":0.95,"evidence":"AI and Digital Twin solutions to government clients"},{"name":"IT 基礎設施方案設計","category":"infrastructure","requirement_level":"required","confidence":0.96,"evidence":"Design IT infrastructure solutions"},{"name":"ISO 27001","category":"security_compliance","requirement_level":"required","confidence":0.98,"evidence":"compliance with government standards such as ISO 27001"}],"non_technical":[{"name":"技術提案","category":"presales_delivery","requirement_level":"required","confidence":0.93,"evidence":"technical proposals"}]},"cross_industry_profile":{"industry_context":[{"name":"政府/公共部門","confidence":0.94,"evidence":"government and public sector clients"}],"business_scenario":[{"name":"水處理設施監測","confidence":0.96,"evidence":"water treatment facilities"}],"solution_domain":[{"name":"Digital Twin 解決方案","confidence":0.95,"evidence":"Digital Twin solutions"}],"delivery_motion":[{"name":"POC 測試","confidence":0.93,"evidence":"Proof-Of-Concept (POC) tests"},{"name":"投標","confidence":0.9,"evidence":"tender preparation"}],"compliance_standard":[{"name":"ISO 27001","confidence":0.98,"evidence":"such as ISO 27001"}],"system_or_asset":[{"name":"傳感器","confidence":0.94,"evidence":"recommending and specifying suitable sensors brands"}]},"candidate_taxonomy_updates":[{"name":"水處理設施知識","category":"domain_knowledge","aliases":["water treatment facilities"],"evidence":"water treatment facilities for government clients","reason":"domain knowledge not in current taxonomy","confidence":0.96,"requirement_level":"required","status":"candidate"}],"candidate_alias_updates":[{"alias":"Proof-Of-Concept","canonical":"POC 測試","category":"presales_delivery","evidence":"Proof-Of-Concept (POC) tests","confidence":0.95}]}

Job description:
""" + jd_text[:3000]

    return [{"role": "user", "content": instruction}]
