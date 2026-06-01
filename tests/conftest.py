from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


MOCK_JOBS = [
    {
        "job_id": "MOCK_001",
        "title": "Senior Python Developer",
        "company": "HK Fintech Ltd",
        "location": "Central",
        "salary_raw": "HK$45,000 - HK$60,000 /month",
        "jd_raw": "<p>We are looking for a senior Python developer with experience in <strong>Django</strong> and <strong>AWS</strong>. Knowledge of <strong>PostgreSQL</strong> and <strong>Docker</strong> is required.</p>",
        "source": "jobsdb",
    },
    {
        "job_id": "MOCK_002",
        "title": "Frontend Engineer (React)",
        "company": "Tech Corp HK",
        "location": "Quarry Bay",
        "salary_raw": "HK$600,000 - HK$720,000 per annum",
        "jd_raw": "We need a React expert with TypeScript experience. Familiar with Next.js and Tailwind CSS. Agile team player with strong communication skills.",
        "source": "jobsdb",
    },
    {
        "job_id": "MOCK_003",
        "title": "Data Scientist",
        "company": "AI Lab HK",
        "location": "Science Park",
        "salary_raw": "HK$50,000 - HK$80,000 /month",
        "jd_raw": "Looking for data scientist proficient in Python, TensorFlow, and PyTorch. Experience with Spark and Kafka is a plus.",
        "source": "jobsdb",
    },
    {
        "job_id": "MOCK_004",
        "title": "DevOps Engineer",
        "company": "Cloud Native HK",
        "location": "Kwai Chung",
        "salary_raw": "HK$40,000 - HK$65,000 /month",
        "jd_raw": "AWS certified DevOps engineer needed. Must know Kubernetes, Terraform, CI/CD pipelines.",
        "source": "jobsdb",
    },
    {
        "job_id": "MOCK_005",
        "title": "Java Spring Boot Developer",
        "company": "Banking Tech",
        "location": "Central",
        "salary_raw": "HK$480,000 - HK$600,000 per annum",
        "jd_raw": "Senior Java developer with Spring Boot expertise. Experience in MySQL, Redis, and microservices.",
        "source": "jobsdb",
    },
]


@pytest.fixture
def mock_jobs():
    return MOCK_JOBS


@pytest.fixture
def temp_dir(tmp_path):
    return tmp_path


@pytest.fixture
def sample_jd_text():
    return (
        "We are looking for a senior Python developer with experience in "
        "Django and AWS. Knowledge of PostgreSQL and Docker is required. "
        "Strong problem-solving and communication skills."
    )


@pytest.fixture
def sample_salaries():
    return [
        ("HK$45,000 - HK$60,000 /month", (45000.0, 60000.0)),
        ("HK$600,000 - HK$720,000 per annum", (50000.0, 60000.0)),
        ("HK$50,000 - HK$80,000 /month", (50000.0, 80000.0)),
        ("HK$25,000 up", (25000.0, None)),
        ("HK$30,000 /month", (30000.0, None)),
        ("", (None, None)),
    ]
