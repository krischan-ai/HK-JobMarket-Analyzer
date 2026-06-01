from __future__ import annotations

from typing import Any, Optional

from pymongo import ASCENDING, TEXT, IndexModel

from config.settings import settings
from src.logger import get_logger


class JobDatabase:
    """岗位数据 MongoDB 持久化管理器"""

    def __init__(self, uri: str = None, db_name: str = None):
        self.uri = uri or settings.mongodb_uri
        self.db_name = db_name or settings.mongodb_db_name
        self.logger = get_logger(self.__class__.__name__)
        self._client = None
        self._db = None
        self._collection = None
        self._connect()

    def _connect(self):
        try:
            from pymongo import MongoClient
            self._client = MongoClient(self.uri, serverSelectionTimeoutMS=5000)
            self._db = self._client[self.db_name]
            self._collection = self._db["job_postings"]
            self._ensure_indexes()
            self._client.admin.command("ping")
            self.logger.info("Connected to MongoDB: %s/%s", self.uri, self.db_name)
        except Exception as e:
            self.logger.warning("Failed to connect to MongoDB: %s. Running in CSV-only mode.", e)
            self._client = None

    def _ensure_indexes(self):
        if self._collection is None:
            return
        indexes = [
            IndexModel([("job_id", ASCENDING), ("source", ASCENDING)], unique=True, sparse=True),
            IndexModel([("source", ASCENDING), ("crawled_at", -1)]),
            IndexModel([("location", ASCENDING), ("salary_min", ASCENDING)]),
            IndexModel([("jd_text", TEXT), ("title", TEXT)]),
        ]
        try:
            existing = self._collection.index_information()
            existing_keys = {info["key"][0][0] for info in existing.values() if isinstance(info, dict) and "key" in info}
            for idx in indexes:
                key_name = idx.document["key"][0][0]
                if key_name not in existing_keys:
                    self._collection.create_indexes([idx])
                    self.logger.info("Created index on %s", key_name)
        except Exception as e:
            self.logger.warning("Index creation warning: %s", e)

    @property
    def is_connected(self) -> bool:
        return self._client is not None

    def insert_job(self, job: dict) -> Optional[str]:
        if not self.is_connected:
            return None
        try:
            result = self._collection.update_one(
                {"job_id": job.get("job_id", ""), "source": job.get("source", "")},
                {"$set": job},
                upsert=True,
            )
            return str(result.upserted_id) if result.upserted_id else None
        except Exception as e:
            self.logger.error("Insert failed for %s: %s", job.get("job_id"), e)
            return None

    def bulk_insert(self, jobs: list[dict]) -> int:
        if not self.is_connected:
            return 0
        count = 0
        for job in jobs:
            result = self.insert_job(job)
            if result is not None:
                count += 1
        return count

    def find_all(self, query: dict = None, limit: int = 0) -> list[dict]:
        if not self.is_connected:
            return []
        cursor = self._collection.find(query or {}, {"_id": 0}).limit(limit)
        return list(cursor)

    def search_text(self, keyword: str, limit: int = 50) -> list[dict]:
        if not self.is_connected:
            return []
        cursor = self._collection.find(
            {"$text": {"$search": keyword}},
            {"_id": 0, "score": {"$meta": "textScore"}},
        ).sort([("score", {"$meta": "textScore"})]).limit(limit)
        return list(cursor)

    def aggregate(self, pipeline: list[dict]) -> list[dict]:
        if not self.is_connected:
            return []
        return list(self._collection.aggregate(pipeline))

    def count(self, query: dict = None) -> int:
        if not self.is_connected:
            return 0
        return self._collection.count_documents(query or {})

    def delete_many(self, query: dict) -> int:
        if not self.is_connected:
            return 0
        result = self._collection.delete_many(query)
        return result.deleted_count

    def close(self):
        if self._client:
            self._client.close()
            self.logger.info("MongoDB connection closed")
