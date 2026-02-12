"""
CSS selector-based extraction of job cards from Indeed SERP DOM.
Fallback when mosaic JSON extraction fails.
"""

import logging
from typing import List, Dict
from playwright.async_api import Page

from scraper.adapters.indeed.config import BASE_URL
from scraper.adapters.indeed.selectors import (
    SERP_CARD_SELECTORS,
    JOB_LINK_SELECTOR,
    JOB_TITLE_SPAN_SELECTOR,
    COMPANY_NAME_SELECTOR,
    LOCATION_SELECTOR,
)

logger = logging.getLogger(__name__)


async def extract_jobs_from_dom(page: Page) -> List[Dict[str, str]]:
    """
    Fallback: Extract job data from DOM using stable selectors.
    Returns list of job dictionaries with id, title, company, location, url.
    Based on actual Indeed HTML structure: #mosaic-provider-jobcards > div > ul > li
    """
    jobs = []
    try:
        # Try user-provided specific path first (slider items), then generic list items
        # User path: #mosaic-provider-jobcards ... div.slider_item ...
        job_cards = []
        for selector in SERP_CARD_SELECTORS:
            cards = await page.locator(selector).all()
            if cards:
                logger.info(f"Found {len(cards)} job cards using selector: {selector}")
                job_cards = cards
                break

        if not job_cards:
            logger.warning("No job cards found with any selector")
            return []

        for card in job_cards:
            try:
                job_data = {}

                # Extract job link with data-jk attribute (contains job ID)
                # Use .first to find it anywhere within the card container
                link = card.locator(JOB_LINK_SELECTOR).first
                if await link.count() == 0:
                    continue

                # Job ID from data-jk attribute
                job_id = await link.get_attribute("data-jk")
                if not job_id:
                    continue
                job_data["id"] = job_id

                # Job URL from href
                href = await link.get_attribute("href")
                if href:
                    # Indeed URLs can be relative, make absolute
                    if href.startswith("/"):
                        job_data["url"] = f"{BASE_URL}{href}"
                    else:
                        job_data["url"] = href
                else:
                    # job_data["url"] = f"{BASE_URL}/viewjob?jk={job_id}"
                    job_data["url"] = f"{BASE_URL}/viewjob?jk={job_id}&from=shareddesktop_copy"

                # Job Title from span with title attribute or link text
                title_span = card.locator(JOB_TITLE_SPAN_SELECTOR).first
                if await title_span.count() > 0:
                    title = await title_span.get_attribute("title")
                    job_data["title"] = title if title else await link.inner_text()
                else:
                    job_data["title"] = await link.inner_text()

                # Company name from data-testid="company-name"
                company_elem = card.locator(COMPANY_NAME_SELECTOR).first
                if await company_elem.count() > 0:
                    job_data["company"] = await company_elem.inner_text()

                # Location from data-testid="text-location"
                location_elem = card.locator(LOCATION_SELECTOR).first
                if await location_elem.count() > 0:
                    job_data["location"] = await location_elem.inner_text()

                jobs.append(job_data)

            except Exception as e:
                logger.debug(f"Failed to extract job card: {e}")
                continue

        logger.info(f"Successfully extracted {len(jobs)} jobs from DOM")
    except Exception as e:
        logger.warning(f"Failed to extract jobs from DOM: {e}")

    return jobs
