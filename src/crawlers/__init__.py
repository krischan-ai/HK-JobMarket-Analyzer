from __future__ import annotations

from src.crawlers.base import BaseCrawler
from src.crawlers.jobsdb import JobsDBCrawler
from src.crawlers.jijis import JIJISCrawler
from src.crawlers.offertoday import OfferTodayCrawler
from src.crawlers.hkstp import HKSTPCrawler
from src.crawlers.cyberport import CyberportCrawler
from src.crawlers.indeed import IndeedCrawler


_CRAWLER_REGISTRY: dict[str, type[BaseCrawler]] = {
    "jobsdb": JobsDBCrawler,
    "jijis": JIJISCrawler,
    "offertoday": OfferTodayCrawler,
    "hkstp": HKSTPCrawler,
    "cyberport": CyberportCrawler,
    "indeed": IndeedCrawler,
}


def register_crawler(source: str, crawler_cls: type[BaseCrawler]):
    _CRAWLER_REGISTRY[source] = crawler_cls


def get_crawler(source: str = "jobsdb") -> BaseCrawler:
    if source not in _CRAWLER_REGISTRY:
        raise ValueError(
            f"Unknown crawler source: {source}. "
            f"Available: {list(_CRAWLER_REGISTRY.keys())}"
        )
    return _CRAWLER_REGISTRY[source]()


def list_sources() -> list[str]:
    return list(_CRAWLER_REGISTRY.keys())


__all__ = [
    "BaseCrawler",
    "JobsDBCrawler",
    "JIJISCrawler",
    "OfferTodayCrawler",
    "HKSTPCrawler",
    "CyberportCrawler",
    "IndeedCrawler",
    "get_crawler",
    "register_crawler",
    "list_sources",
]
