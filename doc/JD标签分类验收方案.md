# JD 标签分类验收方案：跨行业复合标签与候选词库发现

**版本**: v1.0  
**日期**: 2026-06-27  
**状态**: 验收方案  

---

## 1. 验收目标

本方案用于验收当前项目的角色分类与标签提炼能力，重点验证系统是否能从跨行业 JD 中提取出：

- 角色方向：如解决方案架构师、售前解决方案工程师、技术顾问。
- 技术能力：如 AI、Digital Twin、IT Infrastructure、Network Security。
- 行业/客户场景：如政府/公共部门、水处理设施、公用事业、环保工程。
- 业务交付动作：如需求分析、技术提案、方案演示、POC、投标准备。
- 合规与标准：如 ISO 27001、政府合规、信息安全合规。
- 系统/设备对象：如传感器、机械设备、设备状态监测。
- 结构化要求层级：`required`、`preferred`、`example`、`inferred`。
- 候选词库发现：现有词库没有覆盖的新标签是否进入候选池，而不是被直接丢弃。

验收重点不是只判断角色分类是否正确，而是判断系统是否保留了 JD 的“技术 + 行业 + 业务场景 + 交付动作 + 合规标准”的复合语义。

---

## 2. 验收样本

### 2.1 样本岗位

| 字段 | 值 |
|------|----|
| `job_id` | `jobsdb_AI_engineer_p1_5` |
| `title` | `Technical Engineer (AI/ML/Digital Twins Solutions)` |
| `company` | `ATAL Engineering Ltd` |
| 数据位置 | `data/cleaned/jobs.csv`、`data/raw/jobsdb_raw.json` |

### 2.2 核心 JD 证据

验收时至少应覆盖以下原文证据：

| 原文证据 | 应提炼方向 |
|---------|------------|
| `Understand client requirement and analyze their pain points... achieve business outcomes` | 需求分析、痛点分析、业务成果导向、解决方案式技术方法 |
| `persuasive presentations, solution designs, technical proposals, solution demonstrations, and Proof-Of-Concept (POC) tests` | 技术演示、解决方案设计、技术提案、方案演示、POC 测试 |
| `Design IT infrastructure solutions covering hardware, software, and security` | IT 基础设施方案设计、硬件方案、软件方案、安全方案 |
| `business development, vendors, and client... transitions from presales to project delivery` | 业务拓展支持、供应商沟通、客户沟通、售前到交付衔接 |
| `AI and Digital Twin solutions to government and public sector clients` | AI、Digital Twin、政府/公共部门客户 |
| `tender preparation & submission for tender bidding` | 投标准备、投标提交 |
| `At least 4 years of relevant working experience in the IT industry` | 4 年以上 IT 行业相关经验，`required` |
| `pre-sales or engineering background being preferred` | 售前经验或工程背景，`preferred` |
| `suitable sensors brands... physical condition of machinery in water treatment facilities` | 传感器选型、传感器品牌指定、设备状态监测、机械状态监测、水处理设施 |
| `networking, hardware, software, and network security... ISO 27001` | 网络架构、硬件方案、软件方案、网络安全、ISO 27001 |
| `spoken & written English and Chinese` | 英语、中文 |
| `PowerPoint, Excel & other MS Office software` | PowerPoint、Excel、MS Office，办公工具/售前交付辅助工具 |

---

## 3. 前置条件

### 3.1 数据前置条件

验收前确认：

- `data/cleaned/jobs.csv` 存在。
- `jobsdb_AI_engineer_p1_5` 存在于 `jobs.csv`。
- `jd_raw` 或 `jd_text` 包含 `water treatment facilities`、`Digital Twin`、`ISO 27001`、`Proof-Of-Concept` 等证据。

### 3.2 分类前置条件

验收前确认：

- 已执行一次角色分类。
- `data/role_cache.json` 存在。
- `role_cache.json` 中应能通过 JD cache key 或 `_job_id` 找到该岗位。

如果 `role_cache.json` 中找不到该岗位，本次验收直接判定为 **分类覆盖失败**，应先排查全量分类是否真正覆盖 `data/cleaned/jobs.csv` 的全部 244 条岗位。

---

## 4. 验收指标

### 4.1 角色分类指标

