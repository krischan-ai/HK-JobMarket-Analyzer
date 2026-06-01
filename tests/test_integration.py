"""端到端集成测试：清洗 → 分析 → 可视化 → 导出"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.cleaner.pipeline import CleaningPipeline
from src.analyzer.rule_engine import RuleBasedSkillExtractor
from src.storage.csv_exporter import CSVExporter
from src.utils import ensure_dir


class TestPipeline:
    def test_full_pipeline(self, mock_jobs, temp_dir):
        # Step 1: Clean
        pipeline = CleaningPipeline()
        cleaned = pipeline.clean_batch(mock_jobs)
        assert len(cleaned) == len(mock_jobs)
        for job in cleaned:
            assert "jd_text" in job
            assert "salary_min" in job

        # Step 2: Analyze
        extractor = RuleBasedSkillExtractor()
        analyzed = extractor.analyze_batch(cleaned)
        for job in analyzed:
            assert "skills" in job

        # Step 3: Convert to DataFrame
        df = pd.DataFrame(analyzed)
        assert len(df) == len(mock_jobs)

        # Step 4: Export CSV
        output_dir = ensure_dir(temp_dir / "output")
        exporter = CSVExporter(output_dir=str(output_dir))
        csv_path = exporter.export(analyzed, filename="test_jobs.csv")
        assert csv_path.exists()

        # Step 5: Verify CSV content
        loaded = pd.read_csv(csv_path)
        assert len(loaded) == len(mock_jobs)

    def test_pipeline_with_empty_data(self, temp_dir):
        pipeline = CleaningPipeline()
        extractor = RuleBasedSkillExtractor()

        cleaned = pipeline.clean_batch([])
        assert cleaned == []

        analyzed = extractor.analyze_batch([])
        assert analyzed == []

    def test_salary_parsing_in_pipeline(self, mock_jobs):
        pipeline = CleaningPipeline()
        cleaned = pipeline.clean_batch(mock_jobs)
        salary_checks = [
            ("MOCK_001", 45000.0, 60000.0),
            ("MOCK_002", 50000.0, 60000.0),
            ("MOCK_003", 50000.0, 80000.0),
        ]
        for jid, exp_min, exp_max in salary_checks:
            job = next(j for j in cleaned if j["job_id"] == jid)
            assert job["salary_min"] == exp_min
            assert job["salary_max"] == exp_max

    def test_skill_extraction_in_pipeline(self, mock_jobs):
        pipeline = CleaningPipeline()
        extractor = RuleBasedSkillExtractor()
        cleaned = pipeline.clean_batch(mock_jobs)
        analyzed = extractor.analyze_batch(cleaned)

        skill_checks = [
            ("MOCK_001", "Python", "programming_languages"),
            ("MOCK_002", "React", "frameworks_libraries"),
            ("MOCK_004", "Aws", "cloud_devops"),
        ]
        for jid, skill, category in skill_checks:
            job = next(j for j in analyzed if j["job_id"] == jid)
            skills_in_cat = [s.lower() for s in job["skills"].get(category, [])]
            assert skill.lower() in skills_in_cat
