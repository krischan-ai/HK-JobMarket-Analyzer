import pandas as pd
from pathlib import Path
from functools import lru_cache

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "cleaned"


@lru_cache(maxsize=1)
def load_jobs_df() -> pd.DataFrame:
    csv_path = DATA_DIR / "jobs.csv"
    if csv_path.exists():
        df = pd.read_csv(csv_path, encoding="utf-8-sig")
        if "skills" in df.columns:
            import json
            df["skills"] = df["skills"].apply(lambda x: json.loads(x.replace("'", '"')) if isinstance(x, str) else x)
        return df
    return pd.DataFrame()


def load_skills_df() -> pd.DataFrame:
    df = load_jobs_df()
    if df.empty or "skills" not in df.columns:
        return pd.DataFrame()
    records = []
    for _, row in df.dropna(subset=["skills"]).iterrows():
        skills = row["skills"]
        if isinstance(skills, dict):
            for category, skill_list in skills.items():
                if isinstance(skill_list, list):
                    for skill in skill_list:
                        records.append({"skill": skill, "category": category, "job_id": row.get("job_id")})
    return pd.DataFrame(records)
