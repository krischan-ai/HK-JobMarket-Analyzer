from __future__ import annotations
"""依次尝试所有爬虫数据源，通过代理收集真实岗位数据"""
import sys
import json
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.cleaner.pipeline import CleaningPipeline
from src.analyzer.rule_engine import RuleBasedSkillExtractor
from src.storage.csv_exporter import CSVExporter
from src.logger import setup_logger, get_logger

setup_logger(level="INFO")
logger = get_logger("crawl_all")

PROXY = "http://127.0.0.1:10808"

KEYWORDS = [
    "software engineer", "data scientist", "frontend developer",
    "backend developer", "devops engineer", "full stack developer",
    "AI engineer", "mobile developer", "data engineer",
]

MAX_PAGES = 2
RAW_DIR = Path("data/raw")
CLEAN_DIR = Path("data/cleaned")
RAW_DIR.mkdir(parents=True, exist_ok=True)
CLEAN_DIR.mkdir(parents=True, exist_ok=True)


def try_first(proxy: str):
    """快速测试每个爬虫能否拿到数据，优先跑成功的"""
    logger.info("=== Quick connectivity test ===")
    results = {}

    for name, fn, args in [
        ("Indeed", _try_indeed, ()),
        ("Cyberport", _try_cyberport, ()),
        ("HKSTP", _try_hkstp, ()),
        ("JIJIS", _try_jijis, ()),
        ("OfferToday", _try_offertoday, ()),
    ]:
        try:
            logger.info("Testing %s...", name)
            jobs = fn(proxy, quick=True)
            count = len(jobs) if jobs else 0
            logger.info("  %s: %d jobs", name, count)
            results[name] = jobs if count > 0 else []
        except Exception as e:
            logger.warning("  %s: ERROR - %s", name, type(e).__name__)
            results[name] = []
    return results


def _try_indeed(proxy: str, quick: bool = False):
    from src.crawlers.indeed import IndeedCrawler
    crawler = IndeedCrawler(headless=True, proxy_server=proxy)
    kw = "software engineer"
    try:
        jobs = crawler.run(kw, max_pages=2 if not quick else 1)
        logger.info("  Indeed: %d jobs for '%s'", len(jobs), kw)
        return jobs
    except Exception as e:
        logger.warning("  Indeed: %s", e)
        return []


def _try_cyberport(proxy: str, quick: bool = False):
    from src.crawlers.cyberport import CyberportCrawler
    crawler = CyberportCrawler(headless=True, proxy_server=proxy)
    try:
        jobs = crawler.run("software", max_pages=2 if not quick else 1)
        logger.info("  Cyberport: %d jobs", len(jobs))
        return jobs
    except Exception as e:
        logger.warning("  Cyberport: %s", e)
        return []


def _try_hkstp(proxy: str, quick: bool = False):
    from src.crawlers.hkstp import HKSTPCrawler
    crawler = HKSTPCrawler(headless=True, proxy_server=proxy)
    try:
        jobs = crawler.run("software", max_pages=2 if not quick else 1)
        logger.info("  HKSTP: %d jobs", len(jobs))
        return jobs
    except Exception as e:
        logger.warning("  HKSTP: %s", e)
        return []


def _try_jijis(proxy: str, quick: bool = False):
    from src.crawlers.jijis import JIJISCrawler
    crawler = JIJISCrawler(proxy_server=proxy)
    try:
        jobs = crawler.run("software", max_pages=2 if not quick else 1)
        logger.info("  JIJIS: %d jobs", len(jobs))
        return jobs
    except Exception as e:
        logger.warning("  JIJIS: %s", e)
        return []


def _try_offertoday(proxy: str, quick: bool = False):
    from src.crawlers.offertoday import OfferTodayCrawler
    crawler = OfferTodayCrawler(proxy_server=proxy)
    try:
        jobs = crawler.run("software", max_pages=2 if not quick else 1)
        logger.info("  OfferToday: %d jobs", len(jobs))
        return jobs
    except Exception as e:
        logger.warning("  OfferToday: %s", e)
        return []


def crawl_full(source_name: str, proxy: str):
    """在快速测试成功后，用更多关键词全量抓取"""
    logger.info("=== Full crawl: %s ===", source_name)

    if source_name == "Indeed":
        from src.crawlers.indeed import IndeedCrawler
        crawler = IndeedCrawler(headless=True, proxy_server=proxy)
    elif source_name == "Cyberport":
        from src.crawlers.cyberport import CyberportCrawler
        crawler = CyberportCrawler(headless=True, proxy_server=proxy)
    elif source_name == "HKSTP":
        from src.crawlers.hkstp import HKSTPCrawler
        crawler = HKSTPCrawler(headless=True, proxy_server=proxy)
    elif source_name == "JIJIS":
        from src.crawlers.jijis import JIJISCrawler
        crawler = JIJISCrawler(proxy_server=proxy)
    elif source_name == "OfferToday":
        from src.crawlers.offertoday import OfferTodayCrawler
        crawler = OfferTodayCrawler(proxy_server=proxy)
    else:
        return []

    all_jobs = []
    for kw in KEYWORDS:
        try:
            jobs = crawler.run(kw, max_pages=MAX_PAGES)
            logger.info("  '%s': %d jobs", kw, len(jobs))
            all_jobs.extend(jobs)
            time.sleep(1)
        except Exception as e:
            logger.warning("  '%s': %s", kw, e)
    return all_jobs


def deduplicate(jobs: list[dict]) -> list[dict]:
    seen = set()
    unique = []
    for j in jobs:
        key = (j.get("job_id"), j.get("source"))
        if key in seen:
            continue
        seen.add(key)
        unique.append(j)
    return unique


def main():
    logger.info("Proxy: %s", PROXY)

    results = try_first(PROXY)
    working = {k: v for k, v in results.items() if v}
    logger.info("Working sources: %s", list(working.keys()))

    all_jobs = []
    for name, quick_jobs in working.items():
        if quick_jobs:
            logger.info("%s quick test: %d jobs, launching full crawl...", name, len(quick_jobs))
            full_jobs = crawl_full(name, PROXY)
            all_jobs.extend(full_jobs)
            time.sleep(2)
        else:
            logger.info("%s: no jobs in quick test, skipping", name)

    all_jobs = deduplicate(all_jobs)
    logger.info("Total unique jobs: %d", len(all_jobs))

    if not all_jobs:
        logger.error("No data collected from any source. Check proxy connectivity.")
        return

    raw_path = RAW_DIR / "all_sources.json"
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(all_jobs, f, ensure_ascii=False, indent=2)
    logger.info("Saved raw data to %s", raw_path)

    logger.info("=== Cleaning & Analysis ===")
    pipeline = CleaningPipeline()
    extractor = RuleBasedSkillExtractor()
    cleaned = pipeline.clean_batch(all_jobs)
    analyzed = extractor.analyze_batch(cleaned)

    exporter = CSVExporter(output_dir=str(CLEAN_DIR))
    csv_path = exporter.export(analyzed, "jobs.csv")
    logger.info("Exported %d jobs to %s", len(analyzed), csv_path)

    import pandas as pd
    df = pd.DataFrame(analyzed)
    if "source" in df.columns:
        logger.info("Source distribution:\n%s", df["source"].value_counts().to_string())
    if "salary_min" in df.columns:
        logger.info("Salary: %.0f - %.0f HKD", df["salary_min"].min(), df["salary_max"].max())
    if "location" in df.columns:
        logger.info("Unique locations: %d", df["location"].nunique())
    logger.info("DONE! Run: uvicorn api.main:app --reload")


if __name__ == "__main__":
    main()