| 指标 | 期望结果 | 通过标准 |
|------|----------|----------|
| 角色分类 | `solution_architect` 优先；也可接受 `it_analyst` 但需有低置信提示 | 角色不能是 `frontend`、`backend`、`other` |
| 角色名称 | 解决方案架构师 / 售前解决方案工程师 / 技术顾问相关 | 能体现方案设计与客户技术支持属性 |
| 置信度 | `medium` 或 `high` | 若为 `low` 需视为待优化 |

### 4.2 技术标签指标

| 标签 | 分类 | 层级 | 证据要求 |
|------|------|------|----------|
| AI | `ai_concepts` 或 `solution_domain` | required | `AI and Digital Twin solutions` |
| Digital Twin | `ai_concepts` 或 `solution_domain` | required | `Digital Twin solutions` |
| IT Infrastructure | `infrastructure` | required | `Design IT infrastructure solutions` |
| Networking | `infrastructure` | required | `networking` |
| Hardware | `infrastructure` | required | `hardware` |
| Software | `infrastructure` | required | `software` |
| Network Security | `security_compliance` 或 `infrastructure` | required | `network security` |
| Sensors | `industrial_iot` 或 `system_or_asset` | required | `suitable sensors brands` |

### 4.3 行业与业务场景指标

| 标签 | 分类 | 层级 | 证据要求 |
|------|------|------|----------|
| 政府/公共部门客户 | `industry_context` / `domain_knowledge` | required | `government and public sector clients` |
| 水处理设施知识 | `business_scenario` / `domain_knowledge` | required | `water treatment facilities` |
| 公用事业/环保工程 | `industry_context` | inferred 或 required | `Environmental` + `water treatment facilities` |
| 设备状态监测 | `business_scenario` | required | `monitoring and tracking the physical condition` |
| 机械状态监测 | `system_or_asset` / `business_scenario` | required | `physical condition of machinery` |

### 4.4 售前与业务交付指标

| 标签 | 分类 | 层级 | 证据要求 |
|------|------|------|----------|
| 需求分析 | `business_skill` / `delivery_motion` | required | `Understand client requirement` |
| 痛点分析 | `business_skill` / `delivery_motion` | required | `analyze their pain points` |
| 业务成果导向 | `business_skill` | required | `achieve business outcomes` |
| 解决方案设计 | `presales_delivery` / `delivery_motion` | required | `solution designs` |
| 技术提案 | `presales_delivery` | required | `technical proposals` |
| 技术演示 / 方案演示 | `presales_delivery` | required | `presentations`、`solution demonstrations` |
| POC 测试 | `presales_delivery` | required | `Proof-Of-Concept (POC) tests` |
| 投标准备 | `presales_delivery` | required | `tender preparation` |
| 投标提交 | `presales_delivery` | required | `submission for tender bidding` |
| 业务拓展支持 | `presales_delivery` | required | `Partner with the business development manager` |
| 售前到交付衔接 | `delivery_motion` | required | `transitions from presales to project delivery` |
| 供应商沟通 | `business_skill` | required | `vendors` |
| 客户沟通 | `business_skill` | required | `client` |

### 4.5 合规与标准指标

| 标签 | 分类 | 层级 | 证据要求 |
|------|------|------|----------|
| ISO 27001 | `security_compliance` / `compliance_standard` | required | `ISO 27001` |
| 政府合规 | `security_compliance` | required | `government standards` |
| 信息安全合规 | `security_compliance` | required | `network security` + `ISO 27001` |
| 可靠运行保障 | `business_skill` / `infrastructure` | required | `ensuring reliable operations` |

### 4.6 经验、学历、语言与工具指标

| 标签 | 分类 | 层级 | 证据要求 |
|------|------|------|----------|
| 4 年以上 IT 行业相关经验 | `experience` | required | `At least 4 years... IT industry` |
| 售前经验 | `experience` / `presales_delivery` | preferred | `pre-sales... being preferred` |
| 工程背景 | `experience` | preferred | `engineering background being preferred` |
| AI / Environmental / Computer Science Engineering 相关学位 | `education` | required | `Degree holder in...` |
| 英语 | `language` | required | `spoken & written English` |
| 中文 | `language` | required | `spoken & written... Chinese` |
| 独立工作能力 | `soft_skill` | required | `work independently` |
| 团队合作 | `soft_skill` | required | `part of a team` |
| PowerPoint | `office_tool` | required | `PowerPoint` |
| Excel | `office_tool` | required | `Excel` |
| MS Office | `office_tool` | required | `MS Office` |

