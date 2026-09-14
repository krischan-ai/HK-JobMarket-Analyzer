# HK Job Market Analyzer

Hong Kong technology-job intelligence platform for automated collection, normalization, NLP/LLM extraction, search, and interactive market analysis.

> **Portfolio focus:** applied data engineering, web automation, NLP/LLM pipelines, backend APIs, and full-stack analytics.

## Why this project

Hong Kong technology job data is fragmented across multiple platforms, mixes English and Chinese, and expresses roles, skills, and salary information inconsistently. This project turns that unstructured market data into a searchable and analyzable dataset for understanding technology demand, role distribution, skills, and salary signals.

## What it demonstrates

| Area | Implementation |
| --- | --- |
| Data acquisition | Multi-source collection with REST-based ingestion and Playwright for dynamic pages |
| Data engineering | Cleaning, normalization, field mapping, salary standardization, import pipelines |
| NLP / LLM | Keyword and LLM-assisted extraction/classification for roles and technology requirements |
| Knowledge layer | Searchable knowledge-base workflow with vector-storage support |
| Backend | FastAPI APIs for data, analysis, configuration, and knowledge-base operations |
| Frontend | Vue 3 + TypeScript dashboard with interactive analytics and visualization |
| Deployment | Docker, Docker Compose, Nginx, environment-based configuration, CI-oriented testing |

## Architecture

```text
Job Platforms
    ↓
REST / Playwright Collectors
    ↓
Cleaning & Normalization
    ↓
Structured Job Dataset
    ├── Keyword / Rule Extraction
    ├── LLM Classification & Extraction
    └── Knowledge / Vector Search
    ↓
FastAPI Service Layer
    ↓
Vue 3 + TypeScript Dashboard
    ↓
Technology Demand · Salary · Role · Market Analysis
```

## Engineering highlights

- Built a pipeline that separates acquisition, normalization, extraction, storage, API, and presentation concerns.
- Supports both deterministic keyword-based analysis and LLM-assisted extraction rather than depending on a single opaque model path.
- Handles Hong Kong job-market specifics such as mixed-language descriptions and non-uniform salary formats.
- Provides a full-stack path from scraping and structured ingestion through FastAPI services to a Vue analytics interface.
- Includes Docker-based deployment assets and automated test configuration for repeatable local development.

## Tech stack

**Python · Playwright · FastAPI · NLP / LLM · Vector Search · Vue 3 · TypeScript · ECharts · Docker · Nginx**

## Repository map

```text
api/                 Backend API services
config/              Runtime and application configuration
data/                Data assets and processing outputs
doc/                 Project documentation
Dockerfile           Container build
docker-compose.yml   Multi-service deployment
nginx.conf           Reverse-proxy configuration
pytest.ini            Test configuration
```

## Quick start

Review `.env.example` first, then use the repository's Docker configuration for the most reproducible setup:

```bash
docker compose up --build
```

For component-level development, see the complete technical specification for environment details, data-source setup, API endpoints, frontend structure, milestones, and validation notes.

## Documentation

- [Full technical specification](./docs/TECHNICAL_SPEC.md) — the original complete design and implementation document.
- [`doc/`](./doc) — supporting design and development documentation.
- [`.env.example`](./.env.example) — configuration reference.

## Project status

This repository contains a working multi-stage engineering implementation spanning collection, data processing, NLP/LLM analysis, backend APIs, frontend analytics, deployment, and testing. The full technical document records the project's detailed milestones and implementation history.

---

**Use this README for a fast engineering overview; use [`docs/TECHNICAL_SPEC.md`](./docs/TECHNICAL_SPEC.md) for the complete design record.**
