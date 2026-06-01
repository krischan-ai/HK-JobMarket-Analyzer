"""Phase 1 调试脚本：使用模拟数据验证后端全链路"""
from __future__ import annotations

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.logger import setup_logger, get_logger
from src.utils import json_dump

setup_logger(level="INFO")
logger = get_logger("debug")

# 模拟 20 条岗位数据
MOCK_JOBS = [
    {"job_id": "MOCK_001", "title": "Senior Python Developer", "company": "HK Fintech Ltd", "location": "Central", "salary_raw": "HK$45,000 - HK$60,000 /month", "jd_raw": "<p>We are looking for a senior Python developer with experience in <strong>Django</strong> and <strong>AWS</strong>. Knowledge of <strong>PostgreSQL</strong> and <strong>Docker</strong> is required.</p>", "source": "jobsdb"},
    {"job_id": "MOCK_002", "title": "Frontend Engineer (React)", "company": "Tech Corp HK", "location": "Quarry Bay", "salary_raw": "HK$600,000 - HK$720,000 per annum", "jd_raw": "We need a React expert with TypeScript experience. Familiar with Next.js and Tailwind CSS. Agile team player with strong communication skills.", "source": "jobsdb"},
    {"job_id": "MOCK_003", "title": "Data Scientist", "company": "AI Lab HK", "location": "Science Park", "salary_raw": "HK$50,000 - HK$80,000 /month", "jd_raw": "Looking for data scientist proficient in Python, TensorFlow, and PyTorch. Experience with Spark and Kafka is a plus. Strong analytical and problem-solving skills.", "source": "jobsdb"},
    {"job_id": "MOCK_004", "title": "DevOps Engineer", "company": "Cloud Native HK", "location": "Kwai Chung", "salary_raw": "HK$40,000 - HK$65,000 /month", "jd_raw": "AWS certified DevOps engineer needed. Must know Kubernetes, Terraform, CI/CD pipelines, and monitoring with Prometheus and Grafana.", "source": "jobsdb"},
    {"job_id": "MOCK_005", "title": "Java Spring Boot Developer", "company": "Banking Tech", "location": "Central", "salary_raw": "HK$480,000 - HK$600,000 per annum", "jd_raw": "Senior Java developer with Spring Boot expertise. Experience in MySQL, Redis, and microservices architecture. Good communication and teamwork skills.", "source": "jobsdb"},
    {"job_id": "MOCK_006", "title": "Full Stack Engineer", "company": "Startup HK", "location": "Wong Chuk Hang", "salary_raw": "HK$35,000 - HK$55,000 /month", "jd_raw": "Full stack developer proficient in React, Node.js, and MongoDB. Understanding of Docker and cloud services (AWS/GCP). Self-motivated and independent.", "source": "jobsdb"},
    {"job_id": "MOCK_007", "title": "Mobile Developer (Flutter)", "company": "App Studio HK", "location": "Causeway Bay", "salary_raw": "HK$30,000 - HK$50,000 /month", "jd_raw": "Flutter developer with Dart experience. Knowledge of Firebase and RESTful APIs. Team player with good presentation skills.", "source": "jobsdb"},
    {"job_id": "MOCK_008", "title": "Machine Learning Engineer", "company": "AI Startup", "location": "Cyberport", "salary_raw": "HK$55,000 - HK$75,000 /month", "jd_raw": "ML engineer skilled in Python, TensorFlow, and Kubernetes. Experience with MLOps, data pipelines, and model deployment in production.", "source": "jobsdb"},
    {"job_id": "MOCK_009", "title": "Backend Engineer (Go)", "company": "Trading Firm", "location": "Central", "salary_raw": "HK$60,000 - HK$90,000 /month", "jd_raw": "Backend engineer with Go expertise. Strong understanding of distributed systems, Kafka, and Redis. Critical thinking and cross-functional collaboration required.", "source": "jobsdb"},
    {"job_id": "MOCK_010", "title": "Cloud Architect", "company": "MNC HK", "location": "Kowloon Bay", "salary_raw": "HK$80,000 - HK$120,000 /month", "jd_raw": "Cloud architect with deep AWS knowledge (ECS, EKS, Lambda, RDS). Experience with Terraform, CI/CD, and cloud security. Leadership and stakeholder management skills.", "source": "jobsdb"},
]

MOCK_JOBS_EXTRA = [
    {"job_id": "MOCK_011", "title": "Data Engineer", "company": "Big Data Ltd", "location": "Hong Kong", "salary_raw": "HK$45,000 - HK$70,000 /month", "jd_raw": "Data engineer with Spark, Airflow, and Snowflake experience. Python and SQL proficiency. Strong problem-solving and analytical abilities.", "source": "jobsdb"},
    {"job_id": "MOCK_012", "title": "Security Engineer", "company": "CyberSec HK", "location": "Central", "salary_raw": "HK$50,000 - HK$80,000 /month", "jd_raw": "Security engineer specializing in cloud security. Knowledge of AWS security services, penetration testing, and security best practices. CISSP preferred.", "source": "jobsdb"},
    {"job_id": "MOCK_013", "title": "QA Engineer", "company": "Quality First", "location": "Tsim Sha Tsui", "salary_raw": "HK$30,000 - HK$45,000 /month", "jd_raw": "QA engineer with Selenium and Cypress experience. Knowledge of automated testing frameworks and CI/CD integration. Attention to detail and analytical thinking.", "source": "jobsdb"},
    {"job_id": "MOCK_014", "title": "Product Manager (Tech)", "company": "Product Co", "location": "Wan Chai", "salary_raw": "HK$55,000 - HK$75,000 /month", "jd_raw": "Technical product manager with agile/scrum experience. Understanding of software development lifecycle. Excellent communication and stakeholder management.", "source": "jobsdb"},
    {"job_id": "MOCK_015", "title": "System Administrator", "company": "IT Services HK", "location": "Shatin", "salary_raw": "HK$25,000 - HK$40,000 /month", "jd_raw": "System admin with Linux expertise. Knowledge of shell scripting, nginx, and monitoring tools. Teamwork and time management skills.", "source": "jobsdb"},
]

