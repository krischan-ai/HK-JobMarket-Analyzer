"""AI/LLM 大模型岗位爬虫 — Indeed HK + Playwright + 代理"""
import sys, json, re, asyncio
from collections import Counter
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

PROXY = "http://127.0.0.1:10808"
HEADLESS = False
MAX_PAGES_PER_KW = 3
RAW_DIR = Path("data/raw"); CLEAN_DIR = Path("data/cleaned")
RAW_DIR.mkdir(parents=True, exist_ok=True)
CLEAN_DIR.mkdir(parents=True, exist_ok=True)
AUTH_FILE = Path("indeed_auth.json")

EXCLUDE_PATTERN = re.compile(
    r'(wealth|asset\s*management|insurance|banking|'
    r'financial\s*(advisor|consultant|planner)|'
    r'maintenance|sales|marketing|'
    r'HR|human\s*resource|recruitment|accounting|audit|compliance|'
    r'legal|counsel|secretary|clerk|reception)',
    re.IGNORECASE
)

def is_it_job(title):
    """判断岗位标题是否属于 IT/技术类（覆盖全部 22 种角色）"""
    if not title:
        return False
    title_lower = title.lower()
    if EXCLUDE_PATTERN.search(title_lower):
        return False
    it_keywords = [
        # AI / 前沿技术
        "ai", "ml", "llm", "nlp", "rag", "langchain", "gpt",
        "chatgpt", "openai", "deepseek", "generative",
        "machine learning", "deep learning", "neural network",
        "artificial intelligence", "computer vision",
        "prompt", "large language model", "fine-tuning", "pretrain",
        "genai", "llama", "transformer", "diffusion",
        "multi-modal", "multimodal", "world model", "embodied",
        # 数据类
        "data scien", "data analy", "data engineer",
        "data architect", "data infrastructure",
        "ml engineer", "mlops", "data pipeline", "etl",
        # 软件开发
        "software engineer", "software developer",
        "developer", "programmer", "analyst programmer",
        "frontend", "front-end", "front end",
        "backend", "back-end", "back end",
        "fullstack", "full stack", "full-stack",
        "web developer", "web programmer",
        "mobile developer", "ios developer", "android developer",
        # 架构
        "architect", "system architect", "solution architect",
        "cloud architect", "enterprise architect",
        # 工程管理
        "engineering manager", "tech lead", "technical lead",
        "team lead", "development manager",
        # 分析师
        "system analyst", "business analyst", "it analyst",
        # DevOps / 基础设施
        "devops", "sre", "cloud engineer", "platform engineer",
        "kubernetes", "docker", "ci/cd", "infrastructure",
        # 质量 / 安全
        "qa engineer", "test automation", "quality assurance",
        "tester", "cybersecurity", "security engineer",
        "devsecops", "information security",
        # 产品 / 设计
        "product manager", "product owner", "scrum master",
        "ui designer", "ux designer", "product designer",
        "figma", "ui/ux",
        # 区块链
        "blockchain", "web3", "solidity", "smart contract",
    ]
    return any(kw in title_lower for kw in it_keywords)


async def check_cloudflare(page):
    """检查页面是否被 Cloudflare 拦截"""
    t = await page.title()
    if "Access Denied" in t or "Just a moment" in t or "challenge" in t.lower():
        return True
    body = await page.evaluate("() => document.body?.innerText?.slice(0, 500) || ''")
    cf_signals = ["checking your browser", "just a moment", "attention required",
                   "verify you are human", "cloudflare", "ddos protection"]
    return any(s in body.lower() for s in cf_signals)


async def do_login(page):
    """打开 Indeed 登录页, 让用户手动登录"""
    print("\n" + "!" * 60)
    print("!! 正在打开 Indeed 登录页...                    !!")
    print("!! 请手动登录, 登录后按 Enter 开始爬取           !!")
    print("!" * 60)

    await page.goto("https://secure.indeed.com/auth?hl=en_HK&co=HK&continue=https://hk.indeed.com/",
                    wait_until="domcontentloaded", timeout=60000)
    await page.wait_for_timeout(5000)

    if await check_cloudflare(page):
        print(">>> Cloudflare 弹出, 手动验证后按 Enter...")
        input()
        await page.wait_for_timeout(5000)

    if await check_cloudflare(page):
        print(">>> 还有 Cloudflare, 再验证一次后按 Enter...")
        input()
        await page.wait_for_timeout(5000)

    print(">>> 请在浏览器中完成登录, 然后按 Enter 开始爬取...")
    input()
    await page.wait_for_timeout(3000)


