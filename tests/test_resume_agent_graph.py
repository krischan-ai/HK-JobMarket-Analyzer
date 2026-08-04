from __future__ import annotations

from dataclasses import dataclass

import pytest

from src.resume_agent.graph import run_resume_agent, run_resume_agent_stream
from src.resume_agent.utils import ResumeAgentError


class FakeLLM:
    def __init__(self):
        self.calls = []

    def chat_json(self, system_prompt, *_args, **_kwargs):
        self.calls.append(system_prompt)
        if "简历解析" in system_prompt:
            return '{"sections":{"技能":"Python, FastAPI"},"raw_skills":["Python","FastAPI"],"years_of_experience":3,"education_level":"Bachelor","current_titles":["Backend Developer"]}'
        if "目标职位理解" in system_prompt or "招聘市场顾问" in system_prompt:
            return '{"role_id":"backend","role_name":"后端开发","role_summary":"Backend API role","expanded_query":"Backend Engineer Python FastAPI AWS APIs","core_tech":["Python","FastAPI","AWS"],"responsibilities":["Build APIs"]}'
        if "招聘匹配顾问" in system_prompt:
            return '{"ranked_job_ids":["1"],"match_reasons":{"1":"Matches backend API and AWS direction."},"match_advice":{"summary":"Backend API role is the best fit.","suggestions":["Highlight Python APIs","Mention AWS honestly"]}}'
        if "技术趋势分析" in system_prompt:
            return '{"tech_stack_themes":[{"theme":"云平台与工程交付","items":["AWS","Docker","CI/CD"],"evidence":["ranking"]}]}'
        if "技术栈分析专家" in system_prompt:
            return '{"tech_stack_themes":[{"theme":"后端工程与 API","items":["Python","FastAPI","REST API"],"evidence":["Backend Engineer"]},{"theme":"云平台与交付自动化","items":["AWS","Docker"],"evidence":["AWS APIs"]}],"other_competencies":["Cantonese communication","Cross-functional collaboration"],"core_capabilities":["API design","Cloud deployment awareness"]}'
        if "岗位 JD" in system_prompt:
            return '{"required_skills":["Python","AWS"],"preferred_skills":["Docker"],"responsibilities":["Build APIs"],"min_experience":3,"education_required":null,"language_requirements":["English"],"key_requirements":["Python backend"]}'
        if "目标岗位市场分析专家" in system_prompt or "目标岗位市场画像" in system_prompt:
            return '{"required_skills":["Python","AWS"],"preferred_skills":["Docker"],"responsibilities":["Build APIs"],"min_experience":3,"education_required":null,"language_requirements":["English"],"key_requirements":["Python backend"]}'
        if "匹配分析专家" in system_prompt:
            return '{"matched_skills":["Python"],"missing_skills":["AWS"],"weak_skills":["FastAPI"],"experience_gap":"Cloud experience is not explicit","keyword_suggestions":[{"keyword":"AWS","priority":"high","placement":"工作经验"}],"market_demand_analysis":"Market favors backend and cloud delivery themes."}'
        if "简历润色" in system_prompt:
            return '[{"section":"技能","original":"Python","suggested":"Python, FastAPI, AWS","changes":["Add AWS when truthful"],"keywords_added":["AWS"]}]'
        if "评分专家" in system_prompt:
            return '{"overall_score":8,"keyword_coverage":8,"experience_alignment":7,"skill_relevance":8,"language_quality":9,"suggestions":["Add measurable outcomes"]}'
        if "面试教练" in system_prompt:
            return '[{"bullet_id":"b1","final_text":"Built Python APIs","target_capability":"Backend","evidence_source":"工作经验","evidence_confidence":"strong","talk_track_30s":"I built...","follow_up_questions":["How did you scale?"],"risk_notes":[],"fallback_answer":"Honest answer"}]'
        raise AssertionError(f"Unexpected prompt: {system_prompt[:80]}")


@dataclass
class FakeRole:
    role_id: str = "backend"
    role_name: str = "后端开发"


class FakeClassifier:
    def classify(self, _jd_text):
        return FakeRole()


_FAKE_JOB = {
    "job_id": "1",
    "title": "Backend Engineer",
    "company": "HK Tech",
    "location": "Central",
    "source": "jobsdb",
    "url": "https://example.com",
    "score": 0.91,
    "snippet": "Python AWS APIs",
}

_FAKE_INSIGHTS = {
    "total_jobs": 244,
    "tech_stack_ranking": [{"skill": "Python", "count": 79}, {"skill": "Aws", "count": 53}],
    "role_demand_ranking": [{"role_id": "ai_application", "role_name": "AI应用开发", "count": 37}],
}


class FakeVectorStore:
    def search(self, _query, top_k=5):
        return [dict(_FAKE_JOB)][:top_k]


class FakeHybridSearch:
    def __init__(self, *_args, **_kwargs):
        pass

    def search(self, _query, _options=None):
        return {"results": [dict(_FAKE_JOB)], "rerank_used": True}


class FakeHybridSearchEmpty:
    def __init__(self, *_args, **_kwargs):
        pass

    def search(self, _query, _options=None):
        return {"results": [], "rerank_used": False}


def _patch_retrieval(monkeypatch, hybrid, vector):
    import src.resume_agent.nodes as nodes

    monkeypatch.setattr(nodes, "RoleClassifier", FakeClassifier)
    monkeypatch.setattr(nodes, "VectorStore", vector)
    monkeypatch.setattr(nodes, "HybridJobSearch", hybrid)
    monkeypatch.setattr(nodes, "compute_market_insights", lambda top_n=12: dict(_FAKE_INSIGHTS))