---

## 5. 不应误判的内容

| 不应输出 | 原因 | 正确处理 |
|---------|------|----------|
| 只输出 `人工智能/數據服務知識` | 过度泛化，丢失政府、水处理、传感器、基础设施、售前场景 | 应输出复合画像 |
| `PowerPoint` / `Excel` 进入核心工程技术栈榜单 | 它们是办公工具，不是软件工程技术栈 | 归入 `office_tool` 或售前交付辅助工具 |
| `售前经验` 标为 required | JD 明确 `being preferred` | 标为 `preferred` |
| `IoT` / `智慧水務` 标为 required | JD 未直接写 IoT / Smart Water | 可作为 `inferred`，置信度不超过 0.7 |
| 泛化 `風險合規知識` | JD 明确的是政府标准、ISO 27001、网络安全 | 应细化为 ISO 27001、政府合规、信息安全合规 |
| 从隐私声明提取合规标签 | `Personal data collected...` 是招聘隐私声明，不是岗位能力要求 | 不参与标签提取 |
| 从 Apply Now / salary / availability 提取业务能力 | 这是招聘流程说明 | 不参与标签提取 |

---

## 6. 验收步骤

### 6.1 定位岗位数据

检查 `data/cleaned/jobs.csv`：

```powershell
rg -n "water treatment facilities|Technical Engineer \(AI/ML/Digital Twins Solutions\)|ATAL Engineering" data/cleaned data/raw
```

通过标准：

- 至少在 `data/cleaned/jobs.csv` 中找到 `jobsdb_AI_engineer_p1_5`。

### 6.2 检查分类覆盖

检查 `data/role_cache.json`：

```powershell
python -c "import json; cache=json.load(open('data/role_cache.json',encoding='utf-8')); print(len(cache)); print([v.get('_job_id') for v in cache.values() if v.get('_job_id')])"
```

通过标准：

- 缓存条目数应接近 `jobs.csv` 岗位数。
- 至少应存在 `_job_id = jobsdb_AI_engineer_p1_5`，或能通过 JD hash 找到该岗位。

失败判定：

- 如果 `role_cache.json` 只有少量记录，例如 6 条，且没有 `_job_id`，则不是完整分类结果，不能证明该 JD 已被分类。

### 6.3 检查角色分类结果

检查缓存 entry：

| 字段 | 通过标准 |
|------|----------|
| `role_id` | `solution_architect` 优先 |
| `role_name` | 解决方案架构师或等价名称 |
| `confidence` | `medium` / `high` |

### 6.4 检查传统 `soft_skills`

当前已实现的结构主要是：

```json
{
  "education": [],
  "language": [],
  "soft_skill": [],
  "domain_knowledge": [],
  "certification": [],
  "business_skill": []
}
```

最低通过标准：

- `language` 至少包含 `英語`、`中文`。
- `soft_skill` 至少包含 `溝通能力`、`團隊協作` 或 `獨立工作能力`。
- `domain_knowledge` 至少包含 `政府/公共服務知識`。
- `business_skill` 至少包含 `需求分析`、`匯報/演示`、`客戶溝通`、`供應商管理` 中的一部分。

注意：当前 `soft_skills` 结构无法完整表达 `required/preferred/example/inferred` 和证据，完整验收需要 `tag_profile`。

### 6.5 检查结构化标签

如果已实现 v1.2+，检查：

```json
{
  "tag_profile": {},
  "cross_industry_profile": {},
  "job_context_profile": {},
  "taxonomy_candidates": []
}
```

通过标准：

- `tag_profile` 不能是空对象或空数组。
- `cross_industry_profile.industry_context` 应包含政府/公共部门。
- `cross_industry_profile.business_scenario` 应包含水处理设施、设备状态监测。
- `cross_industry_profile.solution_domain` 应包含 Digital Twin、IT 基础设施。
- `cross_industry_profile.delivery_motion` 应包含 POC、技术提案、投标。
- `cross_industry_profile.compliance_standard` 应包含 ISO 27001。
- `cross_industry_profile.system_or_asset` 应包含传感器、机械设备。
- `taxonomy_candidates` 应包含词库缺失但证据明确的候选标签，例如水处理设施知识、传感器品牌指定、设备状态监测。

### 6.6 检查前端展示

岗位浏览页应能展示：

