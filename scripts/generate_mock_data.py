"""生成 Streamlit 看板所需的模拟数据"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.cleaner import CleaningPipeline
from src.analyzer import RuleBasedSkillExtractor
from src.storage import CSVExporter
import pandas as pd

mock_jobs = [
    {"job_id": "MOCK_001", "title": "Senior Python Developer", "company": "HK Fintech Ltd", "location": "Central", "salary_raw": "HK$45000 - HK$60000 /month", "jd_raw": "<p>Python <b>Django</b> <b>AWS</b>. PostgreSQL and Docker required.</p>", "source": "jobsdb"},
    {"job_id": "MOCK_002", "title": "Frontend Engineer (React)", "company": "Tech Corp HK", "location": "Quarry Bay", "salary_raw": "HK$600000 - HK$720000 per annum", "jd_raw": "React expert with TypeScript. Next.js and Tailwind CSS. Agile team player.", "source": "jobsdb"},
    {"job_id": "MOCK_003", "title": "Data Scientist", "company": "AI Lab HK", "location": "Science Park", "salary_raw": "HK$50000 - HK$80000 /month", "jd_raw": "Python TensorFlow PyTorch Spark Kafka. Strong analytical skills.", "source": "jobsdb"},
    {"job_id": "MOCK_004", "title": "DevOps Engineer", "company": "Cloud Native HK", "location": "Kwai Chung", "salary_raw": "HK$40000 - HK$65000 /month", "jd_raw": "AWS Kubernetes Terraform CI/CD Prometheus Grafana.", "source": "jobsdb"},
    {"job_id": "MOCK_005", "title": "Java Spring Boot Developer", "company": "Banking Tech", "location": "Central", "salary_raw": "HK$480000 - HK$600000 per annum", "jd_raw": "Java Spring Boot MySQL Redis microservices. Teamwork skills.", "source": "jobsdb"},
    {"job_id": "MOCK_006", "title": "Full Stack Engineer", "company": "Startup HK", "location": "Wong Chuk Hang", "salary_raw": "HK$35000 - HK$55000 /month", "jd_raw": "React Node.js MongoDB Docker AWS. Self-motivated.", "source": "jobsdb"},
    {"job_id": "MOCK_007", "title": "Mobile Developer (Flutter)", "company": "App Studio HK", "location": "Causeway Bay", "salary_raw": "HK$30000 - HK$50000 /month", "jd_raw": "Flutter Dart Firebase RESTful APIs. Team player.", "source": "jobsdb"},
    {"job_id": "MOCK_008", "title": "ML Engineer", "company": "AI Startup", "location": "Cyberport", "salary_raw": "HK$55000 - HK$75000 /month", "jd_raw": "ML engineer Python TensorFlow Kubernetes MLOps.", "source": "jobsdb"},
    {"job_id": "MOCK_009", "title": "Backend Engineer (Go)", "company": "Trading Firm", "location": "Central", "salary_raw": "HK$60000 - HK$90000 /month", "jd_raw": "Go distributed systems Kafka Redis. Cross-functional collaboration.", "source": "jobsdb"},
    {"job_id": "MOCK_010", "title": "Cloud Architect", "company": "MNC HK", "location": "Kowloon Bay", "salary_raw": "HK$80000 - HK$120000 /month", "jd_raw": "AWS ECS EKS Lambda RDS Terraform. Leadership skills.", "source": "jobsdb"},
    {"job_id": "MOCK_011", "title": "Data Engineer", "company": "Big Data Ltd", "location": "Hong Kong", "salary_raw": "HK$45000 - HK$70000 /month", "jd_raw": "Spark Airflow Snowflake Python SQL. Problem-solving.", "source": "jobsdb"},
    {"job_id": "MOCK_012", "title": "Security Engineer", "company": "CyberSec HK", "location": "Central", "salary_raw": "HK$50000 - HK$80000 /month", "jd_raw": "Cloud security AWS penetration testing. CISSP preferred.", "source": "jobsdb"},
    {"job_id": "MOCK_013", "title": "QA Engineer", "company": "Quality First", "location": "Tsim Sha Tsui", "salary_raw": "HK$30000 - HK$45000 /month", "jd_raw": "Selenium Cypress automated testing CI/CD. Analytical thinking.", "source": "jobsdb"},
    {"job_id": "MOCK_014", "title": "Product Manager (Tech)", "company": "Product Co", "location": "Wan Chai", "salary_raw": "HK$55000 - HK$75000 /month", "jd_raw": "Technical PM agile scrum SDLC. Communication and stakeholder management.", "source": "jobsdb"},
    {"job_id": "MOCK_015", "title": "System Administrator", "company": "IT Services HK", "location": "Shatin", "salary_raw": "HK$25000 - HK$40000 /month", "jd_raw": "Linux shell scripting nginx monitoring. Time management.", "source": "jobsdb"},
]

pipe = CleaningPipeline()
cleaned = pipe.clean_batch(mock_jobs)
ext = RuleBasedSkillExtractor()
analyzed = ext.analyze_batch(cleaned)

exporter = CSVExporter(output_dir="data/cleaned")
exporter.export(analyzed, "jobs.csv")

df = pd.DataFrame(analyzed)
print(f"Exported {len(analyzed)} jobs to data/cleaned/jobs.csv")
print(f"Columns: {list(df.columns)}")
print(f"Salary range: {df['salary_min'].min():.0f} - {df['salary_max'].max():.0f} HKD")
print(f"Locations: {df['location'].nunique()}")
print("Ready for Streamlit!")
