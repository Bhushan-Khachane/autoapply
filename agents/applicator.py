"""Agent 5: Application Agent — auto-applies to jobs on Naukri using Playwright."""
import asyncio
from playwright.async_api import async_playwright
from loguru import logger
from typing import Dict
from config.settings import settings


async def login_naukri(page, email: str, password: str) -> bool:
    """Log in to Naukri.com."""
    try:
        await page.goto("https://www.naukri.com/nlogin/login", wait_until="networkidle", timeout=20000)
        await page.fill("#usernameField", email)
        await page.fill("#passwordField", password)
        await page.click(".loginButton")
        await page.wait_for_load_state("networkidle", timeout=15000)
        # Check if login succeeded
        if "nlogin" not in page.url:
            logger.info("Naukri login successful")
            return True
        logger.error("Naukri login failed — check credentials")
        return False
    except Exception as e:
        logger.error(f"Login error: {e}")
        return False


async def apply_to_job(page, job: dict, cover_letter: str = "") -> bool:
    """Navigate to job page and click Apply."""
    try:
        await page.goto(job["job_url"], wait_until="networkidle", timeout=20000)
        # Try to find the Apply button
        apply_btn = await page.query_selector(".apply-button") or await page.query_selector("#apply-button")
        if not apply_btn:
            # Try alternate selectors
            apply_btn = await page.query_selector("[data-ga-track='Apply']")
        if not apply_btn:
            logger.warning(f"No apply button found for: {job['job_title']}")
            return False

        await apply_btn.click()
        await page.wait_for_load_state("networkidle", timeout=10000)

        # Handle cover letter modal if present
        cover_letter_field = await page.query_selector("textarea[name='coverLetter']")
        if cover_letter_field and cover_letter:
            await cover_letter_field.fill(cover_letter[:1000])

        # Submit the application
        submit_btn = await page.query_selector(".submit-btn") or await page.query_selector("#submit-button")
        if submit_btn:
            await submit_btn.click()
            await page.wait_for_load_state("networkidle", timeout=10000)

        logger.info(f"✅ Applied to: {job['job_title']} @ {job['company']}")
        return True

    except Exception as e:
        logger.error(f"Application error for {job.get('job_title')}: {e}")
        return False


def apply_to_jobs(jobs: list, cover_letters: dict, headless: bool = True) -> dict:
    """Apply to a list of jobs. Returns results dict {job_id: success}."""
    return asyncio.run(_apply_all(jobs, cover_letters, headless))


async def _apply_all(jobs: list, cover_letters: dict, headless: bool) -> dict:
    results = {}
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context()
        page = await context.new_page()

        logged_in = await login_naukri(page, settings.naukri_email, settings.naukri_password)
        if not logged_in:
            await browser.close()
            return {j["job_id"]: False for j in jobs}

        for job in jobs:
            cover_letter = cover_letters.get(job["job_id"], "")
            success = await apply_to_job(page, job, cover_letter)
            results[job["job_id"]] = success

        await browser.close()
    return results
