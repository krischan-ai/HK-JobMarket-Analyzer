from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.analyzer.role_classifier import RoleClassifier, RoleResult, CACHE_PATH
from src.analyzer.role_prompt import ROLE_DEFINITIONS, build_role_classify_messages


class TestRolePrompt:
    def test_build_messages_structure(self):
        messages = build_role_classify_messages("Python developer with Django")
        assert len(messages) >= 4
        assert messages[0]["role"] == "system"
        assert messages[-1]["role"] == "user"
        assert "Python developer with Django" in messages[-1]["content"]

    def test_role_definitions_count(self):
        assert len(ROLE_DEFINITIONS) == 14
        assert "frontend" in ROLE_DEFINITIONS
        assert "other" in ROLE_DEFINITIONS
        assert ROLE_DEFINITIONS["frontend"]["name"] == "前端开发"


class TestRoleClassifierRules:
    def setup_method(self):
        self.c = RoleClassifier(api_key="", api_base="")

    def test_classify_empty_text(self):
        result = self.c.classify("")
        assert result.role_id == "other"
        assert result.confidence == "low"

    def test_classify_none(self):
        result = self.c.classify(None)
        assert result.role_id == "other"
        assert result.confidence == "low"

    def test_classify_frontend_rule(self):
        result = self.c.classify("We need a React developer with Vue experience and CSS skills")
        assert result.role_id == "frontend"
        assert result.role_name == "前端开发"

    def test_classify_backend_rule(self):
        result = self.c.classify("Looking for Django developer with REST API skills and database design")
        assert result.role_id == "backend"
        assert result.role_name == "后端开发"

    def test_classify_devops_rule(self):
        result = self.c.classify("DevOps engineer needed: Docker, Kubernetes, CI/CD, Terraform")
        assert result.role_id == "devops"
        assert result.role_name == "DevOps/SRE"

    def test_classify_data_science_rule(self):
        result = self.c.classify("Data scientist with machine learning, TensorFlow, NLP experience")
        assert result.role_id == "data_science"
        assert result.role_name == "数据科学"

    def test_classify_ai_engineer_rule(self):
        result = self.c.classify("AI engineer: LLM, LangChain, RAG, prompt engineering")
        assert result.role_id == "ai_engineer"
        assert result.role_name == "AI 工程师"

    def test_classify_no_match_returns_other(self):
        result = self.c.classify("Good communication skills and team player")
        assert result.role_id == "other"
        assert result.role_name == "其他"
        assert result.confidence in ("low", "medium")

    def test_classify_batch(self):
        jobs = [
            {"jd_raw": "React developer with CSS experience"},
            {"jd_raw": "Django backend engineer with PostgreSQL"},
            {"jd_raw": "Machine learning data scientist with Python"},
        ]
        results = self.c.classify_batch(jobs)
        assert len(results) == 3
        assert results[0]["role_id"] == "frontend"
        assert results[1]["role_id"] == "backend"
        assert results[2]["role_id"] == "data_science"

    def test_cache_persistence(self):
        self.c.classify("React frontend developer")
        assert len(self.c._cache) > 0
        assert CACHE_PATH.exists()

    def test_clear_cache(self):
        self.c.classify("React frontend developer")
        self.c.clear_cache()
        assert len(self.c._cache) == 0

    def test_get_statistics(self):
        self.c.clear_cache()
        self.c.classify("React developer")
        self.c.classify("Django developer")
        self.c.classify("React developer 2")
        stats = self.c.get_statistics()
        assert stats["total_classified"] >= 2
        dist = stats["distribution"]
        total_count = sum(d["count"] for d in dist)
        assert total_count == stats["total_classified"]


class TestRoleClassifierLLM:
    def test_available_true(self):
        c = RoleClassifier(api_key="sk-test", api_base="https://api.test.com")
        assert c.available is True

    def test_available_false(self):
        c = RoleClassifier(api_key="", api_base="")
        assert c.available is False

    def test_llm_classify(self):
        c = RoleClassifier(api_key="sk-test", api_base="https://api.test.com")

        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": '{"role_id": "backend", "role_name": "后端开发", "confidence": "high"}'}}],
        }
        mock_resp.raise_for_status.return_value = None

        with patch.object(c, "_call_api", return_value=mock_resp.json.return_value):
            result = c.classify("Django backend developer with Postgres")

        assert result.role_id == "backend"
        assert result.role_name == "后端开发"
        assert result.confidence == "high"

    def test_llm_unknown_role_falls_back(self):
        c = RoleClassifier(api_key="sk-test", api_base="https://api.test.com")

        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": '{"role_id": "unknown_role", "role_name": "未知", "confidence": "low"}'}}],
        }
        mock_resp.raise_for_status.return_value = None

        with patch.object(c, "_call_api", return_value=mock_resp.json.return_value):
            result = c.classify("Some job description")

        assert result.role_id == "other"

    def test_llm_api_error_falls_back_to_rules(self):
        c = RoleClassifier(api_key="sk-test", api_base="https://api.test.com")

        with patch.object(c, "_call_api", side_effect=Exception("Network error")):
            result = c.classify("React developer with Vue CSS")

        assert result.role_id == "frontend"
