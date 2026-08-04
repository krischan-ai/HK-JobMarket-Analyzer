from __future__ import annotations
"""快速爬虫：JobsDB 网页版 + Indeed Playwright"""
import sys, json, time, re, math
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests
from bs4 import BeautifulSoup

from src.cleaner.pipeline import CleaningPipeline
from src.analyzer.rule_engine import RuleBasedSkillExtractor
from src.storage.csv_exporter import CSVExporter
from src.logger import setup_logger, get_logger
from scripts.crawl_utils import is_insurance_sales, parse_job_fields

setup_logger(level="INFO")
logger = get_logger("quick_crawl")

PROXY = "http://127.0.0.1:10808"
PROXIES = {"http": PROXY, "https": PROXY}

KEYWORDS = [
    # 软件开发
    "software-engineer", "frontend-developer",
    "backend-developer", "full-stack",
    "mobile-developer", "web-developer",
    "java-developer", "python-developer",
    # AI / 数据
    "AI-engineer", "data-scientist",
    "machine-learning", "data-engineer",
    "data-analyst", "ML-engineer",
    "LLM", "generative-AI",
    # 架构
    "solution-architect", "system-architect",
    "cloud-architect", "enterprise-architect",
    # DevOps / 基础设施
    "devops", "cloud-engineer",
    "SRE", "platform-engineer",
    # 其他 IT
    "cybersecurity", "qa-engineer",
    "product-manager", "ui-ux-designer",
    "blockchain-developer",
    "engineering-manager",
    "system-analyst", "business-analyst",
]

MAX_PAGES = 5
RAW_DIR = Path("data/raw")
CLEAN_DIR = Path("data/cleaned")
RAW_DIR.mkdir(parents=True, exist_ok=True)
CLEAN_DIR.mkdir(parents=True, exist_ok=True)


def fetch_jobsdb_search(kw: str, page: int = 1) -> list[dict]:
    url = f"https://hk.jobsdb.com/{kw}-jobs-in-hong-kong"
    params = {}
    if page > 1:
        params["page"] = page
    s = requests.Session()
    s.proxies.update(PROXIES)
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0",
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "zh-HK,en;q=0.9",
    })
    resp = s.get(url, params=params, timeout=30)
    resp.raise_for_status()
    return parse_jobsdb_html(resp.text)


def parse_jobsdb_html(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")

    script_data = None
    for script in soup.find_all("script"):
        if script.string and "window.__INITIAL_STATE__" in script.string:
            script_data = script.string
            break

    jobs = []

    if script_data:
        try:
            match = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.*?});\s*(?:\n|$)', script_data, re.DOTALL)
            if not match:
                match = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.+})\s*$', script_data, re.DOTALL)
            if match:
                data = json.loads(match.group(1))
                for result in _extract_jobs_from_state(data):
                    jobs.append(result)
        except (json.JSONDecodeError, KeyError) as e:
            logger.debug("JSON parse failed: %s", e)

    if not jobs:
        logger.debug("Falling back to HTML scraping")
        cards = soup.select('[data-automation="jobCard"]')
        if not cards:
            cards = soup.select('.yvsb870')
        if not cards:
            cards = soup.find_all('article', attrs={'data-card-type': True})
        for i, card in enumerate(cards):
            title_el = card.select_one('[data-automation="jobTitle"]')
            if not title_el:
                title_el = card.find('a', href=re.compile(r'/job/'))
            company_el = card.select_one('[data-automation="jobCompany"]')
            if not company_el:
                company_el = card.find(string=re.compile(r'(Ltd|Limited|Co\.|Company|Corp)'))
            location_el = card.select_one('[data-automation="jobLocation"]')
            salary_el = card.select_one('[data-automation="jobSalary"]')
            desc_el = card.select_one('[data-automation="jobShortDescription"]')

            link_el = card.find('a', href=re.compile(r'/job/'))
            job_url = ""
            if link_el and link_el.get('href'):
                href = link_el['href']
                job_url = f"https://hk.jobsdb.com{href}" if href.startswith('/') else href

            jobs.append({
                "job_id": f"jobsdb_{i}",
                "title": title_el.get_text(strip=True) if title_el else "",
                "company": company_el.get_text(strip=True) if company_el else "",
                "location": location_el.get_text(strip=True) if location_el else "Hong Kong",
                "salary_raw": salary_el.get_text(strip=True) if salary_el else "",
                "jd_raw": desc_el.get_text(strip=True) if desc_el else "",
                "url": job_url,
                "source": "jobsdb",
            })

    for j in jobs:
        j.setdefault("salary_raw", "")
        j.setdefault("url", "")
        j.setdefault("source", "jobsdb")

    return jobs