- 技术标签：AI、Digital Twin、IT Infrastructure、Network Security。
- 非技术能力：需求分析、技术提案、POC、投标、客户沟通。
- 行业知识：政府/公共部门、水处理设施。
- 合规：ISO 27001。

如果前端只显示 `Analytical`、`Communication`，则说明目前仍停留在清洗数据 `skills.soft_skills` 或旧版 `soft_skills` 层级，未消费结构化标签。

---

## 7. 通过标准

### 7.1 最低通过

满足以下条件即可视为当前已实现能力的最低通过：

- 该 JD 被纳入 `role_cache.json`。
- 角色不是 `frontend` / `backend` / `other`。
- `soft_skills.language` 识别出英语、中文。
- `soft_skills.domain_knowledge` 至少识别出政府/公共服务。
- `soft_skills.business_skill` 至少识别出需求分析、演示、客户沟通、供应商管理中的两项。
- `skills` 或 `soft_skills` 不把隐私声明误判为岗位合规要求。

### 7.2 完整通过

满足以下条件视为 v1.2-v1.5 目标完整通过：

- `tag_profile` 存在且包含证据、置信度、要求层级。
- `cross_industry_profile` 六维均有合理标签。
- `job_context_profile.summary_tags` 生成跨行业组合画像，例如 `政府公用事業 AI/Digital Twin 售前解決方案`。
- `taxonomy_candidates` 包含词库缺失的新标签候选。
- `preferred` 和 `required` 能正确区分。
- `PowerPoint` / `Excel` 不进入核心技术栈统计。

---

## 8. 缺失项排查路径

| 缺失现象 | 优先排查位置 | 可能原因 |
|---------|--------------|----------|
| `role_cache.json` 找不到该岗位 | `api/routers/role_stats.py::_run_classify_in_background` | 没有真正执行全量分类；缓存被局部测试覆盖；`_job_id` 未写入 |
| 角色被分成 frontend/backend | `src/analyzer/role_prompt.py`、`src/analyzer/role_classifier.py::_classify_with_rules` | Prompt 对售前解决方案/基础设施方案岗位描述不足；规则关键词偏开发 |
| 没有政府/水处理/传感器标签 | `api/routers/stats.py::_canonical_non_tech_label`、`_scan_non_tech_labels_from_text` | 词库缺少水处理、传感器、设备状态监测、公用事业 |
| 没有 POC/投标/技术提案 | `role_prompt.py`、`_canonical_non_tech_label` 的 `business_skill` 组 | 售前交付动作未被纳入标签体系 |
| 没有 ISO 27001 | `certification` / `domain_knowledge` / 新 `security_compliance` 分类 | 当前六类 `soft_skills` 没有合规标准专门分类 |
| `PowerPoint` / `Excel` 进入技术栈 | `RuleBasedSkillExtractor` 或清洗阶段技能词库 | 办公工具和工程技术栈未分层 |
| `tag_profile` 为空 | `RoleResult`、`role_classifier.py`、`role_prompt.py` | v1.2+ 结构化标签尚未实现或未解析 |
| `taxonomy_candidates` 为空 | `TaxonomyDiscoveryAgent` | v1.5 候选词库发现 Agent 尚未实现 |

---

## 9. 当前项目预期结论模板

验收后按以下模板记录：

```text
岗位：jobsdb_AI_engineer_p1_5 / Technical Engineer (AI/ML/Digital Twins Solutions)

分类覆盖：
- 是否进入 role_cache.json：
- cache key / _job_id：

角色分类：
- 实际 role_id：
- 实际 role_name：
- 是否通过：

已识别标签：
- 技术：
- 行业/场景：
- 售前交付：
- 合规：
- 经验/学历/语言：

缺失标签：
- 

误判标签：
- 

原因归类：
- 数据覆盖问题 / Prompt 问题 / 词库缺口 / 后处理缺口 / 前端展示缺口 / v1.5 Agent 未实现

结论：
- 最低通过 / 部分通过 / 未通过
```

---

## 10. 本样本建议缺陷单

如果按当前代码能力验收，预计会出现以下缺陷：