async def scrape_indeed(page, keyword, max_pages=MAX_PAGES_PER_KW):
    jobs = []
    for pg in range(max_pages):
        start = pg * 10
        url = f"https://hk.indeed.com/jobs?q={quote(keyword)}&l=Hong+Kong&start={start}"
        print(f"  Indeed [{keyword}] page {pg+1}")
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(5000)

            # 检测 Cloudflare
            if await check_cloudflare(page):
                print("  >>> Cloudflare 拦截! 在浏览器中验证后按 Enter...")
                input()
                await page.wait_for_timeout(5000)
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                await page.wait_for_timeout(4000)

            raw = await page.evaluate("""() => {
                const cards = document.querySelectorAll('[class*=job_seen_beacon], [class*=slider_container], li[class*=css-], td.resultContent, .jobsearch-ResultsList > div');
                return Array.from(cards).slice(0, 25).map(c => {
                    const t = c.querySelector('h2 a, h2 span[title], a[data-jk], a.jcs-JobTitle, span[title]');
                    const co = c.querySelector('[data-testid=company-name], .companyName, [class*=companyName]');
                    const lo = c.querySelector('[data-testid=text-location], .companyLocation, [class*=companyLocation]');
                    const sa = c.querySelector('.salary-snippet, [class*=salary]');
                    const de = c.querySelector('[class*=job-snippet], .underShelfFooter, ul');
                    return {
                        title: (t ? t.textContent.trim() : ''),
                        company: (co ? co.textContent.trim() : ''),
                        location: (lo ? lo.textContent.trim() : 'Hong Kong'),
                        salary: (sa ? sa.textContent.trim() : ''),
                        desc: (de ? de.textContent.trim() : '')
                    };
                }).filter(j => j.title);
            }""")

            # page 1 返回 0 条 → 大概率被盾 → 让用户处理
            if pg == 0 and len(raw) == 0:
                print(f"  >>> 第1页返回0条, 可能被 Cloudflare 拦截!")
                print(f"  >>> 请在浏览器中检查, 解决后按 Enter 重试...")
                input()
                await page.wait_for_timeout(3000)
                # 重试当前页
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                await page.wait_for_timeout(5000)
                if await check_cloudflare(page):
                    print("  >>> 仍有 Cloudflare, 再验证一次后按 Enter...")
                    input()
                    await page.wait_for_timeout(5000)
                raw = await page.evaluate("""() => {
                    const cards = document.querySelectorAll('[class*=job_seen_beacon], [class*=slider_container], li[class*=css-], td.resultContent, .jobsearch-ResultsList > div');
                    return Array.from(cards).slice(0, 25).map(c => {
                        const t = c.querySelector('h2 a, h2 span[title], a[data-jk], a.jcs-JobTitle, span[title]');
                        const co = c.querySelector('[data-testid=company-name], .companyName, [class*=companyName]');
                        const lo = c.querySelector('[data-testid=text-location], .companyLocation, [class*=companyLocation]');
                        const sa = c.querySelector('.salary-snippet, [class*=salary]');
                        const de = c.querySelector('[class*=job-snippet], .underShelfFooter, ul');
                        return {
                            title: (t ? t.textContent.trim() : ''),
                            company: (co ? co.textContent.trim() : ''),
                            location: (lo ? lo.textContent.trim() : 'Hong Kong'),
                            salary: (sa ? sa.textContent.trim() : ''),
                            desc: (de ? de.textContent.trim() : '')
                        };
                    }).filter(j => j.title);
                }""")

            for j in raw:
                if is_it_job(j["title"]):
                    jobs.append({
                        "job_id": f"indeed_{pg}_{len(jobs)}",
                        "title": j["title"],
                        "company": j["company"],
                        "location": j["location"] or "Hong Kong",
                        "salary_raw": j["salary"],
                        "jd_raw": j["desc"][:500],
                        "source": "indeed",
                    })

            page_titles = [j["title"][:50] for j in jobs[-5:]] if jobs else []
            print(f"    Page {pg+1}: {len(jobs)} AI jobs (from {len(raw)} raw) ex: {page_titles}")
        except Exception as e:
            print(f"    Error: {e}")
            break
        await page.wait_for_timeout(1500)
    return jobs


