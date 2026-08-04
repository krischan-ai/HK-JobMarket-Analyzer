from __future__ import annotations

from src.analyzer.skill_postprocessor import (
    build_summary_tags,
    postprocess_cross_industry_profile,
)


# 政府/公用事业售前解决方案 JD（doc §11.12）的六维原子标签
GOV_RAW = {
    "industry_context": [
        {"name": "政府/公共部門", "confidence": 0.94, "evidence": "government and public sector clients"},
    ],
    "business_scenario": [
        {"name": "水處理設施監測", "confidence": 0.96, "evidence": "water treatment facilities"},
    ],
    "solution_domain": [
        {"name": "Digital Twin", "confidence": 0.95, "evidence": "AI and Digital Twin solutions"},
    ],
    "delivery_motion": [
        {"name": "POC 測試", "confidence": 0.93, "evidence": "Proof-Of-Concept (POC) tests"},
        {"name": "tender", "confidence": 0.9, "evidence": "tender preparation"},
    ],
    "compliance_standard": [
        {"name": "ISO 27001", "confidence": 0.98, "evidence": "such as ISO 27001"},
    ],
    "system_or_asset": [
        {"name": "sensors", "confidence": 0.94, "evidence": "recommending and specifying suitable sensors brands"},
    ],
}


def _names(dim):
    return {t["name"] for t in dim}


class TestCrossIndustryNormalization:
    def test_six_dimensions_present(self):
        out = postprocess_cross_industry_profile(GOV_RAW)
        assert set(out.keys()) == {
            "industry_context", "business_scenario", "solution_domain",
            "delivery_motion", "compliance_standard", "system_or_asset",
        }

    def test_sensor_alias_normalized(self):
        out = postprocess_cross_industry_profile(GOV_RAW)
        assert _names(out["system_or_asset"]) == {"傳感器"}

    def test_tender_alias_normalized(self):
        out = postprocess_cross_industry_profile(GOV_RAW)
        assert "投標" in _names(out["delivery_motion"])

    def test_empty_and_invalid(self):
        empty = postprocess_cross_industry_profile(None)
        assert all(v == [] for v in empty.values())
        assert postprocess_cross_industry_profile({})["industry_context"] == []


class TestSummaryTags:
    def test_gov_summary_triggered(self):
        out = postprocess_cross_industry_profile(GOV_RAW)
        summary = build_summary_tags(out)
        names = {s["name"] for s in summary}
        assert "政府公用事業 AI/Digital Twin 售前解決方案" in names

    def test_summary_has_multiple_supporting_dimensions(self):
        out = postprocess_cross_industry_profile(GOV_RAW)
        gov = next(s for s in build_summary_tags(out) if s["name"].startswith("政府公用事業"))
        assert len(gov["supporting_dimensions"]) >= 2

    def test_single_dimension_does_not_trigger(self):
        solo = postprocess_cross_industry_profile(
            {"industry_context": [{"name": "政府/公共部門", "confidence": 0.9, "evidence": "government"}]}
        )
        assert build_summary_tags(solo) == []

    def test_retail_erp_summary(self):
        raw = {
            "industry_context": [{"name": "零售/電商", "confidence": 0.9, "evidence": "retail e-commerce client"}],
            "solution_domain": [{"name": "D365 ERP", "confidence": 0.92, "evidence": "Dynamics 365 ERP integration"}],
            "business_scenario": [{"name": "訂單管理", "confidence": 0.88, "evidence": "order management and promotion"}],
        }
        names = {s["name"] for s in build_summary_tags(postprocess_cross_industry_profile(raw))}
        assert "零售/電商 ERP 系統集成" in names


class TestContextDisambiguation:
    def test_payment_banking_to_finance(self):
        raw = {"business_scenario": [
            {"name": "支付", "confidence": 0.8, "evidence": "payment gateway for banking and KYC"},
        ]}
        out = postprocess_cross_industry_profile(raw)
        assert _names(out["business_scenario"]) == {"金融/金融科技業務"}

    def test_payment_order_to_ecommerce(self):
        raw = {"business_scenario": [
            {"name": "支付", "confidence": 0.8, "evidence": "payments, promotions, order management"},
        ]}
        out = postprocess_cross_industry_profile(raw)
        assert _names(out["business_scenario"]) == {"電商/零售業務"}

    def test_insurance_benefit_dropped(self):
        raw = {"industry_context": [
            {"name": "保險業務", "confidence": 0.8, "evidence": "medical and life insurance coverage"},
        ]}
        out = postprocess_cross_industry_profile(raw)
        assert out["industry_context"] == []

    def test_sensor_machinery_to_monitoring(self):
        raw = {"business_scenario": [
            {"name": "傳感器應用", "confidence": 0.9,
             "evidence": "sensors tracking physical condition of machinery at water treatment"},
        ]}
        out = postprocess_cross_industry_profile(raw)
        assert _names(out["business_scenario"]) == {"設備狀態監測"}
