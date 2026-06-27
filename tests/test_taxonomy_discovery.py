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
