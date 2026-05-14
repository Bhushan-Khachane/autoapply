"""Agent 5: Application Agent — auto-applies to jobs on Naukri using Playwright."""
import asyncio
import nest_asyncio
from playwright.async_api import async_playwright, Page
from loguru import logger
from typing import Dict, List
from config.settings import settings
import concurrent.futures

nest_asyncio.apply()


async def _login_naukri(page: Page, email: str, password: str) -> bool:
    """Log in to Naukri.com. Returns True on success."""
    try:
        await page.goto("https://www.naukri.com/nlogin/login", wait_until="domcontentloaded", timeout=20000)
        await page.wait_for_selector("#usernameField", timeout=10000)
        await page.fill("#usernameField", email)
        await page.fill("#passwordField", password)
        await page.click(".loginButton")
        await page.wait_for_load_state("networkidle", timeout=15000)
        if "nlogin" not in page.url:
            logger.info("Naukri login successful")
            return True
        logger.error("Naukri login failed — check NAUKRI_EMAIL and NAUKRI_PASSWORD in .env")
        return False
    except Exception as e:
        logger.error(f"Login error: {e}")
        return False


async def _find_element(page: Page, *selectors: str):
    """Try multiple CSS selectors; return the first element found or None."""
    for selector in selectors:
        el = await page.query_selector(selector)
        if el:
            return el
    return None


async def _apply_to_job(page: Page, job: dict, cover_letter: str = "") -> bool:
    """Navigate to job page and click Apply. Returns True on success."""
    try:
        await page.goto(job["job_url"], wait_until="domcontentloaded", timeout=20000)

        apply_btn = await _find_element(
            page,
            ".apply-button",
            "#apply-button",
            "[data-ga-track='Apply']",
            ".applyBtn",
            "button[contains(text(), 'Apply')]",
        )
        if not apply_btn:
            logger.warning(f"No apply button found: {job['job_title']} @ {job['company']}")
            return False

        await apply_btn.click()
        await page.wait_for_load_state("domcontentloaded", timeout=10000)

        # Fill cover letter if modal/field appears
        if cover_letter:
            cl_field = await _find_element(
                page,
                "textarea[name='coverLetter']",
                "#coverLetter",
                "textarea[placeholder*='cover']",
            )
            if cl_field:
                await cl_field.fill(cover_letter[:1000])

        # Submit
        submit_btn = await _find_element(page, ".submit-btn", "#submit-button", "button[type='submit']")
        if submit_btn:
            await submit_btn.click()
            await page.wait_for_load_state("domcontentloaded", timeout=10000)

        logger.info(f"✅ Applied: {job['job_title']} @ {job['company']} (score={job.get('score', 'N/A')})")
        return True

    except Exception as e:
        logger.error(f"Application failed for '{job.get('job_title')}': {e}")
        return False


async def _apply_all_async(jobs: List[dict], cover_letters: Dict[str, str], headless: bool) -> Dict[str, bool]:
    results: Dict[str, bool] = {}
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        )
        page = await context.new_page()

        logged_in = await _login_naukri(page, settings.naukri_email, settings.naukri_password)
        if not logged_in:
            await browser.close()
            return {j["job_id"]: False for j in jobs}

        for job in jobs:
            cover_letter = cover_letters.get(job["job_id"], "")
            success = await _apply_to_job(page, job, cover_letter)
            results[job["job_id"]] = success

        await browser.close()
    return results


def apply_to_jobs(jobs: List[dict], cover_letters: Dict[str, str], headless: bool = True) -> Dict[str, bool]:
    """Synchronous entry point — safe to call from any context."""
    if not jobs:
        return {}
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, _apply_all_async(jobs, cover_letters, headless))
                return future.result(timeout=600)
        else:
            return loop.run_until_complete(_apply_all_async(jobs, cover_letters, headless))
    except Exception as e:
        logger.error(f"apply_to_jobs failed: {e}")
        return {j["job_id"]: False for j in jobs}
