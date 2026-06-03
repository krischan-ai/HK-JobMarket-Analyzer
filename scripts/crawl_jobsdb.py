"""AI/LLM 大模型岗位爬虫 — JobsDB HK + 系统 Chrome + 搜索框输入 + Cookies 持久化"""
import sys, json, re, asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

PROXY = "http://127.0.0.1:10808"
MAX_PAGES_PER_KW = 3
RAW_DIR = Path("data/raw")
RAW_DIR.mkdir(parents=True, exist_ok=True)
AUTH_DIR = Path("data/auth")
AUTH_DIR.mkdir(parents=True, exist_ok=True)
JOBSDB_AUTH_FILE = AUTH_DIR / "jobsdb_auth.json"
USER_DATA_DIR = str(AUTH_DIR / "jobsdb_profile")

EXCLUDE_PATTERN = re.compile(
    r'(wealth|asset\s*management|insurance|banking|'
    r'financial\s*(advisor|consultant|planner)|'
    r'maintenance|sales|marketing|'
    r'HR|human\s*resource|recruitment|accounting|audit|compliance|'
    r'legal|counsel|secretary|clerk|reception)',
    re.IGNORECASE
)

def is_ai_job(title):
    if not title:
        return False
    title_lower = title.lower()
    if EXCLUDE_PATTERN.search(title_lower):
        return False
    ai_keywords = [
        "ai", "ml", "llm", "nlp", "rag", "langchain", "gpt",
        "chatgpt", "openai", "deepseek", "generative",
        "machine learning", "deep learning", "neural network",
        "artificial intelligence", "computer vision",
        "prompt", "large language model", "fine-tuning",
        "data scien", "data analy", "data engineer",
        "software engineer", "developer", "programmer",
        "frontend", "backend", "fullstack", "full stack",
        "devops", "cloud", "backend", "front end",
        "data engineer", "data architect",
        "system", "architect",
    ]
    return any(kw in title_lower for kw in ai_keywords)


def deduplicate(jobs):
    seen = set()
    unique = []
    for j in jobs:
        key = (j["title"].lower(), j["company"].lower())
        if key not in seen:
            seen.add(key)
            unique.append(j)
    return unique


