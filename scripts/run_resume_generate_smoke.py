from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.resume_agent.generator_graph import run_resume_generator
from src.resume_agent.generator_models import ResumeGenerateRequest
from src.resume_agent.pdf_parser import extract_resume_text_from_pdf

pdf_path = Path(r"D:\Users\c4018\Desktop\简历CV.pdf")
print(f"PDF_EXISTS={pdf_path.exists()} PATH={pdf_path}")
text = extract_resume_text_from_pdf(pdf_path.read_bytes())
print(f"EXTRACTED_CHARS={len(text)}")
request = ResumeGenerateRequest(
    resume_text=text,
    target_role="AI Engineer",
    target_market="Hong Kong",
    language="en",
    style="professional",
    narrative_angle="ai",
    top_k_jobs=8,
)
result = run_resume_generator(request)
print(f"SUCCESS={result.get('success')}")
print(f"CONFIDENCE={result.get('confidence')}")
q = result.get("quality_gate") or {}
print(f"QUALITY_STATUS={q.get('status')}")
print(f"P0_COUNT={len(q.get('p0_violations') or [])}")
print(f"P1_COUNT={len(q.get('p1_gaps') or [])}")
target = result.get("target_job_profile") or {}
print(f"TARGET_SAMPLE_COUNT={target.get('sample_count')}")
print(f"TARGET_CONFIDENCE={target.get('confidence')}")
print(f"TARGET_CORE_CAPS={target.get('core_capabilities')}")
print(f"TARGET_TECH_STACK={len(target.get('tech_stack') or [])} groups")
print(f"TARGET_HIDDEN_REQS={len(target.get('hidden_requirements') or [])}")
print(f"CAPABILITY_MATCHES={len(result.get('capability_matches') or [])}")
plan = result.get("selected_experience_plan") or {}
print(f"SELECTED_COUNT={len(plan.get('selected') or [])}")
selected = plan.get("selected") or []
kb_count = sum(1 for s in selected if s.get("source_type") == "knowledge_base")
print(f"SELECTED_KB_COUNT={kb_count}")
print(f"EXCLUDED_COUNT={len(plan.get('excluded') or [])}")
print(f"CONFIRMATION_COUNT={len(plan.get('user_confirmation_required') or [])}")
print(f"MARKDOWN_CHARS={len(result.get('markdown') or '')}")
print("MARKDOWN_PREVIEW_START")
preview = (result.get("markdown") or "")[:1200].encode("ascii", "backslashreplace").decode("ascii")
print(preview)
print("MARKDOWN_PREVIEW_END")
if result.get("error"):
    print(f"ERROR={result.get('error')}")

