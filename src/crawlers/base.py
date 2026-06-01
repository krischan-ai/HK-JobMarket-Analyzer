from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.logger import get_logger


class BaseCrawler(ABC):
    """爬虫抽象基类，定义爬虫的统一接口"""

    def __init__(self, proxy_config: Optional[dict] = None):
        self.logger = get_logger(self.__class__.__name__)
        self.session = self._create_session()
        self.proxies = proxy_config
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
            kwargs.setdefault("timeout", 15)
            response = self.session.get(url, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            self.logger.error("Request failed for %s: %s", url, e)
            return None

    @abstractmethod
    def fetch_page(self, keyword: str, page: int = 1) -> Optional[Any]:
        ...

    @abstractmethod
    def parse(self, raw_data: Any) -> list[dict]:
        ...

    @abstractmethod
    def run(self, keyword: str, max_pages: int = 5) -> list[dict]:
        ...