| 编号 | 缺陷 | 严重度 | 建议修复 |
|------|------|--------|----------|
| ACC-JD-001 | `role_cache.json` 未覆盖该岗位或缓存条目过少 | 高 | 确保 `/api/stats/classify-jobs` 对 `jobs.csv` 全量执行，并写入 `_job_id` |
| ACC-JD-002 | `tag_profile` / `cross_industry_profile` 为空 | 高 | 实现 v1.2 结构化标签解析 |
| ACC-JD-003 | 水处理设施、传感器选型、设备状态监测缺失 | 高 | 扩展跨行业词库或启用 Taxonomy Discovery Agent |
| ACC-JD-004 | POC、投标、技术提案等售前动作缺失 | 中 | 扩展 `business_skill` / `presales_delivery` 标签 |
| ACC-JD-005 | ISO 27001 无法结构化归入合规标准 | 中 | 新增 `security_compliance` / `compliance_standard` 分类 |
| ACC-JD-006 | PowerPoint / Excel 与核心技术栈混排风险 | 中 | 新增 `office_tool` 分类，并从核心技术栈统计排除 |

---

## 11. 跨行业角色分类延伸标准

第 1–10 章以单一样本（售前解决方案架构师）说明验收口径。本章把同一套提炼逻辑**泛化为全行业、全角色通用标准**，使系统对任意 JD 都遵循一致的提炼粒度与归类规则，而不是只对样本岗位“凑答案”。

### 11.1 通用提炼原则（与行业无关）

无论 JD 属于哪个行业、哪个角色，提炼时都应满足：

1. **复合语义优先**：保留“技术 + 行业 + 业务场景 + 交付动作 + 合规标准”的组合，不得用单一泛标签（如 `軟件開發知識`）覆盖全部语义。
2. **证据可追溯**：每个标签都应能回指 JD 原文片段，无原文支撑的标签最高只能作为 `inferred`，置信度 ≤ 0.7。
3. **要求层级区分**：`required` / `preferred` / `example` / `inferred` 必须按 JD 措辞判定，`preferred`、`nice to have`、`being preferred`、`a plus` 一律归 `preferred`。
4. **同义归并但不过度合并**：同义词归并到规范词；语义不同的能力（如“流程自动化”与“数据集成”）不得合并。
5. **工具分层**：办公/低代码/原型工具（PowerPoint、Excel、Zapier、Make.com）归 `office_tool` / `lowcode_tool`，不进入核心工程技术栈统计。
6. **招聘流程噪声剔除**：隐私声明、薪资、Apply Now、到岗时间、EOE 声明等不参与标签提取。
7. **词库缺口进候选池**：词库未覆盖但证据明确的新标签进入 `taxonomy_candidates`，不得直接丢弃。

### 11.2 通用六维跨行业画像（`cross_industry_profile`）

六个维度对所有行业通用，下表给出跨行业定义与取值示例，替代“只面向某一岗位”的理解：

| 维度 | 通用含义 | 跨行业取值示例 |
|------|----------|----------------|
| `industry_context` | 行业 / 客户 / 组织场景 | 政府公共部门、金融、医疗、零售、制造、企业内部运营、教育、物流 |
| `business_scenario` | 具体业务场景 / 问题域 | 设备状态监测、流程自动化、风控、理赔、供应链优化、内部降本增效 |
| `solution_domain` | 解决方案 / 技术域 | AI/LLM、Digital Twin、数据中台、IT 基础设施、网络安全、RPA、集成中间件 |
| `delivery_motion` | 交付 / 工作动作 | 需求分析、方案设计、POC、投标、流程审计、端到端开发、部署运维 |
| `compliance_standard` | 合规 / 标准 / 认证 | ISO 27001、GDPR、PCI-DSS、政府标准、行业监管要求 |
| `system_or_asset` | 系统 / 设备 / 数据对象 | 传感器、机械设备、遗留办公系统、内部工具、数据库、第三方平台 |

> 规则：任一维度无证据则留空，不得为了“凑满六维”而臆造标签。

### 11.3 角色原型库（替代 frontend/backend 二分）

全行业分类不能退化为 `frontend` / `backend` / `other`。系统应至少能区分以下角色原型（`role_id` 建议值），并允许复合角色（主角色 + 次角色）：

