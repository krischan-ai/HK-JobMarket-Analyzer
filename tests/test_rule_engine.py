from __future__ import annotations

import pytest

from src.analyzer.rule_engine import RuleBasedSkillExtractor


@pytest.fixture(scope="module")
def extractor():
    return RuleBasedSkillExtractor()


class TestRuleBasedSkillExtractor:
    def test_extract_python(self, extractor):
        result = extractor.extract("Python expert needed")
        assert "Python" in result.get("programming_languages", [])

    def test_extract_multiple(self, extractor):
        result = extractor.extract("Python expert with Django and AWS")
        assert "Python" in result.get("programming_languages", [])
        assert "Django" in result.get("frameworks_libraries", [])
        assert "Aws" in result.get("cloud_devops", [])

    def test_extract_soft_skills(self, extractor):
        result = extractor.extract("Strong communication and teamwork")
        assert "Communication" in result.get("soft_skills", [])

    def test_extract_empty(self, extractor):
        result = extractor.extract("")
        assert all(v == () for v in result.values())

    def test_extract_none(self, extractor):
        result = extractor.extract(None)
        assert all(v == () for v in result.values())

    def test_extract_flat(self, extractor):
        result = extractor.extract_flat("Python expert with Django and PostgreSQL")
        assert "Python" in result
        assert "Django" in result

    def test_analyze_batch(self, extractor, mock_jobs):
        from src.cleaner.pipeline import CleaningPipeline
        pipeline = CleaningPipeline()
        cleaned = pipeline.clean_batch(mock_jobs)
        result = extractor.analyze_batch(cleaned)
        assert len(result) == len(mock_jobs)
        for job in result:
            assert "skills" in job

    @pytest.mark.parametrize("text,category,expected", [
        ("Experience with Python", "programming_languages", "Python"),
        ("Expert in React", "frameworks_libraries", "React"),
        ("AWS Certified", "cloud_devops", "Aws"),
        ("PostgreSQL experience", "databases", "Postgresql"),
    ])
    def test_individual_skills(self, extractor, text, category, expected):
        result = extractor.extract(text)
        assert any(expected.lower() == s.lower() for s in result.get(category, []))
