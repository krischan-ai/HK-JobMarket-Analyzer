import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.config import app
from api.routers import system, jobs, stats, upload, knowledge, llm, role_stats, crawler, scheduler, resume

app.include_router(system.router)
app.include_router(jobs.router)
app.include_router(stats.router)
app.include_router(upload.router)
app.include_router(knowledge.router)
app.include_router(llm.router)
app.include_router(role_stats.router)
app.include_router(crawler.router)
app.include_router(scheduler.router)
app.include_router(resume.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