def _extract_jobs_from_state(data: dict) -> list[dict]:
    results = []
    try:
        search_results = data.get("results", {}).get("results", {})
        job_list = search_results.get("jobs", []) or []
        if not job_list:
            job_list = data.get("searchResults", {}).get("jobResults", []) or []
        if not job_list:
            state_key = next((k for k in data if isinstance(data[k], dict) and "jobs" in data[k]), None)
            if state_key:
                job_list = data[state_key].get("jobs", []) or []

        for idx, job in enumerate(job_list):
            jid = job.get("id") or job.get("jobId") or f"jd_{idx}"
            title = job.get("title") or ""
            company_name = ""
            company_data = job.get("company") or job.get("advertiser") or {}
            if isinstance(company_data, dict):
                company_name = company_data.get("name") or company_data.get("displayName") or ""
            elif isinstance(company_data, str):
                company_name = company_data
            location = job.get("location") or job.get("locations") or ""
            if isinstance(location, list):
                location = ", ".join(location)
            salary = job.get("salary") or ""
            if isinstance(salary, dict):
                salary = salary.get("display", "")
            snippet = job.get("snippet") or job.get("summary") or job.get("bulletText") or ""
            if isinstance(snippet, list):
                snippet = " ".join(snippet)

            jd_link = job.get("jobUrl") or job.get("url") or job.get("shareLink") or ""
            if not jd_link:
                slug = job.get("seoSlug") or job.get("slug") or ""
                jid_val = job.get("id") or job.get("jobId") or ""
                if slug and jid_val:
                    jd_link = f"https://hk.jobsdb.com/job/{jid_val}?type=standout&ref=search-standalone"

            results.append({
                "job_id": f"jobsdb_{jid}",
                "title": title,
                "company": company_name,
                "location": location or "Hong Kong",
                "salary_raw": salary,
                "jd_raw": snippet,
                "url": jd_link,
                "source": "jobsdb",
            })
    except Exception as e:
        logger.warning("SSR data parse error: %s", e)
    return results


def try_indeed_playwright():
    logger.info("=== Trying Indeed HK (Playwright + Proxy) ===")
    try:
        from src.crawlers.indeed import IndeedCrawler
        crawler = IndeedCrawler(headless=True, proxy_server=PROXY)
        all_jobs = []
        for kw in ["software engineer", "data scientist", "frontend developer", "backend developer"]:
            try:
                jobs = crawler.run(kw, max_pages=2)
                logger.info("  Indeed '%s': %d jobs", kw, len(jobs))
                all_jobs.extend(jobs)
                time.sleep(1.5)
            except Exception as e:
                logger.warning("  Indeed '%s': %s", kw, e)
        return all_jobs
    except Exception as e:
        logger.error("Indeed: %s", e)
        return []


def deduplicate(jobs: list[dict]) -> list[dict]:
    seen = set()
    unique = []
    for j in jobs:
        kid = (j.get("job_id"), j.get("source"))
        if kid in seen:
            continue
        if not j.get("title"):
            continue
        seen.add(kid)
        unique.append(j)
    return unique


def enrich_raw_jobs(jobs: list[dict]) -> list[dict]:
    for job in jobs:
        if "is_insurance_sales" not in job or "insurance_score" not in job:
            is_ins, score, _ = is_insurance_sales(job)
            job["is_insurance_sales"] = is_ins
            job["insurance_score"] = score
        parse_job_fields(job)
    return jobs


def main():
    logger.info("Starting quick crawl with JobsDB HTML + Indeed Playwright")
    logger.info("Proxy: %s", PROXY)

    all_jobs = []

    logger.info("=== JobsDB HTML scraping ===")
    for kw in KEYWORDS:
        try:
            page1 = fetch_jobsdb_search(kw, page=1)
            logger.info("  JobsDB '%s' page1: %d jobs", kw, len(page1))
            all_jobs.extend(page1)

            total_pages = min(MAX_PAGES, 5)
            for p in range(2, total_pages + 1):
                try:
                    more = fetch_jobsdb_search(kw, page=p)
                    if not more:
                        break
                    logger.info("  JobsDB '%s' page%d: %d jobs", kw, p, len(more))
                    all_jobs.extend(more)
                    time.sleep(1)
                except Exception:
                    break
            time.sleep(1.5)
        except Exception as e:
            logger.warning("  JobsDB '%s': %s", kw, e)

    logger.info("JobsDB total: %d jobs", len(all_jobs))

    indeed_jobs = try_indeed_playwright()
    logger.info("Indeed total: %d jobs", len(indeed_jobs))
    all_jobs.extend(indeed_jobs)

    all_jobs = deduplicate(all_jobs)
    all_jobs = enrich_raw_jobs(all_jobs)
    logger.info("After dedup: %d unique jobs", len(all_jobs))

    if not all_jobs:
        logger.error("No data collected!")
        return

    raw_path = RAW_DIR / "all_sources.json"
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(all_jobs, f, ensure_ascii=False, indent=2)
    logger.info("Saved raw to %s", raw_path)

    logger.info("=== Cleaning & Analysis ===")
    pipeline = CleaningPipeline()
    extractor = RuleBasedSkillExtractor()
    cleaned = pipeline.clean_batch(all_jobs)
    analyzed = extractor.analyze_batch(cleaned)

    exporter = CSVExporter(output_dir=str(CLEAN_DIR))
    csv_path = exporter.export(analyzed, "jobs.csv")
    logger.info("Exported %d jobs to %s", len(analyzed), csv_path)

    import pandas as pd
    df = pd.DataFrame(analyzed)
    logger.info("Sources: %s", df["source"].value_counts().to_dict() if "source" in df.columns else {})
    if "salary_min" in df.columns and df["salary_min"].notna().any():
        logger.info("Salary range: %.0f - %.0f HKD", df["salary_min"].min(), df["salary_max"].max())
    if "location" in df.columns:
        logger.info("Unique locations: %d", df["location"].nunique())
    logger.info("DONE!")


if __name__ == "__main__":
    main()
