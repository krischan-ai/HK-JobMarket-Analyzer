"""补充已有岗位的完整 JD — 直接导航到每个岗位详情页提取"""
import asyncio, json
from pathlib import Path
from playwright.async_api import async_playwright

PROXY = "http://127.0.0.1:10808"
RAW_DIR = Path("data/raw")
JOBSDB_AUTH_FILE = Path("data/auth/jobsdb_auth.json")


async def main():
    # 读取已有数据
    jobsdb_raw_path = RAW_DIR / "jobsdb_raw.json"
    if not jobsdb_raw_path.exists():
        print("没有找到数据文件")
        return

    data = json.loads(jobsdb_raw_path.read_text(encoding="utf-8"))
    print(f"总岗位数: {len(data)}")

    # 筛选需要补充 JD 的岗位
    need = [(i, j) for i, j in enumerate(data)
            if j.get("url") and len(j.get("jd_raw", "")) <= 300]
    total_need = len(need)
    print(f"需要补充 JD: {total_need} 个（有 URL 且 JD <= 300 字）")

    if total_need == 0:
        return

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False, channel="chrome",
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled",
                  f"--proxy-server={PROXY}"]
        )
        ctx = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            storage_state=str(JOBSDB_AUTH_FILE) if JOBSDB_AUTH_FILE.exists() else None
        )
        page = await ctx.new_page()

        # 先访问首页确认登录状态
        await page.goto("https://hk.jobsdb.com/", wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(2000)

        success = 0
        for idx, (orig_idx, job) in enumerate(need):
            url = job["url"]
            print(f"\r  [{idx+1}/{total_need}] {job['title'][:35]:35s} | {url[:50]}", end="")

            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(3000)

                jd_text = await page.evaluate("""() => {
                    // 优先从 jobAdDetails 提取
                    const el = document.querySelector('[data-automation="jobAdDetails"]');
                    if (el) {
                        const t = (el.innerText || '').trim();
                        if (t.length > 100) return t;
                    }
                    // 备选: jobDetailsPage
                    const p = document.querySelector('[data-automation="jobDetailsPage"]');
                    if (p) {
                        const t = (p.innerText || '').trim();
                        if (t.length > 100) return t;
                    }
                    // 最后: body 截取
                    const body = document.body.innerText || '';
                    let start = 0;
                    for (const m of ['Quick apply', 'Save\\n', 'Posted']) {
                        const i = body.indexOf(m);
                        if (i >= 0) start = Math.max(start, i + m.length);
                    }
                    let end = body.length;
                    for (const m of ['Job seekers', 'Employers', 'Download our app']) {
                        const i = body.indexOf(m, start);
                        if (i >= 0) end = Math.min(end, i);
                    }
                    return body.slice(start, end).trim();
                }""")

                if jd_text and len(jd_text) > len(job.get("jd_raw", "")):
                    data[orig_idx]["jd_raw"] = jd_text
                    success += 1
                    if len(jd_text) > 300:
                        print(f" ✓ {len(jd_text)}字", end="")
                    else:
                        print(f" ~ {len(jd_text)}字", end="")

            except Exception as e:
                print(f" ✗ {type(e).__name__}", end="")

            await page.wait_for_timeout(1000)

            # 每 20 条存盘一次
            if (idx + 1) % 20 == 0:
                jobsdb_raw_path.write_text(
                    json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
                # 存 cookies
                await ctx.storage_state(path=str(JOBSDB_AUTH_FILE))

        # 最终存盘
        jobsdb_raw_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        await ctx.storage_state(path=str(JOBSDB_AUTH_FILE))

        await browser.close()

    print(f"\n\n完成: {success}/{total_need} 条 JD 已补充")

    # 统计
    lens = [len(j.get("jd_raw", "")) for j in data]
    print(f"JD > 300字: {sum(1 for l in lens if l > 300)}/{len(data)}")
    print(f"JD > 1000字: {sum(1 for l in lens if l > 1000)}/{len(data)}")


if __name__ == "__main__":
    asyncio.run(main())
