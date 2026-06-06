"""保险销售岗位 LLM 复审模块 — 发送规则集 + JD 给模型 API，获取复审结果和解释"""
from __future__ import annotations

import json
import time
from typing import Optional

from src.llm_config_manager import LLMConfigManager
from config.settings import settings
from src.logger import get_logger

# 保险销售判定规则集（供 LLM 参考）
INSURANCE_REVIEW_RULES = """
## 保险销售伪装岗位检测规则

### 检测维度与权重

A. 标题特征（高权重 +3）：岗位名称包含以下关键词之一即高度疑似保险销售
- "wealth management", "wealth manager", "wealth planner", "wealth management trainee"
- "financial consultant", "financial planner", "financial advisor"
- "family office", "理财顾问", "management trainee", "management associate"

B. 公司特征（中权重 +2）：公司名包含保险公司关键词
- AIA 友邦、AXA 安盛、Prudential 保诚、Manulife 宏利、FWD 富卫
- 中国人寿 China Life、平安保险 Ping An、MetLife、Chubb、Zurich
- AMG Financial、Family Office 类公司

C. JD 内容特征（累计制，每个+1，上限10）：
- 核心保险词：wealth management, financial planning, insurance product, retirement planning, estate planning, 财富管理, 投资规划, 保险产品
- 低门槛特征：fresh graduate, 应届, IANG, 优才, 普通话, no experience, 无需经验, training provided
- 薪酬模式：底薪+佣金, 高额佣金, commission based, 收入无上限, unlimited income, 快速晋升, fast track, 月入可达
- 培训相关：考试费用, exam fee, 牌照考试, IIQE, 保险中介人, 提供培训, 在职培训, mentorship
- 工作方式：弹性工作, flexible hours, 自主安排, overseas conference, 海外会议, 海外旅游奖励

D. 位置特征（中权重 +2）：公司地址在保险销售重灾区
- 尖沙咀 Tsim Sha Tsui, 铜锣湾 Causeway Bay, 海港城 Harbour City

E. 薪酬特征（中权重 +2）：薪资范围极大，如 15k-50k, 17000-50000

F. 组合特征（+2）：标题含 "trainee" 且公司为保险公司

### 判定阈值
总分 >= 5 即标记为"疑似保险销售"。

### 注意事项
- 真实保险公司的 IT 岗位（如 AIA 的 Software Engineer）不命中标题/JD/薪酬特征，得分极低（通常只有公司名 +2），不应判为保险
- 保险公司 IT 岗的 JD 通常包含 python/react/aws/docker 等技术关键词，不存在 wealth management/底薪+佣金等保险销售词
- 仅标题命中 "management trainee" 而公司非保险且 JD 无保险销售特征，可能只是普通管培生，不判为保险

### 复审要求
根据上述规则检测，对给定岗位进行二审：
1. 重新评估每个维度的匹配情况
2. 判断是否确实为保险销售伪装岗位（而非保险公司真实 IT 岗）
3. 用中文给出简明复审理由和最终判定
"""

REVIEW_SYSTEM_PROMPT = f"""{INSURANCE_REVIEW_RULES}

请对以下岗位进行二审，输出 JSON 格式：
{{"is_insurance": true/false, "confidence": "high/medium/low", "explanation": "中文解释，100字以内，说明为什么判定为保险销售或为什么不是"}}
"""


class InsuranceReviewer:
    """保险岗位 LLM 复审器"""

    def __init__(self, api_key: str = None, api_base: str = None, model: str = None, timeout: int = 30):
        self.logger = get_logger(self.__class__.__name__)
        file_config = LLMConfigManager().build_kwargs()

        self.api_key = api_key or file_config.get("api_key") or settings.llm_api_key or ""
        self.api_base = (api_base or file_config.get("api_base") or settings.llm_base_url or "").rstrip("/")
        self.model = model or file_config.get("model") or settings.llm_model or "deepseek-chat"
        self.timeout = timeout or file_config.get("timeout", 30)

    @property
    def available(self) -> bool:
        return bool(self.api_key) and bool(self.api_base)

    def review_one(self, job: dict) -> dict:
        """复审单个岗位"""
        if not self.available:
            return {
                "is_insurance": job.get("is_insurance_sales", False),
                "confidence": "low",
                "explanation": "LLM 未配置，无法复审，保留规则检测结果",
            }

        title = job.get("title", "")
        company = job.get("company", "")
        jd_text = job.get("jd_raw", "")
        location = job.get("location", "")
        salary = job.get("salary_raw", "")
        score = job.get("insurance_score", 0)

        user_message = f"""【岗位信息】
标题: {title}
公司: {company}
地点: {location}
薪资: {salary}
规则检测得分: {score}

【岗位 JD】
{jd_text[:3000]}

请根据规则集进行二审，输出 JSON。"""

        messages = [
            {"role": "system", "content": REVIEW_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ]

        for attempt in range(3):
            try:
                response = self._call_api(messages)
                result = self._parse_response(response)
                if result is not None:
                    return result
            except Exception as e:
                self.logger.error("Insurance review attempt %d failed: %s", attempt + 1, e)
                if attempt < 2:
                    time.sleep(2 ** attempt)

        return {
            "is_insurance": False,
            "confidence": "low",
            "explanation": "LLM 复审失败，回退为不标记",
        }

    def review_batch(self, jobs: list[dict]) -> list[dict]:
        """批量复审"""
        results = []
        for job in jobs:
            result = self.review_one(job)
            job["llm_is_insurance"] = result["is_insurance"]
            job["llm_confidence"] = result["confidence"]
            job["llm_explanation"] = result["explanation"]
            results.append(job)
            if len(results) < len(jobs):
                time.sleep(0.3)  # API 限流
        return results

    def _call_api(self, messages: list[dict]) -> dict:
        import requests
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1,
            "max_tokens": 512,
        }
        url = f"{self.api_base}/chat/completions"
        resp = requests.post(
            url, headers=headers, json=payload,
            timeout=self.timeout,
            proxies={"http": None, "https": None},
        )
        resp.raise_for_status()
        return resp.json()

    def _parse_response(self, response: dict) -> Optional[dict]:
        try:
            content = response["choices"][0]["message"]["content"]
            content = content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[-1]
                content = content.rsplit("```", 1)[0]
            result = json.loads(content)
            return {
                "is_insurance": bool(result.get("is_insurance", False)),
                "confidence": str(result.get("confidence", "low")),
                "explanation": str(result.get("explanation", "")),
            }
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            self.logger.error("Failed to parse review response: %s", e)
            return None
