from __future__ import annotations

from src.resume_agent.generator_nodes import check_generation_input, render_generated_resume_markdown, run_quality_gates


def _base_state():
    return {
        "resume_text": "Python backend developer with FastAPI project experience." * 5,
        "target_role": "Backend Engineer",
        "target_market": "Hong Kong",
        "language": "en",
        "selected_experience_plan": {
            "selected": [
                {
                    "source_type": "work",
                    "source_id": "work_1",
                    "source_title": "Acme - Developer",
                    "target_capability": "Backend API development",
                    "evidence_text": "Built internal APIs with Python.",
                    "selection_reason": "Relevant backend evidence.",
                    "evidence_confidence": "strong",
                }
            ],
            "excluded": [],
            "selection_summary": "Selected backend evidence.",
            "user_confirmation_required": [],
        },
        "generated_resume": {
            "language": "en",
            "headline": "Backend Engineer",
            "positioning_statement": "Backend engineer targeting Hong Kong roles.",
            "summary": "Python backend candidate.",
            "skills": ["Python", "FastAPI"],
            "work_experience": [
                {
                    "company": "Acme",
                    "title": "Developer",
                    "start_date": "2022",
                    "end_date": "Present",
                    "location": "Hong Kong",
                    "bullets": [
                        {
                            "bullet_id": "b1",
                            "text": "Built internal APIs with Python.",
                            "evidence_id": "work_1",
                            "target_capability": "Backend API development",
                            "interview_risk": "low",
                        }
                    ],
                }
            ],
            "projects": [],
            "education": [],
            "certifications": [],
        },
        "claim_audit": [
            {
                "claim": "Built internal APIs with Python.",
                "claim_type": "achievement",
                "source": "selected_experience",
                "confidence": "strong",
                "action": "keep",
                "reason": "Supported by selected evidence.",
                "suggested_revision": "",
            }
        ],
        "capability_matches": [
            {
                "capability": "Backend API development",
                "job_basis": "Target role requires APIs.",
                "matched_sources": ["work_1"],
                "evidence_strength": "strong",
                "resume_angle": "API delivery.",
                "risk_note": "",
            }
        ],
        "resume_profile": {"contact": {"name": "Candidate", "email": "me@example.com"}},
    }


def test_generation_input_blocks_missing_target():
    state = {"resume_text": "x" * 80, "target_role": ""}
    health = check_generation_input(state)["input_health"]
    assert health["status"] == "blocked"
    assert health["target_status"] == "missing"


def test_quality_gate_passes_traceable_bullet():
    result = run_quality_gates(_base_state())["quality_gate"]
    assert result["status"] == "pass"
    assert result["p0_violations"] == []


def test_quality_gate_blocks_missing_evidence_id():
    state = _base_state()
    state["generated_resume"]["work_experience"][0]["bullets"][0]["evidence_id"] = ""
    result = run_quality_gates(state)["quality_gate"]
    assert result["status"] == "blocked"
    assert "lacks evidence_id" in result["p0_violations"][0]


def test_quality_gate_blocks_knowledge_base_claim_kept():
    state = _base_state()
    state["claim_audit"] = [
        {
            "claim": "Candidate has Kubernetes production experience.",
            "claim_type": "skill",
            "source": "knowledge_base",
            "confidence": "risky",
            "action": "keep",
            "reason": "Only found in JD.",
            "suggested_revision": "",
        }
    ]
    result = run_quality_gates(state)["quality_gate"]
    assert result["status"] == "blocked"
    assert any("Knowledge-base claim" in item for item in result["p0_violations"])


def test_markdown_renderer_outputs_resume():
    state = _base_state()
    markdown = render_generated_resume_markdown(state)["markdown"]
    assert "# Candidate" in markdown
    assert "## Work Experience" in markdown
    assert "Built internal APIs" in markdown
