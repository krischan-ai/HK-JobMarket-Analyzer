"""v2.9 全链路端到端跑通脚本（真实 LLM + 知识库）。

用法：python scripts/run_resume_v29_e2e.py "<pdf_path>"
仅用于本地验证，不落盘简历内容。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

# 以脚本文件运行时，sys.path[0] 是 scripts/ 目录，需补上仓库根目录。
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.resume_agent.graph import run_resume_agent_stream
from src.resume_agent.pdf_parser import extract_resume_text_from_pdf


def main(pdf_path: str) -> None:
    with open(pdf_path, "rb") as fh:
        data = fh.read()
    resume_text = extract_resume_text_from_pdf(data)
    print(f"[PDF] extracted {len(resume_text)} chars", flush=True)

    start = time.time()
    final = None
    for ev in run_resume_agent_stream(resume_text=resume_text, jd_text=""):
        elapsed = time.time() - start
        stage = ev.get("stage")
        if stage == "status":
            print(f"  {elapsed:6.1f}s  · {ev.get('message')}", flush=True)
        elif stage == "input_health":
            h = ev.get("input_health") or {}
            print(f"{elapsed:6.1f}s [input_health] status={h.get('status')} "
                  f"resume={h.get('resume_status')} jd={h.get('jd_status')}", flush=True)
        elif stage == "matched_jobs":
            jobs = ev.get("matched_jobs") or []
            print(f"{elapsed:6.1f}s [matched_jobs] {len(jobs)} 条, rerank={ev.get('rerank_used')} :: "
                  + " | ".join(j.get("title", "") for j in jobs[:5]), flush=True)
        elif stage == "market_insights":
            mi = ev.get("market_insights") or {}
            roles = mi.get("role_demand_ranking") or []
            print(f"{elapsed:6.1f}s [market_insights] top roles: "
                  + ", ".join(f"{r.get('role_name')}({r.get('count')})" for r in roles[:3]), flush=True)
        elif stage == "jd":
            jd = ev.get("jd") or {}
            print(f"{elapsed:6.1f}s [jd] source={jd.get('source','jd')} role={jd.get('role_name')} "
                  f"required={(jd.get('required_skills') or [])[:6]}", flush=True)
        elif stage == "job_research":
            jr = ev.get("job_research") or {}
            print(f"{elapsed:6.1f}s [job_research] source={jr.get('source')} conf={jr.get('confidence')} "
                  f"samples={jr.get('sample_count')}", flush=True)
            print(f"           核心能力: {jr.get('core_capabilities')}", flush=True)
            print(f"           改写靶心: {jr.get('resume_positioning_advice')}", flush=True)
        elif stage == "gap":
            g = ev.get("gap_analysis") or {}
            print(f"{elapsed:6.1f}s [gap] missing={g.get('missing_skills')} weak={g.get('weak_skills')}", flush=True)
        elif stage == "polish":
            ps = ev.get("polish_suggestions") or []
            print(f"{elapsed:6.1f}s [polish] {len(ps)} 段 :: " + " | ".join(p.get("section", "") for p in ps), flush=True)
        elif stage == "score":
            sc = ev.get("score") or {}
            print(f"{elapsed:6.1f}s [score] overall={sc.get('overall_score')} :: {sc.get('overall_comment','')[:80]}", flush=True)
        elif stage == "interview_prep":
            bi = ev.get("bullet_inventory") or []
            print(f"{elapsed:6.1f}s [interview_prep] {len(bi)} 条 bullet", flush=True)
            for b in bi[:3]:
                print(f"           · [{b.get('evidence_confidence')}] {b.get('target_capability')}: "
                      f"{(b.get('talk_track_30s') or '')[:70]}", flush=True)
        elif stage == "done":
            final = ev.get("result")
            print(f"{elapsed:6.1f}s [done]", flush=True)
        elif stage == "error":
            print(f"{elapsed:6.1f}s [ERROR] {ev.get('error')}", flush=True)

    if final:
        print("\n===== FINAL SUMMARY =====", flush=True)
        print(f"polish segments : {len(final.get('polish_suggestions') or [])}", flush=True)
        print(f"bullet inventory: {len(final.get('bullet_inventory') or [])}", flush=True)
        jr = final.get("job_research") or {}
        print(f"job_research    : source={jr.get('source')} conf={jr.get('confidence')} samples={jr.get('sample_count')}", flush=True)
        sc = final.get("score") or {}
        print(f"score           : {sc.get('overall_score')}", flush=True)


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else r"D:\Users\c4018\Desktop\简历CV.pdf"
    main(path)
