from __future__ import annotations

from typing import Optional

from src.cleaner.text import JDTextCleaner
from src.cleaner.salary import SalaryParser
from src.logger import get_logger


class CleaningPipeline:
    """数据清洗管道，组合文本清洗与薪资解析"""

    def __init__(self):
        self.text_cleaner = JDTextCleaner()
        self.logger = get_logger(self.__class__.__name__)

    def clean_job(self, job: dict) -> dict:
        cleaned = dict(job)
        raw_jd = job.get("jd_raw", "")
        cleaned["jd_text"] = self.text_cleaner.clean(raw_jd)
        salary_raw = job.get("salary_raw", "")
        min_sal, max_sal = SalaryParser.parse(salary_raw)
        cleaned["salary_min"] = min_sal
        cleaned["salary_max"] = max_sal
        cleaned["salary_currency"] = "HKD"
        return cleaned

    def clean_batch(self, jobs: list[dict]) -> list[dict]:
        cleaned = []
        for job in jobs:
            try:
                cleaned.append(self.clean_job(job))
            except Exception as e:
                self.logger.warning("Failed to clean job %s: %s", job.get("job_id", "unknown"), e)
                cleaned.append(job)
        return cleaned
