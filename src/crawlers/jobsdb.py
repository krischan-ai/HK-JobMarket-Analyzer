from __future__ import annotations

import json
import time
from typing import Any, Optional

from config.settings import settings
from src.crawlers.base import BaseCrawler
from src.crawlers.delay import AdaptiveDelayController
from src.crawlers.proxy import ProxyManager


class JobsDBCrawler(BaseCrawler):
    """JobsDB 香港招聘数据爬虫"""

    BASE_URL = "https://hk.jobsdb.com/api/jobs"
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Referer": "https://hk.jobsdb.com/",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-HK,en-HK;q=0.9,en;q=0.8,zh-CN;q=0.7",
    }

    def __init__(self):
        proxy_mgr = ProxyManager.from_settings(
            http=settings.proxy_http,
            https=settings.proxy_https,
        )
        super().__init__(proxy_config=proxy_mgr.get_random())
        self.session.headers.update(self.HEADERS)
        self.delay_controller = AdaptiveDelayController(
            delay_min=settings.crawl_delay_min,
            delay_max=settings.crawl_delay_max,
        )
        self.timeout = settings.crawl_timeout

    def fetch_page(self, keyword: str, page: int = 1) -> Optional[dict]:
        params = {
            "keyword": keyword,
            "page": page,
            "location": "Hong Kong",
        }
        try:
            response = self.session.get(
                self.BASE_URL,
                params=params,
                timeout=self.timeout,
            )
            response.raise_for_status()
            self.delay_controller.record(True)
            return response.json()
        except Exception as e:
            self.logger.error(
                "Failed to fetch keyword=[%s] page=[%d]: %s",
                keyword, page, e,
            )
            self.delay_controller.record(False)
            return None

    def parse(self, raw_data: Optional[dict]) -> list[dict]:
        if not raw_data:
            return []

        jobs = raw_data.get("jobs") or raw_data.get("data", {}).get("jobs") or []
        parsed = []

        for job in jobs:
            parsed.append(self._parse_single(job))

        return parsed

    def _parse_single(self, job: dict) -> dict:
        return {
            "job_id": job.get("id") or job.get("jobId", ""),
            "title": job.get("title", ""),
            "company": job.get("company", {}).get("name", "") if isinstance(job.get("company"), dict) else job.get("company", ""),
            "location": job.get("location", ""),
            "salary_raw": job.get("salary", ""),
            "jd_raw": job.get("description") or job.get("advertiser", {}).get("description", ""),
            "url": job.get("url") or job.get("jobUrl", ""),
            "source": "jobsdb",
        }

    def run(self, keyword: str, max_pages: int = None) -> list[dict]:
        max_pages = max_pages or settings.crawl_max_pages
        all_jobs = []

        for page in range(1, max_pages + 1):
            self.logger.info("Crawling keyword=[%s] page=[%d/%d]", keyword, page, max_pages)
            raw = self.fetch_page(keyword, page)
            jobs = self.parse(raw)

            if not jobs:
                self.logger.info("No more jobs for keyword=[%s], stopping at page=%d", keyword, page)
                break

            all_jobs.extend(jobs)
            self.logger.info("Collected %d jobs (total: %d)", len(jobs), len(all_jobs))
            self.delay_controller.wait()

        return all_jobs

    def search_keywords(self, keywords: list[str], max_pages: int = None) -> list[dict]:
        all_jobs = []
        for kw in keywords:
            jobs = self.run(kw, max_pages=max_pages)
            all_jobs.extend(jobs)
        return all_jobs
