"""AI/LLM 大模型岗位爬虫 — JobsDB HK + 系统 Chrome + 搜索框输入 + Cookies 持久化"""
import sys, json, re, asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.crawl_utils import (
    deduplicate, build_existing_keys, build_dedup_key,
    load_progress, mark_keyword_completed,
    jd_contains_tech, is_insurance_sales,
)

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




async def search_jobsdb(page, keyword, max_pages=3):
    """在搜索框输入关键词搜索，获取真实结果（通过点击卡片从右侧面板提取完整 JD）"""
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
                await search_btn.click(force=True)
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

            # 逐页处理
            for pg in range(1, max_pages + 1):
                if pg > 1:
                    pg_url = f"{base_url}?page={pg}"
                    print(f"    第{pg}页...")
                    await page.goto(pg_url, wait_until="domcontentloaded", timeout=60000)
                    await page.wait_for_timeout(5000)
                    try:
                        await page.wait_for_selector('[data-automation="jobTitle"]', timeout=15000)
                    except:
                        print(f"      第{pg}页无结果，结束")
                        break

                # 先获取本页所有卡片数据
                raw = await page.evaluate("""() => {
                    const cards = document.querySelectorAll('[data-automation="normalJob"]');
                    return Array.from(cards).slice(0, 25).map((c, i) => {
                        const t = c.querySelector('[data-automation="jobTitle"]');
                        const co = c.querySelector('[data-automation="jobCompany"]');
                        const lo = c.querySelector('[data-automation="jobCardLocation"], [data-automation="jobLocation"]');
                        const sa = c.querySelector('[data-automation="jobSalary"]');
                        const de = c.querySelector('[data-automation="jobShortDescription"]');
                        const dt = c.querySelector('[data-automation="jobListingDate"]');
                        const url = t ? t.href : '';
                        return {
                            idx: i,
                            title: (t ? t.textContent.trim() : ''),
                            company: (co ? co.textContent.trim() : ''),
                            location: (lo ? lo.textContent.trim() : 'Hong Kong'),
                            salary: (sa ? sa.textContent.trim() : ''),
                            desc: (de ? de.textContent.trim() : ''),
                            date: (dt ? dt.textContent.trim() : ''),
                            url: url,
                        };
                    }).filter(j => j.title);
                }""")

                pg_titles = [j["title"] for j in raw if is_ai_job(j["title"])]
                print(f"      第{pg}页: {len(raw)} raw, {len(pg_titles)} AI jobs")

                # 逐一点击所有卡片，从右侧面板提取完整 JD，由 JD 内容判断是否收录
                page_card_count = 0
                page_jd_ok = 0
                page_tech_ok = 0
                for j in raw:
                    page_card_count += 1

                    # 点击卡片打开右侧详情面板
                    try:
                        card = page.locator('[data-automation="normalJob"]').nth(j["idx"])
                        if await card.count() == 0:
                            continue
                        await card.click()
                        await page.wait_for_timeout(2000)

                        # 等待详情面板出现
                        try:
                            await page.wait_for_selector('[data-automation="jobAdDetails"]', timeout=10000)
                        except:
                            pass

                        # 从右侧面板提取完整 JD
                        jd_full = await page.evaluate("""() => {
                            const el = document.querySelector('[data-automation="jobAdDetails"]');
                            if (el) {
                                const t = (el.innerText || '').trim();
                                if (t.length > 100) return t;
                            }
                            const panel = document.querySelector('[data-automation="jobDetailsPage"]');
                            if (panel) {
                                const t = (panel.innerText || '').trim();
                                if (t.length > 100) return t;
                            }
                            return '';
                        }""")
                    except:
                        jd_full = ""

                    jd_final = jd_full.strip() if jd_full and len(jd_full.strip()) > 100 else j["desc"][:500]
                    if len(jd_final) > 300:
                        page_jd_ok += 1

                    # 方案二：基于完整 JD 内容判定是否为 IT 岗位
                    if not jd_contains_tech(jd_final):
                        continue

                    page_tech_ok += 1

                    # 创建岗位记录
                    is_ins, ins_score, ins_reasons = is_insurance_sales({
                        "title": j["title"],
                        "company": j["company"],
                        "jd_raw": jd_final,
                        "location": j.get("location", "Hong Kong"),
                        "salary_raw": j.get("salary", ""),
                    })
                    job_entry = {
                        "job_id": f"jobsdb_{keyword_clean.replace(' ','_')}_p{pg}_{len(jobs)}",
                        "title": j["title"],
                        "company": j["company"],
                        "location": j["location"] or "Hong Kong",
                        "salary_raw": j["salary"],
                        "jd_raw": jd_final,
                        "url": j.get("url", ""),
                        "source": "jobsdb",
                        "is_insurance_sales": is_ins,
                        "insurance_score": ins_score,
                    }
                    if is_ins:
                        print(f"        ⚠ 疑似保险销售: 得分={ins_score} {ins_reasons[:2]}")
                    jobs.append(job_entry)

                    await page.wait_for_timeout(500)

                # 打印统计
                if page_card_count > 0:
                    print(f"      卡片={page_card_count} JD完整={page_jd_ok} 收录={page_tech_ok}")

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
        "data analyst", "data engineer",
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
    print("AI/LLM Job Crawler — JobsDB HK")
    print(f"Proxy: {PROXY}")
    print(f"Keywords: {len(IT_KEYWORDS)} IT/tech related terms")
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

        # ===== 加载已有数据 + 进度追踪 =====
        jobsdb_raw_path = RAW_DIR / "jobsdb_raw.json"
        if jobsdb_raw_path.exists():
            existing_data = json.loads(jobsdb_raw_path.read_text(encoding="utf-8"))
            all_jobs = list(existing_data)
            existing_keys = build_existing_keys(existing_data)
            print(f">>> 已有 {len(existing_data)} 条数据，跳过已收集的岗位")
        else:
            all_jobs = []
            existing_keys = set()

        # 进度追踪：跳过已完成的关键词
        progress = load_progress()
        completed_kws = set(progress.get("completed_keywords", []))
        remaining_kws = [kw for kw in IT_KEYWORDS if kw not in completed_kws]
        if completed_kws:
            print(f">>> 进度: {len(completed_kws)}/{len(IT_KEYWORDS)} 个关键词已完成，跳过")
            print(f">>> 剩余 {len(remaining_kws)} 个: {remaining_kws[:3]}{'...' if len(remaining_kws)>3 else ''}")

        total_new = 0
        for kw in IT_KEYWORDS:
            # 跳过已完成的关键词
            if kw in completed_kws:
                print(f"\n>>> 搜索: {kw} — 已完成，跳过")
                continue

            print(f"\n>>> 搜索: {kw}")
            jj = await search_jobsdb(page, kw, max_pages=MAX_PAGES_PER_KW)

            # URL 去重：只保留真正新增的岗位
            jj_new = deduplicate(jj, existing_keys)
            new_count = len(jj_new)
            total_new += new_count

            if jj_new:
                # 将新增岗位的去重键加入 existing_keys，避免下次重复
                for j in jj_new:
                    existing_keys.add(build_dedup_key(j))
                all_jobs.extend(jj_new)
                print(f"    [{kw}] 新增 {new_count} 条 (已跳过 {len(jj) - new_count} 条重复), 总计 {len(all_jobs)} 条")
            else:
                print(f"    [{kw}] 无新增岗位 (全部已存在)")

            # 标记关键词为已完成
            mark_keyword_completed(progress, kw, len(all_jobs))

            # 每个关键词增量存盘
            (RAW_DIR / "jobsdb_raw.json").write_text(
                json.dumps(all_jobs, ensure_ascii=False, indent=2), encoding="utf-8"
            )

            # 存 Cookies
            await ctx.storage_state(path=str(JOBSDB_AUTH_FILE))

        await browser.close()

    print(f"\n{'=' * 60}")
    print(f"Total: {len(all_jobs)} unique IT/tech jobs from JobsDB")
    if total_new > 0:
        print(f"本次新增: {total_new} 条 (跳过 {len(all_jobs) - total_new} 条已有数据)")
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