| 角色原型 | `role_id` 建议 | 典型信号 |
|----------|----------------|----------|
| 前端工程师 | `frontend` | UI、React/Vue、用户交互 |
| 后端工程师 | `backend` | 服务端、API、数据库、并发 |
| 全栈工程师 | `fullstack` | 前后端通吃、端到端 |
| 解决方案架构师 / 售前 | `solution_architect` | 方案设计、技术提案、POC、投标 |
| 数据 / 算法工程师 | `data_ml_engineer` | 建模、特征、训练、推理 |
| AI / LLM 应用工程师 | `ai_engineer` | LLM API、RAG、向量库、Agent |
| 自动化 / 内部工具工程师 | `automation_engineer` | 流程自动化、RPA、内部工具、降本 |
| 平台 / DevOps / SRE | `platform_engineer` | CI/CD、容器、云、可靠性 |
| 数据工程师 | `data_engineer` | ETL、数仓、管道、SQL/NoSQL |
| 技术顾问 / 业务分析 | `it_analyst` | 需求梳理、跨职能沟通、流程优化 |
| 其他 / 待归类 | `other` | 仅当确实无法归入上述原型 |

判定规则：

- 优先匹配**业务意图**而非技术名词堆叠（如“替业务部门造内部工具降本”优先归 `automation_engineer`，即使写了 React）。
- 复合角色用主/次角色表达，置信度按证据强度给 `high/medium/low`。
- 当角色被分到与 JD 主诉求明显冲突的原型（如把“内部自动化降本”岗分成 `frontend`），按 §8 排查 `role_prompt.py` / `role_classifier.py`。

### 11.4 技术标签通用分类（`tag_profile` 子类）

| 子类 | 含义 | 示例 |
|------|------|------|
| `programming_language` | 编程语言 | Python、TypeScript、Go、Java、SQL |
| `ai_concepts` | AI/ML 概念与技术 | LLM、RAG、向量数据库、Agent、智能文档处理 |
| `framework_library` | 框架 / 库 / 编排 | LangChain、LlamaIndex、React、Vue |
| `infrastructure` | 基础设施 / 网络 / 硬件 | 云平台、网络、IT 基础设施、Docker |
| `data_storage` | 数据库 / 存储 | SQL、NoSQL、数仓、向量库 |
| `security_compliance` | 安全 / 合规 | 网络安全、ISO 27001 |
| `automation_integration` | 自动化 / 集成 | Web 爬虫、Cron、API 集成、RPA、中间件 |
| `industrial_iot` | 工业 / IoT / 设备 | 传感器、设备监测、Digital Twin |
| `lowcode_tool` | 低代码 / 原型工具 | Zapier、Make.com |
| `office_tool` | 办公工具 | PowerPoint、Excel、MS Office |

> `lowcode_tool`、`office_tool` 不计入核心工程技术栈榜单（沿用 §5、§10 规则）。

### 11.5 非技术标签通用分类

沿用现有 `soft_skills` 六类并扩展，对全行业通用：`education`、`language`、`soft_skill`、`domain_knowledge`、`certification`、`business_skill`，新增 `experience`（年限/背景）、`mindset`（工作理念，如“产品工程师思维”）、`presales_delivery`（售前交付动作）。

---

## 12. 验收样本二：内部自动化 / AI 工程师

本样本用于验证第 11 章泛化标准在**非售前、内部研发降本类岗位**上的适用性，与样本一（外部售前解决方案）形成跨角色对照。

### 12.1 样本岗位

| 字段 | 值 |
|------|----|
| `title` | `Internal Automation / AI Engineer`（产品工程师方向） |
| 角色原型 | `automation_engineer` 优先；可复合 `ai_engineer`、`fullstack` |
| 岗位主诉求 | 审计内部流程、自动化重复劳动、改造遗留系统、落地 AI、替代付费工具降本 |

### 12.2 核心 JD 证据 → 应提炼方向

