"""Phase 1 快速调试验证"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.cleaner import CleaningPipeline
from src.analyzer import RuleBasedSkillExtractor
from src.visualization import TechTrendAnalyzer
from src.storage import CSVExporter
import pandas as pd

print("=== Module imports OK ===")

jobs = [
    {"job_id": "1", "jd_raw": "<p>Python <b>AWS</b></p>", "salary_raw": "HK$45000 - HK$60000 /month"},
    {"job_id": "2", "jd_raw": "React TypeScript AWS Docker", "salary_raw": "HK$600000 - HK$720000 per annum"},
]
print(f"Test jobs: {len(jobs)}")

pipe = CleaningPipeline()
cleaned = pipe.clean_batch(jobs)
assert len(cleaned) == 2
assert "jd_text" in cleaned[0]
assert cleaned[0]["salary_min"] == 45000
print(f"Cleaning OK: salary_min={cleaned[0]['salary_min']}, text={cleaned[0]['jd_text'][:30]}")

assert cleaned[1]["salary_min"] == 50000, f"Expected 50000, got {cleaned[1]['salary_min']}"
print(f"Annual salary OK: {cleaned[1]['salary_min']}")

ext = RuleBasedSkillExtractor()
analyzed = ext.analyze_batch(cleaned)
assert "Python" in analyzed[0]["skills"]["programming_languages"]
assert "Aws" in analyzed[0]["skills"]["cloud_devops"]
assert "React" in analyzed[1]["skills"]["frameworks_libraries"]
print(f"Analysis OK: skills={analyzed[0]['skills']}")

exporter = CSVExporter(output_dir="data/cleaned")
path = exporter.export(analyzed, "test_verify.csv")
print(f"Export OK: {path}")

df = pd.DataFrame(analyzed)
viz = TechTrendAnalyzer(df, output_dir="output/debug_charts")
charts = viz.generate_all_charts()
for k, v in charts.items():
    print(f"  Chart [{k}]: {v}")
print("=== ALL PHASE 1 TESTS PASSED ===")
