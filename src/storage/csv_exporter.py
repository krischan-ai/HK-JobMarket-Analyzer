from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd

from src.logger import get_logger
from src.utils import ensure_dir


class CSVExporter:
    """将岗位数据导出为 CSV"""

    def __init__(self, output_dir: str | Path = "data/cleaned"):
        self.output_dir = ensure_dir(output_dir)
        self.logger = get_logger(self.__class__.__name__)

    def export(self, jobs: list[dict], filename: str = "jobs.csv") -> Path:
        if not jobs:
            self.logger.warning("No jobs to export")
            return self.output_dir / filename

        df = pd.DataFrame(jobs)
        output_path = self.output_dir / filename
        df.to_csv(output_path, index=False, encoding="utf-8-sig")
        self.logger.info("Exported %d jobs to %s", len(jobs), output_path)
        return output_path

    def export_from_mongodb(self, db, filename: str = "jobs.csv", query: dict = None) -> Optional[Path]:
        if not db.is_connected:
            self.logger.warning("MongoDB not connected, skipping export")
            return None
        jobs = db.find_all(query)
        return self.export(jobs, filename)