async def main():
    from playwright.async_api import async_playwright

    IT_KEYWORDS = [
        # AI / ML / LLM
        "AI engineer", "machine learning", "deep learning",
        "large language model", "LLM", "NLP engineer",
        "computer vision", "AI developer", "ML engineer",
        "data scientist", "AI researcher",
        "LangChain", "RAG", "generative AI",
        "prompt engineer", "AI architect",
        "artificial intelligence", "AI agent",
        # 数据类
        "data scientist", "data analyst", "data engineer",
        "data architect", "MLOps",
        # 软件开发
        "software engineer", "frontend developer",
        "backend developer", "full stack developer",
        "mobile developer", "web developer",
        "Java developer", "Python developer",
        # 架构
        "solution architect", "system architect",
        "cloud architect", "enterprise architect",
        # 工程管理
        "engineering manager", "tech lead",
        # 分析师
        "system analyst", "business analyst",
        # DevOps / 基础设施
        "DevOps engineer", "cloud engineer", "SRE",
        "platform engineer",
        # 质量 / 安全
        "QA engineer", "test automation",
        "cybersecurity", "security engineer",
        # 产品 / 设计 / 区块链
        "product manager", "UI UX designer",
        "blockchain developer", "Web3",
    ]

    print("=" * 60)
    print("AI/LLM Job Crawler for Hong Kong")
    print(f"Proxy: {PROXY} | Headless: {HEADLESS}")
    print(f"Keywords: {len(IT_KEYWORDS)} AI/ML related terms")
    print("=" * 60)
    print("Cloudflare: solve in browser -> press Enter to continue")
    print()

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=HEADLESS,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled", f"--proxy-server={PROXY}"]
        )

        # ===== Cookies 持久化: 复用登录态 =====
        if AUTH_FILE.exists():
            print(f"\n>>> 发现已保存的登录态 ({AUTH_FILE}), 正在加载...")
            ctx = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                storage_state=str(AUTH_FILE),
            )
            page = await ctx.new_page()
            await page.goto("https://hk.indeed.com/", wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(5000)
            if await check_cloudflare(page):
                print(">>> Cloudflare 拦截! 在浏览器中验证后按 Enter...")
                input()
                await page.wait_for_timeout(5000)
            body = await page.evaluate("() => document.body?.innerText?.slice(0, 300) || ''")
            if "sign in" not in body.lower() and "Sign in" not in body:
                print(">>> 登录态有效, 跳过登录, 直接开始爬取!")
            else:
                print(">>> Cookies 已过期, 需要重新登录...")
                AUTH_FILE.unlink(missing_ok=True)
                await ctx.close()
                ctx = await browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                )
                page = await ctx.new_page()
                await do_login(page)
                await ctx.storage_state(path=str(AUTH_FILE))
                print(f">>> 登录态已保存到 {AUTH_FILE}")
        else:
            print(f"\n>>> 没有找到已保存的登录态, 需要进行登录...")
            ctx = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            )
            page = await ctx.new_page()
            await do_login(page)
            await ctx.storage_state(path=str(AUTH_FILE))
            print(f">>> 登录态已保存到 {AUTH_FILE}")

        page = await ctx.new_page()
        all_jobs = []

        for kw in IT_KEYWORDS:
            print(f"\n>>> Searching: {kw}")
            ij = await scrape_indeed(page, kw, max_pages=MAX_PAGES_PER_KW)
            all_jobs.extend(ij)
            await page.wait_for_timeout(1500)
            # 每个关键词爬完立即保存, 防止中途停止丢数据
            with open(RAW_DIR / "it_jobs_raw.json", "w", encoding="utf-8") as f:
                json.dump(all_jobs, f, ensure_ascii=False, indent=2)
            print(f"  >>> 已保存 {len(all_jobs)} 条临时数据到 it_jobs_raw.json")

        await browser.close()

    seen = set()
    unique = []
    for j in all_jobs:
        key = (j["title"].lower(), j["company"].lower(), j["source"])
        if key not in seen:
            seen.add(key)
            unique.append(j)

    print(f"\n{'=' * 60}")
    print(f"Total: {len(all_jobs)} raw -> {len(unique)} unique IT/tech jobs")
    print(f"Source: indeed")
    print(f"Keywords used: {', '.join(IT_KEYWORDS)}")

    import pandas as pd

    raw_path = RAW_DIR / "it_jobs_raw.json"
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(unique, f, ensure_ascii=False, indent=2)
    print(f"Saved raw: {raw_path}")

    from src.cleaner.pipeline import CleaningPipeline
    from src.analyzer.rule_engine import RuleBasedSkillExtractor
    from src.storage.csv_exporter import CSVExporter

    pipeline = CleaningPipeline()
    extractor = RuleBasedSkillExtractor()
    cleaned = pipeline.clean_batch(unique)
    analyzed = extractor.analyze_batch(cleaned)

    exporter = CSVExporter(output_dir=str(CLEAN_DIR))
    csv_path = exporter.export(analyzed, "jobs.csv")
    print(f"Exported: {csv_path}")

    df = pd.DataFrame(analyzed)
    if "salary_min" in df.columns and df["salary_min"].notna().any():
        s = df["salary_min"].dropna()
        print(f"Salary: {s.min():.0f}-{s.max():.0f} HKD, avg={s.mean():.0f}")
    if "location" in df.columns:
        print(f"Locations: {df['location'].nunique()} unique")
    print(f"Skills count: {len(df)}")
    print(f"\nDONE! {len(unique)} AI/LLM jobs ready. Run: uvicorn api.main:app --reload")


if __name__ == "__main__":
    asyncio.run(main())
