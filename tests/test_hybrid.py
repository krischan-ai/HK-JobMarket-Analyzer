from __future__ import annotations

import pytest

from src.analyzer.hybrid import HybridExtractor


@pytest.fixture(scope="module")
def hybrid():
    return HybridExtractor()


class TestHybridExtractor:
    def test_fallback_to_rule_when_llm_unconfigured(self, hybrid):
        result = hybrid.extract("Python expert with Django and AWS")
        assert result.get("engine") in ("rule", "rule_only")
        assert "Python" in result.get("programming_languages", [])

    def test_is_sufficient(self, hybrid):
        assert hybrid._is_sufficient({"a": ["x", "y", "z"], "b": []})
        assert not hybrid._is_sufficient({"a": [], "b": []})

    def test_llm_configured_property(self, hybrid):
        assert isinstance(hybrid.llm_configured, bool)

    def test_merge_results(self, hybrid):
        rule = {"programming_languages": ["Python"], "frameworks_libraries": [], "cloud_devops": [], "databases": [], "soft_skills": []}
        llm = {"programming_languages": ["Python", "Java"], "frameworks_libraries": [], "cloud_devops": [], "databases": [], "soft_skills": []}
        merged = hybrid._merge_results(rule, llm)
        assert "Python" in merged["programming_languages"]
        assert "Java" in merged["programming_languages"]

    def test_find_new_terms(self, hybrid):
        rule = {"programming_languages": ["Python"], "frameworks_libraries": [], "cloud_devops": [], "databases": [], "soft_skills": []}
        llm = {"programming_languages": ["Python", "Java"], "frameworks_libraries": [], "cloud_devops": [], "databases": [], "soft_skills": []}
        new = hybrid.find_new_terms(rule, llm)
        assert "java" in new.get("programming_languages", [])

    def test_extract_batch(self, hybrid, mock_jobs):
        result = hybrid.extract_batch(mock_jobs)
        assert len(result) == len(mock_jobs)
        for job in result:
            assert "skills" in job
            assert "extract_engine" in job
