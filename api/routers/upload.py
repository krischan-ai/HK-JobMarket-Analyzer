from fastapi import APIRouter, UploadFile, File, Form, Query
from pathlib import Path
import json
import tempfile
import os

router = APIRouter(prefix="/api/upload", tags=["upload"])


@router.post("/file")
async def upload_file(
    file: UploadFile = File(...),
    source_tag: str = Form(default="user_upload"),
    run_cleaning: bool = Form(default=True),
    run_extraction: bool = Form(default=True),
):
    allowed = {".csv", ".json", ".xlsx"}
    ext = Path(file.filename or "").suffix.lower()
    if ext not in allowed:
        return {"total": 0, "success": 0, "skipped": 0, "new_records": 0, "updated_records": 0, "errors": [f"不支持的文件格式: {ext}"], "duration_ms": 0}

    content = await file.read()

    try:
        if ext == ".json":
            data = json.loads(content.decode("utf-8"))
            if isinstance(data, dict):
                data = [data]
        elif ext == ".csv":
            import pandas as pd
            import io
            df = pd.read_csv(io.BytesIO(content), encoding="utf-8-sig")
            data = df.to_dict(orient="records")
        else:
            import pandas as pd
            import io
            df = pd.read_excel(io.BytesIO(content))
            data = df.to_dict(orient="records")
    except Exception as e:
        return {"total": 0, "success": 0, "skipped": 0, "new_records": 0, "updated_records": 0, "errors": [f"文件解析失败: {str(e)}"], "duration_ms": 0}

    import time
    t0 = time.time()

    try:
        cleaned = []
        if run_cleaning:
            from src.cleaner.pipeline import CleaningPipeline
            pipeline = CleaningPipeline()
            cleaning_input = []
            for i, r in enumerate(data):
                cleaning_input.append({
                    "job_id": r.get("job_id") or r.get("id") or f"upload_{i}",
                    "title": r.get("title", ""),
                    "company": r.get("company", ""),
                    "location": r.get("location", ""),
                    "salary_raw": r.get("salary_raw") or r.get("salary", ""),
                    "jd_raw": r.get("jd_raw") or r.get("description", ""),
                    "source": source_tag,
                })
            cleaned = pipeline.clean_batch(cleaning_input)
        else:
            cleaned = data

        if run_extraction:
            from src.analyzer.rule_engine import RuleBasedSkillExtractor
            extractor = RuleBasedSkillExtractor()
            cleaned = extractor.analyze_batch(cleaned, text_field="jd_text")

        elapsed = (time.time() - t0) * 1000
        return {
            "total": len(data),
            "success": len(cleaned),
            "skipped": len(data) - len(cleaned),
            "new_records": len(cleaned),
            "updated_records": 0,
            "errors": [],
            "duration_ms": round(elapsed, 1),
        }
    except Exception as e:
        elapsed = (time.time() - t0) * 1000
        return {"total": len(data), "success": 0, "skipped": len(data), "new_records": 0, "updated_records": 0, "errors": [str(e)], "duration_ms": round(elapsed, 1)}


@router.get("/formats")
def supported_formats():
    return {
        "formats": [".csv", ".json", ".xlsx"],
        "max_file_size_mb": 50,
        "max_rows": 10000,
    }
