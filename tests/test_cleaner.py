from __future__ import annotations

import pytest

from src.cleaner.text import JDTextCleaner
from src.cleaner.salary import SalaryParser
from src.cleaner.pipeline import CleaningPipeline


class TestJDTextCleaner:
    def test_remove_html_tags(self):
        cleaner = JDTextCleaner()
        result = cleaner.remove_html_tags("<p>Hello <strong>World</strong></p>")
        assert "Hello" in result
        assert "World" in result
        assert "<" not in result

    def test_remove_html_tags_none(self):
        assert JDTextCleaner.remove_html_tags("") == ""

    def test_normalize_unicode(self):
        result = JDTextCleaner.normalize_unicode("Hello\u3000World\xa0Test")
        assert result == "Hello World Test"

    def test_normalize_jobsdb_artifacts(self):
        result = JDTextCleaner().clean("Python聽developer 鈥檚 role 路 Build APIs")
        assert "Python developer" in result
        assert "Build APIs" in result
        assert "聽" not in result

    def test_normalize_whitespace(self):
        result = JDTextCleaner.normalize_whitespace("  Hello   World  ")
        assert result == "Hello World"

    def test_remove_special_chars(self):
        result = JDTextCleaner.remove_special_chars("Hello! @World# $Test%")
        assert "!" in result
        assert "@" in result

    def test_remove_email_urls(self):
        result = JDTextCleaner.remove_email_urls("Contact: test@example.com or https://example.com")
        assert "test@example.com" not in result
        assert "https://" not in result

    def test_clean_pipeline(self):
        cleaner = JDTextCleaner()
        raw = "<p>Senior <strong>Python</strong> developer. Contact: hr@company.com</p>"
        result = cleaner.clean(raw)
        assert "Senior" in result
        assert "Python" in result
        assert "<p>" not in result
        assert "hr@company.com" not in result

    def test_clean_empty(self):
        assert JDTextCleaner().clean("") == ""


class TestSalaryParser:
    @pytest.mark.parametrize("raw,expected", [
        ("HK$45,000 - HK$60,000 /month", (45000.0, 60000.0)),
        ("HK$600,000 - HK$720,000 per annum", (50000.0, 60000.0)),
        ("HK$50,000 - HK$80,000 /month", (50000.0, 80000.0)),
        ("HK$25,000 up", (25000.0, None)),
        ("HK$30,000 /month", (30000.0, None)),
        ("", (None, None)),
        (None, (None, None)),
        ("not a salary", (None, None)),
    ])
    def test_parse(self, raw, expected):
        assert SalaryParser.parse(raw) == expected


class TestCleaningPipeline:
    def test_clean_job(self, mock_jobs):
        pipeline = CleaningPipeline()
        job = pipeline.clean_job(mock_jobs[0])
        assert job["jd_text"] is not None
        assert "<" not in job["jd_text"]
        assert "Python" in job["jd_text"]
        assert job["salary_min"] == 45000.0
        assert job["salary_max"] == 60000.0
        assert job["salary_currency"] == "HKD"

    def test_clean_batch(self, mock_jobs):
        pipeline = CleaningPipeline()
        result = pipeline.clean_batch(mock_jobs)
        assert len(result) == len(mock_jobs)
        for job in result:
            assert "jd_text" in job
            assert "salary_min" in job
            assert "salary_max" in job

    def test_clean_batch_error_resilience(self):
        pipeline = CleaningPipeline()
        jobs = [
            {"job_id": "1", "jd_raw": "<p>Valid JD</p>", "salary_raw": "HK$50,000 /month"},
            {"job_id": "2"},
        ]
        result = pipeline.clean_batch(jobs)
        assert len(result) == 2
        assert result[0].get("jd_text") is not None
