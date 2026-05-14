"""Agent 2: Job Search Agent — scrapes Naukri.com for matching jobs."""
import asyncio
import nest_asyncio
from playwright.async_api import async_playwright
from loguru import logger
from typing import List, Dict
from config.settings import settings

# Allow asyncio.run() inside already-running event loops (e.g. FastAPI, Jupyter)
nest_asyncio.apply()

NAUKRI_BASE = "https://www.naukri.com"


async def _fetch_job_description(page, url: str) -> str:
    """Fetch a single job's description page."""
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=20000)
        for selector in [".job-desc", ".jd-desc", ".description__Content", "[class*='description']"]:
            el = await page.query_selector(selector)
            if el:
                text = await el.inner_text()
                return text[:3000]
    except Exception as e:
        logger.warning(f"Could not fetch JD from {url}: {e}")
    return ""


async def scrape_naukri_jobs(
    keywords: List[str],
    locations: List[str],
    experience_min: int = 0,
    experience_max: int = 10,
    max_jobs: int = 50,
    headless: bool = True,
) -> List[Dict]:
    """Scrape Naukri search results using Playwright. Returns deduplicated job list."""
    jobs: Dict[str, Dict] = {}  # keyed by job_id to deduplicate

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 900},
        )
        page = await context.new_page()
        detail_page = await context.new_page()

        for keyword in keywords:
            for location in locations:
                if len(jobs) >= max_jobs:
                    break

                search_url = (
                    f"{NAUKRI_BASE}/{keyword.lower().replace(' ', '-')}-jobs"
                    f"?k={keyword.replace(' ', '%20')}"
                    f"&l={location.replace(' ', '%20')}"
                    f"&experience={experience_min}"
                )
                logger.info(f"Searching Naukri: keyword='{keyword}' location='{location}'")

                try:
                    await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
                    await page.wait_for_selector(".srp-jobtuple-wrapper", timeout=15000)
                except Exception as e:
                    logger.warning(f"Search page load failed for '{keyword}' in '{location}': {e}")
                    continue

                job_cards = await page.query_selector_all(".srp-jobtuple-wrapper")
                logger.info(f"Found {len(job_cards)} job cards")

                for card in job_cards:
                    if len(jobs) >= max_jobs:
                        break
                    try:
                        title_el = await card.query_selector(".title")
                        company_el = await card.query_selector(".comp-name")
                        exp_el = await card.query_selector(".expwdth")
                        loc_el = await card.query_selector(".locWdth")
                        salary_el = await card.query_selector(".sal")
                        link_el = await card.query_selector("a.title")
                        job_id = await card.get_attribute("data-job-id")

                        title = (await title_el.inner_text()).strip() if title_el else ""
                        company = (await company_el.inner_text()).strip() if company_el else ""
                        exp = (await exp_el.inner_text()).strip() if exp_el else ""
                        loc = (await loc_el.inner_text()).strip() if loc_el else ""
                        salary = (await salary_el.inner_text()).strip() if salary_el else "Not disclosed"
                        link = await link_el.get_attribute("href") if link_el else ""

                        if not title or not company:
                            continue

                        if not link:
                            continue
                        if not link.startswith("http"):
                            link = NAUKRI_BASE + link

                        # Use job_id from data attr; fallback to URL hash
                        if not job_id:
                            job_id = f"naukri_{abs(hash(link))}"

                        if job_id in jobs:
                            continue  # deduplicate

                        jobs[job_id] = {
                            "job_id": job_id,
                            "job_title": title,
                            "company": company,
                            "location": loc,
                            "experience_required": exp,
                            "salary": salary,
                            "job_url": link,
                            "job_description": "",
                            "search_keyword": keyword,
                            "search_location": location,
                        }
                    except Exception as e:
                        logger.warning(f"Error parsing job card: {e}")

        # Fetch JDs in a second pass
        job_list = list(jobs.values())
        logger.info(f"Fetching job descriptions for {len(job_list)} jobs...")
        for job in job_list:
            if job["job_url"]:
                job["job_description"] = await _fetch_job_description(detail_page, job["job_url"])

        await browser.close()

    return job_list


def search_jobs(
    keywords: List[str],
    locations: List[str],
    experience_min: int,
    experience_max: int,
    max_jobs: int,
    headless: bool,
) -> List[Dict]:
    """Synchronous wrapper — safe to call from any context including FastAPI."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Already inside an event loop (FastAPI) — use nest_asyncio
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(
                    asyncio.run,
                    scrape_naukri_jobs(keywords, locations, experience_min, experience_max, max_jobs, headless),
                )
                return future.result(timeout=300)
        else:
            return loop.run_until_complete(
                scrape_naukri_jobs(keywords, locations, experience_min, experience_max, max_jobs, headless)
            )
    except Exception as e:
        logger.error(f"Job search failed: {e}")
        return []
