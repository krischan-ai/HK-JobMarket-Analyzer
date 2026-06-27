from __future__ import annotations

import json

import pytest

from src.analyzer.skill_taxonomy import compact_known_labels
from src.analyzer.taxonomy_discovery_agent import TaxonomyDiscoveryAgent


@pytest.fixture
def agent(tmp_path):
    return TaxonomyDiscoveryAgent(taxonomy_dir=tmp_path / "taxonomy")


class TestKnownLabels:
    def test_snapshot_non_empty_and_contains_known(self):
        labels = compact_known_labels()
        assert labels
        assert "傳感器" in labels


class TestValidateCandidate:
    def test_good_candidate_kept(self, agent):
        known = agent.known_snapshot()
        c = {"name": "水處理設施知識", "category": "domain_knowledge",
             "evidence": "water treatment facilities for government clients",
             "confidence": 0.96, "requirement_level": "required"}
        out = agent.validate_candidate(c, known)
        assert out is not None and out["name"] == "水處理設施知識"

    def test_no_evidence_dropped(self, agent):
        assert agent.validate_candidate({"name": "X", "evidence": ""}, set()) is None

    def test_known_label_dropped(self, agent):
        known = agent.known_snapshot()
        assert agent.validate_candidate({"name": "傳感器", "evidence": "sensors"}, known) is None

    def test_benefit_context_dropped(self, agent):
        c = {"name": "保險知識", "category": "domain_knowledge",
             "evidence": "medical and life insurance coverage", "confidence": 0.8}
        assert agent.validate_candidate(c, set()) is None

    def test_overlong_phrase_dropped(self, agent):
        c = {"name": "a very long descriptive sentence not a reusable label at all here",
             "evidence": "something", "confidence": 0.9}
        assert agent.validate_candidate(c, set()) is None

    def test_inferred_dropped(self, agent):
        c = {"name": "新場景", "evidence": "some evidence about industry",
             "confidence": 0.9, "requirement_level": "inferred"}
        assert agent.validate_candidate(c, set()) is None

    def test_low_confidence_dropped(self, agent):
        c = {"name": "新場景", "evidence": "industry evidence", "confidence": 0.4}
        assert agent.validate_candidate(c, set()) is None


def _cache(jobid, candidates):
    return {"taxonomy_candidates": candidates, "_job_id": jobid}


class TestConsolidate:
    def test_merge_same_name_across_jobs(self, agent):
        cache = {
            "k1": _cache("job1", [{"name": "水處理設施知識", "category": "domain_knowledge",
                                    "evidence": "water treatment facilities", "confidence": 0.96,
                                    "requirement_level": "required"}]),
            "k2": _cache("job2", [{"name": "水處理設施知識", "category": "domain_knowledge",
                                    "evidence": "water treatment plant design", "confidence": 0.9,
                                    "requirement_level": "required"}]),
        }
        summary = agent.consolidate_candidates(cache)
        assert summary["new"] == 1
        data = json.loads(agent.candidates_path.read_text(encoding="utf-8"))
        assert len(data) == 1
        rec = data[0]
        assert rec["support_count"] == 2
        assert set(rec["source_job_ids"]) == {"job1", "job2"}
        assert agent.log_path.exists()

    def test_second_run_accumulates_new_job(self, agent):
        cand = [{"name": "傳感器品牌指定", "category": "industrial_iot",
                 "evidence": "specifying suitable sensors brands", "confidence": 0.91,
                 "requirement_level": "required"}]
        agent.consolidate_candidates({"k1": _cache("job1", cand)})
        agent.consolidate_candidates({"k2": _cache("job2", cand)})
        data = json.loads(agent.candidates_path.read_text(encoding="utf-8"))
        rec = next(c for c in data if c["name"] == "傳感器品牌指定")
        assert rec["support_count"] == 2
        assert set(rec["source_job_ids"]) == {"job1", "job2"}

    def test_no_candidates_writes_nothing(self, agent):
        summary = agent.consolidate_candidates({"k1": _cache("job1", [])})
        assert summary["new"] == 0
        assert not agent.candidates_path.exists()


def _seed(agent, records):
    agent._write_candidates(records)


