#!/bin/bash
set -e

uvicorn api.main:app --host 0.0.0.0 --port 8000 --log-level info &
streamlit run src/app.py --server.port 8501 --server.address 0.0.0.0 &
nginx -g "daemon off;"
