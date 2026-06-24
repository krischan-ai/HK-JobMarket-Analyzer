"""探针：验证 /polish-stream 是否按事件增量 flush（而非跑完才返回）。

只看前几个事件的到达时刻：input_health 在任何 LLM 调用前就被 yield，
若它在 ~0s 到达，说明 HTTP 流式逐事件 flush 正常；matched_jobs 约 30s。
收到 job_research 或超过 90s 即停止。
"""
from __future__ import annotations

import json
import os
import time

import requests

PORT = os.environ.get("PROBE_PORT", "8011")
URL = f"http://127.0.0.1:{PORT}/api/resume/polish-stream"
BODY = {"resume_text": "Backend developer with Python and FastAPI experience building APIs. " * 2, "jd_text": ""}

start = time.time()
tokens = 0
first_token_t = None
with requests.post(URL, json=BODY, stream=True, timeout=600, proxies={"http": None, "https": None}) as resp:
    print(f"status={resp.status_code}", flush=True)
    for raw in resp.iter_lines(decode_unicode=True):
        if not raw or not raw.startswith("data:"):
            continue
        ev = json.loads(raw[5:].strip())
        t = time.time() - start
        stage = ev.get("stage")
        if stage == "token":
            tokens += 1
            if first_token_t is None:
                first_token_t = t
                print(f"{t:6.2f}s  [first token] step={ev.get('step')} delta={ev.get('delta')!r}", flush=True)
            continue
        print(f"{t:6.2f}s  stage={stage}  {ev.get('step') or ev.get('message') or ''}  (tokens so far={tokens})", flush=True)
        if stage in ("matched_jobs",) and tokens > 0:
            print(f"--- parse_resume streamed {tokens} tokens, first at {first_token_t:.2f}s; stopping ---", flush=True)
            break
        if t > 120:
            print("--- timeout stop ---", flush=True)
            break
