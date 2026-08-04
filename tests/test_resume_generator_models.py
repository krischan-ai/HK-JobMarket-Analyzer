from __future__ import annotations

import pytest
from src.resume_agent.generator_models import ResumeGenerateRequest, SelectedExperiencePlan, TargetJobProfile


def test_resume_generate_request_defaults():
    req = ResumeGenerateRequest(resume_text="x" * 80, target_role="AI Engineer")
    assert req.target_market == "Hong Kong"
    assert req.language == "en"
    assert req.top_k_jobs == 8


def test_resume_generate_request_allows_sparse_resume():
    req = ResumeGenerateRequest(resume_text="Python", target_role="AI Engineer")
    assert req.resume_text == "Python"


def test_target_job_profile_defaults_to_knowledge_base():
    profile = TargetJobProfile(target_role="Backend Engineer")
    assert profile.source == "knowledge_base"
    assert profile.confidence == "medium"
    assert profile.sample_count == 0


def test_selected_experience_plan_defaults():
    plan = SelectedExperiencePlan()
    assert plan.selected == []
    assert plan.excluded == []
    assert plan.user_confirmation_required == []