def test_run_resume_agent_happy_path(monkeypatch):
    _patch_retrieval(monkeypatch, FakeHybridSearch, FakeVectorStore)

    result = run_resume_agent(
        resume_text="Backend developer with Python and FastAPI experience. " * 2,
        jd_text="We need a Python backend engineer with AWS API experience. " * 2,
        llm=FakeLLM(),
    )

    assert result["jd"]["role_category"] == "backend"
    assert result["matched_jobs"][0]["title"] == "Backend Engineer"
    assert result["matched_jobs"][0]["match_reason"]
    assert result["match_advice"]["summary"]
    assert result["rerank_used"] is True
    assert result["gap"]["missing_skills"] == ["AWS"]
    assert result["polish_suggestions"][0]["section"] == "技能"
    assert result["score"]["overall_score"] == 8.0

    mc = result["market_context"]
    assert mc is not None
    assert mc["job_count"] == 1
    assert mc["common_titles"] == ["Backend Engineer"]
    skills = {item["skill"].lower() for item in mc["top_skills"]}
    assert "python" in skills and "aws" in skills

    insights = result["market_insights"]
    assert insights["role_demand_ranking"][0]["role_id"] == "ai_application"
    assert insights["tech_stack_ranking"][0]["skill"] == "Python"

    # v2.9：输入体检与岗位调研应作为可见产物贯通
    assert result["input_health"]["status"] in {"complete", "workable"}
    assert result["input_health"]["resume_status"] in {"provided", "partial"}
    research = result["job_research"]
    assert research["source"] == "jd"
    assert research["sample_count"] == 1
    assert research["core_capabilities"]  # JD 硬技能作为靶心
    assert research["tech_stack_themes"][0]["theme"] == "后端工程与 API"
    assert "Cantonese communication" in research["other_competencies"]
    assert research["common_titles"] == ["Backend Engineer"]


def test_build_market_context_empty_when_no_matches():
    from src.resume_agent.nodes import build_market_context

    assert build_market_context({"matched_jobs": []})["market_context"] is None


class EmptyVectorStore:
    def search(self, *_args, **_kwargs):
        return []


def test_run_resume_agent_knowledge_base_mode(monkeypatch):
    """未提供目标 JD 时，应用知识库相似岗位合成目标画像并完成润色。"""
    _patch_retrieval(monkeypatch, FakeHybridSearch, FakeVectorStore)

    result = run_resume_agent(
        resume_text="Backend developer with Python and FastAPI experience. " * 2,
        jd_text="",  # 不提供 JD
        target_role="Backend Engineer",
        llm=FakeLLM(),
    )

    assert result["jd"]["source"] == "knowledge_base"
    assert result["jd"]["role_category"] == "backend"
    assert result["matched_jobs"][0]["title"] == "Backend Engineer"
    assert result["market_context"]["job_count"] == 1
    assert result["market_insights"]["tech_stack_ranking"][0]["skill"] == "Python"
    assert result["score"]["overall_score"] == 8.0
    assert result["target_role_understanding"]["expanded_query"]


def test_run_resume_agent_stream_emits_progressive_events(monkeypatch):
    """流式接口应按阶段顺序产出事件，先完成的先输出，最后给出完整结果。"""
    _patch_retrieval(monkeypatch, FakeHybridSearch, FakeVectorStore)

    events = list(
        run_resume_agent_stream(
            resume_text="Backend developer with Python and FastAPI experience. " * 2,
            jd_text="We need a Python backend engineer with AWS API experience. " * 2,
            llm=FakeLLM(),
        )
    )
    stages = [e["stage"] for e in events]

    # 输入体检先行，召回先于岗位调研/差距分析，评分后做面试深挖，done 收尾
    assert stages.index("input_health") < stages.index("matched_jobs")
    assert stages.index("matched_jobs") < stages.index("job_research") < stages.index("gap")
    assert stages.index("gap") < stages.index("score") < stages.index("interview_prep") < stages.index("done")
    assert "market_insights" in stages
    assert "target_understanding" in stages

    matched_event = next(e for e in events if e["stage"] == "matched_jobs")
    assert matched_event["matched_jobs"][0]["title"] == "Backend Engineer"
    assert matched_event["rerank_used"] is True
    assert matched_event["matched_jobs"][0]["match_reason"]

    research_event = next(e for e in events if e["stage"] == "job_research")
    assert research_event["job_research"]["source"] == "jd"
    assert research_event["job_research"]["sample_count"] == 1

    interview_event = next(e for e in events if e["stage"] == "interview_prep")
    assert interview_event["bullet_inventory"][0]["bullet_id"] == "b1"

    done = events[-1]
    assert done["stage"] == "done"
    assert done["result"]["score"]["overall_score"] == 8.0
    assert done["result"]["job_research"]["core_capabilities"]
    assert done["result"]["bullet_inventory"][0]["talk_track_30s"] == "I built..."


def test_run_resume_agent_kb_mode_errors_without_matches(monkeypatch):
    """既无目标 JD、知识库又无相似岗位时，应给出明确错误。"""
    _patch_retrieval(monkeypatch, FakeHybridSearchEmpty, EmptyVectorStore)

    with pytest.raises(ResumeAgentError):
        run_resume_agent(
            resume_text="Backend developer with Python and FastAPI experience. " * 2,
            jd_text="",
            llm=FakeLLM(),
        )
