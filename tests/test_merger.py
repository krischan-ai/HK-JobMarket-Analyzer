from __future__ import annotations

import pytest

from src.storage.merger import MultiSourceMerger


class TestMultiSourceMerger:
    def test_deduplicate(self):
        merger = MultiSourceMerger()
        jobs = [
            {"job_id": "1", "source": "a"},
            {"job_id": "1", "source": "a"},
            {"job_id": "2", "source": "a"},
            {"job_id": "1", "source": "b"},
        ]
        result = merger._deduplicate(jobs)
        assert len(result) == 3

    def test_deduplicate_empty(self):
        merger = MultiSourceMerger()
        assert merger._deduplicate([]) == []

    def test_deduplicate_no_dupes(self):
        merger = MultiSourceMerger()
        jobs = [{"job_id": "1", "source": "a"}, {"job_id": "2", "source": "b"}]
        result = merger._deduplicate(jobs)
        assert len(result) == 2

    def test_merge_all_produces_stats(self, temp_dir):
        csv_path = str(temp_dir / "test_jobs.csv")
        merger = MultiSourceMerger(output_csv=csv_path)
        sources = {
            "jobsdb": [{"job_id": "1", "source": "jobsdb", "title": "Dev"}],
            "jijis": [{"job_id": "2", "source": "jijis", "title": "Engineer"}],
        }
        stats = merger.merge_all(sources)
        assert stats["received"] == 2
        assert stats["csv_added"] == 2
        assert stats["deduped"] == 0

    def test_csv_roundtrip(self, temp_dir):
        csv_path = str(temp_dir / "test_jobs.csv")
        merger = MultiSourceMerger(output_csv=csv_path)
        merger.merge([{"job_id": "1", "source": "a", "title": "Dev"}])
        import os
        assert os.path.exists(csv_path)
        import pandas as pd
        df = pd.read_csv(csv_path)
        assert len(df) == 1

    def test_get_source_stats_empty(self, temp_dir):
        csv_path = str(temp_dir / "empty_jobs.csv")
        merger = MultiSourceMerger(output_csv=csv_path)
        df = merger.get_source_stats()
        assert len(df) == 0
