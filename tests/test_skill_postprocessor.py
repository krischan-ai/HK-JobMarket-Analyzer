from __future__ import annotations

from src.analyzer.skill_postprocessor import postprocess_tag_profile
from src.analyzer import skill_taxonomy as tax


def _names(bucket):
    return {t["name"] for t in bucket}


def _by_name(bucket, name):
    for t in bucket:
        if t["name"] == name:
            return t
    return None


class TestRequirementLevel:
    def test_essential_marks_required(self):
        out = postprocess_tag_profile({"technical": [
            {"name": "Python", "category": "programming_languages",
             "requirement_level": "preferred", "confidence": 0.9,
             "evidence": "Python (essential for AI/automation)"},
        ]})
        assert _by_name(out["technical"], "Python")["requirement_level"] == "required"

    def test_eg_demoted_to_example(self):
        out = postprocess_tag_profile({"technical": [
            {"name": "JavaScript", "category": "programming_languages",
             "requirement_level": "required", "confidence": 0.9,
             "evidence": "e.g., JavaScript/TypeScript, Go, or Java"},
        ]})
        assert _by_name(out["technical"], "JavaScript")["requirement_level"] == "example"

    def test_etc_does_not_demote(self):
        # "etc." 列举不应把 OpenAI 降级为 example（doc §11.8）
        out = postprocess_tag_profile({"technical": [
            {"name": "openai", "category": "frameworks_libraries",
             "requirement_level": "required", "confidence": 0.92,
             "evidence": "AI APIs (OpenAI, Anthropic, etc.)"},
        ]})
        tag = _by_name(out["technical"], "OpenAI")
        assert tag["requirement_level"] == "required"
        assert tag["category"] == "ai_api"

    def test_inferred_confidence_capped(self):
        out = postprocess_tag_profile({"technical": [
            {"name": "RAG", "category": "ai_concepts",
             "requirement_level": "inferred", "confidence": 0.95,
             "evidence": "retrieval over internal documents"},
        ]})
        tag = _by_name(out["technical"], "RAG")
        assert tag["requirement_level"] == "inferred"
        assert tag["confidence"] <= tax.INFERRED_MAX_CONFIDENCE


class TestCategoryCorrection:
    def test_openai_anthropic_to_ai_api(self):
        out = postprocess_tag_profile({"technical": [
            {"name": "Anthropic", "category": "frameworks_libraries",
             "requirement_level": "required", "confidence": 0.9, "evidence": "Anthropic API"},
        ]})
        assert _by_name(out["technical"], "Anthropic")["category"] == "ai_api"

    def test_llamaindex_to_ai_framework(self):
        out = postprocess_tag_profile({"technical": [
            {"name": "llamaindex", "category": "frameworks_libraries",
             "requirement_level": "preferred", "confidence": 0.8, "evidence": "familiarity with LlamaIndex"},
        ]})
        tag = _by_name(out["technical"], "LlamaIndex")
        assert tag is not None
        assert tag["category"] == "ai_framework"

    def test_office_tools_not_core_stack(self):
        out = postprocess_tag_profile({"technical": [
            {"name": "PowerPoint", "category": "programming_languages",
             "requirement_level": "required", "confidence": 0.8, "evidence": "presentations in PowerPoint"},
        ]})
        assert _by_name(out["technical"], "PowerPoint")["category"] == "office_tools"


class TestLlamaDisambiguation:
    def test_standalone_llama_from_llamaindex_merged(self):
        out = postprocess_tag_profile({"technical": [
            {"name": "llama", "category": "ai_concepts",
             "requirement_level": "required", "confidence": 0.9, "evidence": "use LlamaIndex for retrieval"},
        ]})
        assert _names(out["technical"]) == {"LlamaIndex"}

    def test_standalone_llama_without_context_dropped(self):
        out = postprocess_tag_profile({"technical": [
            {"name": "llama", "category": "ai_concepts",
             "requirement_level": "required", "confidence": 0.9, "evidence": "build AI features"},
        ]})
        assert out["technical"] == []


class TestDomainDisambiguation:
    def test_insurance_benefit_dropped(self):
        out = postprocess_tag_profile({"non_technical": [
            {"name": "保險/財富管理知識", "category": "domain_knowledge",
             "requirement_level": "required", "confidence": 0.8, "evidence": "life insurance coverage"},
        ]})
        assert out["non_technical"] == []

    def test_payment_ecommerce_context(self):
        out = postprocess_tag_profile({"non_technical": [
            {"name": "金融/金融科技知識", "category": "domain_knowledge",
             "requirement_level": "required", "confidence": 0.8,
             "evidence": "payments, promotions, order management"},
        ]})
        assert _names(out["non_technical"]) == {"電商/零售業務知識"}

    def test_payment_banking_context(self):
        out = postprocess_tag_profile({"non_technical": [
            {"name": "金融/金融科技知識", "category": "domain_knowledge",
             "requirement_level": "required", "confidence": 0.85,
             "evidence": "payment gateway for banking and KYC"},
        ]})
        assert _names(out["non_technical"]) == {"金融/金融科技知識"}


class TestStructure:
    def test_empty_and_invalid_input(self):
        assert postprocess_tag_profile(None) == {"technical": [], "non_technical": []}
        assert postprocess_tag_profile({}) == {"technical": [], "non_technical": []}

    def test_dedupe_keeps_strongest(self):
        out = postprocess_tag_profile({"technical": [
            {"name": "Python", "category": "programming_languages",
             "requirement_level": "preferred", "confidence": 0.7, "evidence": "Python nice to have"},
            {"name": "Python", "category": "programming_languages",
             "requirement_level": "required", "confidence": 0.95, "evidence": "Python is essential"},
        ]})
        pythons = [t for t in out["technical"] if t["name"] == "Python"]
        assert len(pythons) == 1
        assert pythons[0]["requirement_level"] == "required"
