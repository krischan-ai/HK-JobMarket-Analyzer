"""重新清洗数据并翻译地点"""
import sys, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.cleaner.pipeline import CleaningPipeline
from src.analyzer.rule_engine import RuleBasedSkillExtractor
from src.storage.csv_exporter import CSVExporter

with open("data/raw/it_jobs_raw.json", encoding="utf-8") as f:
    raw = json.load(f)

print(f"Loaded {len(raw)} raw jobs")

pipeline = CleaningPipeline()
extractor = RuleBasedSkillExtractor()
cleaned = pipeline.clean_batch(raw)
analyzed = extractor.analyze_batch(cleaned)

exporter = CSVExporter(output_dir="data/cleaned")
csv_path = exporter.export(analyzed, "jobs.csv")
print(f"Exported: {csv_path}")

import pandas as pd
df = pd.read_csv(csv_path, encoding="utf-8-sig")
print(f"\nLocations after translation:")
for loc, cnt in df["location"].value_counts().items():
    print(f"  {cnt:3d} x {loc}")
