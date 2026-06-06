from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from src.logger import get_logger

_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "cron_jobs.json"

_DEFAULT_JOBS: list[dict] = []


class SchedulerConfig:
    """Cron 任務配置持久化管理"""

    def __init__(self, config_path: Optional[Path] = None):
        self.path = config_path or _CONFIG_PATH
        self.logger = get_logger(self.__class__.__name__)
        self._ensure_file()

    def _ensure_file(self):
        if not self.path.exists():
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(_DEFAULT_JOBS, f, indent=2)

    def load_all(self) -> list[dict]:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return _DEFAULT_JOBS

    def add_job(self, job: dict) -> list[dict]:
        jobs = self.load_all()
        jobs.append(job)
        self._save(jobs)
        return jobs

    def update_job(self, job_id: str, updates: dict) -> Optional[dict]:
        jobs = self.load_all()
        for j in jobs:
            if j.get("id") == job_id:
                j.update(updates)
                self._save(jobs)
                return j
        return None

    def delete_job(self, job_id: str) -> bool:
        jobs = self.load_all()
        new_jobs = [j for j in jobs if j.get("id") != job_id]
        if len(new_jobs) == len(jobs):
            return False
        self._save(new_jobs)
        return True

    def _save(self, jobs: list[dict]):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(jobs, f, indent=2, ensure_ascii=False)
