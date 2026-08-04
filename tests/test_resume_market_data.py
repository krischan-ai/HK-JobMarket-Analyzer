"""v1.2（设计文档第 13 章）：复用统计分析结构化标签资产的回归测试。"""
from __future__ import annotations

from dataclasses import dataclass

import src.resume_agent.market_data as md
import src.resume_agent.nodes as nodes


# --- market_data 桥接层单元测试 ---------------------------------------------

_TAG_PROFILE = {
    "technical": [
        {"name": "Python", "category": "programming_languages", "requirement_level": "required",
         "confidence": 0.95, "evidence": "strong Python background"},
        {"name": "Go", "category": "programming_languages", "requirement_level": "example",
         "confidence": 0.6, "evidence": "e.g. Go / Java"},
        {"name": "Kubernetes", "category": "cloud_devops", "requirement_level": "preferred",
         "confidence": 0.8, "evidence": "k8s a plus"},
        {"name": "Excel", "category": "office_tools", "requirement_level": "required",
         "confidence": 0.7, "evidence": "MS Excel"},
    ],
    "non_technical": [
        {"name": "4 年以上经验", "category": "experience", "requirement_level": "required",
         "confidence": 0.9, "evidence": "At least 4 years"},
    ],
}


def test_split_jd_by_requirement_buckets():
    buckets = md.split_jd_by_requirement(_TAG_PROFILE)
    assert md.tag_names(buckets["required"]) == ["Python", "Excel", "4 年以上经验"]
    assert md.tag_names(buckets["example"]) == ["Go"]
    assert md.tag_names(buckets["preferred"]) == ["Kubernetes"]
    assert buckets["inferred"] == []


def test_normalize_keywords_dedup_and_rejection(monkeypatch):
    taxonomy = {
        "taxonomy_aliases": {"POC 測試": ["Proof-Of-Concept", "POC"]},
        "taxonomy_rejections": {"insurance": {"aliases": ["medical insurance"]}},
    }
    out = md.normalize_keywords(
        ["Proof-Of-Concept", "poc", "Python", "Python", "insurance", "Medical Insurance"],
        taxonomy,
    )
    assert out == ["POC 測試", "Python"]  # 别名归一 + 去重 + 拒绝词剔除


def test_load_job_tag_profile_miss_returns_none():
    assert md.load_job_tag_profile("a totally unknown jd not in cache zzz") is None
    assert md.load_job_tag_profile("") is None


def test_candidate_capability_hints_filters_low_confidence_and_alias():
    cands = [
        {"name": "水处理设施知识", "category": "domain_knowledge", "confidence": 0.96, "evidence": "x"},
        {"name": "低置信项", "category": "domain_knowledge", "confidence": 0.5, "evidence": "y"},
        {"name": "Proof-Of-Concept", "category": "alias", "confidence": 0.99, "evidence": "z"},
    ]
    hints = md.candidate_capability_hints(cands)
    assert [h["name"] for h in hints] == ["水处理设施知识"]


# --- analyze_jd 复用路径 ------------------------------------------------------

@dataclass
class _FakeRole:
    role_id: str = "backend"
    role_name: str = "后端开发"


class _FakeClassifier:
    def classify(self, _text):
        return _FakeRole()


def test_analyze_jd_reuses_governed_tag_profile(monkeypatch):
    """命中缓存时直接复用治理标签、免 LLM 重解析，且 example 单列不计硬技能。"""
    reused = {
        "tag_profile": _TAG_PROFILE,
        "soft_skills": {"language": ["English"], "education": ["相关学位"], "business_skill": []},
        "cross_industry_profile": {"delivery_motion": [{"name": "方案设计"}], "business_scenario": []},
        "job_context_profile": {"summary_tags": []},
        "taxonomy_candidates": [],
    }
    monkeypatch.setattr(nodes, "load_job_tag_profile", lambda _t: reused)
    monkeypatch.setattr(nodes, "RoleClassifier", _FakeClassifier)

    class _BoomLLM:
        def chat_json(self, *_a, **_k):
            raise AssertionError("LLM should not be called on cache hit")

    out = nodes.analyze_jd({"target_jd_text": "jd text", "target_role": None}, _BoomLLM())
    jd = out["jd"]
    assert jd["reused_from_cache"] is True
    assert "Go" not in jd["required_skills"]      # example 不进硬技能
    assert jd["example_skills"] == ["Go"]
    assert jd["min_experience"] == 4.0
    assert jd["language_requirements"] == ["English"]
    assert jd["role_category"] == "backend"
    assert jd["tag_evidence"]["Python"] == "strong Python background"


def test_analyze_jd_falls_back_to_llm_on_cache_miss(monkeypatch):
    monkeypatch.setattr(nodes, "load_job_tag_profile", lambda _t: None)
    monkeypatch.setattr(nodes, "RoleClassifier", _FakeClassifier)

    class _LLM:
        def chat_json(self, *_a, **_k):
            return '{"required_skills":["Python"],"preferred_skills":[],"responsibilities":["Build"],"min_experience":3,"language_requirements":["English"],"key_requirements":["Python"]}'

    out = nodes.analyze_jd({"target_jd_text": "jd text", "target_role": None}, _LLM())
    assert out["jd"]["reused_from_cache"] is False
    assert out["jd"]["required_skills"] == ["Python"]


def test_gap_analysis_excludes_example_skills_from_missing(monkeypatch):
    """gap 守卫：备选/推断技能池即便被 LLM 误判，也不计入 missing_skills。"""
    monkeypatch.setattr(nodes, "load_job_tag_profile", lambda _t: None)

    class _LLM:
        def chat_json(self, *_a, **_k):
            return ('{"matched_skills":["Python"],"missing_skills":["Go","java","Kubernetes"],'
                    '"weak_skills":[],"experience_gap":"","keyword_suggestions":[],'
                    '"market_demand_analysis":"x"}')

    state = {
        "target_jd_text": "jd",
        "resume": {}, "matched_jobs": [], "market_context": {}, "market_insights": {},
        "jd": {"example_skills": ["Go", "Java"], "inferred_skills": ["Bash"], "cross_industry_profile": {}},
    }
    gap = nodes.gap_analysis(state, _LLM())["gap"]
    assert gap["missing_skills"] == ["Kubernetes"]  # Go/Java 被剔除
    assert gap["emerging_suggestions"] == []
