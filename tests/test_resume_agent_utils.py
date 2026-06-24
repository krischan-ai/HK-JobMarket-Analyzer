from __future__ import annotations

import pytest

from src.resume_agent.utils import ResumeAgentError, parse_llm_json


def test_parse_llm_json_plain_object():
    assert parse_llm_json('{"ok": true}') == {"ok": True}


def test_parse_llm_json_fenced_array():
    assert parse_llm_json("```json\n[{\"section\":\"skills\"}]\n```") == [{"section": "skills"}]


def test_parse_llm_json_embedded_object():
    assert parse_llm_json('Here is the result: {"score": 8}') == {"score": 8}


def test_parse_llm_json_rejects_empty():
    with pytest.raises(ResumeAgentError):
        parse_llm_json("")
