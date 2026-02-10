"""
Job detail page scraping orchestration.
Handles navigating to individual job pages and extracting structured data.
"""

import logging
import urllib.parse
from typing import List, Optional
from playwright.async_api import Page

from scraper.config.settings import settings
from scraper.core.models import Job
from scraper.core.rate_limit import with_retry, page_limiter
from scraper.adapters.indeed.config import BASE_URL
from scraper.adapters.indeed.selectors import DESCRIPTION_SELECTOR_ALT
from scraper.adapters.indeed.extraction.json_ld import (
    extract_json_ld,
    extract_title,
    extract_company,
    extract_location,
    extract_description,
)
from scraper.adapters.indeed.extraction.salary import extract_salary
from scraper.adapters.indeed.discovery import (
    detect_bot_challenge,
    scroll_to_load_all_jobs,
)

logger = logging.getLogger(__name__)


async def extract_job_from_page(page: Page, url: str) -> Optional[Job]:
    """
    Extract job data from an already-loaded job detail page.
    Uses #jobDescriptionText as the primary selector.

    Args:
        page: Already navigated page object
        url: Job URL for reference

    Returns:
        Job object or None if extraction fails
    """
    try:
        # Extract job ID from URL
        parsed_url = urllib.parse.urlparse(url)
        qs = urllib.parse.parse_qs(parsed_url.query)
        job_id = qs.get("jk", ["unknown"])[0]

        # Try JSON-LD extraction first (best source of structured data)
        json_ld = await extract_json_ld(page)

        # Extract core fields
        title = await extract_title(page, json_ld)
        company = await extract_company(page, json_ld)
        location = await extract_location(page, json_ld)
        salary = await extract_salary(page, json_ld)

        # Extract description using #jobDescriptionText selector
        description = ""
        try:
            desc_element = page.locator(DESCRIPTION_SELECTOR_ALT)
            if await desc_element.count() > 0:
                description = await desc_element.inner_text()
                logger.debug(f"Extracted description ({len(description)} chars)")
            else:
                # Fallback to JSON-LD
                if json_ld and "description" in json_ld:
                    description = json_ld["description"]
                    logger.debug("Used JSON-LD description")
        except Exception as e:
            logger.warning(f"Failed to extract description: {e}")

        # Extract posted date from JSON-LD if available
        posted_at = None
        if json_ld and "datePosted" in json_ld:
            posted_at = json_ld["datePosted"]

        # Validate required fields
        if title.startswith("Unknown") or job_id == "unknown":
            logger.warning(f"Missing critical fields for {url}")
            return None

        job = Job(
            id=job_id,
            title=title,
            company=company,
            location=location,
            description=description,
            source="indeed",
            url=url,
            salary=salary,
            posted_at=posted_at,
        )

        return job

    except Exception as e:
        logger.error(f"Error extracting job from page: {e}")
        return None


async def scrape_jobs_batch(
    context, job_urls: List[str], max_concurrent: int = 5
) -> List[Job]:
    """
    Scrape multiple jobs concurrently using a batch/queue approach.
    Opens up to max_concurrent tabs at a time to avoid overwhelming the browser.

    Args:
        context: Browser context
        job_urls: List of job URLs to scrape
        max_concurrent: Maximum number of concurrent tabs (default 5)

    Returns:
        List of successfully scraped Job objects
    """
    # Force concurrency to 1 if using ScrapeOps to avoid hitting plan limits
    if settings.SCRAPEOPS_API_KEY and max_concurrent > 1:
        logger.info(
            "ScrapeOps proxy detected: Forcing max_concurrent to 1 to respect rate limits"
        )
        max_concurrent = 1

    jobs: List[Job] = []
    total = len(job_urls)

    logger.info(
        f"Starting batch scraping of {total} jobs with max {max_concurrent} concurrent tabs"
    )

    # Process in batches
    for batch_start in range(0, total, max_concurrent):
        batch_end = min(batch_start + max_concurrent, total)
        batch_urls = job_urls[batch_start:batch_end]
        batch_num = (batch_start // max_concurrent) + 1
        total_batches = (total + max_concurrent - 1) // max_concurrent

        logger.info(
            f"Processing batch {batch_num}/{total_batches} ({len(batch_urls)} jobs)"
        )

        # Open all tabs in this batch
        pages_and_urls = []
        for url in batch_urls:
            try:
                page = await context.new_page()
                pages_and_urls.append((page, url))
            except Exception as e:
                logger.error(f"Failed to open tab for {url}: {e}")

        # Navigate all tabs
        for page, url in pages_and_urls:
            try:
                logger.info(f"Loading: {url}")
                await page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=settings.NAVIGATION_TIMEOUT,
                )
                await page.wait_for_timeout(1000)  # Let page settle

                # Scroll to bottom to ensure full content loading (user requested)
                await scroll_to_load_all_jobs(page)
            except Exception as e:
                logger.error(f"Failed to navigate to {url}: {e}")

        # Extract data from all tabs
        for page, url in pages_and_urls:
            try:
                # Check for bot detection
                if await detect_bot_challenge(page):
                    logger.warning(f"Bot challenge detected for {url}")
                    await page.close()
                    continue

                # Extract job data using simplified approach
                job = await extract_job_from_page(page, url)
                if job:
                    jobs.append(job)
                    logger.info(f"✓ Scraped: {job.title} at {job.company}")

            except Exception as e:
                logger.error(f"Failed to extract job from {url}: {e}")
            finally:
                await page.close()

        logger.info(
            f"Batch {batch_num}/{total_batches} complete. Total scraped: {len(jobs)}"
        )

    logger.info(
        f"Batch scraping complete: {len(jobs)}/{total} jobs successfully scraped"
    )
    return jobs


@with_retry()
async def scrape_job(context, url: str) -> Job:
    """
    Scrape job details using JSON-LD first, CSS selectors as fallback.
    Never crashes - returns partial data with warnings.
    """
    async with page_limiter:
        page = await context.new_page()
        try:
            logger.info(f"Scraping job: {url}")
            await page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=settings.NAVIGATION_TIMEOUT,
            )

            # Check for bot detection
            if await detect_bot_challenge(page):
                logger.error(f"Bot challenge detected for {url}")
                raise Exception("Bot detection triggered")

            # Try JSON-LD extraction first
            json_ld = await extract_json_ld(page)
            if json_ld:
                logger.info("Successfully extracted JSON-LD data")

            # Extract all fields with fallbacks
            title = await extract_title(page, json_ld)
            company = await extract_company(page, json_ld)
            location = await extract_location(page, json_ld)
            description = await extract_description(page, json_ld)
            salary = await extract_salary(page, json_ld)

            # Extract posted date from JSON-LD if available
            posted_at = None
            if json_ld and "datePosted" in json_ld:
                posted_at = json_ld["datePosted"]

            # Extract job ID from URL
            parsed_url = urllib.parse.urlparse(url)
            qs = urllib.parse.parse_qs(parsed_url.query)
            job_id = qs.get("jk", ["unknown"])[0]

            # Skip if critical fields are missing
            if title.startswith("Unknown") or job_id == "unknown":
                logger.warning(f"Skipping job {url}: missing critical fields")
                raise Exception("Missing critical job fields")

            job = Job(
                id=job_id,
                title=title,
                company=company,
                location=location,
                description=description,
                source="indeed",
                url=url,
                salary=salary,
                posted_at=posted_at,
            )

            return job

        except Exception as e:
            logger.error(f"Error scraping job {url}: {e}")
            raise
        finally:
            await page.close()
