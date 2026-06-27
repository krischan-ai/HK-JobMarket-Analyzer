"""Taxonomy Discovery Agent（v1.5 第一期：候选发现 + 缓存沉淀，doc §11.11）

职责边界（§11.11.7）：发现、归并、暂存。
- 第一期不自行调用 LLM，只消费角色分类 LLM 返回的 `candidate_taxonomy_updates` /
  `candidate_alias_updates`（已写入 role_cache 每条记录的 `taxonomy_candidates`）。
- 汇总后只写入候选池 `data/taxonomy/taxonomy_candidates.json` 与审计日志，
  绝不写入正式词库、不进入核心技术/趋势榜单。
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.analyzer import skill_taxonomy as tax
from src.logger import get_logger

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

_MAX_NAME_CHARS = 40
_MAX_NAME_WORDS = 6
_MIN_CONFIDENCE = 0.6
_MAX_EVIDENCE_SAMPLES = 5
_MAX_SOURCE_JOBS = 50


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _coerce_confidence(value: Any, default: float = 0.8) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return default


class TaxonomyDiscoveryAgent:
    def __init__(self, taxonomy_dir: Path | None = None):
        self.logger = get_logger(self.__class__.__name__)
        self.taxonomy_dir = Path(taxonomy_dir) if taxonomy_dir else (DATA_DIR / "taxonomy")
        self.candidates_path = self.taxonomy_dir / "taxonomy_candidates.json"
        self.log_path = self.taxonomy_dir / "taxonomy_discovery_log.jsonl"

    # ------------------------------------------------------------------ #
    # 已知词库快照
    # ------------------------------------------------------------------ #
    def known_snapshot(self) -> set[str]:
        """正式词库标签（小写）集合，用于候选去重。"""
        return {label.lower() for label in tax.compact_known_labels()}

    # ------------------------------------------------------------------ #
    # 单候选校验
    # ------------------------------------------------------------------ #
    def validate_candidate(self, candidate: Any, known: set[str]) -> dict | None:
        """过滤低质量候选；返回规整候选或 None（丢弃）。"""
        if not isinstance(candidate, dict):
            return None
        name = str(candidate.get("name", "")).strip()
        evidence = str(candidate.get("evidence", "") or "").strip()
        if not name or not evidence:
            return None
        # 已在正式词库
        if name.lower() in known:
            return None
        # 名称过长（疑似整句而非可复用标签）
        if len(name) > _MAX_NAME_CHARS or len(name.split()) > _MAX_NAME_WORDS:
            return None
        # 福利/地点/公司介绍语境
        ev_low = evidence.lower()
        if any(w in ev_low for w in tax.BENEFIT_CONTEXT_WORDS) and not self._has_industry_signal(ev_low):
            return None
        req_level = str(candidate.get("requirement_level", "") or "").strip().lower()
        if req_level == "inferred":
            return None
        confidence = _coerce_confidence(candidate.get("confidence"))
        if confidence < _MIN_CONFIDENCE:
            return None
        aliases = candidate.get("aliases", [])
        aliases = [str(a).strip() for a in aliases if str(a).strip()] if isinstance(aliases, list) else []
        return {
            "name": name,
            "category": str(candidate.get("category", "") or "other").strip(),
            "aliases": aliases,
            "evidence": evidence[:160],
            "reason": str(candidate.get("reason", "") or "").strip()[:200],
            "confidence": round(confidence, 2),
            "requirement_level": req_level,
            "status": "candidate",
        }

    @staticmethod
    def _has_industry_signal(ev: str) -> bool:
        signals = (
            "industry", "sector", "business", "client", "customer", "domain",
            "government", "public sector", "utility", "water treatment", "erp",
            "行業", "業務", "客戶", "政府",
        )
        return any(s in ev for s in signals)

    # ------------------------------------------------------------------ #
    # 单岗位处理（薄封装，供测试/未来使用）
    # ------------------------------------------------------------------ #
    def process_job(self, job: dict, role_result: Any, snapshot: set[str] | None = None) -> list[dict]:
        known = snapshot if snapshot is not None else self.known_snapshot()
        raw = getattr(role_result, "taxonomy_candidates", None) or []
        job_id = str(job.get("job_id", "") or "")
        out: list[dict] = []
        for cand in raw:
            validated = self.validate_candidate(cand, known)
            if validated:
                validated["source_job_id"] = job_id
                out.append(validated)
        return out

    # ------------------------------------------------------------------ #
    # 批量汇总（主线程，§11.11.5）
    # ------------------------------------------------------------------ #
    def consolidate_candidates(self, role_cache: dict) -> dict:
        known = self.known_snapshot()

        # 1. 收集本次运行全部已校验候选
        collected: dict[str, dict] = {}  # name_lower -> 聚合中间体
        if isinstance(role_cache, dict):
            for entry in role_cache.values():
                if not isinstance(entry, dict):
                    continue
                job_id = str(entry.get("_job_id", "") or "")
                for cand in entry.get("taxonomy_candidates", []) or []:
                    validated = self.validate_candidate(cand, known)
                    if not validated:
                        continue
                    key = validated["name"].lower()
                    agg = collected.setdefault(key, {
                        "name": validated["name"], "category": validated["category"],
                        "aliases": set(), "source_job_ids": set(),
                        "evidence_samples": [], "confidences": [],
                    })
                    agg["aliases"].update(validated["aliases"])
                    if job_id:
                        agg["source_job_ids"].add(job_id)
                    if validated["evidence"] and validated["evidence"] not in agg["evidence_samples"]:
                        agg["evidence_samples"].append(validated["evidence"])
                    agg["confidences"].append(validated["confidence"])

        # 2. 与已有候选池累积合并
        existing = self._load_candidates()
        existing_by_key = {c["name"].lower(): c for c in existing if isinstance(c, dict) and c.get("name")}
        now = _now_iso()
        new_count = 0
        updated_count = 0
        log_lines: list[dict] = []

        for key, agg in collected.items():
            new_confs = agg["confidences"]
            new_avg = round(sum(new_confs) / len(new_confs), 2) if new_confs else 0.0
            prev = existing_by_key.get(key)
            if prev is None:
                record = {
                    "name": agg["name"],
                    "category": agg["category"],
                    "aliases": sorted(agg["aliases"]),
                    "first_seen_at": now,
                    "last_seen_at": now,
                    "support_count": len(agg["source_job_ids"]),
                    "source_job_ids": sorted(agg["source_job_ids"])[:_MAX_SOURCE_JOBS],
                    "evidence_samples": agg["evidence_samples"][:_MAX_EVIDENCE_SAMPLES],
                    "confidence_avg": new_avg,
                    "status": "candidate",
                }
                existing_by_key[key] = record
                new_count += 1
            else:
                merged_jobs = set(prev.get("source_job_ids", [])) | agg["source_job_ids"]
                merged_aliases = set(prev.get("aliases", [])) | agg["aliases"]
                merged_evidence = list(dict.fromkeys(
                    list(prev.get("evidence_samples", [])) + agg["evidence_samples"]
                ))[:_MAX_EVIDENCE_SAMPLES]
                prev_avg = float(prev.get("confidence_avg", 0.0) or 0.0)
                combined_avg = round((prev_avg + new_avg) / 2, 2) if prev_avg else new_avg
                prev.update({
                    "category": prev.get("category") or agg["category"],
                    "aliases": sorted(merged_aliases),
                    "last_seen_at": now,
                    "support_count": len(merged_jobs),
                    "source_job_ids": sorted(merged_jobs)[:_MAX_SOURCE_JOBS],
                    "evidence_samples": merged_evidence,
                    "confidence_avg": combined_avg,
                    "status": "candidate",
                })
                updated_count += 1
            log_lines.append({
                "ts": now, "name": agg["name"], "category": agg["category"],
                "support_count": len(agg["source_job_ids"]),
                "evidence": agg["evidence_samples"][0] if agg["evidence_samples"] else "",
            })

        # 3. 写回（原子）+ 追加日志
        merged_list = sorted(existing_by_key.values(), key=lambda c: c.get("support_count", 0), reverse=True)
        if collected:
            self._write_candidates(merged_list)
            self._append_log(log_lines)

        summary = {"total_candidates": len(merged_list), "new": new_count, "updated": updated_count}
        self.logger.info(
            "Taxonomy consolidation: %d new, %d updated, %d total candidates",
            new_count, updated_count, len(merged_list),
        )
        return summary

    # ------------------------------------------------------------------ #
    # 文件 I/O
    # ------------------------------------------------------------------ #
    def _load_candidates(self) -> list[dict]:
        if not self.candidates_path.exists():
            return []
        try:
            with open(self.candidates_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except (OSError, json.JSONDecodeError):
            return []

    def _write_candidates(self, candidates: list[dict]) -> None:
        self.taxonomy_dir.mkdir(parents=True, exist_ok=True)
        tmp = self.candidates_path.with_suffix(".json.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(candidates, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.candidates_path)

    def _append_log(self, lines: list[dict]) -> None:
        if not lines:
            return
        self.taxonomy_dir.mkdir(parents=True, exist_ok=True)
        with open(self.log_path, "a", encoding="utf-8") as f:
            for line in lines:
                f.write(json.dumps(line, ensure_ascii=False) + "\n")
