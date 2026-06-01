from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any


def ensure_dir(path: str | Path) -> Path:
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def json_dump(data: Any, path: str | Path, indent: int = 2, ensure_ascii: bool = False):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent, ensure_ascii=ensure_ascii)


def json_load(path: str | Path) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def chunk_list(lst: list, size: int):
    for i in range(0, len(lst), size):
        yield lst[i : i + size]


def normalize_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text


def safe_filename(text: str, max_len: int = 80) -> str:
    safe = re.sub(r"[^\w\-_. ]", "_", text)
    safe = safe.strip().replace(" ", "_")
    return safe[:max_len]


def get_project_root() -> Path:
    return Path(__file__).resolve().parent.parent
