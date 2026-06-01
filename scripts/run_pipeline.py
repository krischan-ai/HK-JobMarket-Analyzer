#!/usr/bin/env python3
"""一键运行端到端数据流水线：采集 → 清洗 → 分析 → 可视化"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.crawlers import get_crawler
from src.cleaner import CleaningPipeline
from src.storage import CSVExporter
from src.analyzer import RuleBasedSkillExtractor
from src.visualization import TechTrendAnalyzer
from src.logger import setup_logger, get_logger
from src.utils import ensure_dir, json_dump


def parse_args():
    parser = argparse.ArgumentParser(description="HK-JobMarket-Analyzer 端到端数据流水线")
    parser.add_argument("--keywords", type=str, default="software engineer,data scientist,frontend,backend,devops",
                        help="搜索关键词，逗号分隔")
    parser.add_argument("--pages", type=int, default=5,
                        help="每个关键词爬取页数")
    parser.add_argument("--output", type=str, default="data/cleaned",
                        help="输出目录")
    parser.add_argument("--skip-crawl", action="store_true",
                        help="跳过爬取阶段（使用已有数据）")
    parser.add_argument("--chart-only", action="store_true",
                        help="仅生成图表（不运行流水线）")
    return parser.parse_args()


def main():
    args = parse_args()
    setup_logger(level="INFO")
    logger = get_logger("pipeline")

    keywords = [kw.strip() for kw in args.keywords.split(",")]
    output_dir = ensure_dir(args.output)

    all_jobs = []

    if not args.skip_crawl:
        logger.info("=== Phase 1: Crawling ===")
        crawler = get_crawler("jobsdb")
        for kw in keywords:
            logger.info("Crawling keyword: %s", kw)
            jobs = crawler.run(kw, max_pages=args.pages)
            all_jobs.extend(jobs)
            logger.info("Collected %d jobs for keyword=%s", len(jobs), kw)

        logger.info("Total jobs collected: %d", len(all_jobs))
    else:
        logger.info("Skipping crawl phase")

    if all_jobs:
        logger.info("=== Phase 2: Cleaning ===")
        cleaner = CleaningPipeline()
        all_jobs = cleaner.clean_batch(all_jobs)
        logger.info("Cleaned %d jobs", len(all_jobs))

        logger.info("=== Phase 3: Analysis ===")
        extractor = RuleBasedSkillExtractor()
        all_jobs = extractor.analyze_batch(all_jobs)
        logger.info("Analyzed %d jobs", len(all_jobs))

        logger.info("=== Phase 4: Export ===")
        exporter = CSVExporter(output_dir)
        csv_path = exporter.export(all_jobs, filename="jobs.csv")
        json_dump(all_jobs, output_dir / "jobs.json")

        logger.info("=== Phase 5: Visualization ===")
        import pandas as pd
        df = pd.DataFrame(all_jobs)
        analyzer = TechTrendAnalyzer(df, output_dir=output_dir.parent / "charts")
        charts = analyzer.generate_all_charts()

        logger.info("Pipeline completed successfully!")
        logger.info("Data: %s", csv_path)
        for name, path in charts.items():
            if path:
                logger.info("Chart: %s -> %s", name, path)
    else:
        logger.warning("No jobs to process")


if __name__ == "__main__":
    main()