async def search_jobsdb(page, keyword, max_pages=3):
    """在搜索框输入关键词搜索，获取真实结果"""
    jobs = []
    keyword_clean = keyword.strip()

    for attempt in range(3):
        try:
            print(f"  搜索 [{keyword_clean}]...")
            await page.goto("https://hk.jobsdb.com/", wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(4000)

            kw_region = page.locator('[data-automation="searchKeywordsField"]')
            await kw_region.wait_for(state="visible", timeout=15000)
            await kw_region.click()
            await page.wait_for_timeout(1000)
            kw_input = page.locator('input[type="text"]').first
            await kw_input.fill("")
            await page.wait_for_timeout(500)
            await kw_input.fill(keyword_clean)
            await page.wait_for_timeout(1000)

            where_input = page.locator('[data-automation="SearchBar__Where"]')
            if await where_input.count() > 0:
                await where_input.click()
                await where_input.fill("")
                await page.wait_for_timeout(500)
                await where_input.fill("Hong Kong")
                await page.wait_for_timeout(500)

            search_btn = page.locator('[data-automation="searchButton"]')
            if await search_btn.count() > 0:
                await search_btn.click()
            else:
                await page.keyboard.press("Enter")
            await page.wait_for_timeout(6000)

            # 等结果加载
            try:
                await page.wait_for_selector('[data-automation="jobTitle"]', timeout=20000)
            except:
                print(f"    没有搜索结果，重试...")
                continue

            print(f"    URL: {page.url[:100]}")
            base_url = page.url

            # 第1页
            raw = await page.evaluate("""() => {
                const cards = document.querySelectorAll('[data-automation="normalJob"]');
                return Array.from(cards).slice(0, 25).map(c => {
                    const t = c.querySelector('[data-automation="jobTitle"]');
                    const co = c.querySelector('[data-automation="jobCompany"]');
                    const lo = c.querySelector('[data-automation="jobCardLocation"], [data-automation="jobLocation"]');
                    const sa = c.querySelector('[data-automation="jobSalary"]');
                    const de = c.querySelector('[data-automation="jobShortDescription"]');
                    const dt = c.querySelector('[data-automation="jobListingDate"]');
                    return {
                        title: (t ? t.textContent.trim() : ''),
                        company: (co ? co.textContent.trim() : ''),
                        location: (lo ? lo.textContent.trim() : 'Hong Kong'),
                        salary: (sa ? sa.textContent.trim() : ''),
                        desc: (de ? de.textContent.trim() : ''),
                        date: (dt ? dt.textContent.trim() : ''),
                    };
                }).filter(j => j.title);
            }""")

            page1_titles = [j["title"] for j in raw if is_ai_job(j["title"])]
            print(f"    第1页: {len(raw)} raw, {len(page1_titles)} AI jobs")
            for j in raw[:5]:
                if is_ai_job(j["title"]):
                    jobs.append({
                        "job_id": f"jobsdb_{keyword_clean.replace(' ','_')}_p1_{len(jobs)}",
                        "title": j["title"],
                        "company": j["company"],
                        "location": j["location"] or "Hong Kong",
                        "salary_raw": j["salary"],
                        "jd_raw": j["desc"][:500],
                        "source": "jobsdb",
                    })

            # 后续页
            for pg in range(2, max_pages + 1):
                print(f"    第{pg}页...")
                pg_url = f"{base_url}?page={pg}"
                await page.goto(pg_url, wait_until="domcontentloaded", timeout=60000)
                await page.wait_for_timeout(5000)
                try:
                    await page.wait_for_selector('[data-automation="jobTitle"]', timeout=15000)
                except:
                    print(f"      第{pg}页无结果，结束")
                    break

                raw_pg = await page.evaluate("""() => {
                    const cards = document.querySelectorAll('[data-automation="normalJob"]');
                    return Array.from(cards).slice(0, 25).map(c => {
                        const t = c.querySelector('[data-automation="jobTitle"]');
                        const co = c.querySelector('[data-automation="jobCompany"]');
                        const lo = c.querySelector('[data-automation="jobCardLocation"], [data-automation="jobLocation"]');
                        const sa = c.querySelector('[data-automation="jobSalary"]');
                        const de = c.querySelector('[data-automation="jobShortDescription"]');
                        return {
                            title: (t ? t.textContent.trim() : ''),
                            company: (co ? co.textContent.trim() : ''),
                            location: (lo ? lo.textContent.trim() : 'Hong Kong'),
                            salary: (sa ? sa.textContent.trim() : ''),
                            desc: (de ? de.textContent.trim() : ''),
                        };
                    }).filter(j => j.title);
                }""")

                pg_titles = [j["title"] for j in raw_pg if is_ai_job(j["title"])]
                print(f"      第{pg}页: {len(raw_pg)} raw, {len(pg_titles)} AI jobs")
                for j in raw_pg:
                    if is_ai_job(j["title"]):
                        jobs.append({
                            "job_id": f"jobsdb_{keyword_clean.replace(' ','_')}_p{pg}_{len(jobs)}",
                            "title": j["title"],
                            "company": j["company"],
                            "location": j["location"] or "Hong Kong",
                            "salary_raw": j["salary"],
                            "jd_raw": j["desc"][:500],
                            "source": "jobsdb",
                        })

                await page.wait_for_timeout(2000)

            # 去重
            unique = deduplicate(jobs)
            print(f"    [{keyword_clean}] 共 {len(jobs)} 条, 去重后 {len(unique)} 条")
            return unique

        except Exception as e:
            print(f"    搜索失败: {e}")
            await page.wait_for_timeout(3000)
            continue

    return jobs


async def main():
    from playwright.async_api import async_playwright

    AI_KEYWORDS = [
        "AI engineer", "machine learning", "deep learning",
        "large language model", "LLM", "NLP engineer",
        "computer vision", "AI developer", "ML engineer",
        "data scientist", "AI researcher",
        "LangChain", "RAG", "generative AI",
        "prompt engineer", "AI architect",
        "artificial intelligence",
    ]

    print("=" * 60)
    print("AI/LLM Job Crawler — JobsDB HK")
    print(f"Proxy: {PROXY}")
    print(f"Keywords: {len(AI_KEYWORDS)} AI/ML related terms")
    print(f"Auth: {JOBSDB_AUTH_FILE}")
    print("=" * 60)
    print()

    async with async_playwright() as p:
        # 使用系统 Chrome + 持久化用户目录
        browser = await p.chromium.launch(
            headless=False,
            channel="chrome",
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                f"--proxy-server={PROXY}",
            ]
        )

        # 持久化 context: 保存 cookies 和 session
        ctx = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            storage_state=JOBSDB_AUTH_FILE if JOBSDB_AUTH_FILE.exists() else None,
        )

        page = await ctx.new_page()

        # 注入 stealth 脚本隐藏自动化特征
        await page.add_init_script("""() => {
            Object.defineProperty(navigator, 'webdriver', { get: () => false });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            Object.defineProperty(navigator, 'languages', { get: () => ['zh-HK', 'zh-CN', 'en'] });
        }""")

        # 如果有 cookies 文件，直接测试跳转到搜索页
        if JOBSDB_AUTH_FILE.exists():
            print(">>> 使用已保存的 Cookies...")
            await page.goto("https://hk.jobsdb.com/", wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(3000)
            current_url = page.url
            print(f"    URL: {current_url}")
        else:
            print(">>> 首次运行 — 会打开 JobsDB 首页")
            print(">>> 如需要登录，可以在浏览器中手动登录")
            print(">>> 登录后 Cookies 会自动保存，下次免登录")
            print()
            await page.goto("https://hk.jobsdb.com/", wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(5000)
            print(">>> 检查页面中，请确保已加载完成...")
            print(">>> 按 Enter 开始爬取 (可先登录以保存 cookies)...")
            input()
            await page.wait_for_timeout(2000)
            # 保存 cookies
            await ctx.storage_state(path=str(JOBSDB_AUTH_FILE))
            print(f">>> Cookies 已保存到 {JOBSDB_AUTH_FILE}")

        # 搜索前确认搜索框可用
        try:
            test_input = page.locator('[data-automation="searchKeywordsField"]')
            await test_input.wait_for(state="visible", timeout=10000)
            print(">>> 搜索框可用，开始爬取...")
        except:
            print(">>> 搜索框不可用，可能需要重新登录")
            print(">>> 请在浏览器中登录后按 Enter...")
            input()
            await ctx.storage_state(path=str(JOBSDB_AUTH_FILE))

        all_jobs = []
        for kw in AI_KEYWORDS:
            print(f"\n>>> 搜索: {kw}")
            jj = await search_jobsdb(page, kw, max_pages=MAX_PAGES_PER_KW)
            before = len(all_jobs)
            all_jobs.extend(jj)
            all_jobs = deduplicate(all_jobs)
            new_count = len(all_jobs) - before
            print(f"    [{kw}] 新增 {new_count} 条, 总计 {len(all_jobs)} 条")

            # 每个关键词存盘
            (RAW_DIR / "jobsdb_raw.json").write_text(
                json.dumps(all_jobs, ensure_ascii=False, indent=2), encoding="utf-8"
            )

            # 存 Cookies
            await ctx.storage_state(path=str(JOBSDB_AUTH_FILE))

        await browser.close()

    print(f"\n{'=' * 60}")
    print(f"Total: {len(all_jobs)} unique AI/LLM jobs from JobsDB")
    print(f"Saved: {RAW_DIR / 'jobsdb_raw.json'}")

    if all_jobs:
        import pandas as pd
        from src.cleaner.pipeline import CleaningPipeline
        from src.analyzer.rule_engine import RuleBasedSkillExtractor
        from src.storage.csv_exporter import CSVExporter

        pipeline = CleaningPipeline()
        extractor = RuleBasedSkillExtractor()
        cleaned = pipeline.clean_batch(all_jobs)
        analyzed = extractor.analyze_batch(cleaned)

        exporter = CSVExporter(output_dir="data/cleaned")
        csv_path = exporter.export(analyzed, "jobsdb_jobs.csv")
        print(f"Exported: {csv_path}")

        df = pd.DataFrame(analyzed)
        print(f"Total cleaned: {len(df)}")


if __name__ == "__main__":
    asyncio.run(main())
