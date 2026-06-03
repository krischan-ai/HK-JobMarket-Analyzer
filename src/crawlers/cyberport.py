from __future__ import annotations

from typing import Any, Optional

from src.crawlers.base import BaseCrawler
from src.crawlers.playwright_mixin import PlaywrightMixin
from src.logger import get_logger


class CyberportCrawler(BaseCrawler, PlaywrightMixin):
    """数码港 (Cyberport) 招聘数据爬虫

    数据源：https://www.cyberport.hk/job-vacancy/
    数码港社群企业招聘，侧重金融科技/Web3/数码娱乐
    使用 Playwright 动态渲染获取页面内容
    """

    BASE_URL = "https://www.cyberport.hk/job-vacancy/"

    def __init__(self, headless: bool = True, proxy_server: str = None):
        BaseCrawler.__init__(self)
        PlaywrightMixin.__init__(self, headless=headless, proxy_server=proxy_server, timeout=60000)
        self.logger = get_logger(self.__class__.__name__)

    def fetch_page(self, keyword: str, page: int = 1) -> Optional[list[dict]]:
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(self._async_fetch(keyword, page))

    async def _async_fetch(self, keyword: str, page: int = 1) -> Optional[list[dict]]:
        await self._start_browser()
        try:
            url = f"{self.BASE_URL}?search={keyword}&page={page}"
            success = await self._navigate(url, wait_selector=".job-listing", wait_ms=3000)
            if not success:
                return None

            html = await self._get_html(".job-listing")
            return self._parse_html(html)
        finally:
            await self._close_browser()

    def _parse_html(self, html: str) -> list[dict]:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        jobs = []
        for item in soup.select(".job-card"):
            title_el = item.select_one(".job-title a")
            company_el = item.select_one(".company")
            desc_el = item.select_one(".description")
            jobs.append({
                "title": title_el.get_text(strip=True) if title_el else "",
                "company": company_el.get_text(strip=True) if company_el else "",
                "location": "Cyberport",
                "jd_raw": desc_el.get_text(strip=True) if desc_el else "",
                "url": title_el.get("href", "") if title_el else "",
                "source": "cyberport",
            })
        for i, job in enumerate(jobs):
            job["job_id"] = f"cyberport_{i}"
        return jobs

    def parse(self, raw_data: Optional[list[dict]]) -> list[dict]:
        return raw_data or []

    def run(self, keyword: str, max_pages: int = 5) -> list[dict]:
        all_jobs = []
        for page in range(1, max_pages + 1):
            jobs = self.fetch_page(keyword, page)
            if not jobs:
                break
            all_jobs.extend(jobs)
        return all_jobs
