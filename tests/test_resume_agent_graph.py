from __future__ import annotations

from dataclasses import dataclass

from src.resume_agent.graph import run_resume_agent


class FakeLLM:
    def __init__(self):
        self.responses = [
            '{"sections":{"技能":"Python, FastAPI"},"raw_skills":["Python","FastAPI"],"years_of_experience":3,"education_level":"Bachelor","current_titles":["Backend Developer"]}',
            '{"required_skills":["Python","AWS"],"preferred_skills":["Docker"],"responsibilities":["Build APIs"],"min_experience":3,"education_required":null,"language_requirements":["English"],"key_requirements":["Python backend"]}',
            '{"matched_skills":["Python"],"missing_skills":["AWS"],"weak_skills":["FastAPI"],"experience_gap":"Cloud experience is not explicit","keyword_suggestions":[{"keyword":"AWS","priority":"high","placement":"工作经验"}]}',
            '[{"section":"技能","original":"Python","suggested":"Python, FastAPI, AWS","changes":["Add AWS when truthful"],"keywords_added":["AWS"]}]',
            '{"overall_score":8,"keyword_coverage":8,"experience_alignment":7,"skill_relevance":8,"language_quality":9,"suggestions":["Add measurable outcomes"]}',
        ]

    def chat_json(self, *_args, **_kwargs):
        return self.responses.pop(0)


@dataclass
class FakeRole:
    role_id: str = "backend"
    role_name: str = "后端开发"


class FakeClassifier:
    def classify(self, _jd_text):
        return FakeRole()


class FakeVectorStore:
    def search(self, _query, top_k=5):
        return [
            {
                "job_id": "1",
                "title": "Backend Engineer",
                "company": "HK Tech",
                "location": "Central",
                "source": "jobsdb",
                "url": "https://example.com",
                "score": 0.91,
                "snippet": "Python AWS APIs",
            }
        ][:top_k]


def test_run_resume_agent_happy_path(monkeypatch):
    import src.resume_agent.nodes as nodes

    monkeypatch.setattr(nodes, "RoleClassifier", FakeClassifier)
    monkeypatch.setattr(nodes, "VectorStore", FakeVectorStore)

    result = run_resume_agent(
        resume_text="Backend developer with Python and FastAPI experience. " * 2,
        jd_text="We need a Python backend engineer with AWS API experience. " * 2,
        llm=FakeLLM(),
    )

    assert result["jd"]["role_category"] == "backend"
    assert result["matched_jobs"][0]["title"] == "Backend Engineer"
    assert result["gap"]["missing_skills"] == ["AWS"]
    assert result["polish_suggestions"][0]["section"] == "技能"
    assert result["score"]["overall_score"] == 8.0
