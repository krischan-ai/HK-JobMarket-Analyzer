from __future__ import annotations

import pytest

from src.resume_agent.utils import ResumeAgentError, extract_json_objects, parse_llm_json


def test_parse_llm_json_plain_object():
    assert parse_llm_json('{"ok": true}') == {"ok": True}


def test_parse_llm_json_fenced_array():
    assert parse_llm_json("```json\n[{\"section\":\"skills\"}]\n```") == [{"section": "skills"}]


def test_parse_llm_json_embedded_object():
    assert parse_llm_json('Here is the result: {"score": 8}') == {"score": 8}


def test_parse_llm_json_rejects_empty():
    with pytest.raises(ResumeAgentError):
        parse_llm_json("")


def test_extract_json_objects_salvages_truncated_array():
    # 第二个对象被截断，应只抢救出第一个完整对象
    text = '[{"section":"技能","suggested":"Python, AWS"}, {"section":"经验","suggested":"un终止'
    objs = extract_json_objects(text)
    assert len(objs) == 1
    assert objs[0]["section"] == "技能"


def test_extract_json_objects_handles_braces_in_strings():
    text = '[{"a":"has } brace"},{"b":"ok"}]'
    objs = extract_json_objects(text)
    assert objs == [{"a": "has } brace"}, {"b": "ok"}]
