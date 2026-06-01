from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from src.logger import get_logger


class Validator:
    """上传字段校验器"""

    MAX_ROWS = 10_000
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)

    def validate_file_size(self, file_path: str) -> bool:
        size = Path(file_path).stat().st_size
        if size > self.MAX_FILE_SIZE:
            self.logger.error("文件大小超出限制: %.1f MB > 50 MB", size / 1024 / 1024)
            return False
        return True

    def validate_row_count(self, records: list[dict]) -> bool:
        if len(records) > self.MAX_ROWS:
            self.logger.error("记录条数超出限制: %d > %d", len(records), self.MAX_ROWS)
            return False
        return True

    def validate_records(self, records: list[dict], raise_on_missing_jd: bool = True) -> list[dict]:
        valid = []
        for i, r in enumerate(records):
            jd = r.get("jd_raw")
            if not jd or not str(jd).strip():
                self.logger.warning("第 %d 条缺失 jd_raw，已跳过", i + 1)
                continue
            if raise_on_missing_jd:
                for field in ["title", "company", "location"]:
                    if not r.get(field):
                        self.logger.warning("第 %d 条推荐字段 '%s' 缺失", i + 1, field)
            valid.append(r)
        return valid


def detect_mapping(columns: list[str], mapping_path: str = None) -> dict:
    if mapping_path is None:
        mapping_path = str(Path(__file__).resolve().parent.parent.parent / "config" / "field_mapping.json")
    with open(mapping_path, "r", encoding="utf-8") as f:
        mappings = json.load(f)["user_field_mappings"]

    column_map = {}
    for col in columns:
        col_lower = col.strip().lower()
        matched = False
        for standard_field, aliases in mappings.items():
            if any(a.lower() == col_lower for a in aliases):
                column_map[col] = standard_field
                matched = True
                break
        if not matched:
            column_map[col] = None  # 未匹配的列
    return column_map
