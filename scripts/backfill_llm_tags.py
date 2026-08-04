"""一次性 LLM 标签回填脚本（doc：JD 标签分类验收方案）。

为什么需要：role_cache.json 历史上整批由规则引擎生成（source=rules），
tag_profile / cross_industry_profile / summary_tags 几乎全空。本脚本用 LLM
对 data/cleaned/jobs.csv 全量重算，写回 role_cache.json。

设计要点：
- 受控并发（4 worker）+ 90s 超时，避免供应商端排队导致整批 Read timeout
  后静默降级到规则引擎（30s + 8 并发时几乎 100% 降级）。
- 缓存键与 api/routers/role_stats.py::_do_classify 完全一致
  （classify_text = jd_raw if len>20 else title），保证 API 能命中。
- 增量写盘：每完成一条即覆盖该键并周期性 save，任何读取方读到的都是
  旧值或新值，不会出现空缓存/加载中状态。
"""
from __future__ import annotations

import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402

from src.analyzer.role_classifier import RoleClassifier  # noqa: E402

WORKERS = 4
TIMEOUT = 90


def _entry_from_result(res) -> dict:
    return {
        "role_id": res.role_id,
        "role_name": res.role_name,
        "confidence": res.confidence,
        "soft_skills": res.soft_skills,
        "tag_profile": res.tag_profile,
        "cross_industry_profile": res.cross_industry_profile,
        "job_context_profile": res.job_context_profile,
        "taxonomy_candidates": res.taxonomy_candidates,
    }


def main() -> None:
    df = pd.read_csv(ROOT / "data" / "cleaned" / "jobs.csv")
    jobs = df.to_dict(orient="records")
    total = len(jobs)
    print(f"loaded {total} jobs")

    clf = RoleClassifier(timeout=TIMEOUT)
    if not clf.available:
        print("LLM not configured (api_key/api_base missing). Aborting.")
        sys.exit(1)
    if not clf._quick_check():
        print("LLM quick check failed (API unreachable). Aborting.")
        sys.exit(1)

    cache_lock = Lock()
    done = [0]
    llm_ok = [0]
    fallback = [0]
    start = time.time()

    def work(job: dict):
        jd = str(job.get("jd_raw", "") or "")
        classify_text = jd if len(jd) > 20 else str(job.get("title", ""))
        key = clf._make_cache_key(classify_text)
        try:
            res = clf._classify_with_llm(classify_text)
        except Exception as e:  # noqa: BLE001
            return key, None, str(job.get("job_id", "")), f"EXC {type(e).__name__}"
        # 判断是否真的走了 LLM：tag 的 source 字段
        all_tags = res.tag_profile.get("technical", []) + res.tag_profile.get("non_technical", [])
        used_llm = any(t.get("source") == "llm" for t in all_tags)
        return key, res, str(job.get("job_id", "")), ("llm" if used_llm else "rules")

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = {pool.submit(work, j): j for j in jobs}
        for fut in as_completed(futures):
            key, res, job_id, status = fut.result()
            with cache_lock:
                if res is not None:
                    entry = _entry_from_result(res)
                    entry["_job_id"] = job_id
                    clf._cache[key] = entry
                done[0] += 1
                if status == "llm":
                    llm_ok[0] += 1
                elif status == "rules":
                    fallback[0] += 1
                # 每 10 条写一次盘
                if done[0] % 10 == 0 or done[0] == total:
                    clf._save_cache()
                    elapsed = time.time() - start
                    print(f"{done[0]}/{total}  llm={llm_ok[0]} fallback/rules={fallback[0]}  "
                          f"{elapsed:.0f}s  last={job_id}:{status}", flush=True)

    clf._save_cache()
    print(f"DONE in {time.time()-start:.0f}s  llm={llm_ok[0]} rules/fallback={fallback[0]}")

    # v1.5：汇总候选词库
    try:
        from src.analyzer.taxonomy_discovery_agent import TaxonomyDiscoveryAgent
        summary = TaxonomyDiscoveryAgent().consolidate_candidates(clf._cache)
        print("taxonomy candidates consolidated:", summary)
    except Exception as e:  # noqa: BLE001
        print("taxonomy consolidation skipped:", e)


if __name__ == "__main__":
    main()
