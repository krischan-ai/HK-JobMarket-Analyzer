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
        # v1.5 第二/三期（§11.11.4）：审核生命周期与晋升落地的持久化文件
        self.promoted_path = self.taxonomy_dir / "skill_taxonomy.json"
        self.aliases_path = self.taxonomy_dir / "taxonomy_aliases.json"
        self.rejections_path = self.taxonomy_dir / "taxonomy_rejections.json"

    # ------------------------------------------------------------------ #
    # 已知词库快照
    # ------------------------------------------------------------------ #
    def known_snapshot(self) -> set[str]:
        """已知标签（小写）集合，用于候选去重。

        包含：正式词库快照 + 已晋升标签（含别名）+ 已拒绝标签。
        已晋升标签纳入后，后续分类不再重复发现；已拒绝标签纳入后，同名候选不再回流。
        """
        known = {label.lower() for label in tax.compact_known_labels()}
        for rec in self.load_promoted():
            name = str(rec.get("name", "")).strip().lower()
            if name:
                known.add(name)
            for alias in rec.get("aliases", []) or []:
                a = str(alias).strip().lower()
                if a:
                    known.add(a)
        for rec in self.load_aliases():
            alias = str(rec.get("alias", "")).strip().lower()
            if alias:
                known.add(alias)
        for rec in self.load_rejections():
            name = str(rec.get("name", "")).strip().lower()
            if name:
                known.add(name)
        return known

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
    # 审核生命周期（v1.5 第二期，§11.11.6）
    # ------------------------------------------------------------------ #
    def review_overview(self) -> dict:
        """供管理页/趋势页消费：候选池、已晋升、已拒绝、别名的汇总视图。"""
        candidates = sorted(
            self.load_candidates(),
            key=lambda c: (c.get("support_count", 0), c.get("confidence_avg", 0.0)),
            reverse=True,
        )
        return {
            "candidates": candidates,
            "promoted": self.load_promoted(),
            "aliases": self.load_aliases(),
            "rejections": self.load_rejections(),
            "counts": {
                "candidates": len(candidates),
                "promoted": len(self.load_promoted()),
                "aliases": len(self.load_aliases()),
                "rejections": len(self.load_rejections()),
            },
        }

    def _pop_candidate(self, name: str) -> tuple[dict | None, list[dict]]:
        """从候选池移除并返回匹配候选（按名称小写匹配）。"""
        key = str(name or "").strip().lower()
        remaining: list[dict] = []
        found: dict | None = None
        for c in self.load_candidates():
            if found is None and str(c.get("name", "")).strip().lower() == key:
                found = c
            else:
                remaining.append(c)
        return found, remaining

    def confirm_candidate(self, name: str, by: str = "manual") -> dict:
        """人工确认：候选 → 正式词库（晋升 overlay），并移出候选池。"""
        found, remaining = self._pop_candidate(name)
        if found is None:
            return {"ok": False, "reason": "candidate_not_found", "name": name}
        promoted = self.load_promoted()
        if any(str(p.get("name", "")).strip().lower() == found["name"].lower() for p in promoted):
            self._write_candidates(remaining)
            return {"ok": True, "already_promoted": True, "name": found["name"]}
        promoted.append(self._to_promoted_record(found, promoted_by=by))
        self._write_json(self.promoted_path, promoted)
        self._write_candidates(remaining)
        self._append_log([{"ts": _now_iso(), "action": "confirm", "name": found["name"], "by": by}])
        self.logger.info("Taxonomy candidate confirmed: %s (by=%s)", found["name"], by)
        return {"ok": True, "name": found["name"], "promoted_total": len(promoted)}

    def reject_candidate(self, name: str, reason: str = "") -> dict:
        """人工拒绝：候选 → 拒绝列表（永久抑制），并移出候选池。"""
        found, remaining = self._pop_candidate(name)
        target_name = found["name"] if found else str(name or "").strip()
        if not target_name:
            return {"ok": False, "reason": "empty_name"}
        rejections = self.load_rejections()
        if not any(str(r.get("name", "")).strip().lower() == target_name.lower() for r in rejections):
            rejections.append({
                "name": target_name,
                "category": found.get("category", "") if found else "",
                "reason": str(reason or "").strip()[:200],
                "rejected_at": _now_iso(),
            })
            self._write_json(self.rejections_path, rejections)
        self._write_candidates(remaining)
        self._append_log([{"ts": _now_iso(), "action": "reject", "name": target_name, "reason": reason}])
        self.logger.info("Taxonomy candidate rejected: %s", target_name)
        return {"ok": True, "name": target_name, "rejections_total": len(rejections)}

    def merge_alias(self, alias: str, canonical: str, category: str = "", evidence: str = "") -> dict:
        """合并别名：把候选/术语映射到正式标签，并移出同名候选池。"""
        alias = str(alias or "").strip()
        canonical = str(canonical or "").strip()
        if not alias or not canonical:
            return {"ok": False, "reason": "alias_and_canonical_required"}
        aliases = self.load_aliases()
        if not any(str(a.get("alias", "")).strip().lower() == alias.lower() for a in aliases):
            aliases.append({
                "alias": alias,
                "canonical": canonical,
                "category": str(category or "").strip(),
                "evidence": str(evidence or "").strip()[:160],
                "added_at": _now_iso(),
            })
            self._write_json(self.aliases_path, aliases)
        # 移出候选池中名称等于 alias 或 canonical 的候选
        _, remaining = self._pop_candidate(alias)
        remaining = [c for c in remaining if str(c.get("name", "")).strip().lower() != canonical.lower()]
        self._write_candidates(remaining)
        self._append_log([{"ts": _now_iso(), "action": "merge_alias", "alias": alias, "canonical": canonical}])
        self.logger.info("Taxonomy alias merged: %s -> %s", alias, canonical)
        return {"ok": True, "alias": alias, "canonical": canonical}

    @staticmethod
    def _to_promoted_record(candidate: dict, promoted_by: str) -> dict:
        return {
            "name": candidate["name"],
            "category": candidate.get("category", "other"),
            "aliases": list(candidate.get("aliases", []) or []),
            "support_count": int(candidate.get("support_count", 0) or 0),
            "confidence_avg": float(candidate.get("confidence_avg", 0.0) or 0.0),
            "source_job_ids": list(candidate.get("source_job_ids", []) or []),
            "promoted_at": _now_iso(),
            "promoted_by": promoted_by,
        }

    # ------------------------------------------------------------------ #
    # 自动晋升（v1.5 第三期，§11.11.6）
    # ------------------------------------------------------------------ #
    def promote_candidates(
        self,
        company_by_job: dict[str, str] | None = None,
        min_support: int = 3,
        min_companies: int = 2,
        min_confidence: float = 0.85,
        dry_run: bool = False,
    ) -> dict:
        """按 support_count / 公司数 / 平均置信度自动晋升低风险候选。

        晋升条件（全部满足）：
        - support_count >= min_support
        - 来自 >= min_companies 个不同公司（无 company_by_job 时退化为不同岗位数）
        - confidence_avg >= min_confidence
        - 不在拒绝列表
        candidate 池已在写入时过滤 inferred / 无证据，无需在此重复判断。
        """
        company_by_job = company_by_job or {}
        rejected = {str(r.get("name", "")).strip().lower() for r in self.load_rejections()}
        promoted = self.load_promoted()
        promoted_names = {str(p.get("name", "")).strip().lower() for p in promoted}

        eligible: list[dict] = []
        remaining: list[dict] = []
        for c in self.load_candidates():
            name_l = str(c.get("name", "")).strip().lower()
            jobs = c.get("source_job_ids", []) or []
            if company_by_job:
                companies = {company_by_job.get(j) for j in jobs if company_by_job.get(j)}
                company_count = len(companies)
            else:
                company_count = len(set(jobs))
            qualifies = (
                name_l
                and name_l not in rejected
                and name_l not in promoted_names
                and int(c.get("support_count", 0) or 0) >= min_support
                and company_count >= min_companies
                and float(c.get("confidence_avg", 0.0) or 0.0) >= min_confidence
            )
            if qualifies:
                rec = self._to_promoted_record(c, promoted_by="auto")
                rec["company_count"] = company_count
                eligible.append(rec)
            else:
                remaining.append(c)

        if dry_run:
            return {"ok": True, "dry_run": True, "eligible": eligible, "promoted_count": len(eligible)}

        if eligible:
            promoted.extend(eligible)
            self._write_json(self.promoted_path, promoted)
            self._write_candidates(remaining)
            self._append_log([
                {"ts": _now_iso(), "action": "auto_promote", "name": rec["name"],
                 "support_count": rec["support_count"], "company_count": rec.get("company_count")}
                for rec in eligible
            ])
            self.logger.info("Taxonomy auto-promotion: %d candidates promoted", len(eligible))
        return {"ok": True, "promoted_count": len(eligible),
                "promoted": [r["name"] for r in eligible], "promoted_total": len(promoted)}

    # ------------------------------------------------------------------ #
    # 文件 I/O
    # ------------------------------------------------------------------ #
    def load_candidates(self) -> list[dict]:
        return self._load_candidates()

    def load_promoted(self) -> list[dict]:
        return self._read_json_list(self.promoted_path)

    def load_aliases(self) -> list[dict]:
        return self._read_json_list(self.aliases_path)

    def load_rejections(self) -> list[dict]:
        return self._read_json_list(self.rejections_path)

    @staticmethod
    def _read_json_list(path: Path) -> list[dict]:
        if not path.exists():
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return [d for d in data if isinstance(d, dict)] if isinstance(data, list) else []
        except (OSError, json.JSONDecodeError):
            return []

    def _write_json(self, path: Path, data: list[dict]) -> None:
        self.taxonomy_dir.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)

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
