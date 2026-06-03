from __future__ import annotations

from typing import Any, Optional

from src.crawlers.base import BaseCrawler
from src.crawlers.delay import AdaptiveDelayController
from src.logger import get_logger


class JIJISCrawler(BaseCrawler):
    """JIJIS (Joint Institutions Job Information System) 八大联校招聘爬虫

    八大院校：港大、中大、科大、理大、城大、浸大、岭大、教大
    数据源：https://www.jijis.org.hk/
    """

    BASE_URL = "https://www.jijis.org.hk/api/jobs"
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Referer": "https://www.jijis.org.hk/",
        "Accept": "application/json",
    }

    def __init__(self, proxy_server: str = None):
        proxy_config = None
        if proxy_server:
            proxy_config = {"http": proxy_server, "https": proxy_server}
        super().__init__(proxy_config=proxy_config)
        self.session.headers.update(self.HEADERS)
        self.delay_controller = AdaptiveDelayController(delay_min=2, delay_max=5)

    def fetch_page(self, keyword: str, page: int = 1) -> Optional[dict]:
        params = {"keyword": keyword, "page": page, "lang": "en"}
        try:
            resp = self.session.get(self.BASE_URL, params=params, timeout=15)
            resp.raise_for_status()
            self.delay_controller.record(True)
            return resp.json()
        except Exception as e:
            self.logger.error("JIJIS fetch failed: %s", e)
            self.delay_controller.record(False)
            return None

    def parse(self, raw_data: Optional[dict]) -> list[dict]:
        if not raw_data:
            return []
        jobs = raw_data.get("jobs") or raw_data.get("data", [])
        parsed = []
        for job in jobs:
            parsed.append({
                "job_id": f"jijis_{job.get('id', '')}",
                "title": job.get("title", ""),
                "company": job.get("company", {}).get("name", "") if isinstance(job.get("company"), dict) else job.get("company", ""),
                "location": job.get("location", "Hong Kong"),
                "salary_raw": job.get("salary", ""),
                "jd_raw": job.get("description", ""),
                "url": job.get("url", ""),
                "source": "jijis",
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
