from __future__ import annotations

import time
from typing import Any, Optional

from src.crawlers.base import BaseCrawler
from src.logger import get_logger


class PlaywrightMixin:
    """为爬虫提供 Playwright 动态渲染能力的 Mixin 类"""

    def __init__(self, headless: bool = True, timeout: int = 30000):
        self.logger = get_logger(self.__class__.__name__)
        self.headless = headless
        self.timeout = timeout
        self._browser = None
        self._page = None
        self._playwright = None

    async def _start_browser(self):
        try:
            from playwright.async_api import async_playwright
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=self.headless,
                args=[
                    "--no-sandbox",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                ],
            )
            context = await self._browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            )
            self._page = await context.new_page()
            await self._page.set_viewport_size({"width": 1920, "height": 1080})
            self.logger.info("Playwright browser started")
        except ImportError:
            self.logger.error("playwright not installed. Run: pip install playwright && playwright install chromium")
            raise
        except Exception as e:
            self.logger.error("Failed to start browser: %s", e)
            raise

    async def _navigate(self, url: str, wait_selector: str = None, wait_ms: int = 3000) -> bool:
        if not self._page:
            return False
        try:
            await self._page.goto(url, wait_until="networkidle", timeout=self.timeout)
            await self._page.wait_for_timeout(wait_ms)
            if wait_selector:
                await self._page.wait_for_selector(wait_selector, timeout=self.timeout)
            return True
        except Exception as e:
            self.logger.error("Navigation failed for %s: %s", url, e)
            return False

    async def _get_text(self, selector: str) -> str:
        if not self._page:
            return ""
        try:
            el = await self._page.query_selector(selector)
            return await el.inner_text() if el else ""
        except Exception:
            return ""

    async def _get_html(self, selector: str = None) -> str:
        if not self._page:
            return ""
        try:
            if selector:
                el = await self._page.query_selector(selector)
                return await el.inner_html() if el else ""
            return await self._page.content()
        except Exception:
            return ""

    async def _close_browser(self):
        try:
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
            self.logger.info("Playwright browser closed")
        except Exception as e:
            self.logger.error("Error closing browser: %s", e)
