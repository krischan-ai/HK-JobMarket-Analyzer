from __future__ import annotations

from src.resume_agent.graph import check_input_health
from src.resume_agent.nodes import build_job_research, run_input_health


def test_input_health_blocked_without_resume():
    health = check_input_health(resume_text="")
    assert health["status"] == "blocked"
    assert health["resume_status"] == "missing"
    assert health["blocking_questions"]  # 必须给出最少必要问题


def test_input_health_workable_without_jd():
    health = check_input_health(resume_text="x" * 300, target_role="AI Engineer")
    assert health["status"] == "workable"
    assert health["jd_status"] == "missing"
    assert health["resume_status"] == "provided"
    assert any("AI Engineer" in a for a in health["assumptions"])


def test_input_health_complete_with_jd_and_status():
    health = check_input_health(
        resume_text="x" * 300,
        jd_text="Python backend engineer with AWS experience required. " * 2,
        application_status="applied",
    )
    assert health["status"] == "complete"
    assert health["jd_status"] == "provided"
    assert any("已投递" in a for a in health["assumptions"])


def test_input_health_partial_resume_is_workable():
    health = check_input_health(resume_text="x" * 80)
    assert health["resume_status"] == "partial"
    assert health["status"] == "workable"
    assert health["gaps"]


def test_build_job_research_none_without_matches():
    state = {"matched_jobs": [], "market_context": None, "jd": {}, "target_jd_text": ""}
    assert build_job_research(state)["job_research"] is None


def test_build_job_research_knowledge_base_source():
    state = {
        "matched_jobs": [
            {"title": "AI Engineer", "company": "HK Tech", "location": "Central", "url": ""},
            {"title": "ML Engineer", "company": "HK AI", "location": "Kowloon", "url": ""},
        ],
        "market_context": {
            "top_skills": [{"skill": "Python", "count": 5}, {"skill": "AWS", "count": 3}],
            "common_titles": ["AI Engineer"],
        },
        "jd": {"required_skills": ["Python", "PyTorch"], "responsibilities": ["Build models"], "preferred_skills": ["AWS"]},
        "target_jd_text": "",  # 无 JD → 知识库画像
        "target_role": "AI Engineer",
    }
    report = build_job_research(state)["job_research"]
    assert report["source"] == "knowledge_base"
    assert report["sample_count"] == 2
    assert report["confidence"] == "medium"  # 2 条样本
    assert "Python" in report["core_capabilities"]
    assert report["high_frequency_skills"][0]["skill"] == "Python"
    assert report["common_titles"] == ["AI Engineer"]
    assert report["source_coverage_note"]


def test_build_job_research_kb_confidence_capped_at_medium():
    """知识库模式即使样本充足，置信度也封顶 medium，不伪装成确定结论。"""
    state = {
        "matched_jobs": [{"title": f"AI Eng {i}", "company": "C", "location": "HK", "url": ""} for i in range(8)],
        "market_context": {"top_skills": [{"skill": "Python", "count": 8}], "common_titles": []},
        "jd": {"required_skills": ["Python"], "responsibilities": []},
        "target_jd_text": "",  # 无 JD → 知识库画像
    }
    report = build_job_research(state)["job_research"]
    assert report["source"] == "knowledge_base"
    assert report["sample_count"] == 8
    assert report["confidence"] == "medium"


def test_build_job_research_jd_source_high_confidence():
    state = {
        "matched_jobs": [{"title": f"Job {i}", "company": "C", "location": "HK", "url": ""} for i in range(5)],
        "market_context": {"top_skills": [{"skill": "Go", "count": 4}], "common_titles": []},
        "jd": {"required_skills": ["Go"], "responsibilities": []},
        "target_jd_text": "Backend engineer role requiring strong Go experience. " * 2,
    }
    report = build_job_research(state)["job_research"]
    assert report["source"] == "jd"
    assert report["confidence"] == "high"


def test_run_input_health_returns_wrapped_dict():
    out = run_input_health({"resume_text": "x" * 300, "target_jd_text": ""})
    assert "input_health" in out
    assert out["input_health"]["resume_status"] == "provided"
