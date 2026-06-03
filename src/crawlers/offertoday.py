from __future__ import annotations

from typing import Any, Optional

from src.crawlers.base import BaseCrawler
from src.crawlers.delay import AdaptiveDelayController
from src.logger import get_logger


class OfferTodayCrawler(BaseCrawler):
    """OfferToday 毕业生岗位爬虫

    数据源：https://www.ofhr.com.hk/ (OfferToday)
    专注毕业生与初级岗位，中英双语 JD 占比高
    """

    BASE_URL = "https://www.ofhr.com.hk/api/job/search"
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Referer": "https://www.ofhr.com.hk/",
        "Accept": "application/json",
    }

    def __init__(self, proxy_server: str = None):
        proxy_config = None
        if proxy_server:
            proxy_config = {"http": proxy_server, "https": proxy_server}
        super().__init__(proxy_config=proxy_config)
        self.session.headers.update(self.HEADERS)
        self.delay_controller = AdaptiveDelayController(delay_min=2, delay_max=4)

    def fetch_page(self, keyword: str, page: int = 1) -> Optional[dict]:
        params = {"keyword": keyword, "page": page, "pageSize": 20}
        try:
            resp = self.session.get(self.BASE_URL, params=params, timeout=15)
            resp.raise_for_status()
            self.delay_controller.record(True)
            return resp.json()
        except Exception as e:
            self.logger.error("OfferToday fetch failed: %s", e)
            self.delay_controller.record(False)
            return None

    def parse(self, raw_data: Optional[dict]) -> list[dict]:
        if not raw_data:
            return []
        jobs = raw_data.get("data", {}).get("list", []) if isinstance(raw_data.get("data"), dict) else raw_data.get("jobs", [])
        parsed = []
        for job in jobs:
            parsed.append({
                "job_id": f"offertoday_{job.get('id', '')}",
                "title": job.get("title", ""),
                "company": job.get("companyName", ""),
                "location": job.get("location", "Hong Kong"),
                "salary_raw": job.get("salary", ""),
                "jd_raw": job.get("description", ""),
                "url": job.get("url", ""),
                "source": "offertoday",
            })
        return parsed

    def run(self, keyword: str, max_pages: int = 5) -> list[dict]:
        all_jobs = []
        for page in range(1, max_pages + 1):
            raw = self.fetch_page(keyword, page)
            jobs = self.parse(raw)
            if not jobs:
                break
            all_jobs.extend(jobs)
            self.delay_controller.wait()
        return all_jobs
