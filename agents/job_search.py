"""Agent 2: Job Search Agent — scrapes Naukri.com for matching jobs."""
import asyncio
from playwright.async_api import async_playwright
from praisonaiagents import Agent
from loguru import logger
from typing import List, Dict
from tenacity import retry, stop_after_attempt, wait_fixed
from config.settings import settings


NAUKRI_BASE = "https://www.naukri.com"


async def scrape_naukri_jobs(
    keywords: List[str],
    location: str,
    experience_min: int = 0,
    experience_max: int = 10,
    max_jobs: int = 50,
    headless: bool = True,
) -> List[Dict]:
    """Scrape Naukri search results using Playwright."""
    jobs = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = await context.new_page()

        for keyword in keywords:
            if len(jobs) >= max_jobs:
                break
            search_url = (
                f"{NAUKRI_BASE}/{keyword.lower().replace(' ', '-')}-jobs"
                f"?k={keyword.replace(' ', '%20')}"
                f"&l={location.replace(' ', '%20')}"
                f"&experience={experience_min}"
            )
            logger.info(f"Searching: {search_url}")

            try:
                await page.goto(search_url, wait_until="networkidle", timeout=30000)
                await page.wait_for_selector(".srp-jobtuple-wrapper", timeout=15000)

                job_cards = await page.query_selector_all(".srp-jobtuple-wrapper")
                for card in job_cards[:max_jobs]:
                    try:
                        title_el = await card.query_selector(".title")
                        company_el = await card.query_selector(".comp-name")
                        exp_el = await card.query_selector(".expwdth")
                        loc_el = await card.query_selector(".locWdth")
                        salary_el = await card.query_selector(".sal")
                        link_el = await card.query_selector("a.title")
                        job_id_el = await card.get_attribute("data-job-id")

                        title = await title_el.inner_text() if title_el else ""
                        company = await company_el.inner_text() if company_el else ""
                        exp = await exp_el.inner_text() if exp_el else ""
                        loc = await loc_el.inner_text() if loc_el else ""
                        salary = await salary_el.inner_text() if salary_el else "Not disclosed"
                        link = await link_el.get_attribute("href") if link_el else ""

                        if title and company:
                            jobs.append({
                                "job_id": job_id_el or f"{keyword}_{len(jobs)}",
                                "job_title": title.strip(),
                                "company": company.strip(),
                                "location": loc.strip(),
                                "experience_required": exp.strip(),
                                "salary": salary.strip(),
                                "job_url": link if link.startswith("http") else NAUKRI_BASE + link,
                                "job_description": "",  # fetched in detail step
                                "keyword": keyword,
                            })
                    except Exception as e:
                        logger.warning(f"Error parsing job card: {e}")
            except Exception as e:
                logger.error(f"Error scraping keyword '{keyword}': {e}")

        # Fetch job descriptions for each job
        for job in jobs:
            if not job["job_url"]:
                continue
            try:
                await page.goto(job["job_url"], wait_until="networkidle", timeout=20000)
                desc_el = await page.query_selector(".job-desc")
                if not desc_el:
                    desc_el = await page.query_selector(".jd-desc")
                if desc_el:
                    job["job_description"] = (await desc_el.inner_text())[:3000]
            except Exception as e:
                logger.warning(f"Could not fetch JD for {job['job_title']}: {e}")

        await browser.close()
    return jobs


def search_jobs(keywords: List[str], location: str, experience_min: int, experience_max: int, max_jobs: int, headless: bool) -> List[Dict]:
    """Sync wrapper for async scraper."""
    return asyncio.run(scrape_naukri_jobs(keywords, location, experience_min, experience_max, max_jobs, headless))
