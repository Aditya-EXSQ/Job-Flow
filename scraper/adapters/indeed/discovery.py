"""
Job discovery from Indeed SERP pages.
Handles SERP navigation, scrolling, bot detection, deduplication, and pagination.
"""

import logging
import random
from typing import List, Set
from playwright.async_api import Page

from scraper.config.settings import settings
from scraper.core.rate_limit import with_retry, serp_limiter
from scraper.adapters.indeed.config import BASE_URL, MAX_PAGES, JOBS_PER_PAGE
from scraper.adapters.indeed.pagination import build_serp_url
from scraper.browser.human_input import move_cursor_to_element, human_type
from scraper.adapters.indeed.selectors import (
    CAPTCHA_SELECTORS,
    BLOCKING_KEYWORDS,
    JOB_CARDS_CONTAINER_SELECTOR,
    WHAT_INPUT_SELECTOR,
    WHERE_INPUT_SELECTOR,
    FIND_JOBS_BUTTON_SELECTOR,
)

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
        # RANDOMIZED SCROLLING BEHAVIOR
        current_position = 0
        max_scrolls = 50  # Safety limit to prevent infinite scrolling
        scrolls_done = 0

        while scrolls_done < max_scrolls:
            # Randomize scroll step (between 250 and 550 pixels)
            step = random.randint(250, 550)
            current_position += step

            await page.evaluate(f"window.scrollTo(0, {current_position})")

            # Randomize pause (between 0.4 and 1.2 seconds)
            pause_ms = random.randint(2000, 9200)
            await page.wait_for_timeout(pause_ms)

            # Occasionally scroll up a tiny bit to look human
            if random.random() < 0.2:
                scroll_up = random.randint(50, 150)
                current_position = max(0, current_position - scroll_up)
                await page.evaluate(f"window.scrollTo(0, {current_position})")
                await page.wait_for_timeout(random.randint(200, 500))

            scrolls_done += 1

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
) -> List[dict]:
    """
    Discover jobs from Indeed SERP by clicking on job titles and extracting descriptions.
    Instead of opening multiple tabs, we click each job title and extract the description
    that appears in the right pane.
    """
    jobs_data: List[dict] = []
    page_num = 0

    async with serp_limiter:
        page = await context.new_page()
        try:
            # Navigate to homepage and perform search
            logger.info(f"Navigating to Indeed homepage: {BASE_URL}")
            await page.goto(
                BASE_URL,
                wait_until="domcontentloaded",
                timeout=settings.NAVIGATION_TIMEOUT,
            )

            # Perform search as a human would — cursor + typing
            logger.info(f"Performing search for '{query}' in '{location}'")

            await move_cursor_to_element(page, WHAT_INPUT_SELECTOR)
            await human_type(page, WHAT_INPUT_SELECTOR, query)

            await move_cursor_to_element(page, WHERE_INPUT_SELECTOR)
            await human_type(page, WHERE_INPUT_SELECTOR, location)

            await move_cursor_to_element(page, FIND_JOBS_BUTTON_SELECTOR)

            # Wait for results to load
            try:
                await page.wait_for_selector(
                    JOB_CARDS_CONTAINER_SELECTOR, timeout=settings.NAVIGATION_TIMEOUT
                )
            except Exception:
                logger.warning(
                    "Job cards container not found immediately after search."
                )

            while page_num < MAX_PAGES:
                # If we are past the first page, navigate explicitly
                # For the first page (page_num=0), we are already there from the search
                if page_num > 0:
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

                # Extract job descriptions by clicking on each job title
                new_jobs_found = await extract_jobs_by_clicking(
                    page, seen_jks, jobs_data
                )

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

    logger.info(f"Discovery complete: {len(jobs_data)} total jobs found")
    return jobs_data


async def extract_jobs_by_clicking(
    page: Page, seen_jks: Set[str], jobs_data: List[dict]
) -> int:
    """
    Click on each job title and extract the job description from the right pane.
    Returns the number of new jobs found.
    """
    new_jobs_count = 0

    try:
        # Find all job card elements - we need to get a fresh list each time
        # as clicking can modify the DOM
        job_card_selector = "div.job_seen_beacon"  # Common selector for job cards

        # Get the total count of job cards
        job_cards_count = await page.locator(job_card_selector).count()
        logger.info(f"Found {job_cards_count} job cards on the page")

        # Iterate through each job card by index
        for index in range(job_cards_count):
            try:
                # Re-query the job cards to get fresh elements (DOM may have changed)
                job_cards = page.locator(job_card_selector)
                job_card = job_cards.nth(index)

                # Extract the job key from the job card (data-jk attribute)
                jk = await job_card.get_attribute("data-jk")

                if not jk or jk in seen_jks:
                    logger.debug(f"Skipping job {index}: already seen or no jobkey")
                    continue

                # Find the clickable job title within this card
                # Common selectors for job titles
                title_selectors = [
                    "h2.jobTitle a",
                    "a.jcs-JobTitle",
                    "h2 a[id^='job_']",
                ]

                title_element = None
                for selector in title_selectors:
                    title_locator = job_card.locator(selector)
                    if await title_locator.count() > 0:
                        title_element = title_locator.first
                        break

                if not title_element:
                    logger.warning(f"Could not find title element for job {index}")
                    continue

                # Get the job title text before clicking
                job_title = await title_element.text_content()
                logger.info(
                    f"Clicking on job {index + 1}/{job_cards_count}: {job_title}"
                )

                # Click on the job title
                await title_element.click()

                # Wait for the job description to load in the right pane
                try:
                    await page.wait_for_selector(
                        "#jobDescriptionText", timeout=5000, state="visible"
                    )

                    # Add a small delay for content to fully render
                    await page.wait_for_timeout(random.randint(500, 1000))

                    # Extract the job description
                    description_element = page.locator("#jobDescriptionText")
                    description = await description_element.inner_text()

                    # Store the job data
                    job_data = {
                        "jobkey": jk,
                        "title": job_title.strip() if job_title else "",
                        "description": description.strip() if description else "",
                    }

                    jobs_data.append(job_data)
                    seen_jks.add(jk)
                    new_jobs_count += 1

                    logger.info(f"Successfully extracted job {jk}: {job_title}")

                except Exception as e:
                    logger.warning(f"Failed to extract description for job {jk}: {e}")
                    continue

                # Add a small random delay between clicks to appear more human
                await page.wait_for_timeout(random.randint(300, 800))

            except Exception as e:
                logger.warning(f"Error processing job card {index}: {e}")
                continue

    except Exception as e:
        logger.error(f"Error in extract_jobs_by_clicking: {e}")

    return new_jobs_count