all_mock_jobs = MOCK_JOBS + MOCK_JOBS_EXTRA

def run_pipeline():
    logger.info("=" * 50)
    logger.info("Phase 1 调试开始")
    logger.info("=" * 50)

    # Step 1: 测试清洗
    logger.info("\n[Phase 1] 测试数据清洗...")
    from src.cleaner import CleaningPipeline
    cleaner = CleaningPipeline()
    cleaned = cleaner.clean_batch(all_mock_jobs)
    assert len(cleaned) == len(all_mock_jobs), f"Expected {len(all_mock_jobs)}, got {len(cleaned)}"
    assert all(j.get("jd_text") for j in cleaned), "Some jobs missing jd_text"
    assert all(j.get("salary_min") is not None for j in cleaned), "Salary parsing failed"
    logger.info("  ✅ 清洗完成: %d 条", len(cleaned))

    # 验证薪资解析
    salary_checks = [
        ("MOCK_001", 45000, 60000),
        ("MOCK_002", 50000, 60000),  # annual / 12
        ("MOCK_010", 80000, 120000),
    ]
    for jid, exp_min, exp_max in salary_checks:
        job = next(j for j in cleaned if j["job_id"] == jid)
        assert job["salary_min"] == exp_min, f"{jid}: expected min {exp_min}, got {job['salary_min']}"
        assert job["salary_max"] == exp_max, f"{jid}: expected max {exp_max}, got {job['salary_max']}"
    logger.info("  ✅ 薪资解析验证通过")

    # Step 2: 测试规则引擎
    logger.info("\n[Phase 2] 测试规则引擎...")
    from src.analyzer import RuleBasedSkillExtractor
    extractor = RuleBasedSkillExtractor()
    analyzed = extractor.analyze_batch(cleaned)
    assert all(j.get("skills") for j in analyzed), "Some jobs missing skills"

    skill_checks = [
        ("MOCK_001", "Python", "programming_languages"),
        ("MOCK_002", "React", "frameworks_libraries"),
        ("MOCK_003", "Tensorflow", "frameworks_libraries"),
        ("MOCK_004", "Aws", "cloud_devops"),
        ("MOCK_005", "Mysql", "databases"),
        ("MOCK_006", "React", "frameworks_libraries"),
    ]
    for jid, skill, category in skill_checks:
        job = next(j for j in analyzed if j["job_id"] == jid)
        skills_in_cat = [s.lower() for s in job["skills"].get(category, [])]
        assert skill.lower() in skills_in_cat, f"{jid}: expected {skill} in {category}, got {skills_in_cat}"
    logger.info("  ✅ 规则引擎技能提取验证通过")

    # 验证软技能
    job_002 = next(j for j in analyzed if j["job_id"] == "MOCK_002")
    soft_skills = [s.lower() for s in job_002["skills"].get("soft_skills", [])]
    assert "Communication" in job_002["skills"]["soft_skills"], f"Expected 'Communication', got {soft_skills}"
    logger.info("  ✅ 软技能提取验证通过")

    # Step 3: 测试图表生成
    logger.info("\n[Phase 3] 测试图表生成...")
    import pandas as pd
    df = pd.DataFrame(analyzed)
    from src.visualization import TechTrendAnalyzer
    from src.utils import ensure_dir
    output_dir = ensure_dir("output/debug_charts")
    analyzer = TechTrendAnalyzer(df, output_dir=output_dir)
    charts = analyzer.generate_all_charts()

    expected_charts = ["top_skills", "category_distribution", "salary_by_skill", "location_distribution"]
    for name in expected_charts:
        assert charts.get(name) is not None, f"Chart '{name}' not generated"
        assert Path(charts[name]).exists(), f"Chart file '{charts[name]}' not found"
    logger.info("  ✅ 图表生成完成: %s", list(charts.keys()))

    # Step 4: 测试 CSV 导出
    logger.info("\n[Phase 4] 测试数据导出...")
    from src.storage import CSVExporter
    exporter = CSVExporter(output_dir="data/cleaned")
    csv_path = exporter.export(analyzed, filename="debug_jobs.csv")
    assert csv_path.exists(), f"CSV not found at {csv_path}"

    # 测试 JSON 导出
    json_dump(analyzed, "data/cleaned/debug_jobs.json")
    assert Path("data/cleaned/debug_jobs.json").exists(), "JSON not found"
    logger.info("  ✅ 数据导出完成")

    # Step 5: 测试 MongoDB（如果可用）
    logger.info("\n[Phase 5] 测试 MongoDB 连接...")
    from src.storage import JobDatabase
    db = JobDatabase()
    if db.is_connected:
        count = db.bulk_insert(analyzed)
        logger.info("  ✅ MongoDB 已连接，插入 %d 条数据", count)
        db.close()
    else:
        logger.warning("  ⚠️  MongoDB 未连接，跳过数据库测试")

    logger.info("\n" + "=" * 50)
    logger.info("Phase 1 调试全部通过 ✅")
    logger.info("=" * 50)
    return analyzed


if __name__ == "__main__":
    result = run_pipeline()
    logger.info("\n模拟数据处理完成，共 %d 条岗位", len(result))
    logger.info("运行 Streamlit 看板: streamlit run src/app.py")
