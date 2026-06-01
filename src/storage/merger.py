from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

from src.logger import get_logger
from src.storage.mongodb import JobDatabase
from src.storage.csv_exporter import CSVExporter


class MultiSourceMerger:
    """多源数据合并去重器

    职责：
    1. 合并来自不同爬虫源的数据
    2. 按 job_id + source 去重
    3. 统一字段格式
    4. 写入 MongoDB + CSV 快照
    """

    def __init__(self, output_csv: str = "data/cleaned/jobs.csv"):
        self.logger = get_logger(self.__class__.__name__)
        self.db = JobDatabase()
        self.output_csv = output_csv
        self.exporter = CSVExporter(output_dir=str(Path(output_csv).parent))

    def merge(self, new_jobs: list[dict], dedup: bool = True) -> dict:
        start_count = len(new_jobs)

        if dedup:
            new_jobs = self._deduplicate(new_jobs)

        for job in new_jobs:
            job["merged_at"] = datetime.now().isoformat()

        csv_count = self._append_csv(new_jobs)

        db_count = 0
        if self.db.is_connected:
            db_count = self.db.bulk_insert(new_jobs)

        self.logger.info(
            "Merge complete: received=%d, after_dedup=%d, csv=%d, db=%d",
            start_count, len(new_jobs), csv_count, db_count,
        )

        return {
            "received": start_count,
            "deduped": start_count - len(new_jobs),
            "csv_added": csv_count,
            "db_added": db_count,
            "total": len(new_jobs),
        }

    def _deduplicate(self, jobs: list[dict]) -> list[dict]:
        seen = set()
        unique = []
        for job in jobs:
            key = (job.get("job_id", ""), job.get("source", ""))
            if key not in seen:
                seen.add(key)
                unique.append(job)
        return unique

    def _append_csv(self, jobs: list[dict]) -> int:
        import os
        new_df = pd.DataFrame(jobs)
        csv_path = self.output_csv

        if os.path.exists(csv_path):
            existing = pd.read_csv(csv_path, encoding="utf-8-sig")
            combined = pd.concat([existing, new_df], ignore_index=True)
            combined = combined.drop_duplicates(subset=["job_id", "source"], keep="last")
            combined.to_csv(csv_path, index=False, encoding="utf-8-sig")
        else:
            new_df.to_csv(csv_path, index=False, encoding="utf-8-sig")

        return len(new_df)

    def merge_all(self, sources: dict[str, list[dict]]) -> dict:
        """合并多个来源的数据字典

        Args:
            sources: {"jobsdb": [...], "jijis": [...], ...}
        """
        all_jobs = []
        source_stats = {}
        for source, jobs in sources.items():
            source_stats[source] = len(jobs)
            all_jobs.extend(jobs)

        self.logger.info("Merging %d sources: %s", len(sources), source_stats)
        return self.merge(all_jobs, dedup=True)

    def get_source_stats(self) -> pd.DataFrame:
        """从 CSV 或 MongoDB 获取各来源数据量统计"""
        import os
        csv_path = self.output_csv
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
            if "source" in df.columns:
                return df["source"].value_counts().reset_index()
        return pd.DataFrame()
