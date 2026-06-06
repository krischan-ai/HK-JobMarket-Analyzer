"""爬虫后处理管线：清洗 → 角色分类 → 知识库导入（MongoDB + CSV + 向量索引）"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Callable

from src.cleaner.pipeline import CleaningPipeline
from src.analyzer.role_classifier import RoleClassifier
from src.analyzer.rule_engine import RuleBasedSkillExtractor
from src.storage.mongodb import JobDatabase
from src.storage.csv_exporter import CSVExporter
from src.embeddings.vector_store import VectorStore
from src.logger import get_logger


@dataclass
class PostProcessConfig:
    """后处理管线配置"""
    run_cleaning: bool = True
    run_extraction: bool = True
    run_classification: bool = True
    run_kb_import: bool = True
    run_vector_index: bool = True
    fail_on_error: bool = False

    def to_dict(self) -> dict:
        return {
            "run_cleaning": self.run_cleaning,
            "run_extraction": self.run_extraction,
            "run_classification": self.run_classification,
            "run_kb_import": self.run_kb_import,
            "run_vector_index": self.run_vector_index,
            "fail_on_error": self.fail_on_error,
        }

    @classmethod
    def from_dict(cls, d: dict) -> PostProcessConfig:
        return cls(
            run_cleaning=d.get("run_cleaning", True),
            run_extraction=d.get("run_extraction", True),
            run_classification=d.get("run_classification", True),
            run_kb_import=d.get("run_kb_import", True),
            run_vector_index=d.get("run_vector_index", True),
            fail_on_error=d.get("fail_on_error", False),
        )


@dataclass
class PostProcessResult:
    """后处理结果统计"""
    cleaned_count: int = 0
    extracted_count: int = 0
    classified_count: int = 0
    db_inserted: int = 0
    vector_indexed: int = 0
    csv_exported: int = 0
    phase_timings: dict = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "cleaned_count": self.cleaned_count,
            "extracted_count": self.extracted_count,
            "classified_count": self.classified_count,
            "db_inserted": self.db_inserted,
            "vector_indexed": self.vector_indexed,
            "csv_exported": self.csv_exported,
            "phase_timings": self.phase_timings,
            "errors": self.errors,
        }


# 进度回调类型：(phase_name, phase_progress_pct)
ProgressCallback = Callable[[str, float], None]


class PostCrawlPipeline:
    """爬虫后处理管线编排器

    在爬虫任务完成后自动串联：清洗 → 技能提取 → 角色分类 → MongoDB/CSV/向量索引导入。
    支持分阶段进度回调与错误隔离。
    """

    # 各阶段权重（用于整体进度计算）
    _PHASE_WEIGHTS = {
        "cleaning": 0.15,
        "extraction": 0.10,
        "classification": 0.25,
        "kb_import": 0.35,
        "vector_index": 0.15,
    }

    def __init__(self, on_progress: Optional[ProgressCallback] = None):
        self.logger = get_logger(self.__class__.__name__)
        self.on_progress = on_progress
        self._cancelled = False

    def cancel(self):
        """请求取消管线"""
        self._cancelled = True

    def _report(self, phase: str, pct: float):
        if self.on_progress:
            try:
                self.on_progress(phase, pct)
            except Exception:
                pass

    def run(self, raw_jobs: list[dict], config: PostProcessConfig) -> PostProcessResult:
        """执行后处理管线

        Args:
            raw_jobs: 爬虫采集到的原始数据列表
            config: 后处理配置

        Returns:
            PostProcessResult 处理结果统计
        """
        result = PostProcessResult()
        if not raw_jobs:
            self.logger.warning("No jobs to post-process")
            return result

        jobs = list(raw_jobs)
        total = len(jobs)

        # ── Phase 1: 数据清洗 ──
        if self._cancelled:
            return result
        if config.run_cleaning:
            self.logger.info("Phase: Cleaning (%d jobs)", total)
            self._report("cleaning", 0)
            t0 = time.time()
            try:
                cleaner = CleaningPipeline()
                jobs = cleaner.clean_batch(jobs)
                result.cleaned_count = len(jobs)
            except Exception as e:
                msg = f"清洗阶段异常: {e}"
                self.logger.error(msg)
                result.errors.append(msg)
                if config.fail_on_error:
                    result.phase_timings["cleaning"] = round(time.time() - t0, 2)
                    return result
            result.phase_timings["cleaning"] = round(time.time() - t0, 2)
            self._report("cleaning", 100)
        else:
            result.cleaned_count = total

        # ── Phase 2: 技能提取 ──
        if self._cancelled:
            return result
        if config.run_extraction:
            self.logger.info("Phase: Skill extraction (%d jobs)", len(jobs))
            self._report("extraction", 0)
            t0 = time.time()
            try:
                extractor = RuleBasedSkillExtractor()
                jobs = extractor.analyze_batch(jobs)
                result.extracted_count = len(jobs)
            except Exception as e:
                msg = f"技能提取异常: {e}"
                self.logger.error(msg)
                result.errors.append(msg)
                if config.fail_on_error:
                    result.phase_timings["extraction"] = round(time.time() - t0, 2)
                    return result
            result.phase_timings["extraction"] = round(time.time() - t0, 2)
            self._report("extraction", 100)
        else:
            result.extracted_count = total

        # ── Phase 3: 角色分类 ──
        if self._cancelled:
            return result
        if config.run_classification:
            self.logger.info("Phase: Role classification (%d jobs)", len(jobs))
            self._report("classification", 0)
            t0 = time.time()
            try:
                classifier = RoleClassifier()
                classified = []
                for i, job in enumerate(jobs):
                    if self._cancelled:
                        break
                    jd_text = job.get("jd_text") or job.get("jd_raw", "")
                    if not isinstance(jd_text, str):
                        jd_text = str(jd_text) if jd_text else ""
                    role_result = classifier.classify(jd_text)
                    job["role_id"] = role_result.role_id
                    job["role_name"] = role_result.role_name
                    job["role_confidence"] = role_result.confidence
                    classified.append(job)
                    # 批量回调进度
                    if (i + 1) % 10 == 0 or i + 1 == len(jobs):
                        self._report("classification", round((i + 1) / len(jobs) * 100, 1))
                jobs = classified
                result.classified_count = len(jobs)
            except Exception as e:
                msg = f"角色分类异常: {e}"
                self.logger.error(msg)
                result.errors.append(msg)
                if config.fail_on_error:
                    result.phase_timings["classification"] = round(time.time() - t0, 2)
                    return result
            result.phase_timings["classification"] = round(time.time() - t0, 2)
            self._report("classification", 100)
        else:
            result.classified_count = total

        # ── Phase 4: 知识库导入 (MongoDB + CSV) ──
        if self._cancelled:
            return result
        if config.run_kb_import:
            self.logger.info("Phase: Knowledge base import (%d jobs)", len(jobs))
            self._report("kb_import", 0)
            t0 = time.time()
            try:
                # MongoDB
                db = JobDatabase()
                if db.is_connected:
                    result.db_inserted = db.bulk_insert(jobs)
                    self.logger.info("MongoDB inserted: %d", result.db_inserted)
                else:
                    self.logger.warning("MongoDB not available, skipping DB insert")

                # CSV 导出
                csv_dir = Path("data") / "cleaned"
                csv_dir.mkdir(parents=True, exist_ok=True)
                exporter = CSVExporter(str(csv_dir))

                import pandas as pd
                csv_path = csv_dir / "jobs.csv"
                if csv_path.exists():
                    try:
                        existing = pd.read_csv(csv_path, encoding="utf-8-sig")
                    except Exception:
                        existing = pd.DataFrame()
                else:
                    existing = pd.DataFrame()

                new_df = pd.DataFrame(jobs)
                merged = pd.concat([existing, new_df], ignore_index=True)
                merged.to_csv(csv_path, index=False, encoding="utf-8-sig")
                result.csv_exported = len(jobs)
                self.logger.info("CSV exported: %s (total %d rows)", csv_path, len(merged))
            except Exception as e:
                msg = f"知识库导入异常: {e}"
                self.logger.error(msg)
                result.errors.append(msg)
                if config.fail_on_error:
                    result.phase_timings["kb_import"] = round(time.time() - t0, 2)
                    return result
            result.phase_timings["kb_import"] = round(time.time() - t0, 2)
            self._report("kb_import", 100)

        # ── Phase 5: 向量索引更新 ──
        if self._cancelled:
            return result
        if config.run_vector_index:
            self.logger.info("Phase: Vector index update (%d jobs)", len(jobs))
            self._report("vector_index", 0)
            t0 = time.time()
            try:
                store = VectorStore()
                if store.available:
                    store.add_documents(jobs)
                    result.vector_indexed = store.count()
                    self.logger.info("Vector store updated: %d total docs", result.vector_indexed)
                else:
                    self.logger.warning("ChromaDB not available, skipping vector index")
            except Exception as e:
                msg = f"向量索引异常: {e}"
                self.logger.error(msg)
                result.errors.append(msg)
                if config.fail_on_error:
                    result.phase_timings["vector_index"] = round(time.time() - t0, 2)
                    return result
            result.phase_timings["vector_index"] = round(time.time() - t0, 2)
            self._report("vector_index", 100)

        self.logger.info(
            "Post-processing complete: cleaned=%d, classified=%d, db=%d, csv=%d, vector=%d, errors=%d",
            result.cleaned_count, result.classified_count,
            result.db_inserted, result.csv_exported, result.vector_indexed,
            len(result.errors),
        )
        return result