def _cand(name, support, conf, jobs, category="domain_knowledge"):
    return {"name": name, "category": category, "aliases": [],
            "support_count": support, "confidence_avg": conf,
            "source_job_ids": list(jobs), "evidence_samples": ["ev"]}


class TestReviewLifecycle:
    def test_confirm_moves_candidate_to_promoted(self, agent):
        _seed(agent, [_cand("水處理設施知識", 2, 0.9, ["j1", "j2"])])
        res = agent.confirm_candidate("水處理設施知識")
        assert res["ok"]
        assert [p["name"] for p in agent.load_promoted()] == ["水處理設施知識"]
        assert agent.load_candidates() == []
        # promoted label becomes known → filtered from future discovery
        assert "水處理設施知識".lower() in agent.known_snapshot()

    def test_reject_moves_to_rejections_and_suppresses(self, agent):
        _seed(agent, [_cand("誤判標籤", 5, 0.9, ["j1", "j2"])])
        res = agent.reject_candidate("誤判標籤", reason="福利語境")
        assert res["ok"]
        assert agent.load_candidates() == []
        assert [r["name"] for r in agent.load_rejections()] == ["誤判標籤"]
        assert "誤判標籤".lower() in agent.known_snapshot()

    def test_merge_alias_records_mapping(self, agent):
        _seed(agent, [_cand("POC", 2, 0.9, ["j1"])])
        res = agent.merge_alias("POC", "POC 測試", category="presales_delivery")
        assert res["ok"]
        aliases = agent.load_aliases()
        assert aliases and aliases[0]["canonical"] == "POC 測試"
        assert agent.load_candidates() == []

    def test_overview_counts(self, agent):
        _seed(agent, [_cand("A", 1, 0.9, ["j1"]), _cand("B", 2, 0.8, ["j1", "j2"])])
        ov = agent.review_overview()
        assert ov["counts"]["candidates"] == 2
        # sorted by support_count desc
        assert ov["candidates"][0]["name"] == "B"


class TestAutoPromotion:
    def test_promotes_only_qualifying(self, agent):
        _seed(agent, [
            _cand("合格標籤", 3, 0.9, ["j1", "j2", "j3"]),   # support3 / 2 companies / conf0.9
            _cand("支持不足", 1, 0.95, ["j1"]),               # support<3
            _cand("置信不足", 4, 0.6, ["j1", "j2", "j3", "j4"]),  # conf<0.85
        ])
        company = {"j1": "A", "j2": "B", "j3": "A", "j4": "B"}
        res = agent.promote_candidates(company_by_job=company)
        assert res["promoted_count"] == 1
        assert res["promoted"] == ["合格標籤"]
        assert {c["name"] for c in agent.load_candidates()} == {"支持不足", "置信不足"}

    def test_single_company_not_promoted(self, agent):
        _seed(agent, [_cand("同一公司", 3, 0.95, ["j1", "j2", "j3"])])
        company = {"j1": "A", "j2": "A", "j3": "A"}  # 3 jobs but 1 company
        res = agent.promote_candidates(company_by_job=company)
        assert res["promoted_count"] == 0
        assert agent.load_candidates()  # stays

    def test_rejected_name_not_promoted(self, agent):
        _seed(agent, [_cand("被拒標籤", 5, 0.95, ["j1", "j2", "j3"])])
        agent._write_json(agent.rejections_path, [{"name": "被拒標籤", "reason": "x"}])
        company = {"j1": "A", "j2": "B", "j3": "C"}
        res = agent.promote_candidates(company_by_job=company)
        assert res["promoted_count"] == 0

    def test_dry_run_does_not_write(self, agent):
        _seed(agent, [_cand("合格標籤", 3, 0.9, ["j1", "j2", "j3"])])
        company = {"j1": "A", "j2": "B", "j3": "C"}
        res = agent.promote_candidates(company_by_job=company, dry_run=True)
        assert res["dry_run"] and res["promoted_count"] == 1
        assert agent.load_promoted() == []  # nothing written
        assert agent.load_candidates()      # candidate retained

    def test_no_company_map_falls_back_to_job_count(self, agent):
        _seed(agent, [_cand("合格標籤", 3, 0.9, ["j1", "j2", "j3"])])
        res = agent.promote_candidates()  # no company map → distinct jobs as proxy
        assert res["promoted_count"] == 1
