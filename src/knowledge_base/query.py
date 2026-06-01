from __future__ import annotations

from datetime import datetime
from typing import Optional

import pandas as pd

from src.logger import get_logger
from src.storage.mongodb import JobDatabase


class KnowledgeBase:
    """知识库查询接口"""

    def __init__(self, db: Optional[JobDatabase] = None):
        self.db = db or JobDatabase()
        self.logger = get_logger(self.__class__.__name__)

    def search_by_keyword(self, keyword: str, limit: int = 50) -> list[dict]:
        return self.db.search_text(keyword, limit=limit)

    def filter_by_skills(self, skills: list[str], match_all: bool = False) -> list[dict]:
        if match_all:
            query = {"skills": {"$all": skills}}
        else:
            query = {"skills": {"$in": skills}}
        return self.db.find_all(query)

    def filter_by_salary(self, min_sal: Optional[float] = None, max_sal: Optional[float] = None) -> list[dict]:
        query = {}
        if min_sal is not None:
            query["salary_min"] = {"$gte": min_sal}
        if max_sal is not None:
            query.setdefault("salary_min", {})
            query["salary_min"]["$lte"] = max_sal
        return self.db.find_all(query)

    def filter_by_location(self, locations: list[str]) -> list[dict]:
        return self.db.find_all({"location": {"$in": locations}})

    def aggregate_skill_frequency(self, top_n: int = 20) -> pd.Series:
        records = self.db.find_all(limit=5000)
        if not records:
            return pd.Series(dtype=int)
        skill_counts = {}
        for r in records:
            skills = r.get("skills", {})
            if isinstance(skills, dict):
                for cat, skill_list in skills.items():
                    if isinstance(skill_list, list):
                        for s in skill_list:
                            skill_counts[s] = skill_counts.get(s, 0) + 1
        return pd.Series(skill_counts).sort_values(ascending=False).head(top_n)

    def aggregate_salary_stats(self, group_by: str = "location") -> pd.DataFrame:
        records = self.db.find_all(limit=5000)
        if not records:
            return pd.DataFrame()
        df = pd.DataFrame(records)
        if group_by not in df.columns:
            return pd.DataFrame()
        df = df.dropna(subset=["salary_min"])
        return df.groupby(group_by)["salary_min"].agg(["mean", "min", "max", "count"]).round(0).reset_index()

    def get_version_history(self) -> list[dict]:
        records = self.db.find_all(query={"crawled_at": {"$exists": True}}, limit=5000)
        if not records:
            return []
        df = pd.DataFrame(records)
        df["date"] = pd.to_datetime(df["crawled_at"]).dt.date
        history = df.groupby("date").agg(
            record_count=("job_id", "count"),
            sources=("source", lambda x: list(x.unique())),
        ).reset_index().sort_values("date", ascending=False)
        return history.to_dict(orient="records")
