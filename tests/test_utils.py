from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.utils import (
    ensure_dir,
    json_dump,
    json_load,
    chunk_list,
    normalize_text,
    safe_filename,
    get_project_root,
)


class TestUtils:
    def test_ensure_dir(self, temp_dir):
        new_dir = temp_dir / "a" / "b" / "c"
        result = ensure_dir(new_dir)
        assert result.exists()
        assert result.is_dir()

    def test_json_roundtrip(self, temp_dir):
        path = temp_dir / "test.json"
        data = {"key": "value", "num": 42}
        json_dump(data, path)
        assert path.exists()
        loaded = json_load(path)
        assert loaded == data

    def test_chunk_list(self):
        items = [1, 2, 3, 4, 5, 6, 7]
        chunks = list(chunk_list(items, 3))
        assert len(chunks) == 3
        assert chunks[0] == [1, 2, 3]
        assert chunks[1] == [4, 5, 6]
        assert chunks[2] == [7]

    def test_chunk_list_empty(self):
        assert list(chunk_list([], 3)) == []

    def test_normalize_text(self):
        assert normalize_text("  Hello   World  ") == "Hello World"
        assert normalize_text("") == ""

    def test_safe_filename(self):
        assert safe_filename("Hello World") == "Hello_World"
        assert safe_filename("a/b/c") == "a_b_c"
        assert safe_filename("x" * 200) == "x" * 80

    def test_get_project_root(self):
        root = get_project_root()
        assert (root / "src").exists()
        assert (root / "config").exists()
