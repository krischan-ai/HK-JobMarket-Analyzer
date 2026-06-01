from __future__ import annotations

from src.crawlers.base import BaseCrawler
from src.crawlers.jobsdb import JobsDBCrawler


_CRAWLER_REGISTRY = {
    "jobsdb": JobsDBCrawler,
}


def register_crawler(source: str, crawler_cls: type[BaseCrawler]):
    _CRAWLER_REGISTRY[source] = crawler_cls


def get_crawler(source: str = "jobsdb") -> BaseCrawler:
    if source not in _CRAWLER_REGISTRY:
        raise ValueError(f"Unknown crawler source: {source}. Available: {list(_CRAWLER_REGISTRY.keys())}")
    return _CRAWLER_REGISTRY[source]()


__all__ = ["BaseCrawler", "JobsDBCrawler", "get_crawler", "register_crawler"]
