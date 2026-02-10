"""
Job discovery from Indeed SERP pages.
Handles SERP navigation, scrolling, bot detection, deduplication, and pagination.
"""

import logging
from typing import List, Set
from playwright.async_api import Page

from scraper.config.settings import settings
from scraper.core.rate_limit import with_retry, serp_limiter
from scraper.adapters.indeed.config import BASE_URL, MAX_PAGES, JOBS_PER_PAGE
from scraper.adapters.indeed.pagination import build_serp_url
from scraper.adapters.indeed.selectors import (
    CAPTCHA_SELECTORS,
    BLOCKING_KEYWORDS,
    JOB_CARDS_CONTAINER_SELECTOR,
)
from scraper.adapters.indeed.extraction.mosaic import extract_mosaic_data
from scraper.adapters.indeed.extraction.dom import extract_jobs_from_dom

logger = logging.getLogger(__name__)


async def detect_bot_challenge(page: Page) -> bool:
    """
    Detect if Indeed is showing captcha or bot detection page.
    More specific checks to avoid false positives.
    """
    try:
        # Check for actual CAPTCHA elements or challenge page indicators
        for selector in CAPTCHA_SELECTORS:
            if await page.locator(selector).count() > 0:
                logger.warning(f"CAPTCHA detected: {selector}")
                return True

        # Check if we're on an error/blocked page (no job listings)
        has_jobs = await page.locator(JOB_CARDS_CONTAINER_SELECTOR).count() > 0
        if not has_jobs:
            html = await page.content()
            # Only flag if we see blocking keywords AND no job cards
            html_lower = html.lower()
            if any(keyword in html_lower for keyword in BLOCKING_KEYWORDS):
                logger.warning("Possible bot challenge page detected")
                return True

        return False
    except Exception as e:
        logger.debug(f"Error in bot detection: {e}")
        return False


async def scroll_to_load_all_jobs(page: Page) -> None:
    """
    Slowly scroll down to the bottom of the page to ensure all job listings are loaded.
    Indeed uses lazy loading, so scrolling triggers loading of additional job cards.
    """
    try:
        logger.info("Starting slow scroll to load all jobs...")

        # Get initial scroll height
        previous_height = await page.evaluate("document.body.scrollHeight")

        # Scroll in steps to simulate human behavior and trigger lazy loading
        scroll_step = 300  # pixels per scroll
        scroll_pause = 0.3  # seconds between scrolls

        current_position = 0
        max_scrolls = 50  # Safety limit to prevent infinite scrolling
        scrolls_done = 0

        while scrolls_done < max_scrolls:
            # Scroll down by scroll_step pixels
            current_position += scroll_step
            await page.evaluate(f"window.scrollTo(0, {current_position})")

            # Wait for content to load
            await page.wait_for_timeout(int(scroll_pause * 1000))

            # Check if we've reached the bottom
            current_height = await page.evaluate("document.body.scrollHeight")
            viewport_bottom = await page.evaluate(
                "window.pageYOffset + window.innerHeight"
            )

            # If we're at the bottom and no new content loaded, we're done
            if viewport_bottom >= current_height - 100:  # 100px threshold
                # Wait a bit to see if more content loads
                await page.wait_for_timeout(1000)
                new_height = await page.evaluate("document.body.scrollHeight")

                if new_height == previous_height:
                    logger.info(f"Reached bottom after {scrolls_done} scrolls")
                    break

                previous_height = new_height

            scrolls_done += 1

        # Scroll back to top to start extraction
        await page.evaluate("window.scrollTo(0, 0)")
        await page.wait_for_timeout(500)

        logger.info("Scrolling complete, all jobs loaded")

    except Exception as e:
        logger.warning(f"Error during scrolling: {e}")
        # Continue anyway - we'll work with whatever loaded


@with_retry()
async def discover_jobs(
    context, query: str, location: str, seen_jks: Set[str]
) -> List[str]:
    """
    Discover job URLs from Indeed SERP with pagination support.
    Extracts from embedded JSON first, falls back to DOM selectors.
    """
    job_urls: List[str] = []
    page_num = 0

    async with serp_limiter:
        page = await context.new_page()
        try:
            while page_num < MAX_PAGES:
                url = build_serp_url(query, location, page_num, JOBS_PER_PAGE)

                logger.info(f"Navigating to SERP page {page_num + 1}: {url}")
                await page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=settings.NAVIGATION_TIMEOUT,
                )

                # Check for bot detection
                if await detect_bot_challenge(page):
                    logger.error(
                        "Bot detection challenge detected. Stopping pagination."
                    )
                    break

                # Scroll to load all jobs before extraction
                await scroll_to_load_all_jobs(page)

                # Try extracting from mosaic JSON first
                job_cards = await extract_mosaic_data(page)
                new_jobs_found = 0

                if job_cards:
                    # Use JSON data
                    for card in job_cards:
                        jk = card.get("jobkey")
                        if jk and jk not in seen_jks:
                            seen_jks.add(jk)
                            job_url = f"{BASE_URL}/viewjob?jk={jk}"
                            job_urls.append(job_url)
                            new_jobs_found += 1
                else:
                    # Fallback to DOM extraction
                    logger.info("Mosaic JSON not found, using DOM fallback")
                    jobs = await extract_jobs_from_dom(page)
                    for job in jobs:
                        jk = job.get("id")
                        if jk and jk not in seen_jks:
                            seen_jks.add(jk)
                            # Use the URL from the card if available
                            job_url = job.get("url", f"{BASE_URL}/viewjob?jk={jk}")
                            job_urls.append(job_url)
                            new_jobs_found += 1

                # Stop pagination if no new jobs found
                if new_jobs_found == 0:
                    logger.info("No new jobs found, stopping pagination")
                    break

                page_num += 1

        except Exception as e:
            logger.error(f"Error discovering jobs: {e}")
            # Don't raise - return partial results
        finally:
            await page.close()

    logger.info(f"Discovery complete: {len(job_urls)} total jobs found")
    return job_urls