| 原文证据 | 应提炼方向 | 维度 |
|---------|------------|------|
| `Audit existing office workflows, identify repetitive manual tasks` | 工作流审计、重复任务识别 | `delivery_motion` / `business_scenario` |
| `develop robust scripts or applications to automate them` | 流程自动化、脚本/应用开发 | `solution_domain` / `delivery_motion` |
| `Build integration layers, APIs, or middleware to connect... older office systems` | 集成层/中间件/API 集成、遗留系统现代化 | `solution_domain` / `system_or_asset` |
| `deploy AI/ML solutions... leveraging LLM APIs, building internal chatbots, intelligent document processing` | LLM API、内部聊天机器人、智能文档处理 | `solution_domain` / `ai_concepts` |
| `replaces expensive third-party tools or eliminates hundreds of hours of manual data entry` | 成本/人力削减、替代第三方工具 | `business_scenario` |
| `Own the entire software lifecycle... from gathering requirements... to deployment and maintenance` | 端到端开发、需求收集、部署运维 | `delivery_motion` |
| `Python (essential for AI/automation)` | Python | `programming_language`，required |
| `at least one other major language (JavaScript/TypeScript, Go, or Java)` | 第二门主流语言（任一） | `programming_language`，required（择一） |
| `AI APIs (OpenAI, Anthropic, etc.), vector databases, LangChain/LlamaIndex` | LLM API、向量数据库、LangChain/LlamaIndex | `ai_concepts` / `framework_library`，required |
| `web scraping, cron jobs, API integrations, RPA concepts or tools` | Web 爬虫、Cron、API 集成、RPA 概念 | `automation_integration`，required |
| `SQL and NoSQL databases... older, poorly documented data structures` | SQL、NoSQL、遗留数据结构理解 | `data_storage` / `system_or_asset`，required |
| `"product engineer" mentality—solving the business problem and saving money` | 产品工程师思维、业务/降本导向 | `mindset` / `soft_skill`，required |
| `3+ years of professional software development experience` | 3 年以上软件开发经验 | `experience`，required |
| `proven track record of deploying internal automation tools or AI integrations` | 内部自动化/AI 集成落地经验 | `experience`，required |
| `cloud platforms (AWS, GCP, Azure) and basic DevOps (Docker, CI/CD)` | 云平台、Docker、CI/CD | `infrastructure`，preferred |
| `low-code/no-code tools (Make.com, Zapier) for rapid prototyping` | Make.com、Zapier | `lowcode_tool`，preferred |
| `Excellent communication skills—talk to non-technical staff` | 跨职能沟通、面向非技术人员 | `soft_skill`，preferred/required |

### 12.3 期望六维画像

| 维度 | 期望标签 |
|------|----------|
| `industry_context` | 企业内部运营 / 数字化降本（`inferred`，无明确行业，置信度 ≤ 0.7） |
| `business_scenario` | 流程自动化、重复任务消除、降本增效、替代第三方工具、人工录入消除 |
| `solution_domain` | LLM/AI 集成、智能文档处理、内部聊天机器人、系统集成中间件、RPA |
| `delivery_motion` | 工作流审计、需求收集、端到端开发、部署运维、遗留系统改造 |
| `compliance_standard` | （空——JD 未提合规标准，不得臆造） |
| `system_or_asset` | 遗留办公系统、内部工具、SQL/NoSQL 数据库、第三方平台 |

### 12.4 不应误判的内容（样本二专属）

| 不应输出 | 原因 | 正确处理 |
|---------|------|----------|
| Make.com / Zapier 进入核心工程技术栈 | 是低代码原型工具且为 `preferred` | 归 `lowcode_tool`，preferred，排除技术栈榜单 |
| Docker / CI/CD / 云平台标为 required | JD 明确在 `Preferred Qualifications` 下 | 标为 `preferred` |
| 把 Go、Java、TypeScript 全部标 required | JD 是“至少再掌握一门”择一要求 | Python 为 required，其余作为“第二语言候选”，单门不强制 |
| 掌握某具体 RPA 工具（如 UiPath） | JD 只要求 `RPA concepts or tools` 熟悉 | 标为 RPA 概念熟悉，不绑定具体工具 |
| 把 `product engineer mentality` 当技术标签 | 这是工作理念/软技能 | 归 `mindset` / `soft_skill` |
| 臆造合规标签（如 GDPR、ISO） | JD 全文无任何合规标准 | `compliance_standard` 留空 |
| 角色分成 `frontend` / `backend` | 岗位主诉求是内部自动化降本 | 归 `automation_engineer`（可复合 `ai_engineer`） |

### 12.5 跨样本一致性校验

两个样本应共同验证以下泛化能力：

- 同一套六维 + 要求层级 + 证据回指，对**外部售前**与**内部研发降本**两类岗位均适用。
- 工具分层规则（`office_tool` / `lowcode_tool` 排除技术栈）在两类岗位均生效。
- `preferred` 判定在“`being preferred`”与“`Preferred Qualifications` 段落”两种措辞下都正确。
- 角色分类能跳出 frontend/backend 二分，落到 `solution_architect` 与 `automation_engineer` 两个不同原型。
- 无证据维度（样本二的 `compliance_standard`）能正确留空，而非臆造。

