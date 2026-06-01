from __future__ import annotations

import pytest

from src.analyzer.llm_engine import LLMExtractor
from src.analyzer.prompt import build_skill_extraction_messages


class TestPromptTemplates:
    def test_build_messages(self):
        messages = build_skill_extraction_messages("Test JD")
        assert len(messages) >= 4
        assert messages[0]["role"] == "system"
        assert messages[-1]["role"] == "user"
        assert messages[-1]["content"] == "Test JD"

    def test_system_prompt_content(self):
        messages = build_skill_extraction_messages("Test")
        system = messages[0]["content"]
        assert "programming_languages" in system
        assert "frameworks_libraries" in system
        assert "cloud_devops" in system
        assert "databases" in system
        assert "soft_skills" in system

    def test_few_shot_count(self):
        messages = build_skill_extraction_messages("Test")
        few_shot_pairs = sum(1 for m in messages[1:-1] if m["role"] == "assistant")
        user_messages = sum(1 for m in messages[1:-1] if m["role"] == "user")
        assert few_shot_pairs == user_messages
        assert few_shot_pairs >= 1


class TestLLMExtractor:
    def test_not_configured_by_default(self):
        extractor = LLMExtractor()
        assert not extractor.available

    def test_degrade_gracefully(self):
        extractor = LLMExtractor()
        result = extractor.extract("Python developer")
        expected_categories = [
            "programming_languages", "frameworks_libraries",
            "cloud_devops", "databases", "soft_skills",
        ]
        for cat in expected_categories:
            assert cat in result
            assert result[cat] == []

    def test_default_categories(self):
        cats = LLMExtractor._default_categories()
        assert len(cats) == 5
        assert "soft_skills" in cats

    def test_explicit_config_fallback(self):
        extractor = LLMExtractor(api_key="", api_base="")
        assert not extractor.available
        result = extractor.extract("test")
        assert all(v == [] for v in result.values())

    def test_batch_degrade(self):
        extractor = LLMExtractor()
        jobs = [{"jd_raw": "Python dev"}, {"jd_raw": "Java dev"}]
        result = extractor.extract_batch(jobs)
        assert len(result) == 2
        for job in result:
            assert "skills_llm" in job
