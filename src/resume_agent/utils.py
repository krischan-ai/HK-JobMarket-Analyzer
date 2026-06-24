from __future__ import annotations

import json
import re
from typing import Any


class ResumeAgentError(RuntimeError):
    pass


def compact_text(text: str, limit: int = 8000) -> str:
    value = re.sub(r"\s+", " ", text or "").strip()
    if len(value) <= limit:
        return value
    return f"{value[:limit]}..."


def redact_for_log(text: str, limit: int = 120) -> str:
    value = re.sub(r"\s+", " ", text or "").strip()
    return value[:limit] + ("..." if len(value) > limit else "")


def parse_llm_json(content: str) -> Any:
    text = (content or "").strip()
    if not text:
        raise ResumeAgentError("LLM returned empty content")

    candidates = [text]
    fenced = re.findall(r"```(?:json)?\s*([\s\S]*?)\s*```", text, flags=re.IGNORECASE)
    candidates.extend(fenced)

    obj_start = text.find("{")
    obj_end = text.rfind("}")
    if obj_start != -1 and obj_end > obj_start:
        candidates.append(text[obj_start:obj_end + 1])

    arr_start = text.find("[")
    arr_end = text.rfind("]")
    if arr_start != -1 and arr_end > arr_start:
        candidates.append(text[arr_start:arr_end + 1])

    for candidate in candidates:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    raise ResumeAgentError("Unable to parse JSON from LLM response")


def ensure_list(value: Any) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def clamp_score(value: Any) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(10.0, score))
