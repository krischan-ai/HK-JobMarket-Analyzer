from __future__ import annotations

from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.logger import get_logger


class BaseCrawler(ABC):
    """爬虫抽象基类，定义爬虫的统一接口"""

    def __init__(self, proxy_config: Optional[dict] = None, max_workers: int = 3):
        self.logger = get_logger(self.__class__.__name__)
        self.session = self._create_session()
        self.proxies = proxy_config
        self.max_workers = max_workers
        if self.proxies:
            self.session.proxies.update(self.proxies)

    def _create_session(self) -> requests.Session:
        session = requests.Session()
        retry = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
        )
        adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=20)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def _request(self, url: str, **kwargs) -> Optional[requests.Response]:
        try:
            kwargs.setdefault("timeout", 30)
            response = self.session.get(url, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.Timeout:
            self.logger.error("Timeout for %s", url)
            return None
        except requests.exceptions.ConnectionError as e:
            self.logger.error("Connection failed for %s: %s", url, e)
            return None
        except requests.exceptions.HTTPError as e:
            self.logger.error("HTTP error for %s: %s", url, e)
            return None
        except requests.exceptions.RequestException as e:
            self.logger.error("Request failed for %s: %s", url, e)
            return None

    def run_concurrent(self, keywords: list[str], max_pages: int = 5) -> dict[str, list[dict]]:
        """并发爬取多个关键词"""
        results: dict[str, list[dict]] = {}
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_map = {executor.submit(self.run, kw, max_pages): kw for kw in keywords}
            for future in as_completed(future_map):
                kw = future_map[future]
                try:
                    results[kw] = future.result()
                    self.logger.info("Concurrent crawl completed for keyword=[%s]", kw)
                except Exception as e:
                    self.logger.error("Concurrent crawl failed for keyword=[%s]: %s", kw, e)
                    results[kw] = []
        return results

    @abstractmethod
    def fetch_page(self, keyword: str, page: int = 1) -> Optional[Any]:
        ...

    @abstractmethod
    def parse(self, raw_data: Any) -> list[dict]:
        ...

    @abstractmethod
    def run(self, keyword: str, max_pages: int = 5) -> list[dict]:
        ...
