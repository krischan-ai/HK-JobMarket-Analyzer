"""合并 Indeed + JobsDB 数据，清洗后导出"""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.cleaner.pipeline import CleaningPipeline
from src.analyzer.rule_engine import RuleBasedSkillExtractor
from src.storage.csv_exporter import CSVExporter

RAW_DIR = Path("data/raw")

# 加载所有来源
all_jobs = []

indeed_path = RAW_DIR / "it_jobs_raw.json"
if indeed_path.exists():
    indeed = json.loads(indeed_path.read_text(encoding="utf-8"))
    print(f"Indeed: {len(indeed)} jobs")
    all_jobs.extend(indeed)

jobsdb_path = RAW_DIR / "jobsdb_raw.json"
if jobsdb_path.exists():
    jobsdb = json.loads(jobsdb_path.read_text(encoding="utf-8"))
    print(f"JobsDB: {len(jobsdb)} jobs")
    all_jobs.extend(jobsdb)

# 去重
seen = set()
unique = []
for j in all_jobs:
    key = (j["title"].lower().strip(), j["company"].lower().strip(), j.get("source", ""))
    if key not in seen:
        seen.add(key)
        unique.append(j)

print(f"\nTotal: {len(all_jobs)} raw -> {len(unique)} unique")

# 清洗
pipeline = CleaningPipeline()
extractor = RuleBasedSkillExtractor()
cleaned = pipeline.clean_batch(unique)
analyzed = extractor.analyze_batch(cleaned)

# 导出
exporter = CSVExporter(output_dir="data/cleaned")
csv_path = exporter.export(analyzed, "jobs.csv")
print(f"Exported: {csv_path}")

# 统计
sources = {}
for j in analyzed:
    s = j.get("source", "unknown")
    sources[s] = sources.get(s, 0) + 1
print(f"\nBy source:")
for s, c in sorted(sources.items()):
    print(f"  {s}: {c}")

# 存合并后的 JSON
RAW_DIR.mkdir(parents=True, exist_ok=True)
(RAW_DIR / "all_jobs.json").write_text(
    json.dumps(analyzed, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(f"\nSaved: {RAW_DIR / 'all_jobs.json'}")
