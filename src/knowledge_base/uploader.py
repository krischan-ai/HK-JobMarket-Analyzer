from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from src.cleaner.pipeline import CleaningPipeline
from src.analyzer.rule_engine import RuleBasedSkillExtractor
from src.i18n.translator import get_translator
from src.logger import get_logger
from src.storage.mongodb import JobDatabase
from src.storage.csv_exporter import CSVExporter
from src.knowledge_base.validator import Validator, detect_mapping


@dataclass
class ProcessResult:
    total: int = 0
    success: int = 0
    skipped: int = 0
    new_records: int = 0
    updated_records: int = 0
    errors: list[str] = field(default_factory=list)
    duration_ms: float = 0.0


class Uploader:
    """用户上传数据处理管道"""

    SUPPORTED_EXTENSIONS = {".csv", ".json", ".xlsx"}

    def __init__(self, file_path: str, source_tag: str = "user_upload",
                 detect_duplicates: bool = True, run_cleaning: bool = True,
                 run_extraction: bool = True):
        self.file_path = Path(file_path)
        self.source_tag = source_tag
        self.detect_duplicates = detect_duplicates
        self.run_cleaning = run_cleaning
        self.run_extraction = run_extraction
        self.logger = get_logger(self.__class__.__name__)
        self.validator = Validator()
        self.cleaner = CleaningPipeline()
        self.extractor = RuleBasedSkillExtractor()
        self.translator = get_translator()

    def validate_format(self) -> bool:
        ext = self.file_path.suffix.lower()
        if ext not in self.SUPPORTED_EXTENSIONS:
            self.logger.error("不支持的文件格式: %s", ext)
            return False
        if not self.validator.validate_file_size(str(self.file_path)):
            return False
        return True

    def read_file(self) -> list[dict]:
        ext = self.file_path.suffix.lower()
        if ext == ".csv":
            df = pd.read_csv(self.file_path, encoding="utf-8-sig")
        elif ext == ".json":
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
            return data
        elif ext == ".xlsx":
            df = pd.read_excel(self.file_path)
        else:
            raise ValueError(f"Unsupported format: {ext}")
        return df.to_dict(orient="records")

    def apply_mapping(self, records: list[dict]) -> list[dict]:
        if not records:
            return records
        sample_keys = list(records[0].keys())
        mapping = detect_mapping(sample_keys)
        mapped_records = []
        for r in records:
            mapped = {}
            for original_col, standard_col in mapping.items():
                key = standard_col or original_col
                mapped[key] = r.get(original_col)
            mapped["source"] = self.source_tag
            mapped["crawled_at"] = datetime.now().isoformat()
            mapped_records.append(mapped)
        return mapped_records

    def process(self) -> ProcessResult:
        start = time.time()
        result = ProcessResult()

        if not self.validate_format():
            result.errors.append("文件格式校验失败")
            return result

        try:
            raw_records = self.read_file()
        except Exception as e:
            result.errors.append(f"文件读取失败: {e}")
            return result

        result.total = len(raw_records)
        if not self.validator.validate_row_count(raw_records):
            result.errors.append("记录数超出限制")
            return result

        records = self.apply_mapping(raw_records)
        records = self.validator.validate_records(records, raise_on_missing_jd=True)
        result.skipped = result.total - len(records)

        if self.run_cleaning:
            for r in records:
                cleaned = self.cleaner.clean_job(r)
                r.update(cleaned)

        if self.run_extraction:
            for r in records:
                skills = self.extractor.extract(r.get("jd_raw", ""))
                r["skills"] = skills

        if "location" in {k for r in records for k in r.keys()}:
            df = pd.DataFrame(records)
            df = self.translator.translate_df(df)
            records = df.to_dict(orient="records")

        db = JobDatabase()
        if db.is_connected:
            for r in records:
                oid = db.insert_job(r)
                if oid is not None:
                    result.new_records += 1
                else:
                    result.updated_records += 1
            result.success = result.new_records + result.updated_records

        csv_dir = Path("data") / "cleaned"
        csv_dir.mkdir(parents=True, exist_ok=True)
        csv_path = csv_dir / "jobs.csv"
        exporter = CSVExporter(str(csv_path))
        existing = pd.read_csv(csv_path) if csv_path.exists() else pd.DataFrame()
        new_df = pd.DataFrame(records)
        merged = pd.concat([existing, new_df], ignore_index=True)
        merged.to_csv(csv_path, index=False, encoding="utf-8-sig")
        self.logger.info("已追加写入 CSV: %s (共 %d 条)", csv_path, len(merged))

        result.duration_ms = round((time.time() - start) * 1000, 1)
        return result
