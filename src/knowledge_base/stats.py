from __future__ import annotations

from typing import Optional

import pandas as pd

from src.storage.mongodb import JobDatabase


class StatsAggregator:
    """知识库统计聚合"""

    def __init__(self, db: Optional[JobDatabase] = None):
        self.db = db or JobDatabase()

    def total_records(self) -> int:
        return self.db.count()

    def source_distribution(self) -> pd.DataFrame:
        pipeline = [{"$group": {"_id": "$source", "count": {"$sum": 1}}}, {"$sort": {"count": -1}}]
        results = self.db.aggregate(pipeline)
        return pd.DataFrame(results).rename(columns={"_id": "source"}) if results else pd.DataFrame()

    def location_distribution(self) -> pd.DataFrame:
        pipeline = [{"$group": {"_id": "$location", "count": {"$sum": 1}}}, {"$sort": {"count": -1}}]
        results = self.db.aggregate(pipeline)
        return pd.DataFrame(results).rename(columns={"_id": "location"}) if results else pd.DataFrame()

    def salary_range(self) -> dict:
        pipeline = [
            {"$match": {"salary_min": {"$exists": True}}},
            {"$group": {"_id": None, "min": {"$min": "$salary_min"}, "max": {"$max": "$salary_min"}, "avg": {"$avg": "$salary_min"}}},
        ]
        results = self.db.aggregate(pipeline)
        if results:
            r = results[0]
            return {"min": r.get("min"), "max": r.get("max"), "avg": round(r.get("avg", 0), 0)}
        return {}

    def time_trend(self) -> pd.DataFrame:
        pipeline = [
            {"$match": {"crawled_at": {"$exists": True}}},
            {"$group": {"_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$crawled_at"}}, "count": {"$sum": 1}}},
            {"$sort": {"_id": 1}},
        ]
        results = self.db.aggregate(pipeline)
        return pd.DataFrame(results).rename(columns={"_id": "date"}) if results else pd.DataFrame()
