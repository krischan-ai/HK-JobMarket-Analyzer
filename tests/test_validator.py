from __future__ import annotations

import pytest

from src.knowledge_base.validator import Validator


class TestValidator:
    def test_validate_records(self):
        v = Validator()
        records = [
            {"title": "Dev", "company": "Co", "location": "HK", "jd_raw": "Valid JD"},
            {"title": "Dev2", "company": "Co2", "location": "HK", "jd_raw": ""},
        ]
        result = v.validate_records(records, raise_on_missing_jd=True)
        assert len(result) == 1

    def test_validate_records_all_valid(self):
        v = Validator()
        records = [{"title": "Dev", "company": "Co", "location": "HK", "jd_raw": "JD"}]
        result = v.validate_records(records)
        assert len(result) == 1

    def test_validate_row_count(self):
        v = Validator()
        assert v.validate_row_count([1, 2, 3])
        assert not v.validate_row_count(list(range(10001)))

    def test_validate_file_size_small(self, temp_dir):
        p = temp_dir / "small.csv"
        p.write_text("hello")
        v = Validator()
        assert v.validate_file_size(str(p))

    def test_validate_file_size_nonexistent(self, temp_dir):
        v = Validator()
        with pytest.raises(FileNotFoundError):
            v.validate_file_size(str(temp_dir / "nonexistent.csv"))
